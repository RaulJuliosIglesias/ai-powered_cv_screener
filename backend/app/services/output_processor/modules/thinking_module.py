"""
Thinking Module - IMMUTABLE

Extracts and formats :::thinking::: blocks (collapsible reasoning).
DO NOT MODIFY without explicit user request.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ThinkingModule:
    """
    Handles :::thinking::: block extraction and formatting.
    
    This creates the collapsible reasoning dropdown in the UI.
    """
    
    def extract(self, llm_output: str) -> Optional[str]:
        """
        Extract thinking block from LLM output.
        
        Args:
            llm_output: Raw LLM response
            
        Returns:
            Thinking content (without :::markers:::) or None
        """
        if not llm_output:
            return None
        
        # Pattern 1: :::thinking ... :::
        match = re.search(r':::thinking\s*([\s\S]*?)\s*:::', llm_output, re.IGNORECASE)
        if match:
            content = match.group(1).strip()
            if content:
                logger.debug(f"[THINKING] Extracted: {len(content)} chars")
                return content
        
        # Pattern 2: :::thinking ... (no closing)
        match = re.search(
            r':::thinking\s*([\s\S]*?)(?=\n\n\*\*|\n:::|\n\||\Z)',
            llm_output,
            re.IGNORECASE
        )
        if match:
            content = match.group(1).strip()
            if content:
                logger.debug(f"[THINKING] Extracted (no closing): {len(content)} chars")
                return content
        
        logger.debug("[THINKING] Not found")
        return None
    
    def format(self, content: str) -> str:
        """
        Format thinking content with markers.
        
        Args:
            content: Thinking text (without markers)
            
        Returns:
            Formatted: ":::thinking\n{content}\n:::"
        """
        if not content:
            return ""
        
        return f":::thinking\n{content}\n:::"
