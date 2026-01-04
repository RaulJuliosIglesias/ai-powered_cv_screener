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
        
        # Remove "Match Score Legend" section
        cleaned = re.sub(r'Match Score Legend[\s\S]*?(?=\n\n|Table|Conclusion|$)', '', cleaned, flags=re.IGNORECASE)
        
        # Remove "COMPARISON TABLES" and similar instruction headers
        cleaned = re.sub(r'COMPARISON TABLES[\s\S]*?(?=\n\n|$)', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'SPECIAL CASES[\s\S]*?(?=\n\n|$)', '', cleaned, flags=re.IGNORECASE)
        
        # Remove code blocks with instructions (```code Copy code```)
        cleaned = re.sub(r'```[\w]*\s*Copy code[\s\S]*?```', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'code\s*Copy code', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\bCopy\s+code\b', '', cleaned, flags=re.IGNORECASE)
        
        # Remove standalone "code" at start of line (artifact from LLM)
        cleaned = re.sub(r'^code\s*$', '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
        cleaned = re.sub(r'^code\s+', '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
        
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
        
        # CRITICAL: Detect and remove duplicated paragraphs BEFORE processing
        unique_paragraphs = []
        seen = set()
        for para in paragraphs:
            # Normalize for comparison: remove extra spaces, pipes, special chars, lowercase
            normalized = ' '.join(para.split()).lower()
            # Remove trailing pipe patterns like "| Other Attributes | ... |"
            normalized = re.sub(r'\|[^|]*\|[^|]*\|?$', '', normalized).strip()
            # Remove any remaining pipes and extra whitespace
            normalized = re.sub(r'\s*\|\s*', ' ', normalized).strip()
            normalized = ' '.join(normalized.split())  # Re-normalize spaces
            
            # Check for exact duplicate or prefix duplicate (first 100 chars match)
            is_duplicate = normalized in seen
            if not is_duplicate and len(normalized) > 100:
                # Also check if first 100 chars already seen (handles slight variations)
                prefix = normalized[:100]
                is_duplicate = any(s.startswith(prefix) or prefix.startswith(s[:100]) for s in seen if len(s) > 50)
            
            if not is_duplicate and len(normalized) > 10:
                seen.add(normalized)
                unique_paragraphs.append(para)
        
        paragraphs = unique_paragraphs
        if paragraphs and paragraphs[0]:
            first_para = paragraphs[0].strip()
            
            # Skip if it looks like an instruction or prompt fragment
            # Be precise to avoid false positives like "No candidates match"
            skip_patterns = [
                r'^(?:Text|List|Example|References?)[:.]',
                r'^[❌✓•]\s',  # Removed ⭐- to allow star ratings and bullet points
                r'^code\s*Copy',
                r'ABSOLUTELY FORBIDDEN',
                r'Match Score Legend',
                r'^http[s]?://',
                r'^##?\s*CRITICAL RULES',
                r'^-\s*ALL three sections',
                r'^##?\s*MANDATORY',
                r'^-\s*Use.*Candidate Name.*CV_ID.*format',
                r'^-\s*If no match.*state clearly in all',
                r'^-\s*Base everything on CV data',
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
            
            # CRITICAL: Limpiar frases de transición al análisis
            direct_answer = self._clean_transition_phrases(direct_answer)
            
            logger.debug(f"[DIRECT_ANSWER] Extracted: {len(direct_answer)} chars")
            return direct_answer
        
        # Fallback: Try to extract ANY meaningful content
        # Look for sentences that start with common response patterns
        meaningful_patterns = [
            r'(No candidates?[^.]*\.)',
            r'(None of the[^.]*\.)',
            r'(The best candidate[^.]*\.)',
            r'(Based on[^.]*\.)',
            r'([A-Z][^.]{20,}\.)'
        ]
        
        for pattern in meaningful_patterns:
            match = re.search(pattern, llm_output, re.IGNORECASE)
            if match:
                fallback = match.group(1).strip()
                logger.info(f"[DIRECT_ANSWER] Pattern fallback: {fallback[:50]}...")
                return fallback
        
        # Last resort: first 200 chars of cleaned content
        fallback = cleaned[:200].strip() if cleaned else ""
        if fallback:
            logger.warning(f"[DIRECT_ANSWER] Char fallback used: {len(fallback)} chars")
            return fallback
        
        # Generate a generic response based on conclusion if available
        conclusion_match = re.search(r':::conclusion\s*([\s\S]*?):::', llm_output, re.IGNORECASE)
        if conclusion_match:
            conclusion_text = conclusion_match.group(1).strip()
            first_sentence = re.split(r'[.!?]', conclusion_text)[0]
            if first_sentence and len(first_sentence) > 10:
                logger.info(f"[DIRECT_ANSWER] Using conclusion as fallback")
                return first_sentence.strip() + '.'
        
        logger.warning("[DIRECT_ANSWER] Could not extract direct answer")
        return "See the analysis below for candidate details."
    
    def _remove_duplicate_content(self, text: str) -> str:
        """
        Detect and remove duplicated content in LLM output.
        
        Sometimes LLMs repeat the same response multiple times.
        This method identifies and removes such duplications.
        
        Args:
            text: Text that may contain duplicated content
            
        Returns:
            Text with duplications removed
        """
        if not text or len(text) < 100:
            return text
        
        paragraphs = text.split('\n\n')
        if len(paragraphs) < 2:
            return text
        
        # Look for exact or near-exact duplicates
        seen_paragraphs = []
        unique_paragraphs = []
        
        for para in paragraphs:
            para_stripped = para.strip()
            if not para_stripped:
                continue
            
            # Check if this paragraph is a duplicate (or very similar)
            is_duplicate = False
            for seen in seen_paragraphs:
                # Exact match
                if para_stripped == seen:
                    is_duplicate = True
                    break
                # Very similar (80% overlap) - check first 50 chars
                if len(para_stripped) > 50 and len(seen) > 50:
                    if para_stripped[:50] == seen[:50]:
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                seen_paragraphs.append(para_stripped)
                unique_paragraphs.append(para)
        
        result = '\n\n'.join(unique_paragraphs)
        
        if len(result) < len(text):
            logger.info(f"[DIRECT_ANSWER] Removed duplicate content: {len(text)} -> {len(result)} chars")
        
        return result
    
    def _clean_transition_phrases(self, text: str) -> str:
        """
        Elimina frases de transición al análisis que NO deben estar en Direct Answer.
        
        Ejemplos de frases a eliminar:
        - "Here is the detailed analysis"
        - "Below is the analysis"
        - "See the analysis below"
        """
        if not text:
            return text
        
        # Patrones de frases de transición a eliminar
        transition_patterns = [
            r'\.\s*Here is the detailed analysis[:\.]?',
            r'\.\s*Below is the analysis[:\.]?',
            r'\.\s*See the analysis below[:\.]?',
            r'\.\s*Here is the analysis[:\.]?',
            r'\.\s*The detailed analysis follows[:\.]?',
            r'###\s*Detailed Analysis[:\.]?',
            r'\.\s*Detailed Analysis[:\.]?',
        ]
        
        for pattern in transition_patterns:
            text = re.sub(pattern, '.', text, flags=re.IGNORECASE)
        
        # Limpiar puntos dobles
        text = re.sub(r'\.+', '.', text)
        
        return text.strip()
    
    def format(self, content: str) -> str:
        """
        Format direct answer.
        
        Ensures proper capitalization and formatting.
        
        Args:
            content: Direct answer text
            
        Returns:
            Formatted text with proper capitalization
        """
        text = content.strip()
        
        if not text:
            return text
        
        # Ensure first letter is capitalized
        if text[0].islower():
            text = text[0].upper() + text[1:]
        
        return text
