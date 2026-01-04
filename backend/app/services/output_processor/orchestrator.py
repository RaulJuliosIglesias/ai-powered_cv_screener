"""
Orchestrator - Assembles structured output using ONLY modular components.

This is the MAIN ENTRY POINT that RAG service calls.
It coordinates processor and modules to build final output SEQUENTIALLY.

DO NOT create parallel assembly logic - use modules parametrically.
"""

import logging
from typing import List, Dict, Any

from app.models.structured_output import StructuredOutput
from .processor import OutputProcessor
from .modules import (
    ThinkingModule,
    DirectAnswerModule,
    AnalysisModule,
    TableModule,
    ConclusionModule
)

logger = logging.getLogger(__name__)


class OutputOrchestrator:
    """
    Main orchestrator - RAG service calls this.
    
    Coordinates:
    1. Extraction (via OutputProcessor using modules)
    2. Sequential assembly (using each module's format method)
    """
    
    def __init__(self):
        """Initialize with processor and modules."""
        self.processor = OutputProcessor()
        
        # Module instances for formatting
        self.thinking_module = ThinkingModule()
        self.direct_answer_module = DirectAnswerModule()
        self.analysis_module = AnalysisModule()
        self.table_module = TableModule()
        self.conclusion_module = ConclusionModule()
        
        logger.info("[ORCHESTRATOR] Initialized")
    
    def process(
        self,
        raw_llm_output: str,
        chunks: List[Dict[str, Any]] = None
    ) -> tuple[StructuredOutput, str]:
        """
        Process LLM output into structured components and formatted answer.
        
        This is the MAIN METHOD that RAG service calls.
        
        Args:
            raw_llm_output: Raw text from LLM
            chunks: Retrieved CV chunks for fallback
            
        Returns:
            Tuple of (StructuredOutput, formatted_answer_string)
        """
        logger.info("[ORCHESTRATOR] Starting processing")
        
        # STEP 1: Extract all components using processor (which uses modules)
        structured = self.processor.process(raw_llm_output, chunks)
        
        logger.info(
            f"[ORCHESTRATOR] Components extracted: "
            f"thinking={bool(structured.thinking)}, "
            f"table={bool(structured.table_data)}, "
            f"conclusion={bool(structured.conclusion)}"
        )
        
        # STEP 2: Assemble output SEQUENTIALLY using module format methods
        parts = []
        
        # 1. Thinking block (collapsible dropdown)
        if structured.thinking:
            formatted_thinking = self.thinking_module.format(structured.thinking)
            parts.append(formatted_thinking)
        
        # 2. Direct answer (no label)
        formatted_answer = self.direct_answer_module.format(structured.direct_answer)
        parts.append(formatted_answer)
        
        # 3. Analysis (if exists)
        if structured.analysis:
            formatted_analysis = self.analysis_module.format(structured.analysis)
            parts.append(formatted_analysis)
        
        # 4. Table (if exists)
        if structured.table_data:
            formatted_table = self.table_module.format(structured.table_data)
            parts.append(formatted_table)
        
        # 5. Conclusion block
        if structured.conclusion:
            formatted_conclusion = self.conclusion_module.format(structured.conclusion)
            parts.append(formatted_conclusion)
        
        # Join with double newlines for readability
        final_answer = "\n\n".join(parts)
        
        logger.info(f"[ORCHESTRATOR] Final answer: {len(final_answer)} chars")
        
        return structured, final_answer


# Singleton instance
_orchestrator = None


def get_orchestrator() -> OutputOrchestrator:
    """
    Get singleton orchestrator instance.
    
    This is what RAG service imports and uses.
    """
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = OutputOrchestrator()
    return _orchestrator
