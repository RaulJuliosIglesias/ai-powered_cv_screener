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
        1. First try to extract explicit ### Analysis section
        2. If not found, fall back to extracting content between direct answer and table/conclusion
        3. Remove ALL prompt fragments and contamination
        
        Args:
            llm_output: Raw LLM response
            direct_answer: Extracted direct answer to remove
            conclusion: Extracted conclusion to remove
            
        Returns:
            Analysis content or None
        """
        if not llm_output:
            return None
        
        # FIRST: Try to extract explicit ### Analysis section
        analysis_match = re.search(
            r'###?\s*Analysis\s*\n([\s\S]*?)(?=\n\||\n:::conclusion|\n###|\Z)',
            llm_output,
            flags=re.IGNORECASE
        )
        
        if analysis_match:
            analysis_content = analysis_match.group(1).strip()
            # Clean up the analysis content
            analysis_content = self._clean_content(analysis_content)
            if analysis_content and len(analysis_content) > 30:
                logger.info(f"[ANALYSIS] Extracted explicit Analysis section: {len(analysis_content)} chars")
                return analysis_content
        
        # FALLBACK: Remove special blocks and extract remaining content
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
        
        # CRITICAL: Remove "CRITICAL RULES" section (prompt leakage)
        cleaned = re.sub(r'##?\s*CRITICAL RULES[\s\S]*?(?=\n\n[A-Z]|\n\n\*\*[A-Z]|$)', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\bCRITICAL RULES\b[^\n]*\n?', '', cleaned, flags=re.IGNORECASE)
        
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
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
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
        # Be precise to avoid false positives like "No candidates match"
        contamination_patterns = [
            r'ABSOLUTELY FORBIDDEN',
            r'Match Score Legend',
            r'##\s*COMPARISON TABLES',
            r'code\s*Copy code',
            r'^References?:\s*$',
            r'web search was conducted',
            r'##?\s*CRITICAL RULES',
            r'^-\s*ALL three sections',
            r'##?\s*MANDATORY RESPONSE FORMAT',
            r'^-\s*Use.*Candidate Name.*CV_ID.*format',
            r'^-\s*If no match.*state clearly in all',
            r'^-\s*Base everything on CV data',
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
    
    def _clean_content(self, text: str) -> str:
        """Clean analysis content by removing prompt contamination."""
        if not text:
            return text
        
        # Remove prompt contamination patterns
        contamination_patterns = [
            r'\*\*ABSOLUTELY FORBIDDEN[\s\S]*?(?=\n\n|$)',
            r'ABSOLUTELY FORBIDDEN[\s\S]*?(?=\n\n|$)',
            r'##?\s*CRITICAL RULES[\s\S]*?(?=\n\n|$)',
            r'##?\s*MANDATORY RESPONSE FORMAT[\s\S]*?(?=\n\n|$)',
            r'code\s*Copy code',
            r'\bCopy\s+code\b',
        ]
        
        for pattern in contamination_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Clean up whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()
        
        return text
    
    def format(self, content: str) -> str:
        """
        Format analysis content with a visible header.
        
        Adds "### Analysis" header so users can see the reasoning section.
        
        Args:
            content: Analysis text
            
        Returns:
            Formatted text with Analysis header
        """
        text = content.strip()
        if not text:
            return text
        
        # Add Analysis header if not already present
        if not text.startswith('###') and not text.startswith('## '):
            return f"### Analysis\n\n{text}"
        
        return text
