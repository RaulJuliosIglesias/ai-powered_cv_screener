"""
COMPARISON STRUCTURE

Complete structure for comparing multiple candidates.
Combines MODULES:
- ThinkingModule
- Analysis (text)
- TableModule (candidate comparison table)
- ConclusionModule

This structure is used for comparison queries:
- "compare X and Y"
- "X vs Y"
- "difference between X and Y"
"""

import logging
from typing import Dict, Any, List

from ..modules import ThinkingModule, AnalysisModule, TableModule, ConclusionModule

logger = logging.getLogger(__name__)


class ComparisonStructure:
    """
    Assembles the Comparison Structure using modules.
    
    This STRUCTURE combines modules to create a multi-candidate comparison view.
    """
    
    def __init__(self):
        self.thinking_module = ThinkingModule()
        self.analysis_module = AnalysisModule()
        self.table_module = TableModule()
        self.conclusion_module = ConclusionModule()
    
    def assemble(
        self,
        llm_output: str,
        chunks: List[Dict[str, Any]],
        conversation_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Assemble Comparison Structure.
        
        Args:
            llm_output: Raw LLM response
            chunks: CV chunks with metadata
            
        Returns:
            dict with structure_type and all components for frontend
        """
        logger.info("[COMPARISON_STRUCTURE] Assembling comparison view")
        
        # Extract thinking from LLM output
        thinking = self.thinking_module.extract(llm_output)
        
        # Extract conclusion first (needed for analysis extraction)
        conclusion = self.conclusion_module.extract(llm_output)
        
        # Extract comparison table
        table_data = self.table_module.extract(llm_output, chunks)
        
        # Extract analysis section (requires direct_answer and conclusion)
        # For comparison, we don't have a separate direct_answer, so pass empty string
        analysis = self.analysis_module.extract(llm_output, "", conclusion)
        
        return {
            "structure_type": "comparison",
            "thinking": thinking,
            "analysis": analysis,
            "table_data": table_data.to_dict() if table_data else None,
            "conclusion": conclusion,
            "raw_content": llm_output
        }
