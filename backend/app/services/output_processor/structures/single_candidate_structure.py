"""
SINGLE CANDIDATE STRUCTURE

Complete structure for displaying a FULL candidate profile.
Combines multiple MODULES:
- ThinkingModule
- Summary (text extracted from LLM)
- Highlights (key info table)
- Career trajectory
- Skills snapshot
- Credentials
- RiskTableModule  ← REUSABLE MODULE (same as in RiskAssessmentStructure)
- ConclusionModule

This structure is used when user asks for full profile:
- "dame todo el perfil de X"
- "give me full profile of X"
- "tell me everything about X"
"""

import logging
import re
from typing import Dict, Any, List, Optional

from ..modules import ThinkingModule, ConclusionModule
from ..modules.risk_table_module import RiskTableModule

logger = logging.getLogger(__name__)


class SingleCandidateStructure:
    """
    Assembles the Single Candidate Structure using modules.
    
    This STRUCTURE combines multiple MODULES to create a complete profile view.
    """
    
    def __init__(self):
        self.thinking_module = ThinkingModule()
        self.risk_table_module = RiskTableModule()  # REUSABLE MODULE
        self.conclusion_module = ConclusionModule()
    
    def assemble(
        self,
        llm_output: str,
        chunks: List[Dict[str, Any]],
        candidate_name: str,
        cv_id: str
    ) -> Dict[str, Any]:
        """
        Assemble all components of Single Candidate Structure.
        
        Args:
            llm_output: Raw LLM response
            chunks: CV chunks with metadata
            candidate_name: Name of the candidate
            cv_id: CV identifier
            
        Returns:
            dict with structure_type and all components for frontend
        """
        logger.info(f"[SINGLE_CANDIDATE_STRUCTURE] Assembling for {candidate_name}")
        
        # Extract thinking from LLM output
        thinking = self.thinking_module.extract(llm_output)
        
        # Extract summary paragraph
        summary = self._extract_summary(llm_output, candidate_name)
        
        # Extract highlights table
        highlights = self._extract_highlights(llm_output)
        
        # Extract career trajectory
        career = self._extract_career(llm_output)
        
        # Extract skills snapshot
        skills = self._extract_skills(llm_output)
        
        # Extract credentials
        credentials = self._extract_credentials(llm_output)
        
        # Use RiskTableModule to generate risk assessment table
        # Pass llm_output for fallback parsing when metadata is not available
        risk_table_data = self.risk_table_module.extract(
            chunks=chunks, 
            candidate_name=candidate_name, 
            cv_id=cv_id,
            llm_output=llm_output  # Fallback: parse from LLM response
        )
        
        # Extract conclusion
        conclusion = self.conclusion_module.extract(llm_output)
        
        return {
            "structure_type": "single_candidate",
            "candidate_name": candidate_name,
            "cv_id": cv_id,
            "thinking": thinking,
            "summary": summary,
            "highlights": highlights,
            "career": career,
            "skills": skills,
            "credentials": credentials,
            "risk_table": risk_table_data.to_dict() if risk_table_data else None,
            "conclusion": conclusion,
            "raw_content": llm_output
        }
    
    def _extract_summary(self, content: str, candidate_name: str) -> str:
        """Extract summary paragraph after candidate header."""
        if not content:
            return ""
        
        # Look for content after ## 👤 **[Name]** header
        patterns = [
            rf'## 👤 \*\*\[?{re.escape(candidate_name)}[^\n]*\n+([^#\n][^\n]+(?:\n[^#\n][^\n]+)*)',
            rf'## 👤[^\n]*\n+([^#\n][^\n]+(?:\n[^#\n][^\n]+)*)',
            rf'\*\*{re.escape(candidate_name)}\*\*[^\n]*\n+([^#\n][^\n]+(?:\n[^#\n][^\n]+)*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                summary = match.group(1).strip()
                # Clean up markdown artifacts
                summary = re.sub(r'\*\*\[([^\]]+)\]\([^)]+\)\*\*', r'\1', summary)
                if len(summary) > 50:
                    return summary
        
        return ""
    
    def _extract_highlights(self, content: str) -> List[Dict[str, str]]:
        """Extract highlights table (Category | Key Information)."""
        highlights = []
        
        # Find Candidate Highlights section
        highlights_match = re.search(
            r'###\s*📊\s*Candidate Highlights([\s\S]*?)(?=###|:::|\Z)',
            content
        )
        
        if not highlights_match:
            return highlights
        
        section = highlights_match.group(1)
        
        # Parse table rows
        row_pattern = r'\|\s*\*\*([^|*]+)\*\*\s*\|\s*([^|]+)\|'
        for match in re.finditer(row_pattern, section):
            category = match.group(1).strip()
            info = match.group(2).strip()
            
            # Skip header rows
            if 'Category' in category or '---' in category:
                continue
            
            if category and info:
                highlights.append({
                    "category": category,
                    "info": info
                })
        
        return highlights
    
    def _extract_career(self, content: str) -> List[Dict[str, str]]:
        """Extract career trajectory."""
        career = []
        
        # Find Career Trajectory section
        career_match = re.search(
            r'###\s*💼\s*Career Trajectory([\s\S]*?)(?=###|:::|\Z)',
            content
        )
        
        if not career_match:
            return career
        
        section = career_match.group(1)
        
        # Parse job entries: **Title** — *Company* (dates)
        job_pattern = r'\*\*([^*]+)\*\*\s*[—–-]\s*\*([^*]+)\*\s*\(([^)]+)\)\s*\n?→?\s*([^\n]*)'
        for match in re.finditer(job_pattern, section):
            title = match.group(1).strip()
            company = match.group(2).strip()
            dates = match.group(3).strip()
            achievement = match.group(4).strip() if match.group(4) else ""
            
            career.append({
                "title": title,
                "company": company,
                "dates": dates,
                "achievement": achievement
            })
        
        return career
    
    def _extract_skills(self, content: str) -> List[Dict[str, str]]:
        """Extract skills snapshot table."""
        skills = []
        
        # Find Skills Snapshot section
        skills_match = re.search(
            r'###\s*🛠️\s*Skills Snapshot([\s\S]*?)(?=###|:::|\Z)',
            content
        )
        
        if not skills_match:
            return skills
        
        section = skills_match.group(1)
        
        # Parse table rows
        row_pattern = r'\|\s*\*\*([^|*]+)\*\*\s*\|\s*([^|]+)\|\s*([^|]*)\|'
        for match in re.finditer(row_pattern, section):
            area = match.group(1).strip()
            details = match.group(2).strip()
            level = match.group(3).strip() if match.group(3) else ""
            
            # Skip header rows
            if 'Skill Area' in area or '---' in area:
                continue
            
            if area and details:
                skills.append({
                    "area": area,
                    "details": details,
                    "level": level
                })
        
        return skills
    
    def _extract_credentials(self, content: str) -> List[str]:
        """Extract credentials list."""
        credentials = []
        
        # Find Credentials section
        cred_match = re.search(
            r'###\s*Credentials([\s\S]*?)(?=###|:::|\Z)',
            content
        )
        
        if not cred_match:
            return credentials
        
        section = cred_match.group(1)
        
        # Parse list items
        for match in re.finditer(r'-\s*([^\n]+)', section):
            item = match.group(1).strip()
            if item and not item.startswith('['):
                credentials.append(item)
        
        return credentials
