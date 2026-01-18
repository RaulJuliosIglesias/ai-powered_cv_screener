"""
SKILL COVERAGE MODULE

Analyzes team skill coverage.
Used by: TeamBuildStructure
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SkillCoverage:
    """Coverage for a single skill."""
    skill: str
    covered_by: List[str] = field(default_factory=list)
    coverage_level: str = "none"  # "strong", "moderate", "weak", "none"


@dataclass
class SkillCoverageData:
    """Container for skill coverage analysis."""
    coverages: List[SkillCoverage] = field(default_factory=list)
    overall_coverage: float = 0.0
    gaps: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "coverages": [
                {
                    "skill": c.skill,
                    "covered_by": c.covered_by,
                    "coverage_level": c.coverage_level
                }
                for c in self.coverages
            ],
            "overall_coverage": self.overall_coverage,
            "gaps": self.gaps
        }


class SkillCoverageModule:
    """Module for analyzing team skill coverage."""
    
    def analyze(
        self,
        assignments: List[Dict[str, Any]],
        required_skills: List[str] = None
    ) -> Optional[SkillCoverageData]:
        """Analyze skill coverage of team assignments."""
        if not assignments:
            return None
        
        # Collect all skills from assignments
        skill_to_candidates = {}
        all_skills = set()
        
        for assignment in assignments:
            candidate = assignment.get("candidate_name", "")
            matching_skills = assignment.get("matching_skills", [])
            
            for skill in matching_skills:
                skill.lower()
                all_skills.add(skill)
                if skill not in skill_to_candidates:
                    skill_to_candidates[skill] = []
                skill_to_candidates[skill].append(candidate)
        
        # Add required skills not yet covered
        if required_skills:
            for skill in required_skills:
                all_skills.add(skill)
        
        # Analyze coverage
        coverages = []
        gaps = []
        
        for skill in all_skills:
            covered_by = skill_to_candidates.get(skill, [])
            
            if len(covered_by) >= 2:
                level = "strong"
            elif len(covered_by) == 1:
                level = "moderate"
            else:
                level = "none"
                gaps.append(skill)
            
            coverages.append(SkillCoverage(
                skill=skill,
                covered_by=covered_by,
                coverage_level=level
            ))
        
        # Calculate overall coverage
        total_skills = len(coverages)
        covered_skills = sum(1 for c in coverages if c.coverage_level != "none")
        overall = (covered_skills / total_skills * 100) if total_skills > 0 else 0
        
        logger.info(f"[SKILL_COVERAGE_MODULE] Coverage: {overall:.0f}%, {len(gaps)} gaps")
        
        return SkillCoverageData(
            coverages=coverages,
            overall_coverage=round(overall, 1),
            gaps=gaps
        )
    
    def format(self, data: SkillCoverageData) -> str:
        """Format skill coverage into markdown."""
        if not data:
            return ""
        
        lines = [
            "### 📊 Skill Coverage Analysis",
            "",
            f"**Overall Coverage:** {data.overall_coverage:.0f}%",
            "",
        ]
        
        # Group by coverage level
        strong = [c for c in data.coverages if c.coverage_level == "strong"]
        moderate = [c for c in data.coverages if c.coverage_level == "moderate"]
        
        if strong:
            lines.append("**✅ Strong Coverage:**")
            for c in strong:
                members = ", ".join(c.covered_by[:2])
                lines.append(f"- {c.skill} ({members})")
            lines.append("")
        
        if moderate:
            lines.append("**🟡 Single Coverage:**")
            for c in moderate:
                lines.append(f"- {c.skill} ({c.covered_by[0]})")
            lines.append("")
        
        if data.gaps:
            lines.append("**❌ Skill Gaps:**")
            for skill in data.gaps:
                lines.append(f"- {skill}")
        
        return "\n".join(lines)
