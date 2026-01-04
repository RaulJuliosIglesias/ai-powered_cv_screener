"""
Output Processor - Uses ONLY modular components.

This processor coordinates extraction from LLM output using the 5 modules:
1. ThinkingModule
2. DirectAnswerModule
3. AnalysisModule
4. TableModule
5. ConclusionModule

DO NOT create parallel functions - use modules parametrically.
"""

import logging
from typing import List, Dict, Any

from app.models.structured_output import StructuredOutput
from .modules import (
    ThinkingModule,
    DirectAnswerModule,
    AnalysisModule,
    TableModule,
    ConclusionModule
)

logger = logging.getLogger(__name__)


class OutputProcessor:
    """
    Coordinates extraction using modular components.
    
    This is the ONLY processor - no parallel extraction logic allowed.
    """
    
    def __init__(self):
        """Initialize with all modules."""
        self.thinking_module = ThinkingModule()
        self.direct_answer_module = DirectAnswerModule()
        self.analysis_module = AnalysisModule()
        self.table_module = TableModule()
        self.conclusion_module = ConclusionModule()
        
        logger.info("[PROCESSOR] Initialized with 5 modules")
    
    def process(
        self,
        raw_llm_output: str,
        chunks: List[Dict[str, Any]] = None
    ) -> StructuredOutput:
        """
        Process LLM output using modular components.
        
        Args:
            raw_llm_output: Raw text from LLM
            chunks: Retrieved CV chunks for fallback
            
        Returns:
            StructuredOutput with all components extracted
        """
        logger.info("[PROCESSOR] Starting extraction using modules")
        
        # Extract each component using its dedicated module
        thinking = self.thinking_module.extract(raw_llm_output)
        direct_answer = self.direct_answer_module.extract(raw_llm_output)
        conclusion = self.conclusion_module.extract(raw_llm_output)
        
        # Analysis needs direct_answer and conclusion to extract correctly
        analysis = self.analysis_module.extract(
            raw_llm_output, 
            direct_answer, 
            conclusion
        )
        
        # Table extraction (with fallback to chunks)
        table_data = self.table_module.extract(raw_llm_output, chunks)
        
        # Build StructuredOutput
        structured = StructuredOutput(
            direct_answer=direct_answer,
            raw_content=raw_llm_output,
            thinking=thinking,
            analysis=analysis,
            table_data=table_data,
            conclusion=conclusion,
            cv_references=[],  # TODO: Extract from table if needed
            parsing_warnings=[],
            fallback_used=table_data is None and chunks is not None
        )
        
        logger.info(
            f"[PROCESSOR] Extraction complete: "
            f"thinking={bool(thinking)}, "
            f"table={bool(table_data)}, "
            f"conclusion={bool(conclusion)}"
        )
        
        return structured
