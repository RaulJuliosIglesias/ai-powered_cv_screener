"""
JOB MATCH STRUCTURE

Structure for matching candidates against a job description.
Combines MODULES:
- ThinkingModule
- RequirementsModule
- MatchScoreModule
- GapAnalysisModule
- ConclusionModule

This structure is used when user asks for job matching:
- "match candidates to this JD"
- "who fits this role"
- "evaluate against these requirements"
"""

import logging
from typing import Dict, Any, List, Optional

from ..modules import ThinkingModule, ConclusionModule, GapAnalysisModule
from ..modules.requirements_module import RequirementsModule
from ..modules.match_score_module import MatchScoreModule

logger = logging.getLogger(__name__)


class JobMatchStructure:
    """
    Assembles the Job Match Structure using modules.
    
    This STRUCTURE combines modules to create job matching view.
    """
    
    def __init__(self):
        self.thinking_module = ThinkingModule()
        self.requirements_module = RequirementsModule()
        self.match_score_module = MatchScoreModule()
        self.gap_analysis_module = GapAnalysisModule()
        self.conclusion_module = ConclusionModule()
    
    def assemble(
        self,
        llm_output: str,
        chunks: List[Dict[str, Any]],
        query: str = "",
        job_description: str = ""
    ) -> Dict[str, Any]:
        """
        Assemble all components of Job Match Structure.
        
        Args:
            llm_output: Raw LLM response
            chunks: CV chunks with metadata
            query: Original query
            job_description: Job description text
            
        Returns:
            dict with structure_type and all components for frontend
        """
        logger.info("[JOB_MATCH_STRUCTURE] Assembling job match analysis")
        
        # Extract thinking from LLM output
        thinking = self.thinking_module.extract(llm_output)
        
        # Extract requirements from JD or query
        jd_text = job_description or query
        requirements_data = self.requirements_module.extract(
            job_description=jd_text,
            llm_output=llm_output
        )
        
        # Calculate match scores
        requirements_list = requirements_data.to_dict()["requirements"] if requirements_data else []
        match_data = self.match_score_module.calculate(
            requirements=requirements_list,
            chunks=chunks,
            llm_output=llm_output
        )
        
        # Gap analysis
        gap_data = self.gap_analysis_module.extract(
            llm_output=llm_output,
            chunks=chunks,
            query=query
        )
        
        # Extract conclusion
        conclusion = self.conclusion_module.extract(llm_output)
        
        # Get best match
        best_match = None
        if match_data and match_data.matches:
            top = match_data.matches[0]
            best_match = {
                "candidate_name": top.candidate_name,
                "cv_id": top.cv_id,
                "overall_match": top.overall_match,
                "strengths": top.strengths
            }
        
        return {
            "structure_type": "job_match",
            "query": query,
            "thinking": thinking,
            "requirements": requirements_data.to_dict() if requirements_data else None,
            "match_scores": match_data.to_dict() if match_data else None,
            "gap_analysis": gap_data.to_dict() if gap_data else None,
            "best_match": best_match,
            "total_candidates": len(match_data.matches) if match_data else 0,
            "conclusion": conclusion,
            "raw_content": llm_output
        }
