"""
EXPERIENCE DISTRIBUTION MODULE

Analyzes experience level distribution.
Used by: SummaryStructure
"""

import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ExperienceDistributionData:
    """Container for experience distribution."""
    junior: int = 0  # 0-2 years
    mid: int = 0  # 3-5 years
    senior: int = 0  # 6-10 years
    principal: int = 0  # 10+ years
    average_years: float = 0.0
    total_candidates: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "junior": self.junior,
            "mid": self.mid,
            "senior": self.senior,
            "principal": self.principal,
            "average_years": self.average_years,
            "total_candidates": self.total_candidates
        }


class ExperienceDistributionModule:
    """Module for analyzing experience distribution."""
    
    def analyze(self, chunks: List[Dict[str, Any]]) -> Optional[ExperienceDistributionData]:
        """Analyze experience distribution from chunks."""
        if not chunks:
            return None
        
        # Group by candidate
        candidates = {}
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            cv_id = chunk.get("cv_id", "") or meta.get("cv_id", "")
            if cv_id and cv_id not in candidates:
                candidates[cv_id] = meta.get("total_experience_years", 0)
        
        if not candidates:
            return None
        
        total = len(candidates)
        total_years = sum(candidates.values())
        avg_years = total_years / total if total > 0 else 0
        
        # Categorize
        junior = mid = senior = principal = 0
        for exp in candidates.values():
            if exp <= 2:
                junior += 1
            elif exp <= 5:
                mid += 1
            elif exp <= 10:
                senior += 1
            else:
                principal += 1
        
        logger.info(f"[EXPERIENCE_DISTRIBUTION_MODULE] Analyzed {total} candidates, avg: {avg_years:.1f} years")
        
        return ExperienceDistributionData(
            junior=junior,
            mid=mid,
            senior=senior,
            principal=principal,
            average_years=round(avg_years, 1),
            total_candidates=total
        )
    
    def format(self, data: ExperienceDistributionData) -> str:
        """Format experience distribution into markdown."""
        if not data:
            return ""
        
        total = data.total_candidates or 1
        
        lines = [
            "### 📈 Experience Levels",
            "",
            f"**Average Experience:** {data.average_years} years",
            "",
            "| Level | Count | % |",
            "|:------|:-----:|:-:|",
        ]
        
        levels = [
            ("Junior (0-2 yrs)", data.junior),
            ("Mid (3-5 yrs)", data.mid),
            ("Senior (6-10 yrs)", data.senior),
            ("Principal (10+ yrs)", data.principal),
        ]
        
        for name, count in levels:
            pct = (count / total * 100)
            bar = "█" * int(pct / 10)
            lines.append(f"| {name} | {count} | {pct:.0f}% {bar} |")
        
        return "\n".join(lines)
