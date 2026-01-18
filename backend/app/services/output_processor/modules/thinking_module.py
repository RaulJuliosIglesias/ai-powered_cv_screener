"""
Thinking Module - IMMUTABLE

Extracts and formats :::thinking::: blocks (collapsible reasoning).
DO NOT MODIFY without explicit user request.
"""

import logging
import re
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
                # Strip markdown since thinking dropdown doesn't render it
                content = self._strip_markdown(content)
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
                # Strip markdown since thinking dropdown doesn't render it
                content = self._strip_markdown(content)
                logger.debug(f"[THINKING] Extracted (no closing): {len(content)} chars")
                return content
        
        logger.debug("[THINKING] Not found")
        return None
    
    def _strip_markdown(self, text: str) -> str:
        """
        Convert markdown to plain text for the thinking dropdown.
        
        The thinking process UI doesn't render markdown, so we convert:
        - **[Name](cv:cv_xxx)** -> Name (cv_xxx)
        - **text** -> text
        - *text* -> text
        - [text](url) -> text
        - # headers -> headers
        - * bullets -> - bullets
        
        Args:
            text: Text with markdown formatting
            
        Returns:
            Plain text without markdown syntax
        """
        if not text:
            return text
        
        # Convert **[Name](cv:cv_xxx)** to Name (cv_xxx)
        text = re.sub(r'\*\*\[([^\]]+)\]\(cv:(cv_[a-z0-9_-]+)\)\*\*', r'\1 (\2)', text, flags=re.IGNORECASE)
        
        # Convert [text](url) links to just text
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        
        # Remove bold **text** -> text
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
        
        # Remove italic *text* -> text (but not bullet points)
        text = re.sub(r'(?<!\n)\*([^*\n]+)\*(?!\*)', r'\1', text)
        
        # Convert markdown headers to plain text
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        
        # Convert * bullet points to - (cleaner in plain text)
        text = re.sub(r'^\*\s+', '- ', text, flags=re.MULTILINE)
        
        # Clean up any double spaces
        text = re.sub(r'  +', ' ', text)
        
        return text
    
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
