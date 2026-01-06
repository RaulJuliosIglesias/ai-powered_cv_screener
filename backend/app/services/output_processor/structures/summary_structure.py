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
        query: str = ""
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
        
        return {
            "structure_type": "summary",
            "query": query,
            "thinking": thinking,
            "talent_pool": pool_stats.to_dict() if pool_stats else None,
            "skill_distribution": skill_dist.to_dict() if skill_dist else None,
            "experience_distribution": exp_dist.to_dict() if exp_dist else None,
            "total_candidates": pool_stats.total_candidates if pool_stats else 0,
            "top_skills": skill_dist.top_skills if skill_dist else [],
            "conclusion": conclusion,
            "raw_content": llm_output
        }
