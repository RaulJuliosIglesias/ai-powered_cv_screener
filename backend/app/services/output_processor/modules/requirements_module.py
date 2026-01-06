"""
REQUIREMENTS MODULE

Extracts and categorizes requirements from job descriptions.
Used by: JobMatchStructure

Output format:
| Requirement | Category | Type |
|-------------|----------|------|
| Python 5+ years | Required | Skill |
"""

import logging
import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Requirement:
    """Single job requirement."""
    name: str
    category: str = "preferred"  # "required", "preferred", "nice_to_have"
    req_type: str = "skill"  # "skill", "experience", "education", "certification"
    years: Optional[int] = None


@dataclass
class RequirementsData:
    """Container for job requirements."""
    requirements: List[Requirement] = field(default_factory=list)
    job_title: str = ""
    total_required: int = 0
    total_preferred: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "requirements": [
                {
                    "name": r.name,
                    "category": r.category,
                    "type": r.req_type,
                    "years": r.years
                }
                for r in self.requirements
            ],
            "job_title": self.job_title,
            "total_required": self.total_required,
            "total_preferred": self.total_preferred
        }


class RequirementsModule:
    """
    Module for extracting requirements from job descriptions.
    """
    
    # Keywords for requirement categorization
    REQUIRED_KEYWORDS = [
        'required', 'must have', 'essential', 'mandatory', 'necesario',
        'obligatorio', 'imprescindible'
    ]
    
    PREFERRED_KEYWORDS = [
        'preferred', 'nice to have', 'bonus', 'plus', 'desirable',
        'valorable', 'preferible', 'ideal'
    ]
    
    # Technology/skill patterns
    TECH_PATTERNS = [
        r'(Python|Java|JavaScript|TypeScript|React|Angular|Vue|Node\.?js|'
        r'AWS|Azure|GCP|Docker|Kubernetes|SQL|PostgreSQL|MongoDB|Redis|'
        r'Git|CI/CD|DevOps|Machine Learning|ML|AI|Data Science|'
        r'C\+\+|C#|Go|Rust|Ruby|PHP|Swift|Kotlin)',
    ]
    
    def extract(
        self,
        job_description: str,
        llm_output: str = ""
    ) -> Optional[RequirementsData]:
        """
        Extract requirements from job description.
        
        Args:
            job_description: Job description text
            llm_output: LLM analysis for additional context
            
        Returns:
            RequirementsData with extracted requirements
        """
        if not job_description and not llm_output:
            return None
        
        requirements = []
        job_title = self._extract_job_title(job_description or llm_output)
        
        # Extract from job description
        if job_description:
            requirements.extend(self._extract_from_text(job_description))
        
        # Extract from LLM output
        if llm_output:
            llm_reqs = self._extract_from_llm(llm_output)
            # Merge avoiding duplicates
            existing_names = {r.name.lower() for r in requirements}
            for req in llm_reqs:
                if req.name.lower() not in existing_names:
                    requirements.append(req)
        
        # Count by category
        total_required = sum(1 for r in requirements if r.category == "required")
        total_preferred = sum(1 for r in requirements if r.category != "required")
        
        logger.info(f"[REQUIREMENTS_MODULE] Extracted {len(requirements)} requirements")
        
        return RequirementsData(
            requirements=requirements,
            job_title=job_title,
            total_required=total_required,
            total_preferred=total_preferred
        )
    
    def _extract_job_title(self, text: str) -> str:
        """Extract job title from text."""
        patterns = [
            r'(?:position|role|job|puesto)[:\s]+([^\n,]+)',
            r'^#*\s*([^\n]+(?:developer|engineer|manager|analyst|designer|architect))',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                return match.group(1).strip()[:50]
        
        return ""
    
    def _extract_from_text(self, text: str) -> List[Requirement]:
        """Extract requirements from raw text."""
        requirements = []
        
        # Split into lines/bullets
        lines = re.split(r'[\n•\-\*]', text)
        
        current_category = "preferred"
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 5:
                continue
            
            # Check for category headers
            line_lower = line.lower()
            if any(kw in line_lower for kw in self.REQUIRED_KEYWORDS):
                current_category = "required"
                if len(line) < 20:  # Likely a header
                    continue
            elif any(kw in line_lower for kw in self.PREFERRED_KEYWORDS):
                current_category = "preferred"
                if len(line) < 20:
                    continue
            
            # Extract years if mentioned
            years_match = re.search(r'(\d+)\+?\s*(?:years?|años?)', line, re.IGNORECASE)
            years = int(years_match.group(1)) if years_match else None
            
            # Determine requirement type
            req_type = self._determine_type(line)
            
            # Extract the requirement name
            name = self._clean_requirement_name(line)
            
            if name and len(name) > 3:
                requirements.append(Requirement(
                    name=name,
                    category=current_category,
                    req_type=req_type,
                    years=years
                ))
        
        return requirements
    
    def _extract_from_llm(self, llm_output: str) -> List[Requirement]:
        """Extract requirements mentioned in LLM output."""
        requirements = []
        
        # Look for requirements section
        section_match = re.search(
            r'(?:requirements?|requisitos?)[:\s]*([\s\S]*?)(?=###|:::|\Z)',
            llm_output,
            re.IGNORECASE
        )
        
        if section_match:
            section = section_match.group(1)
            requirements.extend(self._extract_from_text(section))
        
        return requirements
    
    def _determine_type(self, line: str) -> str:
        """Determine the type of requirement."""
        line_lower = line.lower()
        
        if any(kw in line_lower for kw in ['degree', 'bachelor', 'master', 'phd', 'education']):
            return "education"
        elif any(kw in line_lower for kw in ['certified', 'certification', 'certificate']):
            return "certification"
        elif any(kw in line_lower for kw in ['years', 'experience', 'experiencia']):
            return "experience"
        else:
            return "skill"
    
    def _clean_requirement_name(self, line: str) -> str:
        """Clean up requirement name."""
        # Remove common prefixes
        line = re.sub(r'^(?:required|preferred|must have|nice to have)[:\s]*', '', line, flags=re.IGNORECASE)
        # Remove years pattern
        line = re.sub(r'\d+\+?\s*(?:years?|años?)\s*(?:of\s+)?(?:experience\s+)?(?:in\s+)?', '', line, flags=re.IGNORECASE)
        # Clean up
        line = line.strip(' .,;:-')
        return line[:100] if line else ""
    
    def format(self, data: RequirementsData) -> str:
        """Format requirements data into markdown."""
        if not data or not data.requirements:
            return ""
        
        lines = ["### 📋 Job Requirements", ""]
        
        if data.job_title:
            lines.append(f"**Position:** {data.job_title}")
            lines.append("")
        
        lines.extend([
            "| Requirement | Category | Type |",
            "|:------------|:--------:|:-----|",
        ])
        
        for r in data.requirements:
            category_emoji = "🔴" if r.category == "required" else "🟡"
            years_str = f" ({r.years}+ yrs)" if r.years else ""
            lines.append(f"| {r.name}{years_str} | {category_emoji} {r.category.title()} | {r.req_type.title()} |")
        
        lines.append("")
        lines.append(f"*Total: {data.total_required} required, {data.total_preferred} preferred*")
        
        return "\n".join(lines)
