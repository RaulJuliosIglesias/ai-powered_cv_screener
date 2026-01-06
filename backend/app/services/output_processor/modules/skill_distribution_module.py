"""
SKILL DISTRIBUTION MODULE

Analyzes skill distribution across talent pool.
Used by: SummaryStructure
"""

import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class SkillStats:
    """Statistics for a single skill."""
    skill: str
    candidate_count: int
    percentage: float


@dataclass
class SkillDistributionData:
    """Container for skill distribution."""
    skills: List[SkillStats] = field(default_factory=list)
    total_candidates: int = 0
    top_skills: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "skills": [
                {"skill": s.skill, "candidate_count": s.candidate_count, "percentage": s.percentage}
                for s in self.skills
            ],
            "total_candidates": self.total_candidates,
            "top_skills": self.top_skills
        }


class SkillDistributionModule:
    """Module for analyzing skill distribution."""
    
    def analyze(self, chunks: List[Dict[str, Any]]) -> Optional[SkillDistributionData]:
        """Analyze skill distribution from chunks."""
        if not chunks:
            return None
        
        # Group by candidate and collect skills
        candidates = {}
        all_skills = Counter()
        
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            cv_id = chunk.get("cv_id", "") or meta.get("cv_id", "")
            
            if not cv_id:
                continue
            
            if cv_id not in candidates:
                candidates[cv_id] = set()
            
            skills_str = meta.get("skills", "")
            if skills_str:
                for skill in skills_str.split(","):
                    skill = skill.strip()
                    if skill and len(skill) > 1:
                        candidates[cv_id].add(skill.lower())
        
        # Count skill occurrences
        for candidate_skills in candidates.values():
            for skill in candidate_skills:
                all_skills[skill] += 1
        
        total = len(candidates)
        
        # Build skill stats
        skill_stats = []
        for skill, count in all_skills.most_common(20):
            pct = (count / total * 100) if total > 0 else 0
            skill_stats.append(SkillStats(
                skill=skill.title(),
                candidate_count=count,
                percentage=round(pct, 1)
            ))
        
        top_skills = [s.skill for s in skill_stats[:5]]
        
        logger.info(f"[SKILL_DISTRIBUTION_MODULE] Found {len(all_skills)} unique skills")
        
        return SkillDistributionData(
            skills=skill_stats,
            total_candidates=total,
            top_skills=top_skills
        )
    
    def format(self, data: SkillDistributionData) -> str:
        """Format skill distribution into markdown."""
        if not data or not data.skills:
            return ""
        
        lines = [
            "### 🛠️ Skill Distribution",
            "",
            f"**Top Skills in Pool:**",
            "",
            "| Skill | Candidates | % of Pool |",
            "|:------|:----------:|:---------:|",
        ]
        
        for s in data.skills[:10]:
            bar = "█" * int(s.percentage / 10)
            lines.append(f"| {s.skill} | {s.candidate_count} | {s.percentage:.0f}% {bar} |")
        
        return "\n".join(lines)
