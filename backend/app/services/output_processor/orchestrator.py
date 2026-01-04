"""
Structured Output Orchestrator.

This is the MAIN ENTRY POINT that RAG service calls.
It orchestrates all modular components to build the final structured output.

Architecture:
- RAG service calls: OutputOrchestrator.process()
- Orchestrator uses:
  1. Processor (extracts components from LLM output)
  2. Formatter (assembles final markdown with labels)
- Returns: StructuredOutput object

CRITICAL: This is the ONLY place RAG service should interact with output processing.
Do NOT modify this when changing RAG service logic - keep separation clean.
"""

import logging
from typing import List, Dict, Any

from app.models.structured_output import StructuredOutput
from .processor import OutputProcessor
from .formatter import StructuredOutputFormatter

logger = logging.getLogger(__name__)


class OutputOrchestrator:
    """
    Main orchestrator for structured output processing.
    
    This is what RAG service calls. It coordinates:
    - Component extraction (thinking, direct answer, table, conclusion)
    - Final assembly with proper formatting and labels
    
    Components used (all modular):
    1. OutputProcessor - extracts components from LLM output
    2. StructuredOutputFormatter - formats components with labels
    """
    
    def __init__(self):
        """Initialize orchestrator with component services."""
        self.processor = OutputProcessor()
        self.formatter = StructuredOutputFormatter()
        logger.info("[ORCHESTRATOR] Initialized with processor and formatter")
    
    def process(
        self,
        raw_llm_output: str,
        chunks: List[Dict[str, Any]] = None
    ) -> tuple[StructuredOutput, str]:
        """
        Process raw LLM output into structured output with formatted answer.
        
        This is the MAIN METHOD that RAG service calls.
        
        Args:
            raw_llm_output: Raw text from LLM
            chunks: Retrieved CV chunks for fallback
            
        Returns:
            Tuple of (StructuredOutput object, formatted_answer_string)
            
        Flow:
            1. Extract components (thinking, direct answer, table, conclusion)
            2. Build StructuredOutput object
            3. Format final markdown with labels
            4. Return both structured data and display string
        """
        logger.info("[ORCHESTRATOR] Starting output processing")
        
        # Step 1: Extract all components using processor
        structured_output = self.processor.process(
            raw_llm_output=raw_llm_output,
            chunks=chunks
        )
        
        logger.info(
            f"[ORCHESTRATOR] Components extracted: "
            f"thinking={bool(structured_output.thinking)}, "
            f"table={bool(structured_output.table_data)}, "
            f"conclusion={bool(structured_output.conclusion)}"
        )
        
        # Step 2: Format final answer with labels using formatter
        formatted_answer = self.formatter.build_formatted_answer(structured_output)
        
        logger.info(
            f"[ORCHESTRATOR] Final answer formatted: {len(formatted_answer)} chars"
        )
        
        # Step 3: Return both structured data and formatted string
        return structured_output, formatted_answer


# Singleton instance for easy import
_orchestrator_instance = None


def get_orchestrator() -> OutputOrchestrator:
    """
    Get singleton orchestrator instance.
    
    This is what RAG service should import and use.
    """
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = OutputOrchestrator()
    return _orchestrator_instance
