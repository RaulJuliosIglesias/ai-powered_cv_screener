"""
SKILLS MODULE

Extracts and formats skills snapshot from LLM output.
Used by: SingleCandidateStructure

Output format:
### 🛠️ Skills Snapshot
| Skill Area | Technologies | Proficiency |
|------------|--------------|-------------|
| **Backend** | Python, Java | Expert |
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SkillEntry:
    """Single skill area entry."""
    area: str
    details: str
    level: str = ""


@dataclass
class SkillsData:
    """Container for extracted skills data."""
    entries: List[SkillEntry] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "entries": [
                {"area": s.area, "details": s.details, "level": s.level}
                for s in self.entries
            ]
        }
    
    def to_list(self) -> List[Dict[str, str]]:
        return [
            {"area": s.area, "details": s.details, "level": s.level}
            for s in self.entries
        ]


class SkillsModule:
    """
    Module for extracting and formatting skills snapshot.
    
    Extracts from LLM output sections like:
    ### 🛠️ Skills Snapshot
    | Skill Area | Technologies | Proficiency |
    | **Backend** | Python, Java | Expert |
    """
    
    def extract(self, llm_output: str) -> Optional[SkillsData]:
        """
        Extract skills snapshot from LLM output.
        
        Args:
            llm_output: Raw LLM response
            
        Returns:
            SkillsData with extracted entries or None
        """
        if not llm_output:
            return None
        
        entries = []
        
        # Find Skills Snapshot section
        section_patterns = [
            r'###\s*🛠️\s*Skills Snapshot([\s\S]*?)(?=###|:::|\Z)',
            r'###\s*Skills Snapshot([\s\S]*?)(?=###|:::|\Z)',
            r'##\s*🛠️\s*Skills([\s\S]*?)(?=##|:::|\Z)',
            r'###\s*Technical Skills([\s\S]*?)(?=###|:::|\Z)',
            r'###\s*Skills([\s\S]*?)(?=###|:::|\Z)',
        ]
        
        section = None
        for pattern in section_patterns:
            match = re.search(pattern, llm_output, re.IGNORECASE)
            if match:
                section = match.group(1)
                break
        
        if not section:
            logger.debug("[SKILLS_MODULE] No skills section found")
            return None
        
        # Parse table rows with 2 or 3 columns
        row_patterns = [
            # | **Area** | Details | Level |
            r'\|\s*\*\*([^|*]+)\*\*\s*\|\s*([^|]+)\|\s*([^|]*)\|',
            # | **Area** | Details |
            r'\|\s*\*\*([^|*]+)\*\*\s*\|\s*([^|]+)\|',
            # | Area | Details | Level |
            r'\|\s*([^|*]+)\s*\|\s*([^|]+)\|\s*([^|]*)\|',
        ]
        
        for pattern in row_patterns:
            for match in re.finditer(pattern, section):
                groups = match.groups()
                area = groups[0].strip() if groups[0] else ""
                details = groups[1].strip() if len(groups) > 1 and groups[1] else ""
                level = groups[2].strip() if len(groups) > 2 and groups[2] else ""
                
                # Skip header rows and separators
                if any(skip in area.lower() for skip in [
                    'skill area', 'technologies', '---', ':--', 'proficiency'
                ]):
                    continue
                
                if area and details and len(area) > 1:
                    entries.append(SkillEntry(
                        area=area,
                        details=details,
                        level=level
                    ))
            
            if entries:
                break
        
        # Fallback: try to extract from list format
        if not entries:
            list_pattern = r'[-•]\s*\*\*([^:*]+)\*\*[:\s]+([^\n]+)'
            for match in re.finditer(list_pattern, section):
                area = match.group(1).strip()
                details = match.group(2).strip()
                if area and details:
                    entries.append(SkillEntry(area=area, details=details, level=""))
        
        if not entries:
            logger.debug("[SKILLS_MODULE] No skill entries extracted")
            return None
        
        logger.info(f"[SKILLS_MODULE] Extracted {len(entries)} skill areas")
        return SkillsData(entries=entries)
    
    def format(self, data: SkillsData) -> str:
        """
        Format skills data into markdown table.
        
        Args:
            data: SkillsData to format
            
        Returns:
            Formatted markdown string
        """
        if not data or not data.entries:
            return ""
        
        # Check if any entry has a level
        has_level = any(e.level for e in data.entries)
        
        lines = ["### 🛠️ Skills Snapshot", ""]
        
        if has_level:
            lines.extend([
                "| Skill Area | Technologies | Proficiency |",
                "|:-----------|:-------------|:------------|",
            ])
            for entry in data.entries:
                lines.append(f"| **{entry.area}** | {entry.details} | {entry.level} |")
        else:
            lines.extend([
                "| Skill Area | Technologies |",
                "|:-----------|:-------------|",
            ])
            for entry in data.entries:
                lines.append(f"| **{entry.area}** | {entry.details} |")
        
        return "\n".join(lines)
