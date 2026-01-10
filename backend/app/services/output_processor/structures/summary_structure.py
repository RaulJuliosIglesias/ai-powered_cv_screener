"""
SUMMARY STRUCTURE

Structure for providing talent pool overview.
Combines MODULES:
- ThinkingModule
- TalentPoolModule
- SkillDistributionModule
- ExperienceDistributionModule
- ConclusionModule

This structure is used when user asks for summaries:
- "overview of all candidates"
- "talent pool summary"
- "summarize the candidates"
"""

import logging
from typing import Dict, Any, List, Optional

from ..modules import ThinkingModule, ConclusionModule
from ..modules.talent_pool_module import TalentPoolModule
from ..modules.skill_distribution_module import SkillDistributionModule
from ..modules.experience_distribution_module import ExperienceDistributionModule

logger = logging.getLogger(__name__)


class SummaryStructure:
    """Assembles the Summary Structure using modules."""
    
    def __init__(self):
        self.thinking_module = ThinkingModule()
        self.talent_pool_module = TalentPoolModule()
        self.skill_distribution_module = SkillDistributionModule()
        self.experience_distribution_module = ExperienceDistributionModule()
        self.conclusion_module = ConclusionModule()
    
    def assemble(
        self,
        llm_output: str,
        chunks: List[Dict[str, Any]],
        query: str = "",
        conversation_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Assemble all components of Summary Structure."""
        logger.info("[SUMMARY_STRUCTURE] Assembling talent pool summary")
        
        # Extract thinking
        thinking = self.thinking_module.extract(llm_output)
        
        # Analyze talent pool
        pool_stats = self.talent_pool_module.analyze(chunks)
        
        # Analyze skill distribution
        skill_dist = self.skill_distribution_module.analyze(chunks)
        
        # Analyze experience distribution
        exp_dist = self.experience_distribution_module.analyze(chunks)
        
        # Extract conclusion
        conclusion = self.conclusion_module.extract(llm_output)
        
        # Generate rich direct_answer with actual statistics
        direct_answer = self._generate_direct_answer(pool_stats, skill_dist, exp_dist, chunks)
        
        return {
            "structure_type": "summary",
            "query": query,
            "thinking": thinking,
            "direct_answer": direct_answer,
            "talent_pool": pool_stats.to_dict() if pool_stats else None,
            "skill_distribution": skill_dist.to_dict() if skill_dist else None,
            "experience_distribution": exp_dist.to_dict() if exp_dist else None,
            "total_candidates": pool_stats.total_candidates if pool_stats else 0,
            "top_skills": skill_dist.top_skills if skill_dist else [],
            "conclusion": conclusion,
            "raw_content": llm_output
        }
    
    def _generate_direct_answer(
        self,
        pool_stats,
        skill_dist,
        exp_dist,
        chunks: List[Dict[str, Any]]
    ) -> str:
        """Generate rich direct answer with actual statistics."""
        if not pool_stats:
            return "No candidate data available for summary."
        
        total = pool_stats.total_candidates
        exp_distribution = pool_stats.experience_distribution
        
        # Count experience levels
        junior_count = exp_distribution.get("junior", 0)
        mid_count = exp_distribution.get("mid", 0)
        senior_count = exp_distribution.get("senior", 0)
        principal_count = exp_distribution.get("principal", 0)
        
        # Get top skills
        top_skills = skill_dist.top_skills[:5] if skill_dist and skill_dist.top_skills else []
        skills_str = ", ".join(top_skills) if top_skills else "Various"
        
        # Calculate average experience from chunks
        experiences = []
        candidates_seen = set()
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            cv_id = meta.get("cv_id", "")
            exp = meta.get("total_experience_years", 0)
            if cv_id and cv_id not in candidates_seen and exp > 0:
                experiences.append(exp)
                candidates_seen.add(cv_id)
        
        avg_exp = sum(experiences) / len(experiences) if experiences else 0
        
        # Build rich summary
        lines = [
            f"## 📊 Talent Pool Summary",
            "",
            f"**Total Candidates:** {total}",
            "",
            "### Experience Distribution",
            f"| Level | Count | % |",
            f"|-------|-------|---|",
        ]
        
        for level, count in [("Junior (0-2 yrs)", junior_count), 
                            ("Mid (3-5 yrs)", mid_count),
                            ("Senior (6-10 yrs)", senior_count),
                            ("Principal (10+ yrs)", principal_count)]:
            pct = (count / total * 100) if total > 0 else 0
            if count > 0:
                lines.append(f"| {level} | {count} | {pct:.0f}% |")
        
        lines.extend([
            "",
            f"**Average Experience:** {avg_exp:.1f} years",
            "",
            f"**Top Skills:** {skills_str}",
        ])
        
        # Add standout candidates if available
        if experiences:
            max_exp = max(experiences)
            lines.extend([
                "",
                f"**Most Experienced:** {max_exp:.0f} years",
            ])
        
        return "\n".join(lines)
