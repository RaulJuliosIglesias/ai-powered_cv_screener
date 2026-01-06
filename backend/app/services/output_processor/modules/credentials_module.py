"""
CREDENTIALS MODULE

Extracts and formats credentials/certifications from LLM output.
Used by: SingleCandidateStructure

Output format:
### 🎓 Credentials
- AWS Solutions Architect Professional
- PMP Certified
"""

import logging
import re
from typing import List, Dict, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class CredentialsData:
    """Container for extracted credentials."""
    items: List[str] = field(default_factory=list)
    education: List[str] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "items": self.items,
            "education": self.education,
            "certifications": self.certifications
        }
    
    def to_list(self) -> List[str]:
        return self.items


class CredentialsModule:
    """
    Module for extracting and formatting credentials.
    
    Extracts from LLM output sections like:
    ### 🎓 Credentials
    - PhD in Computer Science, MIT
    - AWS Solutions Architect
    """
    
    def extract(self, llm_output: str) -> Optional[CredentialsData]:
        """
        Extract credentials from LLM output.
        
        Args:
            llm_output: Raw LLM response
            
        Returns:
            CredentialsData with extracted items or None
        """
        if not llm_output:
            return None
        
        items = []
        education = []
        certifications = []
        
        # Find Credentials section
        section_patterns = [
            r'###\s*🎓\s*Credentials([\s\S]*?)(?=###|:::|\Z)',
            r'###\s*Credentials([\s\S]*?)(?=###|:::|\Z)',
            r'###\s*Education\s*(?:&|and)?\s*Certifications?([\s\S]*?)(?=###|:::|\Z)',
            r'##\s*🎓\s*Education([\s\S]*?)(?=##|:::|\Z)',
        ]
        
        section = None
        for pattern in section_patterns:
            match = re.search(pattern, llm_output, re.IGNORECASE)
            if match:
                section = match.group(1)
                break
        
        if not section:
            logger.debug("[CREDENTIALS_MODULE] No credentials section found")
            return None
        
        # Parse list items
        list_patterns = [
            r'[-•*]\s*([^\n]+)',
            r'\d+\.\s*([^\n]+)',
        ]
        
        for pattern in list_patterns:
            for match in re.finditer(pattern, section):
                item = match.group(1).strip()
                
                # Skip items that look like headers or links
                if item.startswith('[') or item.startswith('#'):
                    continue
                
                # Clean up markdown
                item = re.sub(r'\*\*([^*]+)\*\*', r'\1', item)
                item = re.sub(r'\*([^*]+)\*', r'\1', item)
                
                if item and len(item) > 3:
                    items.append(item)
                    
                    # Categorize
                    item_lower = item.lower()
                    if any(kw in item_lower for kw in [
                        'degree', 'bachelor', 'master', 'phd', 'mba', 
                        'university', 'college', 'institute', 'school'
                    ]):
                        education.append(item)
                    elif any(kw in item_lower for kw in [
                        'certified', 'certification', 'certificate', 
                        'aws', 'azure', 'gcp', 'pmp', 'cissp', 'ccna'
                    ]):
                        certifications.append(item)
            
            if items:
                break
        
        if not items:
            logger.debug("[CREDENTIALS_MODULE] No credential items extracted")
            return None
        
        logger.info(f"[CREDENTIALS_MODULE] Extracted {len(items)} credentials")
        return CredentialsData(
            items=items,
            education=education,
            certifications=certifications
        )
    
    def format(self, data: CredentialsData) -> str:
        """
        Format credentials data into markdown list.
        
        Args:
            data: CredentialsData to format
            
        Returns:
            Formatted markdown string
        """
        if not data or not data.items:
            return ""
        
        lines = ["### 🎓 Credentials", ""]
        
        for item in data.items:
            lines.append(f"- {item}")
        
        return "\n".join(lines)
