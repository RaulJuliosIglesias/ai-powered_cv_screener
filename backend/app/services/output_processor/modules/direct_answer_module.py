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
        4. Remove ALL prompt fragments and instructions
        
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
        
        # Remove tables (markdown format)
        cleaned = re.sub(r'\|[^\n]*\|[\s\S]*?\|[^\n]*\|', '', cleaned)
        
        # CRITICAL: Remove ALL code blocks that contain tables
        # Pattern: ``` ... ``` blocks containing | (table markers)
        def remove_table_code_blocks(match):
            content = match.group(1)
            if '|' in content and '---' in content:
                return ''  # Remove entire block if it's a table
            return match.group(0)  # Keep non-table code blocks
        cleaned = re.sub(r'```(?:markdown|code|text|)?\s*\n?([\s\S]*?)\n?```', remove_table_code_blocks, cleaned, flags=re.IGNORECASE)
        
        # Remove any remaining fenced code blocks (generic)
        cleaned = re.sub(r'```[\s\S]*?```', '', cleaned)
        
        # CRITICAL: Remove prompt fragments and instructions
        # Remove "ABSOLUTELY FORBIDDEN" section
        cleaned = re.sub(r'\*\*ABSOLUTELY FORBIDDEN[\s\S]*?(?=\n\n|$)', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'ABSOLUTELY FORBIDDEN[\s\S]*?(?=\n\n|$)', '', cleaned, flags=re.IGNORECASE)
        
        # Remove "Match Score Legend" section
        cleaned = re.sub(r'Match Score Legend[\s\S]*?(?=\n\n|Table|Conclusion|$)', '', cleaned, flags=re.IGNORECASE)
        
        # Remove "COMPARISON TABLES" and similar instruction headers
        cleaned = re.sub(r'COMPARISON TABLES[\s\S]*?(?=\n\n|$)', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'SPECIAL CASES[\s\S]*?(?=\n\n|$)', '', cleaned, flags=re.IGNORECASE)
        
        # Remove code blocks with instructions (```code Copy code```)
        cleaned = re.sub(r'```[\w]*\s*Copy code[\s\S]*?```', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'code\s*Copy code', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\bCopy\s+code\b', '', cleaned, flags=re.IGNORECASE)
        
        # Remove web search injection artifacts
        cleaned = re.sub(r'A web search was conducted on[\s\S]*?(?=\n\n|$)', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'IMPORTANT: Cite them using[\s\S]*?(?=\n\n|$)', '', cleaned, flags=re.IGNORECASE)
        
        # Remove hallucinated "References" section with fake URLs
        cleaned = re.sub(r'References?\s*\n[\s\S]*?(?=\n\n|Table|Conclusion|$)', '', cleaned, flags=re.IGNORECASE)
        
        # Remove bullet points with instructions (e.g., "❌ External URLs")
        cleaned = re.sub(r'[❌✓⭐•-]\s*(?:External URLs|Email addresses|Phone numbers|http)[^\n]*\n?', '', cleaned, flags=re.IGNORECASE)
        
        # Remove example format lines ("Text:", "List:", "Example:")
        cleaned = re.sub(r'^(?:Text|List|Example):\s*$', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'^(?:Text|List|Example):\s*\n(?:code\s*)?(?:Copy code\s*)?.*?$', '', cleaned, flags=re.MULTILINE)
        
        # Clean up whitespace
        cleaned = cleaned.strip()
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        cleaned = re.sub(r'^\s*\n', '', cleaned, flags=re.MULTILINE)
        
        # Take first paragraph (up to double newline or first 3 sentences)
        paragraphs = [p.strip() for p in cleaned.split('\n\n') if p.strip()]
        if paragraphs and paragraphs[0]:
            first_para = paragraphs[0].strip()
            
            # Skip if it looks like an instruction or prompt fragment
            skip_patterns = [
                r'^(?:Text|List|Example|References?)[:.]',
                r'^[❌✓⭐•-]\s',
                r'^code\s*Copy',
                r'FORBIDDEN',
                r'Match Score',
                r'http[s]?://'
            ]
            
            if any(re.search(pattern, first_para, re.IGNORECASE) for pattern in skip_patterns):
                # Skip contaminated paragraph, try next
                if len(paragraphs) > 1:
                    first_para = paragraphs[1].strip()
                else:
                    logger.warning("[DIRECT_ANSWER] First paragraph contaminated, no fallback")
                    return "Response could not be parsed cleanly."
            
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
