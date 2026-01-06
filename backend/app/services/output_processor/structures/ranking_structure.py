"""
RANKING STRUCTURE

Structure for ranking candidates for a specific role.
Combines MODULES:
- ThinkingModule
- RankingCriteriaModule
- RankingTableModule
- TopPickModule
- ConclusionModule

This structure is used when user asks for ranking:
- "top 5 candidates for backend"
- "rank candidates for this role"
- "best candidates for senior developer"
"""

import logging
from typing import Dict, Any, List, Optional

from ..modules import ThinkingModule, ConclusionModule
from ..modules.ranking_criteria_module import RankingCriteriaModule
from ..modules.ranking_table_module import RankingTableModule
from ..modules.top_pick_module import TopPickModule

logger = logging.getLogger(__name__)


class RankingStructure:
    """
    Assembles the Ranking Structure using modules.
    
    This STRUCTURE combines modules to create ranked candidate view.
    """
    
    def __init__(self):
        self.thinking_module = ThinkingModule()
        self.ranking_criteria_module = RankingCriteriaModule()
        self.ranking_table_module = RankingTableModule()
        self.top_pick_module = TopPickModule()
        self.conclusion_module = ConclusionModule()
    
    def assemble(
        self,
        llm_output: str,
        chunks: List[Dict[str, Any]],
        query: str = "",
        job_context: str = ""
    ) -> Dict[str, Any]:
        """
        Assemble all components of Ranking Structure.
        
        Args:
            llm_output: Raw LLM response
            chunks: CV chunks with metadata
            query: Original ranking query
            job_context: Optional job description context
            
        Returns:
            dict with structure_type and all components for frontend
        """
        logger.info(f"[RANKING_STRUCTURE] Assembling ranking for: {query[:50]}...")
        
        # Extract thinking from LLM output
        thinking = self.thinking_module.extract(llm_output)
        
        # Extract ranking criteria
        criteria_data = self.ranking_criteria_module.extract(
            query=query,
            llm_output=llm_output,
            job_context=job_context
        )
        
        # Generate ranking table
        criteria_list = criteria_data.to_dict()["criteria"] if criteria_data else []
        ranking_data = self.ranking_table_module.extract(
            chunks=chunks,
            criteria=criteria_list,
            llm_output=llm_output
        )
        
        # Generate top pick recommendation
        ranked_list = ranking_data.to_dict()["ranked"] if ranking_data else []
        top_pick_data = self.top_pick_module.extract(
            ranked_candidates=ranked_list,
            llm_output=llm_output,
            criteria=criteria_list
        )
        
        # Extract conclusion
        conclusion = self.conclusion_module.extract(llm_output)
        
        return {
            "structure_type": "ranking",
            "query": query,
            "thinking": thinking,
            "criteria": criteria_data.to_dict() if criteria_data else None,
            "ranking_table": ranking_data.to_dict() if ranking_data else None,
            "top_pick": {
                "candidate_name": top_pick_data.candidate_name,
                "cv_id": top_pick_data.cv_id,
                "overall_score": top_pick_data.overall_score,
                "key_strengths": top_pick_data.key_strengths,
                "justification": top_pick_data.justification,
                "runner_up": top_pick_data.runner_up,
                "runner_up_cv_id": top_pick_data.runner_up_cv_id
            } if top_pick_data else None,
            "total_ranked": len(ranked_list),
            "conclusion": conclusion,
            "raw_content": llm_output
        }
