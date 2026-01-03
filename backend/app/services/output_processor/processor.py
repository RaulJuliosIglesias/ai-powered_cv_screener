"""
Main output processor orchestrating all extraction and parsing.

This module coordinates all output processing components to convert
raw LLM output into a guaranteed structured format.
"""

import logging
from typing import List, Dict, Any

from app.models.structured_output import StructuredOutput, CVReference
from .extractors import (
    ThinkingExtractor,
    ConclusionExtractor, 
    DirectAnswerExtractor,
    CVReferenceFormatter
)
from .table_parser import TableParser

logger = logging.getLogger(__name__)


class OutputProcessor:
    """
    Main processor coordinating all output extraction and formatting.
    
    Guarantees:
    - Always returns StructuredOutput (never fails)
    - Direct answer always exists
    - Other components are optional (None if not found)
    - Each component extraction is independent
    """
    
    def __init__(self):
        self.thinking_extractor = ThinkingExtractor()
        self.conclusion_extractor = ConclusionExtractor()
        self.direct_answer_extractor = DirectAnswerExtractor()
        self.cv_formatter = CVReferenceFormatter()
        self.table_parser = TableParser()
    
    def process(
        self,
        raw_llm_output: str,
        chunks: List[Dict[str, Any]] = None
    ) -> StructuredOutput:
        """
        Process raw LLM output into structured components.
        
        Args:
            raw_llm_output: Raw text from LLM
            chunks: Retrieved chunks for fallback generation
            
        Returns:
            StructuredOutput (always valid, never None)
        """
        logger.info("[OutputProcessor] Starting output processing")
        
        if not raw_llm_output:
            logger.warning("[OutputProcessor] Empty LLM output, generating fallback")
            return self._generate_complete_fallback(chunks)
        
        warnings = []
        
        # Step 1: Format CV references (clean up broken formats)
        logger.debug("[OutputProcessor] Step 1: Formatting CV references")
        formatted_text = self.cv_formatter.format(raw_llm_output)
        
        # Step 2: Extract thinking block
        logger.debug("[OutputProcessor] Step 2: Extracting thinking block")
        thinking = self.thinking_extractor.extract(formatted_text)
        if not thinking:
            warnings.append("No thinking block found")
        
        # Step 3: Extract conclusion block
        logger.debug("[OutputProcessor] Step 3: Extracting conclusion block")
        conclusion = self.conclusion_extractor.extract(formatted_text)
        if not conclusion:
            warnings.append("No conclusion block found")
        
        # Step 4: Extract direct answer (always succeeds with fallback)
        logger.debug("[OutputProcessor] Step 4: Extracting direct answer")
        direct_answer = self.direct_answer_extractor.extract(
            formatted_text,
            fallback="Based on the CV analysis below."
        )
        
        # Step 5: Parse table
        logger.debug("[OutputProcessor] Step 5: Parsing table")
        table_data = self.table_parser.parse(formatted_text, chunks)
        if not table_data:
            warnings.append("No table found or parsing failed")
        
        # Step 6: Extract CV references for metadata
        logger.debug("[OutputProcessor] Step 6: Extracting CV references")
        cv_references = self._extract_cv_references(formatted_text)
        
        # Build result
        result = StructuredOutput(
            direct_answer=direct_answer,
            raw_content=raw_llm_output,
            thinking=thinking,
            table_data=table_data,
            conclusion=conclusion,
            cv_references=cv_references,
            parsing_warnings=warnings,
            fallback_used=False
        )
        
        logger.info(
            f"[OutputProcessor] Processing complete: "
            f"thinking={'✓' if thinking else '✗'}, "
            f"table={'✓' if table_data else '✗'}, "
            f"conclusion={'✓' if conclusion else '✗'}, "
            f"warnings={len(warnings)}"
        )
        
        return result
    
    def _extract_cv_references(self, text: str) -> List[CVReference]:
        """
        Extract all CV references from text for metadata.
        
        Args:
            text: Processed text
            
        Returns:
            List of CVReference objects
        """
        import re
        
        references = []
        
        # Find all **[Name](cv:cv_xxx)** patterns
        pattern = r'\*\*\[([^\]]+)\]\(cv:cv_([a-f0-9]+)\)\*\*'
        matches = re.finditer(pattern, text)
        
        for match in matches:
            name = match.group(1).strip()
            cv_id = f"cv_{match.group(2)}"
            
            # Get context (surrounding text)
            start = max(0, match.start() - 50)
            end = min(len(text), match.end() + 50)
            context = text[start:end].strip()
            
            references.append(CVReference(
                cv_id=cv_id,
                name=name,
                context=context
            ))
        
        logger.debug(f"Extracted {len(references)} CV references")
        return references
    
    def _generate_complete_fallback(
        self,
        chunks: List[Dict[str, Any]]
    ) -> StructuredOutput:
        """
        Generate complete fallback response when LLM fails entirely.
        
        Args:
            chunks: Retrieved chunks
            
        Returns:
            StructuredOutput with generated content
        """
        logger.warning("[OutputProcessor] Generating complete fallback response")
        
        # Generate direct answer from chunks
        direct_answer = self._generate_fallback_answer(chunks)
        
        # Generate fallback table
        table_data = self.table_parser.parse("", chunks)
        
        # Generate fallback conclusion
        conclusion = self._generate_fallback_conclusion(chunks)
        
        return StructuredOutput(
            direct_answer=direct_answer,
            raw_content="[LLM output was empty or invalid]",
            thinking=None,
            table_data=table_data,
            conclusion=conclusion,
            cv_references=[],
            parsing_warnings=["Complete fallback used - LLM output was empty"],
            fallback_used=True
        )
    
    def _generate_fallback_answer(self, chunks: List[Dict[str, Any]]) -> str:
        """Generate direct answer from chunks."""
        if not chunks:
            return "No relevant candidates found in the database."
        
        # Count unique candidates
        cv_ids = set()
        for chunk in chunks:
            cv_id = chunk.get('metadata', {}).get('cv_id')
            if cv_id:
                cv_ids.add(cv_id)
        
        count = len(cv_ids)
        if count == 0:
            return "No candidates matched the query criteria."
        elif count == 1:
            return "One candidate was found matching the query criteria."
        else:
            return f"{count} candidates were found matching the query criteria."
    
    def _generate_fallback_conclusion(self, chunks: List[Dict[str, Any]]) -> str:
        """Generate conclusion from chunks."""
        if not chunks:
            return "No candidates found. Please try a different query or upload more CVs."
        
        # Get top candidate
        if chunks[0].get('metadata', {}).get('candidate_name'):
            top_name = chunks[0]['metadata']['candidate_name']
            return f"Based on relevance scores, {top_name} appears to be the strongest candidate. Review the analysis above for details."
        
        return "Review the candidates above and select the best fit based on your specific requirements."
