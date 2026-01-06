"""
CAREER MODULE

Extracts and formats career trajectory from LLM output.
Used by: SingleCandidateStructure

Output format:
### 💼 Career Trajectory
**Senior Developer** — *TechCorp* (2020 - Present)
→ Led team of 5 engineers
"""

import logging
import re
from typing import List, Dict, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CareerEntry:
    """Single career/job entry."""
    title: str
    company: str
    dates: str
    achievement: str = ""
    is_current: bool = False


@dataclass
class CareerData:
    """Container for extracted career data."""
    entries: List[CareerEntry] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "entries": [
                {
                    "title": e.title,
                    "company": e.company,
                    "dates": e.dates,
                    "achievement": e.achievement,
                    "is_current": e.is_current
                }
                for e in self.entries
            ]
        }
    
    def to_list(self) -> List[Dict[str, str]]:
        return [
            {
                "title": e.title,
                "company": e.company,
                "dates": e.dates,
                "achievement": e.achievement
            }
            for e in self.entries
        ]


class CareerModule:
    """
    Module for extracting and formatting career trajectory.
    
    Extracts from LLM output sections like:
    ### 💼 Career Trajectory
    **Title** — *Company* (dates)
    → Achievement
    """
    
    def extract(self, llm_output: str) -> Optional[CareerData]:
        """
        Extract career trajectory from LLM output.
        
        Args:
            llm_output: Raw LLM response
            
        Returns:
            CareerData with extracted entries or None
        """
        if not llm_output:
            return None
        
        entries = []
        
        # Find Career Trajectory section
        section_patterns = [
            r'###\s*💼\s*Career Trajectory([\s\S]*?)(?=###|:::|\Z)',
            r'###\s*Career Trajectory([\s\S]*?)(?=###|:::|\Z)',
            r'##\s*💼\s*Career([\s\S]*?)(?=##|:::|\Z)',
            r'###\s*Work Experience([\s\S]*?)(?=###|:::|\Z)',
            r'###\s*Experience([\s\S]*?)(?=###|:::|\Z)',
        ]
        
        section = None
        for pattern in section_patterns:
            match = re.search(pattern, llm_output, re.IGNORECASE)
            if match:
                section = match.group(1)
                break
        
        if not section:
            logger.debug("[CAREER_MODULE] No career section found")
            return None
        
        # Parse job entries with multiple patterns
        job_patterns = [
            # **Title** — *Company* (dates) \n→ achievement
            r'\*\*([^*]+)\*\*\s*[—–-]\s*\*([^*]+)\*\s*\(([^)]+)\)\s*(?:\n?→?\s*([^\n]*))?',
            # **Title** at *Company* (dates)
            r'\*\*([^*]+)\*\*\s+(?:at|@|en)\s+\*([^*]+)\*\s*\(([^)]+)\)',
            # **Title** | Company | dates
            r'\*\*([^*|]+)\*\*\s*\|\s*([^|]+)\|\s*([^|\n]+)',
            # Title — Company (dates) without bold
            r'^([A-Z][^—–\n]+?)\s*[—–-]\s*([^(]+?)\s*\(([^)]+)\)',
        ]
        
        for pattern in job_patterns:
            for match in re.finditer(pattern, section, re.MULTILINE):
                groups = match.groups()
                title = groups[0].strip() if groups[0] else ""
                company = groups[1].strip().strip('*') if groups[1] else ""
                dates = groups[2].strip() if len(groups) > 2 and groups[2] else ""
                achievement = groups[3].strip() if len(groups) > 3 and groups[3] else ""
                
                # Clean up
                title = re.sub(r'\*+', '', title).strip()
                company = re.sub(r'\*+', '', company).strip()
                
                # Detect current position
                is_current = bool(re.search(
                    r'present|actual|current|now|heute|hoy|oggi',
                    dates,
                    re.IGNORECASE
                ))
                
                if title and company and len(title) > 2:
                    entries.append(CareerEntry(
                        title=title,
                        company=company,
                        dates=dates,
                        achievement=achievement,
                        is_current=is_current
                    ))
            
            if entries:
                break
        
        if not entries:
            logger.debug("[CAREER_MODULE] No career entries extracted")
            return None
        
        logger.info(f"[CAREER_MODULE] Extracted {len(entries)} career entries")
        return CareerData(entries=entries)
    
    def format(self, data: CareerData) -> str:
        """
        Format career data into markdown.
        
        Args:
            data: CareerData to format
            
        Returns:
            Formatted markdown string
        """
        if not data or not data.entries:
            return ""
        
        lines = ["### 💼 Career Trajectory", ""]
        
        for entry in data.entries:
            line = f"**{entry.title}** — *{entry.company}* ({entry.dates})"
            lines.append(line)
            
            if entry.achievement:
                lines.append(f"→ {entry.achievement}")
            
            lines.append("")
        
        return "\n".join(lines).strip()
