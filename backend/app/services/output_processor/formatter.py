"""
Structured Output Formatter.

This module is responsible for formatting StructuredOutput objects into
final markdown strings for display. It is COMPLETELY SEPARATE from RAG service
to prevent accidental modifications during RAG service updates.

CRITICAL: Do NOT modify this module when changing RAG service logic.
This module ONLY handles formatting, not extraction or generation.
"""
import re
import logging
from typing import Any

logger = logging.getLogger(__name__)


class StructuredOutputFormatter:
    """
    Formats StructuredOutput objects into display-ready markdown.
    
    Responsibilities:
    - Build formatted answer with all components
    - Format tables as markdown
    - Extract analysis sections
    
    Does NOT:
    - Extract content from LLM output (that's OutputProcessor)
    - Generate LLM responses (that's RAG service)
    - Make decisions about pipeline (that's RAG service)
    """
    
    def build_formatted_answer(self, structured_output: Any) -> str:
        """
        Build formatted answer from structured output components.
        
        Ensures the response always has:
        - :::thinking block (if extracted) - collapsible reasoning
        - **Direct Answer:** label + answer
        - **Analysis:** label (if table or analysis present)
        - Table (if present)
        - :::conclusion block (if extracted)
        
        Args:
            structured_output: StructuredOutput object from OutputProcessor
            
        Returns:
            Formatted answer string with all components and labels
        """
        parts = []
        
        # 1. Add thinking block if present (collapsible reasoning)
        if structured_output.thinking:
            parts.append(f":::thinking\n{structured_output.thinking}\n:::")
            parts.append("")  # Empty line
        
        # 2. Add direct answer with explicit label
        parts.append(f"**Direct Answer:**")
        parts.append("")
        parts.append(structured_output.direct_answer)
        parts.append("")  # Empty line
        
        # 3. Add Analysis section if table or analysis content exists
        has_table = structured_output.table_data and structured_output.table_data.headers
        analysis_content = self.extract_analysis_section(
            structured_output.raw_content,
            structured_output.direct_answer,
            structured_output.conclusion
        )
        
        if has_table or analysis_content:
            parts.append("**Analysis:**")
            parts.append("")
            
            # Add table if present
            if has_table:
                table_md = self.format_table_markdown(structured_output.table_data)
                parts.append(table_md)
                parts.append("")  # Empty line
            
            # Add additional analysis
            if analysis_content:
                parts.append(analysis_content)
                parts.append("")  # Empty line
        
        # 4. Add conclusion block if present
        if structured_output.conclusion:
            parts.append(f":::conclusion\n{structured_output.conclusion}\n:::")
        
        result = "\n".join(parts).strip()
        logger.info(
            f"[FORMATTER] Built formatted answer: {len(result)} chars, "
            f"has_thinking={bool(structured_output.thinking)}, "
            f"has_table={has_table}, "
            f"has_conclusion={bool(structured_output.conclusion)}"
        )
        
        return result
    
    def format_table_markdown(self, table_data: Any) -> str:
        """
        Format TableData object as markdown table.
        
        CRITICAL: Fix markdown formatting in cells:
        - Remove spaces before ** for bold to work: " **Name**" -> "**Name**"
        - Clean up malformed markdown
        
        Args:
            table_data: TableData object with headers and rows
            
        Returns:
            Markdown formatted table string
        """
        if not table_data or not table_data.headers or not table_data.rows:
            return ""
        
        lines = []
        
        # Header row
        lines.append("| " + " | ".join(table_data.headers) + " |")
        
        # Separator row
        lines.append("|" + "|".join(["---"] * len(table_data.headers)) + "|")
        
        # Data rows - clean each cell
        for row in table_data.rows:
            cleaned_cells = [self._clean_cell_formatting(str(cell)) for cell in row]
            lines.append("| " + " | ".join(cleaned_cells) + " |")
        
        return "\n".join(lines)
    
    def _clean_cell_formatting(self, cell: str) -> str:
        """
        Clean markdown formatting in table cell.
        
        Fixes:
        - " **Text**" -> "**Text**" (remove space before **)
        - "** Text**" -> "**Text**" (remove space after **)
        - "**Text **" -> "**Text**" (remove space before closing **)
        
        Args:
            cell: Cell content string
            
        Returns:
            Cleaned cell content
        """
        if not cell:
            return cell
        
        # Fix: space before opening **
        cell = re.sub(r'\s+\*\*', '**', cell)
        
        # Fix: space after opening **
        cell = re.sub(r'\*\*\s+', '**', cell)
        
        # Fix: space before closing **
        cell = re.sub(r'\s+\*\*', '**', cell)
        
        return cell.strip()
    
    def extract_analysis_section(
        self,
        raw_content: str,
        direct_answer: str,
        conclusion: str | None
    ) -> str:
        """
        Extract analysis section between direct answer and conclusion.
        
        This captures any detailed analysis, bullet points, or additional
        context that's not in the table or direct answer.
        
        Args:
            raw_content: Original LLM output
            direct_answer: Extracted direct answer
            conclusion: Extracted conclusion (if any)
            
        Returns:
            Analysis section content or empty string
        """
        if not raw_content:
            return ""
        
        # Remove thinking and conclusion blocks
        clean = raw_content
        clean = re.sub(r':::thinking[\s\S]*?:::', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r':::conclusion[\s\S]*?:::', '', clean, flags=re.IGNORECASE)
        
        # Remove the direct answer
        if direct_answer and direct_answer in clean:
            clean = clean.replace(direct_answer, '', 1)
        
        # Remove table (basic detection)
        clean = re.sub(r'\|[^\n]*\|[\s\S]*?\|[^\n]*\|', '', clean)
        
        # Clean up
        clean = clean.strip()
        
        # Remove multiple empty lines
        clean = re.sub(r'\n{3,}', '\n\n', clean)
        
        # Only return if there's meaningful content
        if len(clean) > 50:
            return clean
        
        return ""


# Singleton instance for easy import
_formatter_instance = None


def get_formatter() -> StructuredOutputFormatter:
    """Get singleton formatter instance."""
    global _formatter_instance
    if _formatter_instance is None:
        _formatter_instance = StructuredOutputFormatter()
    return _formatter_instance
