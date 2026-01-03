"""
Content extractors for LLM output parsing.

Each extractor is independent and returns None on failure.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ThinkingExtractor:
    """Extracts :::thinking::: blocks from LLM output."""
    
    @staticmethod
    def extract(text: str) -> Optional[str]:
        """
        Extract thinking block.
        
        Returns:
            Thinking content or None if not found
        """
        if not text:
            return None
        
        # Pattern 1: :::thinking ... :::
        match = re.search(r':::thinking\s*([\s\S]*?)\s*:::', text, re.IGNORECASE)
        if match:
            content = match.group(1).strip()
            if content:
                logger.debug(f"Extracted thinking block: {len(content)} chars")
                return content
        
        # Pattern 2: :::thinking ... (no closing, take until next section)
        match = re.search(
            r':::thinking\s*([\s\S]*?)(?=\n\n\*\*|\n:::|\n\||\Z)',
            text,
            re.IGNORECASE
        )
        if match:
            content = match.group(1).strip()
            if content:
                logger.debug(f"Extracted thinking block (no closing): {len(content)} chars")
                return content
        
        logger.debug("No thinking block found")
        return None


class ConclusionExtractor:
    """Extracts :::conclusion::: blocks from LLM output."""
    
    @staticmethod
    def extract(text: str) -> Optional[str]:
        """
        Extract conclusion block.
        
        Returns:
            Conclusion content or None if not found
        """
        if not text:
            return None
        
        # Pattern 1: :::conclusion ... :::
        match = re.search(r':::conclusion\s*([\s\S]*?)\s*:::', text, re.IGNORECASE)
        if match:
            content = match.group(1).strip()
            if content:
                logger.debug(f"Extracted conclusion block: {len(content)} chars")
                return content
        
        # Pattern 2: :::conclusion ... (no closing)
        match = re.search(r':::conclusion\s*([\s\S]*)$', text, re.IGNORECASE)
        if match:
            content = match.group(1).strip()
            if content:
                logger.debug(f"Extracted conclusion block (no closing): {len(content)} chars")
                return content
        
        # Pattern 3: Markdown headers
        conclusion_headers = [
            r'\n##\s*Conclusi[oó]n\s*\n([\s\S]*)$',
            r'\n\*\*Conclusi[oó]n:?\*\*\s*\n?([\s\S]*)$',
            r'\nConclusion:?\s*\n([\s\S]*)$'
        ]
        
        for pattern in conclusion_headers:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                if content:
                    logger.debug(f"Extracted conclusion from header: {len(content)} chars")
                    return content
        
        logger.debug("No conclusion block found")
        return None


class DirectAnswerExtractor:
    """Extracts or generates direct answer from LLM output."""
    
    @staticmethod
    def extract(text: str, fallback: str = "Based on the analysis below.") -> str:
        """
        Extract direct answer.
        
        Always returns a string (uses fallback if needed).
        
        Args:
            text: LLM output text
            fallback: Default text if extraction fails
            
        Returns:
            Direct answer text (never None)
        """
        if not text:
            logger.warning("Empty text, using fallback direct answer")
            return fallback
        
        # Remove thinking and conclusion blocks for cleaner extraction
        clean_text = text
        clean_text = re.sub(r':::thinking[\s\S]*?:::', '', clean_text, flags=re.IGNORECASE)
        clean_text = re.sub(r':::conclusion[\s\S]*?:::', '', clean_text, flags=re.IGNORECASE)
        
        # Look for "Direct Answer" or "Answer" section
        match = re.search(
            r'\*\*(?:Direct\s+)?Answer\*\*\s*\n(.*?)(?=\n\n|\n\*\*|\n\||\Z)',
            clean_text,
            re.IGNORECASE | re.DOTALL
        )
        if match:
            answer = match.group(1).strip()
            if answer:
                logger.debug(f"Extracted direct answer: {len(answer)} chars")
                return answer
        
        # Fallback: Take first paragraph after thinking block
        paragraphs = [p.strip() for p in clean_text.split('\n\n') if p.strip()]
        for para in paragraphs:
            # Skip table lines
            if '|' in para and para.count('|') > 2:
                continue
            # Skip section headers
            if para.startswith('#') or para.startswith('**'):
                continue
            # Skip very short paragraphs
            if len(para) < 20:
                continue
            
            logger.debug(f"Using first valid paragraph as direct answer: {len(para)} chars")
            return para
        
        # Ultimate fallback
        logger.warning("Could not extract direct answer, using fallback")
        return fallback


class CVReferenceFormatter:
    """Formats and cleans CV references in text."""
    
    @staticmethod
    def format(text: str) -> str:
        """
        Clean and format CV references.
        
        Converts all broken formats to: **[Name](cv:cv_xxx)**
        
        Args:
            text: Text with potentially broken CV references
            
        Returns:
            Text with cleaned CV references
        """
        if not text:
            return text
        
        # Pattern: "Name Role** cv_xxx [cv_xxx](cv_xxx)"
        text = re.sub(
            r'\*\*([^*]+)\*\*\s*cv_([a-f0-9]+)\s*\[cv_[a-f0-9]+\]\(cv_[a-f0-9]+\)',
            r'**[\1](cv:cv_\2)**',
            text
        )
        
        # Pattern: Fix broken bold "** Name**" -> "**Name**"
        text = re.sub(r'\*\*\s+([^*]+?)\s*\*\*', r'**\1**', text)
        
        # Pattern: "**Word** cv_xxx [cv_xxx](cv_xxx)" (non-candidate, remove broken ref)
        text = re.sub(
            r'\*\*(Solutions|Staff|Cloud|Senior|Junior|Lead|Manager|Director|Engineer|Developer|Architect|Brand|Human Resources|NFT)\*\*\s*cv_[a-f0-9]+\s*\[cv_[a-f0-9]+\]\(cv_[a-f0-9]+\)',
            r'\1',
            text,
            flags=re.IGNORECASE
        )
        
        # Pattern: Standalone "cv_xxx [cv_xxx](cv_xxx)" without name
        text = re.sub(
            r'(?<!\w)cv_([a-f0-9]+)\s*\[cv_[a-f0-9]+\]\(cv_[a-f0-9]+\)',
            r'[CV \1](cv:cv_\1)',
            text
        )
        
        # Pattern: Bare cv_xxx not in parentheses (remove if not part of link)
        # Be careful not to remove cv_xxx that are part of valid links
        text = re.sub(
            r'(?<!\(cv:)(?<!\[)cv_[a-f0-9]+(?!\))',
            '',
            text
        )
        
        logger.debug("Formatted CV references")
        return text.strip()
