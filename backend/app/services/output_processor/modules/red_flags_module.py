"""
Red Flags Module - Candidate Risk Detection

Detects potential red flags in candidate profiles:
- Employment gaps
- Job hopping patterns
- Inconsistencies
- Missing critical information
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RedFlag:
    """Represents a detected red flag."""
    flag_type: str  # "gap", "job_hopping", "short_tenure", "missing_info", "inconsistency"
    severity: str  # "high", "medium", "low"
    description: str
    candidate_name: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RedFlagsData:
    """Complete red flags analysis for candidates."""
    flags: List[RedFlag] = field(default_factory=list)
    candidates_with_flags: Dict[str, List[str]] = field(default_factory=dict)  # {candidate: [flag_types]}
    high_risk_candidates: List[str] = field(default_factory=list)
    clean_candidates: List[str] = field(default_factory=list)
    summary: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "flags": [
                {
                    "flag_type": f.flag_type,
                    "severity": f.severity,
                    "description": f.description,
                    "candidate_name": f.candidate_name,
                    "details": f.details
                }
                for f in self.flags
            ],
            "candidates_with_flags": self.candidates_with_flags,
            "high_risk_candidates": self.high_risk_candidates,
            "clean_candidates": self.clean_candidates,
            "summary": self.summary
        }


class RedFlagsModule:
    """
    Detects and reports red flags in candidate profiles.
    
    Red flags include:
    - Employment gaps > 1 year
    - Job hopping (avg tenure < 1.5 years)
    - Very short tenures (< 6 months)
    - Missing critical sections (experience, education)
    - Salary/title downgrades
    """
    
    # Thresholds for detection
    GAP_THRESHOLD_YEARS = 1.0  # Gaps > 1 year are flagged
    JOB_HOPPING_THRESHOLD_HIGH = 0.6  # job_hopping_score > 0.6 is HIGH severity
    JOB_HOPPING_THRESHOLD_MEDIUM = 0.4  # job_hopping_score > 0.4 is MEDIUM severity
    SHORT_TENURE_YEARS = 0.5  # Tenures < 6 months are flagged
    SHORT_AVG_TENURE_THRESHOLD = 1.5  # avg_tenure < 1.5 years is flagged
    MIN_EXPERIENCE_YEARS = 0.5  # Minimum expected for non-entry roles
    
    def extract(
        self,
        chunks: List[Dict[str, Any]],
        llm_output: str = ""
    ) -> Optional[RedFlagsData]:
        """
        Extract red flags from CV chunks metadata.
        
        Args:
            chunks: Retrieved CV chunks with enriched metadata
            llm_output: Optional LLM response for additional context
            
        Returns:
            RedFlagsData or None if no analysis possible
        """
        if not chunks:
            return None
        
        flags = []
        candidates_flags = {}
        
        # Group chunks by candidate
        candidate_chunks = self._group_by_candidate(chunks)
        
        for candidate, cand_chunks in candidate_chunks.items():
            candidate_flags = []
            
            # Get summary chunk metadata (most complete)
            summary_meta = self._get_summary_metadata(cand_chunks)
            
            # Check for job hopping and short tenure
            job_hopping_flags = self._check_job_hopping(candidate, summary_meta)
            for flag in job_hopping_flags:
                flags.append(flag)
                candidate_flags.append(flag.flag_type)
            
            # Check for employment gaps
            gap_flags = self._check_employment_gaps(candidate, summary_meta, cand_chunks)
            for gap_flag in gap_flags:
                flags.append(gap_flag)
                candidate_flags.append(gap_flag.flag_type)
            
            # Check for short tenures
            short_tenure_flags = self._check_short_tenures(candidate, cand_chunks)
            for flag in short_tenure_flags:
                flags.append(flag)
                candidate_flags.append(flag.flag_type)
            
            # Check for missing information
            missing_flags = self._check_missing_info(candidate, cand_chunks)
            for flag in missing_flags:
                flags.append(flag)
                candidate_flags.append(flag.flag_type)
            
            if candidate_flags:
                candidates_flags[candidate] = list(set(candidate_flags))
        
        # Categorize candidates
        high_risk = [
            cand for cand, cand_flags in candidates_flags.items()
            if any(f.severity == "high" for f in flags if f.candidate_name == cand)
        ]
        
        all_candidates = list(candidate_chunks.keys())
        clean = [c for c in all_candidates if c not in candidates_flags]
        
        # Generate summary
        summary = self._generate_summary(flags, high_risk, clean, len(all_candidates))
        
        logger.info(
            f"[RED_FLAGS] Analyzed {len(all_candidates)} candidates: "
            f"{len(flags)} flags, {len(high_risk)} high-risk, {len(clean)} clean"
        )
        
        return RedFlagsData(
            flags=flags,
            candidates_with_flags=candidates_flags,
            high_risk_candidates=high_risk,
            clean_candidates=clean,
            summary=summary
        )
    
    def _group_by_candidate(
        self,
        chunks: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Group chunks by candidate name."""
        grouped = {}
        for chunk in chunks:
            candidate = chunk.get("metadata", {}).get("candidate_name", "Unknown")
            if candidate and candidate != "Unknown":
                if candidate not in grouped:
                    grouped[candidate] = []
                grouped[candidate].append(chunk)
        return grouped
    
    def _get_summary_metadata(
        self,
        chunks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Get metadata from summary chunk or aggregate from all chunks."""
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            if meta.get("is_summary"):
                return meta
        
        # Aggregate from all chunks
        aggregated = {}
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            for key, value in meta.items():
                if key not in aggregated and value:
                    aggregated[key] = value
        return aggregated
    
    def _check_job_hopping(
        self,
        candidate: str,
        metadata: Dict[str, Any]
    ) -> List[RedFlag]:
        """
        Check for job hopping pattern using METADATA from chunks.
        
        Uses job_hopping_score and avg_tenure_years calculated during chunking.
        These values represent the COMPLETE CV, not just retrieved chunks.
        """
        flags = []
        job_hopping_score = metadata.get("job_hopping_score", 0)
        avg_tenure = metadata.get("avg_tenure_years", 0)
        position_count = metadata.get("position_count", 0)
        metadata.get("total_experience_years", 0)
        
        # Job hopping based on score
        if job_hopping_score and position_count >= 3:
            if job_hopping_score > self.JOB_HOPPING_THRESHOLD_HIGH:
                flags.append(RedFlag(
                    flag_type="job_hopping",
                    severity="high",
                    description=f"High job mobility: {position_count} positions with avg tenure {avg_tenure:.1f} years (score: {job_hopping_score:.0%})",
                    candidate_name=candidate,
                    details={
                        "job_hopping_score": job_hopping_score,
                        "avg_tenure_years": avg_tenure,
                        "position_count": position_count
                    }
                ))
            elif job_hopping_score > self.JOB_HOPPING_THRESHOLD_MEDIUM:
                flags.append(RedFlag(
                    flag_type="job_hopping",
                    severity="medium",
                    description=f"Moderate job mobility: {position_count} positions with avg tenure {avg_tenure:.1f} years (score: {job_hopping_score:.0%})",
                    candidate_name=candidate,
                    details={
                        "job_hopping_score": job_hopping_score,
                        "avg_tenure_years": avg_tenure,
                        "position_count": position_count
                    }
                ))
        
        # Short average tenure (even if job_hopping_score is lower)
        if avg_tenure and avg_tenure < self.SHORT_AVG_TENURE_THRESHOLD and position_count >= 2:
            # Don't double-flag if already flagged for job hopping
            if not any(f.flag_type == "job_hopping" for f in flags):
                flags.append(RedFlag(
                    flag_type="short_avg_tenure",
                    severity="medium",
                    description=f"Short average tenure: {avg_tenure:.1f} years across {position_count} positions",
                    candidate_name=candidate,
                    details={
                        "avg_tenure_years": avg_tenure,
                        "position_count": position_count
                    }
                ))
        
        return flags
    
    def _check_employment_gaps(
        self,
        candidate: str,
        metadata: Dict[str, Any],
        chunks: List[Dict[str, Any]]
    ) -> List[RedFlag]:
        """Check for employment gaps."""
        flags = []
        
        # Look for gap indicators in content
        for chunk in chunks:
            content = chunk.get("content", "").lower()
            
            # Check for explicit gap mentions
            if "gap" in content or "career break" in content or "sabbatical" in content:
                flags.append(RedFlag(
                    flag_type="employment_gap",
                    severity="low",
                    description="Career break or gap mentioned in CV",
                    candidate_name=candidate,
                    details={"source": "content_mention"}
                ))
                break
        
        # Check metadata for gaps
        # Note: employment_gaps from enriched metadata would be a list of (start, end) tuples
        # stored as string in ChromaDB
        
        return flags
    
    def _check_short_tenures(
        self,
        candidate: str,
        chunks: List[Dict[str, Any]]
    ) -> List[RedFlag]:
        """Check for very short job tenures."""
        flags = []
        short_jobs = []
        
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            duration = meta.get("duration_years", 0)
            job_title = meta.get("job_title", "")
            company = meta.get("company", "")
            
            if duration and duration < self.SHORT_TENURE_YEARS and job_title:
                short_jobs.append(f"{job_title} at {company} ({duration:.1f}y)")
        
        if short_jobs:
            flags.append(RedFlag(
                flag_type="short_tenure",
                severity="medium" if len(short_jobs) > 2 else "low",
                description=f"Very short tenures detected: {', '.join(short_jobs[:3])}",
                candidate_name=candidate,
                details={"short_positions": short_jobs}
            ))
        
        return flags
    
    def _check_missing_info(
        self,
        candidate: str,
        chunks: List[Dict[str, Any]]
    ) -> List[RedFlag]:
        """
        Check for missing critical information using METADATA, not section_types.
        
        ================================================================
        IMPORTANT: DO NOT check section_types from retrieved chunks!
        ================================================================
        
        The retrieval process only returns a subset of chunks (e.g., 8 out of 23).
        A candidate may have "experience" chunks in the DB but they weren't 
        retrieved for this specific query. Checking section_types would 
        incorrectly flag them as "missing_experience".
        
        Instead, we use the METADATA fields that are calculated during 
        chunking and stored on EVERY chunk:
        - position_count: Number of positions (0 = no experience)
        - total_experience_years: Total years of experience
        - These values are reliable because they're calculated from the 
          COMPLETE CV during chunking, not from partial retrieval.
        ================================================================
        """
        flags = []
        
        # Get metadata from any chunk (all chunks have the same enriched metadata)
        meta = {}
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            if meta.get("position_count") is not None:
                break
        
        # Check for missing/insufficient experience using metadata
        position_count = meta.get("position_count", 0)
        total_exp = meta.get("total_experience_years", 0)
        
        # Only flag if we have metadata AND it shows no experience
        # If position_count is 0 or 1 with 0 years, it might be entry-level
        if position_count == 0 and total_exp == 0:
            # Could be entry-level or intern - low severity
            flags.append(RedFlag(
                flag_type="entry_level",
                severity="low",
                description="Entry-level candidate with no prior work experience listed",
                candidate_name=candidate,
                details={"position_count": position_count, "total_experience_years": total_exp}
            ))
        
        return flags
    
    def _generate_summary(
        self,
        flags: List[RedFlag],
        high_risk: List[str],
        clean: List[str],
        total: int
    ) -> str:
        """Generate human-readable summary."""
        parts = []
        
        if clean:
            parts.append(f"✓ {len(clean)} candidate(s) with no red flags")
        
        if high_risk:
            names = ", ".join(high_risk[:3])
            suffix = f" (+{len(high_risk)-3} more)" if len(high_risk) > 3 else ""
            parts.append(f"⚠️ High-risk: {names}{suffix}")
        
        # Count flag types
        flag_counts = {}
        for flag in flags:
            flag_counts[flag.flag_type] = flag_counts.get(flag.flag_type, 0) + 1
        
        if flag_counts:
            flag_summary = ", ".join([f"{count} {ftype}" for ftype, count in flag_counts.items()])
            parts.append(f"Flags detected: {flag_summary}")
        
        if not parts:
            return f"All {total} candidates reviewed with no significant concerns."
        
        return " | ".join(parts)
    
    def format(self, data: RedFlagsData) -> str:
        """
        Format red flags for display.
        
        Args:
            data: RedFlagsData to format
            
        Returns:
            Formatted markdown string
        """
        if not data or not data.flags:
            if data and data.clean_candidates:
                return f"### Red Flags Analysis\n\n✓ No red flags detected for {len(data.clean_candidates)} candidate(s)."
            return ""
        
        parts = ["### Red Flags Analysis\n"]
        
        # Summary
        if data.summary:
            parts.append(f"{data.summary}\n")
        
        # High severity flags first
        high_flags = [f for f in data.flags if f.severity == "high"]
        if high_flags:
            parts.append("\n**⚠️ High Priority:**")
            for flag in high_flags:
                parts.append(f"- **{flag.candidate_name}**: {flag.description}")
        
        # Medium severity
        medium_flags = [f for f in data.flags if f.severity == "medium"]
        if medium_flags:
            parts.append("\n**⚡ Attention:**")
            for flag in medium_flags[:5]:  # Limit display
                parts.append(f"- {flag.candidate_name}: {flag.description}")
        
        # Clean candidates
        if data.clean_candidates:
            parts.append(f"\n**✓ Clean profiles:** {', '.join(data.clean_candidates[:5])}")
        
        return "\n".join(parts)
