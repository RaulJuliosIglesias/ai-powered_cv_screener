"""
Gap Analysis Module - Skills Gap Detection

Analyzes what skills/requirements are missing from candidates
relative to job requirements specified in the query.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SkillGap:
    """Represents a missing skill or requirement."""
    skill: str
    importance: str  # "critical", "preferred", "nice_to_have"
    candidates_missing: List[str] = field(default_factory=list)
    candidates_have: List[str] = field(default_factory=list)


@dataclass
class GapAnalysisData:
    """Complete gap analysis for candidates."""
    required_skills: List[str] = field(default_factory=list)
    skill_gaps: List[SkillGap] = field(default_factory=list)
    coverage_score: float = 0.0  # 0-100% of requirements covered
    best_coverage_candidate: Optional[str] = None
    summary: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "required_skills": self.required_skills,
            "skill_gaps": [
                {
                    "skill": g.skill,
                    "importance": g.importance,
                    "candidates_missing": g.candidates_missing,
                    "candidates_have": g.candidates_have
                }
                for g in self.skill_gaps
            ],
            "coverage_score": self.coverage_score,
            "best_coverage_candidate": self.best_coverage_candidate,
            "summary": self.summary
        }


class GapAnalysisModule:
    """
    Analyzes skill gaps between job requirements and candidate profiles.
    
    This module:
    1. Extracts required skills from query/context
    2. Compares against candidate skills from chunks
    3. Identifies gaps and coverage
    4. Provides actionable recommendations
    """
    
    # Common skill categories for grouping
    SKILL_CATEGORIES = {
        "programming": [
            "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust",
            "ruby", "php", "scala", "kotlin", "swift"
        ],
        "frontend": [
            "react", "angular", "vue", "svelte", "html", "css", "sass", "tailwind",
            "next.js", "nuxt", "gatsby"
        ],
        "backend": [
            "node.js", "django", "fastapi", "flask", "spring", "express", "rails",
            "asp.net", "laravel"
        ],
        "database": [
            "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
            "dynamodb", "cassandra", "oracle"
        ],
        "cloud": [
            "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "ansible",
            "jenkins", "ci/cd"
        ],
        "data_science": [
            "machine learning", "deep learning", "tensorflow", "pytorch", "pandas",
            "numpy", "scikit-learn", "nlp", "computer vision"
        ],
        "soft_skills": [
            "leadership", "communication", "teamwork", "agile", "scrum", "management",
            "problem solving", "analytical"
        ]
    }
    
    def extract(
        self,
        llm_output: str,
        chunks: List[Dict[str, Any]],
        query: str = ""
    ) -> Optional[GapAnalysisData]:
        """
        Extract gap analysis from LLM output and chunks.
        
        Args:
            llm_output: Raw LLM response
            chunks: Retrieved CV chunks with metadata
            query: Original user query for context
            
        Returns:
            GapAnalysisData or None if no gap analysis applicable
        """
        if not chunks:
            return None
        
        # Step 1: Extract required skills from query and LLM output
        required_skills = self._extract_required_skills(query, llm_output)
        
        if not required_skills:
            logger.debug("[GAP_ANALYSIS] No specific skills requirements detected")
            return None
        
        # Step 2: Build candidate skill profiles from chunks
        candidate_skills = self._build_candidate_skill_profiles(chunks)
        
        if not candidate_skills:
            return None
        
        # Step 3: Analyze gaps
        skill_gaps = []
        total_coverage = 0
        best_candidate = None
        best_coverage = 0
        
        for skill in required_skills:
            skill_lower = skill.lower()
            candidates_have = []
            candidates_missing = []
            
            for candidate, skills in candidate_skills.items():
                skills_lower = [s.lower() for s in skills]
                if any(skill_lower in s or s in skill_lower for s in skills_lower):
                    candidates_have.append(candidate)
                else:
                    candidates_missing.append(candidate)
            
            # Determine importance based on query context
            importance = self._determine_skill_importance(skill, query)
            
            skill_gaps.append(SkillGap(
                skill=skill,
                importance=importance,
                candidates_missing=candidates_missing,
                candidates_have=candidates_have
            ))
        
        # Calculate coverage per candidate
        for candidate, skills in candidate_skills.items():
            skills_lower = [s.lower() for s in skills]
            matched = sum(
                1 for req in required_skills
                if any(req.lower() in s or s in req.lower() for s in skills_lower)
            )
            coverage = (matched / len(required_skills)) * 100 if required_skills else 0
            
            if coverage > best_coverage:
                best_coverage = coverage
                best_candidate = candidate
            total_coverage += coverage
        
        avg_coverage = total_coverage / len(candidate_skills) if candidate_skills else 0
        
        # Generate summary
        summary = self._generate_gap_summary(skill_gaps, best_candidate, best_coverage, len(candidate_skills))
        
        logger.info(
            f"[GAP_ANALYSIS] Analyzed {len(required_skills)} required skills, "
            f"avg coverage: {avg_coverage:.1f}%, best: {best_candidate} ({best_coverage:.1f}%)"
        )
        
        return GapAnalysisData(
            required_skills=required_skills,
            skill_gaps=skill_gaps,
            coverage_score=avg_coverage,
            best_coverage_candidate=best_candidate,
            summary=summary
        )
    
    def _extract_required_skills(self, query: str, llm_output: str) -> List[str]:
        """Extract required skills from query and LLM analysis."""
        skills = []
        combined_text = f"{query} {llm_output}".lower()
        
        # Look for explicit requirement patterns
        requirement_patterns = [
            r"(?:require|need|must have|looking for|with)\s+([a-zA-Z0-9\+\#\.\-\s,]+?)(?:\s+experience|\s+skills|\.|,|$)",
            r"(?:experience (?:in|with)|skills? (?:in|with))\s+([a-zA-Z0-9\+\#\.\-\s,]+)",
        ]
        
        for pattern in requirement_patterns:
            matches = re.findall(pattern, combined_text, re.IGNORECASE)
            for match in matches:
                # Split by comma or 'and'
                parts = re.split(r',|\s+and\s+|\s+y\s+', match)
                skills.extend([p.strip() for p in parts if len(p.strip()) > 1])
        
        # Also check for known skills mentioned
        for _category, category_skills in self.SKILL_CATEGORIES.items():
            for skill in category_skills:
                if skill in combined_text and skill not in [s.lower() for s in skills]:
                    skills.append(skill.title())
        
        # Deduplicate
        seen = set()
        unique_skills = []
        for skill in skills:
            skill_clean = skill.strip().title()
            if skill_clean.lower() not in seen and len(skill_clean) > 1:
                seen.add(skill_clean.lower())
                unique_skills.append(skill_clean)
        
        return unique_skills[:15]  # Limit to top 15
    
    def _build_candidate_skill_profiles(
        self,
        chunks: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """Build skill profiles for each candidate from chunks."""
        profiles = {}
        
        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            candidate = metadata.get("candidate_name", "Unknown")
            
            if not candidate or candidate == "Unknown":
                continue
            
            if candidate not in profiles:
                profiles[candidate] = []
            
            # Extract skills from metadata
            skills_str = metadata.get("skills", "")
            if skills_str:
                if isinstance(skills_str, str):
                    skills = [s.strip() for s in skills_str.split(",")]
                else:
                    skills = skills_str
                profiles[candidate].extend(skills)
            
            # Also scan chunk content for skills
            content = chunk.get("content", "").lower()
            for _category, category_skills in self.SKILL_CATEGORIES.items():
                for skill in category_skills:
                    if skill in content and skill.title() not in profiles[candidate]:
                        profiles[candidate].append(skill.title())
        
        # Deduplicate per candidate
        for candidate in profiles:
            profiles[candidate] = list(set(profiles[candidate]))
        
        return profiles
    
    def _determine_skill_importance(self, skill: str, query: str) -> str:
        """Determine if a skill is critical, preferred, or nice-to-have."""
        query_lower = query.lower()
        skill_lower = skill.lower()
        
        # Critical if explicitly required
        critical_patterns = [
            f"must have {skill_lower}",
            f"require {skill_lower}",
            f"essential {skill_lower}",
            f"mandatory {skill_lower}",
        ]
        
        for pattern in critical_patterns:
            if pattern in query_lower:
                return "critical"
        
        # Preferred if mentioned prominently
        if skill_lower in query_lower:
            return "preferred"
        
        return "nice_to_have"
    
    def _generate_gap_summary(
        self,
        gaps: List[SkillGap],
        best_candidate: Optional[str],
        best_coverage: float,
        total_candidates: int
    ) -> str:
        """Generate human-readable gap analysis summary."""
        parts = []
        
        # Critical gaps
        critical_gaps = [g for g in gaps if g.importance == "critical" and g.candidates_missing]
        if critical_gaps:
            gap_names = [g.skill for g in critical_gaps[:3]]
            parts.append(f"⚠️ Critical skill gaps: {', '.join(gap_names)}")
        
        # Coverage info
        if best_candidate and best_coverage > 0:
            parts.append(
                f"Best match: {best_candidate} covers {best_coverage:.0f}% of requirements"
            )
        
        # Fully covered skills
        fully_covered = [g.skill for g in gaps if not g.candidates_missing]
        if fully_covered:
            parts.append(f"✓ All candidates have: {', '.join(fully_covered[:5])}")
        
        if not parts:
            return "No significant skill gaps identified."
        
        return " | ".join(parts)
    
    def format(self, data: GapAnalysisData) -> str:
        """
        Format gap analysis for display.
        
        Args:
            data: GapAnalysisData to format
            
        Returns:
            Formatted markdown string
        """
        if not data or not data.skill_gaps:
            return ""
        
        parts = ["### Skills Gap Analysis\n"]
        
        # Summary
        if data.summary:
            parts.append(f"{data.summary}\n")
        
        # Coverage score
        parts.append(f"\n**Overall Coverage:** {data.coverage_score:.0f}%\n")
        
        # Gap details by importance
        critical = [g for g in data.skill_gaps if g.importance == "critical"]
        preferred = [g for g in data.skill_gaps if g.importance == "preferred"]
        
        if critical:
            parts.append("\n**Critical Requirements:**")
            for gap in critical:
                status = "✓" if not gap.candidates_missing else "✗"
                have_count = len(gap.candidates_have)
                total = len(gap.candidates_have) + len(gap.candidates_missing)
                parts.append(f"- {status} {gap.skill}: {have_count}/{total} candidates")
        
        if preferred:
            parts.append("\n**Preferred Skills:**")
            for gap in preferred[:5]:
                have_count = len(gap.candidates_have)
                total = len(gap.candidates_have) + len(gap.candidates_missing)
                parts.append(f"- {gap.skill}: {have_count}/{total} candidates")
        
        return "\n".join(parts)
