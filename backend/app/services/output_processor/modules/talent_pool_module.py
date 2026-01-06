"""
TALENT POOL MODULE

Generates talent pool statistics.
Used by: SummaryStructure
"""

import logging
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class PoolStats:
    """Talent pool statistics."""
    total_candidates: int = 0
    experience_distribution: Dict[str, int] = field(default_factory=dict)
    location_distribution: Dict[str, int] = field(default_factory=dict)
    seniority_distribution: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "total_candidates": self.total_candidates,
            "experience_distribution": self.experience_distribution,
            "location_distribution": self.location_distribution,
            "seniority_distribution": self.seniority_distribution
        }


class TalentPoolModule:
    """Module for analyzing talent pool statistics."""
    
    def analyze(self, chunks: List[Dict[str, Any]]) -> Optional[PoolStats]:
        """Analyze talent pool from chunks."""
        if not chunks:
            return None
        
        # Group by candidate
        candidates = {}
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            cv_id = chunk.get("cv_id", "") or meta.get("cv_id", "")
            if cv_id and cv_id not in candidates:
                candidates[cv_id] = {
                    "experience": meta.get("total_experience_years", 0),
                    "location": meta.get("location", "Unknown"),
                    "seniority": meta.get("seniority_level", "mid")
                }
        
        total = len(candidates)
        
        # Experience distribution
        exp_dist = {"0-2 years": 0, "3-5 years": 0, "6-10 years": 0, "10+ years": 0}
        for data in candidates.values():
            exp = data.get("experience", 0)
            if exp <= 2:
                exp_dist["0-2 years"] += 1
            elif exp <= 5:
                exp_dist["3-5 years"] += 1
            elif exp <= 10:
                exp_dist["6-10 years"] += 1
            else:
                exp_dist["10+ years"] += 1
        
        # Location distribution
        locations = [d.get("location", "Unknown") for d in candidates.values()]
        loc_dist = dict(Counter(locations).most_common(5))
        
        # Seniority distribution
        seniorities = [d.get("seniority", "mid") for d in candidates.values()]
        sen_dist = dict(Counter(seniorities))
        
        logger.info(f"[TALENT_POOL_MODULE] Analyzed {total} candidates")
        
        return PoolStats(
            total_candidates=total,
            experience_distribution=exp_dist,
            location_distribution=loc_dist,
            seniority_distribution=sen_dist
        )
    
    def format(self, stats: PoolStats) -> str:
        """Format pool stats into markdown."""
        if not stats:
            return ""
        
        lines = [
            "### 📊 Talent Pool Overview",
            "",
            f"**Total Candidates:** {stats.total_candidates}",
            "",
            "**Experience Distribution:**",
        ]
        
        for level, count in stats.experience_distribution.items():
            pct = (count / stats.total_candidates * 100) if stats.total_candidates > 0 else 0
            bar = "█" * int(pct / 10)
            lines.append(f"- {level}: {count} ({pct:.0f}%) {bar}")
        
        if stats.seniority_distribution:
            lines.append("")
            lines.append("**Seniority Levels:**")
            for level, count in stats.seniority_distribution.items():
                lines.append(f"- {level.title()}: {count}")
        
        return "\n".join(lines)
