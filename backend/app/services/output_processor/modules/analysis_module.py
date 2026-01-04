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
        4. Remove ALL prompt fragments and contamination
        5. Return remaining meaningful content
        
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
        
        # CRITICAL: Remove ALL code blocks that contain tables
        def remove_table_code_blocks(match):
            content = match.group(1)
            if '|' in content and '---' in content:
                return ''  # Remove entire block if it's a table
            return match.group(0)  # Keep non-table code blocks
        cleaned = re.sub(r'```(?:markdown|code|text|)?\s*\n?([\s\S]*?)\n?```', remove_table_code_blocks, cleaned, flags=re.IGNORECASE)
        
        # Remove any remaining fenced code blocks
        cleaned = re.sub(r'```[\s\S]*?```', '', cleaned)
        
        # CRITICAL: Remove ALL prompt contamination (same as DirectAnswerModule)
        cleaned = re.sub(r'\*\*ABSOLUTELY FORBIDDEN[\s\S]*?(?=\n\n|$)', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'ABSOLUTELY FORBIDDEN[\s\S]*?(?=\n\n|$)', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'Match Score Legend[\s\S]*?(?=\n\n|Table|Conclusion|$)', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'COMPARISON TABLES[\s\S]*?(?=\n\n|$)', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'SPECIAL CASES[\s\S]*?(?=\n\n|$)', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'```[\w]*\s*Copy code[\s\S]*?```', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'code\s*Copy code', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\bCopy\s+code\b', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'A web search was conducted on[\s\S]*?(?=\n\n|$)', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'IMPORTANT: Cite them using[\s\S]*?(?=\n\n|$)', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'References?\s*\n[\s\S]*?(?=\n\n|Table|Conclusion|$)', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'[❌✓⭐•-]\s*(?:External URLs|Email addresses|Phone numbers|http)[^\n]*\n?', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'^(?:Text|List|Example):\s*$', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'^(?:Text|List|Example):\s*\n(?:code\s*)?(?:Copy code\s*)?.*?$', '', cleaned, flags=re.MULTILINE)
        
        # Clean up
        cleaned = cleaned.strip()
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        cleaned = re.sub(r'^\s*\n', '', cleaned, flags=re.MULTILINE)
        
        # Validate: ensure no prompt contamination remains
        contamination_patterns = [
            r'FORBIDDEN',
            r'Match Score Legend',
            r'COMPARISON TABLES',
            r'code\s*Copy code',
            r'^References?:',
            r'web search was conducted'
        ]
        
        if any(re.search(pattern, cleaned, re.IGNORECASE) for pattern in contamination_patterns):
            logger.warning("[ANALYSIS] Contaminated content detected, discarding")
            return None
        
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
