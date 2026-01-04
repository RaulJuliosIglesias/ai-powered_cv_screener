"""
Conclusion Module - IMMUTABLE

Extracts and formats :::conclusion::: blocks.
DO NOT MODIFY without explicit user request.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ConclusionModule:
    """
    Handles :::conclusion::: block extraction and formatting.
    
    The conclusion provides final recommendations and actionable next steps.
    """
    
    def extract(self, llm_output: str) -> Optional[str]:
        """
        Extract conclusion block from LLM output.
        
        Args:
            llm_output: Raw LLM response
            
        Returns:
            Conclusion content (without :::markers:::) or None
        """
        if not llm_output:
            return None
        
        # Pattern 1: :::conclusion ... :::
        match = re.search(r':::conclusion\s*([\s\S]*?)\s*:::', llm_output, re.IGNORECASE)
        if match:
            content = match.group(1).strip()
            if content:
                logger.debug(f"[CONCLUSION] Extracted: {len(content)} chars")
                return content
        
        # Pattern 2: :::conclusion ... (no closing, take rest of text)
        match = re.search(r':::conclusion\s*([\s\S]*)', llm_output, re.IGNORECASE)
        if match:
            content = match.group(1).strip()
            if content:
                logger.debug(f"[CONCLUSION] Extracted (no closing): {len(content)} chars")
                return content
        
        logger.debug("[CONCLUSION] Not found")
        return None
    
    def format(self, content: str) -> str:
        """
        Format conclusion content with markers.
        
        Args:
            content: Conclusion text (without markers)
            
        Returns:
            Formatted: ":::conclusion\n{content}\n:::"
        """
        if not content:
            return ""
        
        return f":::conclusion\n{content}\n:::"
