"""
Orchestrator - Assembles structured output using ONLY modular components.

This is the MAIN ENTRY POINT that RAG service calls.
It coordinates processor and modules to build final output SEQUENTIALLY.

DO NOT create parallel assembly logic - use modules parametrically.
"""

import logging
import re
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
        
        # STEP 0: PRE-PROCESS - Clean raw LLM output before any module processing
        cleaned_llm_output = self._pre_clean_llm_output(raw_llm_output)
        
        # STEP 1: Extract all components using processor (which uses modules)
        structured = self.processor.process(cleaned_llm_output, chunks)
        
        logger.info(
            f"[ORCHESTRATOR] Components extracted: "
            f"thinking={bool(structured.thinking)}, "
            f"table={bool(structured.table_data)}, "
            f"conclusion={bool(structured.conclusion)}, "
            f"analysis={bool(structured.analysis)}"
        )
        
        # STEP 1.5: Generate fallback analysis if none was extracted
        if not structured.analysis:
            fallback_analysis = self.analysis_module.generate_fallback(
                structured.direct_answer,
                structured.table_data,
                structured.conclusion
            )
            if fallback_analysis:
                structured.analysis = fallback_analysis
                logger.info(f"[ORCHESTRATOR] Generated fallback analysis: {len(fallback_analysis)} chars")
        
        # STEP 1.6: CRITICAL - Format candidate references with ÚNICO formato
        # Convierte [Nombre](cv_xxx) -> [📄](cv:cv_xxx) **Nombre**
        # Icono clicable + nombre en negrita (sin subrayado)
        if structured.direct_answer:
            structured.direct_answer = self._format_candidate_references(structured.direct_answer)
        if structured.analysis:
            structured.analysis = self._format_candidate_references(structured.analysis)
        if structured.conclusion:
            structured.conclusion = self._format_candidate_references(structured.conclusion)
        
        # STEP 2: Assemble output SEQUENTIALLY using module format methods
        parts = []
        
        # 1. Thinking block (collapsible dropdown)
        if structured.thinking:
            formatted_thinking = self.thinking_module.format(structured.thinking)
            parts.append(formatted_thinking)
        
        # 2. Direct answer (no label)
        formatted_answer = self.direct_answer_module.format(structured.direct_answer)
        parts.append(formatted_answer)
        
        # 3. Analysis (ALWAYS present - fallback generated if needed)
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
        
        # CRITICAL: Final cleanup - remove any duplicated paragraphs that slipped through
        final_answer = self._remove_duplicate_paragraphs(final_answer)
        
        # STEP 4: POST-PROCESS - Final cleanup of formatting issues
        final_answer = self._post_clean_output(final_answer)
        
        logger.info(f"[ORCHESTRATOR] Final answer: {len(final_answer)} chars")
        
        return structured, final_answer
    
    def _pre_clean_llm_output(self, text: str) -> str:
        """
        Pre-process raw LLM output BEFORE module extraction.
        
        This handles cases where LLM wraps EVERYTHING in a code block.
        """
        import re
        
        if not text:
            return text
        
        original_len = len(text)
        
        # CRITICAL: Detect if entire output is wrapped in a code block
        # Pattern: ```code\n...content...\n``` or ```\n...content...\n```
        code_block_wrapper = re.match(
            r'^```(?:code|markdown|text|)?\s*\n([\s\S]*?)\n```\s*$',
            text.strip(),
            flags=re.IGNORECASE
        )
        
        if code_block_wrapper:
            text = code_block_wrapper.group(1)
            logger.info(f"[ORCHESTRATOR] Unwrapped content from code block wrapper")
        
        # Also handle partial code blocks at the start
        text = re.sub(r'^```(?:code|markdown|text|)?\s*\n', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\n```\s*$', '', text)
        
        # Remove "code Copy code" artifacts
        text = re.sub(r'^code\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'code\s*Copy\s*code', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\bCopy\s+code\b', '', text, flags=re.IGNORECASE)
        
        if len(text) != original_len:
            logger.info(f"[ORCHESTRATOR] Pre-cleaned: {original_len} -> {len(text)} chars")
        
        return text.strip()
    
    def _format_candidate_references(self, text: str) -> str:
        """
        Formato ÚNICO para menciones de candidatos en TODAS las secciones.
        
        Convierte: [Nombre](cv:cv_xxx) o [Nombre](cv_xxx)
        A:         [📄](cv:cv_xxx) **Nombre**
        
        - El icono 📄 es el ÚNICO elemento clicable (abre PDF)
        - El nombre va en negrita, SIN subrayado, SIN link
        """
        if not text:
            return text
        
        # Paso 1: Normalizar links sin prefijo cv:
        # [Nombre](cv_xxx) -> [Nombre](cv:cv_xxx)
        text = re.sub(
            r'\[([^\]]+)\]\((cv_[a-z0-9_-]+)\)',
            r'[\1](cv:\2)',
            text,
            flags=re.IGNORECASE
        )
        
        # Paso 2: Convertir al formato final con icono + negrita
        # [Nombre](cv:cv_xxx) -> [📄](cv:cv_xxx) **Nombre**
        text = re.sub(
            r'\[([^\]]+)\]\((cv:cv_[a-z0-9_-]+)\)',
            r'[📄](\2) **\1**',
            text,
            flags=re.IGNORECASE
        )
        
        return text
    
    def _post_clean_output(self, text: str) -> str:
        """
        Post-process final output AFTER module formatting.
        
        This catches any formatting issues that slipped through modules.
        """
        import re
        
        if not text:
            return text
        
        original = text
        
        # 1. Fix bold formatting globally: ** Name** -> **Name**
        text = re.sub(r'\*\*\s+', '**', text)  # Remove space after **
        text = re.sub(r'\s+\*\*', '**', text)  # Remove space before **
        
        # 2. CRITICAL: Ensure ALL cv_id links have cv: prefix for frontend detection
        # Convert [Name](cv_xxx) -> [Name](cv:cv_xxx)
        text = re.sub(
            r'\[([^\]]+)\]\((cv_[a-z0-9_-]+)\)',
            r'[\1](cv:\2)',
            text,
            flags=re.IGNORECASE
        )
        
        # 3. Fix duplicated cv_id references: cv_xxx [cv_xxx](cv_xxx) -> [cv_xxx](cv:cv_xxx)
        text = re.sub(
            r'(cv_[a-z0-9_-]+)\s*\[\1\]\(\1\)',
            r'[\1](cv:\1)',
            text,
            flags=re.IGNORECASE
        )
        text = re.sub(
            r'(cv_[a-z0-9_-]+)\s*\[\1\]\(cv:\1\)',
            r'[\1](cv:\1)',
            text,
            flags=re.IGNORECASE
        )
        
        # 4. Fix triple cv_id: Name cv_xxx [cv_xxx](cv_xxx) -> **Name** cv_xxx
        text = re.sub(
            r'\*\*([^*]+)\*\*\s*(cv_[a-z0-9_-]+)\s*\[\2\]\(\2\)',
            r'**\1** \2',
            text,
            flags=re.IGNORECASE
        )
        text = re.sub(
            r'\*\*([^*]+)\*\*\s*(cv_[a-z0-9_-]+)\s*\[\2\]\(cv:\2\)',
            r'**\1** \2',
            text,
            flags=re.IGNORECASE
        )
        
        # 5. Remove any remaining "code" artifacts at line start
        text = re.sub(r'^code\s*$', '', text, flags=re.MULTILINE)
        
        # 6. Clean up excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        if text != original:
            logger.info(f"[ORCHESTRATOR] Post-cleaned formatting issues")
        
        return text.strip()
    
    def _remove_duplicate_paragraphs(self, text: str) -> str:
        """
        Final pass to remove duplicated paragraphs from assembled output.
        
        This catches cases where the same content appears multiple times
        due to LLM generating duplicates that weren't caught earlier.
        """
        import re
        
        if not text or len(text) < 100:
            return text
        
        paragraphs = text.split('\n\n')
        unique_paragraphs = []
        seen_normalized = set()
        
        for para in paragraphs:
            para_stripped = para.strip()
            if not para_stripped:
                continue
            
            # Normalize: lowercase, remove extra spaces, remove pipes
            normalized = ' '.join(para_stripped.lower().split())
            normalized = re.sub(r'\s*\|\s*', ' ', normalized)
            normalized = re.sub(r'\|[^|]*\|[^|]*\|?', '', normalized)
            normalized = ' '.join(normalized.split())[:150]  # First 150 chars for comparison
            
            # Skip if this is a table line (starts with |)
            if para_stripped.startswith('|'):
                unique_paragraphs.append(para)
                continue
            
            # Check for duplicate
            is_dup = normalized in seen_normalized
            if not is_dup and len(normalized) > 50:
                # Also check prefix match
                is_dup = any(
                    (normalized.startswith(s[:50]) or s.startswith(normalized[:50]))
                    for s in seen_normalized if len(s) > 30
                )
            
            if not is_dup:
                seen_normalized.add(normalized)
                unique_paragraphs.append(para)
            else:
                logger.debug(f"[ORCHESTRATOR] Removed duplicate paragraph: {para_stripped[:60]}...")
        
        result = '\n\n'.join(unique_paragraphs)
        
        if len(result) < len(text):
            logger.info(f"[ORCHESTRATOR] Removed duplicates: {len(text)} -> {len(result)} chars")
        
        return result


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


def reset_orchestrator():
    """Reset singleton for testing or after code changes."""
    global _orchestrator
    _orchestrator = None
    logger.info("[ORCHESTRATOR] Singleton reset")
