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
                # Clean prompt contamination from conclusion
                content = self._clean_contamination(content)
                if content:
                    logger.debug(f"[CONCLUSION] Extracted: {len(content)} chars")
                    return content
        
        # Pattern 2: :::conclusion ... (no closing, take rest of text)
        match = re.search(r':::conclusion\s*([\s\S]*)', llm_output, re.IGNORECASE)
        if match:
            content = match.group(1).strip()
            if content:
                # Clean prompt contamination from conclusion
                content = self._clean_contamination(content)
                if content:
                    logger.debug(f"[CONCLUSION] Extracted (no closing): {len(content)} chars")
                    return content
        
        logger.debug("[CONCLUSION] Not found")
        return None
    
    def _clean_contamination(self, text: str) -> str:
        """Remove prompt fragments from conclusion text."""
        # Remove web search artifacts
        text = re.sub(r'A web search was conducted[\s\S]*?(?=\n\n|$)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'IMPORTANT: Cite them[\s\S]*?(?=\n\n|$)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'References?\s*\n[\s\S]*?(?=\n\n|$)', '', text, flags=re.IGNORECASE)
        
        # Remove instruction fragments
        text = re.sub(r'code\s*Copy code', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^(?:Text|List|Example):\s*', '', text, flags=re.MULTILINE)
        
        # CRITICAL: Remove "CRITICAL RULES" section (prompt leakage)
        text = re.sub(r'##?\s*CRITICAL RULES[\s\S]*?(?=\n\n[A-Z]|\n\n\*\*[A-Z]|$)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\bCRITICAL RULES\b[^\n]*\n?', '', text, flags=re.IGNORECASE)
        
        # Remove specific leaked instruction lines (be precise to avoid false positives)
        leaked_instructions = [
            r'-\s*ALL three sections \(thinking,? direct answer,? conclusion\) are MANDATORY[^\n]*\n?',
            r'-\s*Use \*?\*?\[?Candidate Name\]?\*?\*?\s*\(?CV_ID\)?.*?format for EVERY candidate mention[^\n]*\n?',
            r'-\s*Use Candidate Name CV_ID CV_ID format[^\n]*\n?',
            r'-\s*If no match,? state clearly in all sections[^\n]*\n?',
            r'-\s*Base everything on CV data only—no assumptions[^\n]*\n?',
            r'##?\s*MANDATORY RESPONSE FORMAT[^\n]*\n?',
        ]
        for pattern in leaked_instructions:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove hallucinated URLs
        text = re.sub(r'(?:engx\.space|resumekraft\.com|github\.com|linkedin\.com)[^\s]*', '', text, flags=re.IGNORECASE)
        
        # CRITICAL: Fix malformed bold formatting from LLM
        # LLM sometimes generates "** Name**" instead of "**Name**"
        text = self._fix_bold_formatting(text)
        
        return text.strip()
    
    def _fix_bold_formatting(self, text: str) -> str:
        """
        Fix malformed bold markdown formatting from LLM.
        
        LLM generates two formats:
        1. **[Name](cv:id)** - link inside bold (PRESERVE THIS)
        2. ** Name** - name in bold only (FIX THIS)
        
        Args:
            text: Text that may have malformed bold
            
        Returns:
            Text with corrected bold formatting
        """
        if not text or '*' not in text:
            return text
        
        # Case 1: If text contains **[...](...)**  format, preserve it exactly
        if re.search(r'\*\*\s*\[.+?\]\(.+?\)\s*\*\*', text):
            # This is the correct format with link inside bold, don't touch it
            return text
        
        # Case 2: Fix "** text**" format (name in bold, no link inside)
        # Remove ALL spaces after opening ** and before closing **
        text = re.sub(r'\*\*[ \t\u00a0]+', '**', text)
        text = re.sub(r'[ \t\u00a0]+\*\*', '**', text)
        
        return text
    
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
