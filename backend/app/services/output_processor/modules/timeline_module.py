"""
Timeline Module - Career Trajectory Visualization

Generates chronological career timelines for candidates,
showing career progression and transitions.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TimelineEntry:
    """A single entry in the career timeline."""
    year_start: int
    year_end: Optional[int]  # None = Present
    title: str
    company: str
    is_current: bool = False
    duration_years: float = 0.0
    transition_type: str = ""  # "promotion", "lateral", "company_change", "career_pivot"


@dataclass
class CandidateTimeline:
    """Complete timeline for a single candidate."""
    candidate_name: str
    cv_id: str
    entries: List[TimelineEntry] = field(default_factory=list)
    career_span_years: float = 0.0
    total_companies: int = 0
    progression_score: float = 0.0  # 0-100, higher = better progression
    current_role: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_name": self.candidate_name,
            "cv_id": self.cv_id,
            "entries": [
                {
                    "year_start": e.year_start,
                    "year_end": e.year_end,
                    "title": e.title,
                    "company": e.company,
                    "is_current": e.is_current,
                    "duration_years": e.duration_years,
                    "transition_type": e.transition_type
                }
                for e in self.entries
            ],
            "career_span_years": self.career_span_years,
            "total_companies": self.total_companies,
            "progression_score": self.progression_score,
            "current_role": self.current_role
        }


@dataclass
class TimelineData:
    """Timeline data for multiple candidates."""
    timelines: List[CandidateTimeline] = field(default_factory=list)
    summary: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timelines": [t.to_dict() for t in self.timelines],
            "summary": self.summary
        }


class TimelineModule:
    """
    Generates career timelines from CV data.
    
    Features:
    - Chronological career visualization
    - Transition type detection (promotion, lateral, pivot)
    - Progression scoring
    - Multi-candidate comparison
    """
    
    # Seniority levels for progression detection
    SENIORITY_ORDER = {
        "intern": 1, "trainee": 1, "graduate": 1,
        "junior": 2, "associate": 2,
        "mid": 3, "regular": 3,
        "senior": 4, "sr": 4,
        "lead": 5, "principal": 5, "staff": 5,
        "manager": 6, "head": 6,
        "director": 7, "vp": 7,
        "executive": 8, "cto": 8, "ceo": 8, "coo": 8, "cfo": 8
    }
    
    def extract(
        self,
        chunks: List[Dict[str, Any]],
        llm_output: str = ""
    ) -> Optional[TimelineData]:
        """
        Extract timeline data from CV chunks.
        
        Args:
            chunks: Retrieved CV chunks with enriched metadata
            llm_output: Optional LLM response for additional context
            
        Returns:
            TimelineData or None if no timeline can be built
        """
        if not chunks:
            return None
        
        timelines = []
        
        # Group chunks by candidate
        candidate_chunks = self._group_by_candidate(chunks)
        
        for candidate, cand_chunks in candidate_chunks.items():
            timeline = self._build_candidate_timeline(candidate, cand_chunks)
            if timeline and timeline.entries:
                timelines.append(timeline)
        
        if not timelines:
            logger.debug("[TIMELINE] No valid timelines could be built")
            return None
        
        # Generate summary
        summary = self._generate_summary(timelines)
        
        logger.info(f"[TIMELINE] Built timelines for {len(timelines)} candidates")
        
        return TimelineData(
            timelines=timelines,
            summary=summary
        )
    
    def _group_by_candidate(
        self,
        chunks: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group chunks by candidate name."""
        grouped = {}
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            candidate = meta.get("candidate_name", "Unknown")
            if candidate and candidate != "Unknown":
                if candidate not in grouped:
                    grouped[candidate] = []
                grouped[candidate].append(chunk)
        return grouped
    
    def _build_candidate_timeline(
        self,
        candidate: str,
        chunks: List[Dict[str, Any]]
    ) -> Optional[CandidateTimeline]:
        """Build timeline for a single candidate."""
        entries = []
        cv_id = ""
        current_role = None
        companies = set()
        
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            
            if not cv_id:
                cv_id = meta.get("cv_id", "")
            
            # Extract position data from enriched metadata
            start_year = meta.get("start_year")
            end_year = meta.get("end_year")
            job_title = meta.get("job_title", "")
            company = meta.get("company", "")
            is_current = meta.get("is_current", False)
            duration = meta.get("duration_years", 0)
            
            if start_year and job_title:
                entry = TimelineEntry(
                    year_start=int(start_year),
                    year_end=int(end_year) if end_year else None,
                    title=job_title,
                    company=company,
                    is_current=is_current,
                    duration_years=duration
                )
                entries.append(entry)
                
                if company and company != "Unknown Company":
                    companies.add(company)
                
                if is_current:
                    current_role = job_title
        
        # Also try to extract from summary chunk if no entries yet
        if not entries:
            entries = self._extract_from_summary(chunks)
        
        if not entries:
            return None
        
        # Sort by start year (oldest first for timeline display)
        entries.sort(key=lambda e: e.year_start)
        
        # Remove duplicates
        entries = self._deduplicate_entries(entries)
        
        # Detect transition types
        self._detect_transitions(entries)
        
        # Calculate career span
        if entries:
            earliest = min(e.year_start for e in entries)
            from datetime import datetime
            latest = max(e.year_end or datetime.now().year for e in entries)
            career_span = latest - earliest
        else:
            career_span = 0
        
        # Calculate progression score
        progression_score = self._calculate_progression_score(entries)
        
        return CandidateTimeline(
            candidate_name=candidate,
            cv_id=cv_id,
            entries=entries,
            career_span_years=career_span,
            total_companies=len(companies),
            progression_score=progression_score,
            current_role=current_role
        )
    
    def _extract_from_summary(
        self,
        chunks: List[Dict[str, Any]]
    ) -> List[TimelineEntry]:
        """Extract timeline entries from summary or content."""
        entries = []
        
        for chunk in chunks:
            content = chunk.get("content", "")
            chunk.get("metadata", {})
            
            # Look for "Career Path:" line in summary
            career_match = re.search(r"Career Path:\s*(.+)", content)
            if career_match:
                path = career_match.group(1)
                # Parse format: "Title (Year) → Title (Year)"
                positions = re.findall(r"([^→]+)\s*\((\d{4})\)", path)
                for i, (title, year) in enumerate(positions):
                    entries.append(TimelineEntry(
                        year_start=int(year),
                        year_end=None if i == len(positions) - 1 else None,
                        title=title.strip(),
                        company="",
                        is_current=(i == len(positions) - 1)
                    ))
        
        return entries
    
    def _deduplicate_entries(
        self,
        entries: List[TimelineEntry]
    ) -> List[TimelineEntry]:
        """Remove duplicate entries."""
        seen = set()
        unique = []
        
        for entry in entries:
            key = (entry.year_start, entry.title.lower()[:30])
            if key not in seen:
                seen.add(key)
                unique.append(entry)
        
        return unique
    
    def _detect_transitions(self, entries: List[TimelineEntry]) -> None:
        """Detect transition types between positions."""
        for i in range(1, len(entries)):
            prev = entries[i - 1]
            curr = entries[i]
            
            prev_seniority = self._get_seniority_level(prev.title)
            curr_seniority = self._get_seniority_level(curr.title)
            
            same_company = prev.company.lower() == curr.company.lower() if prev.company and curr.company else False
            
            if curr_seniority > prev_seniority:
                curr.transition_type = "promotion"
            elif same_company and curr_seniority == prev_seniority:
                curr.transition_type = "lateral"
            elif not same_company:
                curr.transition_type = "company_change"
            else:
                curr.transition_type = ""
    
    def _get_seniority_level(self, title: str) -> int:
        """Get seniority level from job title."""
        title_lower = title.lower()
        
        for keyword, level in self.SENIORITY_ORDER.items():
            if keyword in title_lower:
                return level
        
        return 3  # Default to mid-level
    
    def _calculate_progression_score(self, entries: List[TimelineEntry]) -> float:
        """
        Calculate career progression score (0-100).
        
        Higher score = better upward progression.
        """
        if len(entries) < 2:
            return 50.0  # Neutral for single position
        
        # Calculate progression
        promotions = sum(1 for e in entries if e.transition_type == "promotion")
        laterals = sum(1 for e in entries if e.transition_type == "lateral")
        total_transitions = len(entries) - 1
        
        if total_transitions == 0:
            return 50.0
        
        # Score: 100 * (promotions / total) + 50 * (laterals / total)
        score = (promotions / total_transitions) * 100 + (laterals / total_transitions) * 25
        
        # Bonus for reaching senior levels
        max_level = max(self._get_seniority_level(e.title) for e in entries)
        if max_level >= 6:  # Manager+
            score += 20
        elif max_level >= 4:  # Senior+
            score += 10
        
        return min(100.0, score)
    
    def _generate_summary(self, timelines: List[CandidateTimeline]) -> str:
        """Generate summary of all timelines."""
        if not timelines:
            return ""
        
        parts = []
        
        # Longest career
        longest = max(timelines, key=lambda t: t.career_span_years)
        if longest.career_span_years > 0:
            parts.append(f"Longest career: {longest.candidate_name} ({longest.career_span_years:.0f} years)")
        
        # Best progression
        best_prog = max(timelines, key=lambda t: t.progression_score)
        if best_prog.progression_score >= 70:
            parts.append(f"Best progression: {best_prog.candidate_name}")
        
        # Current roles summary
        current_roles = [t for t in timelines if t.current_role]
        if current_roles:
            parts.append(f"{len(current_roles)} candidate(s) currently employed")
        
        return " | ".join(parts) if parts else ""
    
    def format(self, data: TimelineData) -> str:
        """
        Format timeline data for display.
        
        Args:
            data: TimelineData to format
            
        Returns:
            Formatted markdown string
        """
        if not data or not data.timelines:
            return ""
        
        parts = ["### Career Timelines\n"]
        
        # Summary
        if data.summary:
            parts.append(f"{data.summary}\n")
        
        # Individual timelines
        for timeline in data.timelines[:5]:  # Limit to 5 candidates
            parts.append(f"\n**{timeline.candidate_name}** ({timeline.career_span_years:.0f}y career)")
            
            if timeline.entries:
                # Visual timeline
                for entry in timeline.entries[-5:]:  # Last 5 positions
                    end_str = "Present" if entry.is_current else str(entry.year_end or "?")
                    icon = "📈" if entry.transition_type == "promotion" else "•"
                    company_str = f" @ {entry.company}" if entry.company else ""
                    parts.append(f"  {icon} {entry.year_start}-{end_str}: {entry.title}{company_str}")
            
            if timeline.progression_score >= 70:
                parts.append("  ⭐ Strong career progression")
        
        return "\n".join(parts)
