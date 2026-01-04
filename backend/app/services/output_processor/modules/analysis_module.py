"""
Analysis Module - IMMUTABLE

Extracts and formats additional analysis content.
DO NOT MODIFY without explicit user request.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AnalysisModule:
    """
    Handles additional analysis content extraction.
    
    This captures detailed analysis, bullet points, or context
    that appears between direct answer and conclusion.
    """
    
    def extract(self, llm_output: str, direct_answer: str, conclusion: Optional[str]) -> Optional[str]:
        """
        Extract analysis section from LLM output.
        
        Strategy:
        1. Remove thinking and conclusion blocks
        2. Remove direct answer
        3. Remove tables
        4. Return remaining meaningful content
        
        Args:
            llm_output: Raw LLM response
            direct_answer: Extracted direct answer to remove
            conclusion: Extracted conclusion to remove
            
        Returns:
            Analysis content or None
        """
        if not llm_output:
            return None
        
        # Remove special blocks
        cleaned = llm_output
        cleaned = re.sub(r':::thinking[\s\S]*?:::', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r':::conclusion[\s\S]*?:::', '', cleaned, flags=re.IGNORECASE)
        
        # Remove direct answer
        if direct_answer and direct_answer in cleaned:
            cleaned = cleaned.replace(direct_answer, '', 1)
        
        # Remove tables
        cleaned = re.sub(r'\|[^\n]*\|[\s\S]*?\|[^\n]*\|', '', cleaned)
        
        # Clean up
        cleaned = cleaned.strip()
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        # Only return if substantial content (> 50 chars)
        if len(cleaned) > 50:
            logger.debug(f"[ANALYSIS] Extracted: {len(cleaned)} chars")
            return cleaned
        
        logger.debug("[ANALYSIS] No additional content")
        return None
    
    def format(self, content: str) -> str:
        """
        Format analysis content.
        
        NO custom labels - return content as-is.
        
        Args:
            content: Analysis text
            
        Returns:
            Formatted text (no modifications)
        """
        return content.strip()
