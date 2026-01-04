"""
Direct Answer Module - IMMUTABLE

Extracts and formats the direct answer (1-3 sentences).
DO NOT MODIFY without explicit user request.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class DirectAnswerModule:
    """
    Handles direct answer extraction and formatting.
    
    The direct answer is the concise 1-3 sentence response to the user's query.
    """
    
    def extract(self, llm_output: str) -> str:
        """
        Extract direct answer from LLM output.
        
        Strategy:
        1. Look for text between :::thinking::: and table/conclusion
        2. Take first 1-3 sentences
        3. Fallback to first paragraph if no structure found
        
        Args:
            llm_output: Raw LLM response
            
        Returns:
            Direct answer text (always returns something, never None)
        """
        if not llm_output:
            return "No response generated."
        
        # Remove thinking block first
        cleaned = re.sub(r':::thinking[\s\S]*?:::', '', llm_output, flags=re.IGNORECASE)
        
        # Remove conclusion block
        cleaned = re.sub(r':::conclusion[\s\S]*?:::', '', cleaned, flags=re.IGNORECASE)
        
        # Remove tables
        cleaned = re.sub(r'\|[^\n]*\|[\s\S]*?\|[^\n]*\|', '', cleaned)
        
        # Clean up whitespace
        cleaned = cleaned.strip()
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        # Take first paragraph (up to double newline or first 3 sentences)
        paragraphs = cleaned.split('\n\n')
        if paragraphs and paragraphs[0]:
            first_para = paragraphs[0].strip()
            
            # Limit to first 3 sentences
            sentences = re.split(r'[.!?]\s+', first_para)
            direct_answer = '. '.join(sentences[:3])
            if not direct_answer.endswith('.'):
                direct_answer += '.'
            
            logger.debug(f"[DIRECT_ANSWER] Extracted: {len(direct_answer)} chars")
            return direct_answer
        
        # Fallback: first 200 chars
        fallback = cleaned[:200].strip()
        logger.warning(f"[DIRECT_ANSWER] Fallback used: {len(fallback)} chars")
        return fallback if fallback else "Response could not be parsed."
    
    def format(self, content: str) -> str:
        """
        Format direct answer.
        
        NO custom labels - return content as-is.
        
        Args:
            content: Direct answer text
            
        Returns:
            Formatted text (no modifications)
        """
        return content.strip()
