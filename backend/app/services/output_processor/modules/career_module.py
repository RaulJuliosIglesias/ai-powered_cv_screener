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
                
                # PHASE 2.4 FIX: Validate entry before adding
                if title and company and len(title) > 2:
                    # Clean and validate the entry
                    cleaned_entry = self._validate_career_entry(title, company, dates, achievement, is_current)
                    if cleaned_entry:
                        entries.append(cleaned_entry)
            
            if entries:
                break
        
        if not entries:
            logger.debug("[CAREER_MODULE] No career entries extracted")
            return None
        
        # PHASE 2.4: Remove duplicates and clean entries
        entries = self._deduplicate_entries(entries)
        
        logger.info(f"[CAREER_MODULE] Extracted {len(entries)} career entries")
        return CareerData(entries=entries)
    
    def _validate_career_entry(
        self, 
        title: str, 
        company: str, 
        dates: str, 
        achievement: str,
        is_current: bool
    ) -> Optional[CareerEntry]:
        """
        PHASE 2.4 FIX: Validate and clean a career entry.
        
        Rejects entries with:
        - "Not specified" values
        - URLs in wrong fields
        - Duplicate title and company
        - Invalid patterns
        """
        # Clean title
        title = self._clean_career_field(title)
        if not title or title.lower() in ('not specified', 'unknown', 'n/a', 'none'):
            return None
        
        # Clean company
        company = self._clean_career_field(company)
        if not company or company.lower() in ('not specified', 'unknown', 'n/a', 'none'):
            return None
        
        # Remove URLs from title/company (they belong elsewhere)
        url_pattern = r'https?://[^\s]+|www\.[^\s]+|\w+\.(com|org|net|io)[^\s]*'
        if re.search(url_pattern, title, re.IGNORECASE):
            title = re.sub(url_pattern, '', title).strip()
        if re.search(url_pattern, company, re.IGNORECASE):
            company = re.sub(url_pattern, '', company).strip()
        
        # Check for candidate name accidentally in title (common parsing error)
        # Pattern: "Title CandidateName" where CandidateName is 2+ capitalized words at end
        name_at_end = re.search(r'\s+([A-Z][a-z]+\s+[A-Z][a-z]+)$', title)
        if name_at_end:
            # Check if this looks like a person's name (not part of title)
            potential_name = name_at_end.group(1)
            if not any(kw in potential_name.lower() for kw in ['manager', 'director', 'lead', 'engineer']):
                title = title[:name_at_end.start()].strip()
                logger.debug(f"[CAREER_MODULE] Removed name from title: '{potential_name}'")
        
        # Reject if title equals company (parsing error)
        if title.lower() == company.lower():
            return None
        
        # Validate we still have meaningful content
        if len(title) < 3 or len(company) < 2:
            return None
        
        # Clean dates
        dates = dates.strip() if dates else ""
        
        # Clean achievement
        achievement = achievement.strip() if achievement else ""
        if achievement.lower() in ('not specified', 'unknown', 'n/a'):
            achievement = ""
        
        return CareerEntry(
            title=title,
            company=company,
            dates=dates,
            achievement=achievement,
            is_current=is_current
        )
    
    def _clean_career_field(self, field: str) -> str:
        """Clean a career field (title or company)."""
        if not field:
            return ""
        
        # Remove markdown
        field = re.sub(r'\*+', '', field).strip()
        
        # Remove leading/trailing special chars
        field = re.sub(r'^[—–\-\|\s]+', '', field)
        field = re.sub(r'[—–\-\|\s]+$', '', field)
        
        # Remove parenthetical content at end (often dates that got mixed in)
        field = re.sub(r'\s*\([^)]*\)\s*$', '', field)
        
        return field.strip()
    
    def _deduplicate_entries(self, entries: List[CareerEntry]) -> List[CareerEntry]:
        """
        PHASE 2.4: Remove duplicate career entries.
        
        Keeps first occurrence of each unique (title, company) pair.
        """
        seen = set()
        unique_entries = []
        
        for entry in entries:
            key = (entry.title.lower(), entry.company.lower())
            if key not in seen:
                seen.add(key)
                unique_entries.append(entry)
            else:
                logger.debug(f"[CAREER_MODULE] Removing duplicate: {entry.title} at {entry.company}")
        
        return unique_entries
    
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
