"""
SEARCH STRUCTURE

Structure for displaying search results matching specific criteria.
Combines MODULES:
- ThinkingModule
- DirectAnswerModule
- ResultsTableModule
- ConclusionModule

This structure is used when user searches for candidates:
- "who has Python experience"
- "find candidates with React"
- "show me backend developers"
"""

import logging
from typing import Dict, Any, List, Optional

from ..modules import ThinkingModule, DirectAnswerModule, ConclusionModule, AnalysisModule
from ..modules.results_table_module import ResultsTableModule

logger = logging.getLogger(__name__)


class SearchStructure:
    """
    Assembles the Search Structure using modules.
    
    This STRUCTURE combines modules to create search results view.
    """
    
    def __init__(self):
        self.thinking_module = ThinkingModule()
        self.direct_answer_module = DirectAnswerModule()
        self.analysis_module = AnalysisModule()
        self.results_table_module = ResultsTableModule()
        self.conclusion_module = ConclusionModule()
    
    def assemble(
        self,
        llm_output: str,
        chunks: List[Dict[str, Any]],
        query: str = ""
    ) -> Dict[str, Any]:
        """
        Assemble all components of Search Structure.
        
        Args:
            llm_output: Raw LLM response
            chunks: CV chunks with metadata and scores
            query: Original search query
            
        Returns:
            dict with structure_type and all components for frontend
        """
        logger.info(f"[SEARCH_STRUCTURE] Assembling search results for: {query[:50]}...")
        
        # Extract thinking from LLM output
        thinking = self.thinking_module.extract(llm_output)
        
        # Extract direct answer
        direct_answer = self.direct_answer_module.extract(llm_output)
        
        # Generate results table from chunks
        results_data = self.results_table_module.extract(
            chunks=chunks,
            query=query,
            llm_output=llm_output
        )
        
        # Extract conclusion
        conclusion = self.conclusion_module.extract(llm_output)
        
        # Extract analysis (between direct answer and conclusion)
        analysis = self.analysis_module.extract(llm_output, direct_answer or "", conclusion or "")
        
        return {
            "structure_type": "search",
            "query": query,
            "thinking": thinking,
            "direct_answer": direct_answer,
            "analysis": analysis,
            "results_table": results_data.to_dict() if results_data else None,
            "total_results": results_data.total_candidates if results_data else 0,
            "conclusion": conclusion,
            "raw_content": llm_output
        }
