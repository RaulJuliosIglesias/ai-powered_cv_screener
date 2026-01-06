"""
HIGHLIGHTS MODULE

Extracts and formats candidate highlights table from LLM output.
Used by: SingleCandidateStructure

Output format:
| Category | Key Information |
|----------|-----------------|
| **Experience** | 8 years in software development |
"""

import logging
import re
from typing import List, Dict, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class HighlightItem:
    """Single highlight entry."""
    category: str
    info: str


@dataclass
class HighlightsData:
    """Container for extracted highlights."""
    items: List[HighlightItem] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "items": [{"category": h.category, "info": h.info} for h in self.items]
        }
    
    def to_list(self) -> List[Dict[str, str]]:
        return [{"category": h.category, "info": h.info} for h in self.items]


class HighlightsModule:
    """
    Module for extracting and formatting candidate highlights.
    
    Extracts from LLM output sections like:
    ### 📊 Candidate Highlights
    | Category | Key Information |
    |----------|-----------------|
    | **Experience** | 8 years |
    """
    
    def extract(self, llm_output: str) -> Optional[HighlightsData]:
        """
        Extract highlights table from LLM output.
        
        Args:
            llm_output: Raw LLM response
            
        Returns:
            HighlightsData with extracted items or None
        """
        if not llm_output:
            return None
        
        highlights = []
        
        # Find Candidate Highlights section
        section_patterns = [
            r'###\s*📊\s*Candidate Highlights([\s\S]*?)(?=###|:::|\Z)',
            r'###\s*Candidate Highlights([\s\S]*?)(?=###|:::|\Z)',
            r'##\s*📊\s*Highlights([\s\S]*?)(?=##|:::|\Z)',
            r'\*\*Highlights\*\*([\s\S]*?)(?=\*\*|###|:::|\Z)',
        ]
        
        section = None
        for pattern in section_patterns:
            match = re.search(pattern, llm_output, re.IGNORECASE)
            if match:
                section = match.group(1)
                break
        
        if not section:
            logger.debug("[HIGHLIGHTS_MODULE] No highlights section found")
            return None
        
        # Parse table rows: | **Category** | Information |
        row_patterns = [
            r'\|\s*\*\*([^|*]+)\*\*\s*\|\s*([^|]+)\|',
            r'\|\s*([^|*]+)\s*\|\s*([^|]+)\|',
        ]
        
        for pattern in row_patterns:
            for match in re.finditer(pattern, section):
                category = match.group(1).strip()
                info = match.group(2).strip()
                
                # Skip header rows and separators
                if any(skip in category.lower() for skip in ['category', '---', 'key info', ':--']):
                    continue
                
                if category and info and len(category) > 1:
                    highlights.append(HighlightItem(
                        category=category,
                        info=info
                    ))
            
            if highlights:
                break
        
        if not highlights:
            logger.debug("[HIGHLIGHTS_MODULE] No highlight items extracted")
            return None
        
        logger.info(f"[HIGHLIGHTS_MODULE] Extracted {len(highlights)} highlights")
        return HighlightsData(items=highlights)
    
    def format(self, data: HighlightsData) -> str:
        """
        Format highlights data into markdown table.
        
        Args:
            data: HighlightsData to format
            
        Returns:
            Formatted markdown string
        """
        if not data or not data.items:
            return ""
        
        lines = [
            "### 📊 Candidate Highlights",
            "",
            "| Category | Key Information |",
            "|:---------|:----------------|",
        ]
        
        for item in data.items:
            lines.append(f"| **{item.category}** | {item.info} |")
        
        return "\n".join(lines)
