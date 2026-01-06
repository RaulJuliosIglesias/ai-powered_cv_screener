"""
SINGLE CANDIDATE STRUCTURE

Complete structure for displaying a FULL candidate profile.
Combines multiple MODULES:
- ThinkingModule
- Summary (text extracted from LLM)
- HighlightsModule (key info table)
- CareerModule (career trajectory)
- SkillsModule (skills snapshot)
- CredentialsModule (certifications/education)
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

from ..modules import (
    ThinkingModule,
    ConclusionModule,
    HighlightsModule,
    CareerModule,
    SkillsModule,
    CredentialsModule,
)
from ..modules.risk_table_module import RiskTableModule

logger = logging.getLogger(__name__)


class SingleCandidateStructure:
    """
    Assembles the Single Candidate Structure using modules.
    
    This STRUCTURE combines multiple MODULES to create a complete profile view.
    """
    
    def __init__(self):
        self.thinking_module = ThinkingModule()
        self.highlights_module = HighlightsModule()
        self.career_module = CareerModule()
        self.skills_module = SkillsModule()
        self.credentials_module = CredentialsModule()
        self.risk_table_module = RiskTableModule()  # REUSABLE MODULE
        self.conclusion_module = ConclusionModule()
    
    def assemble(
        self,
        llm_output: str,
        chunks: List[Dict[str, Any]],
        candidate_name: str,
        cv_id: str,
        conversation_history: List[Dict[str, str]] = None
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
        
        # Extract highlights table using module
        highlights_data = self.highlights_module.extract(llm_output)
        highlights = highlights_data.to_list() if highlights_data else []
        
        # Extract career trajectory using module
        career_data = self.career_module.extract(llm_output)
        career = career_data.to_list() if career_data else []
        
        # Extract skills snapshot using module
        skills_data = self.skills_module.extract(llm_output)
        skills = skills_data.to_list() if skills_data else []
        
        # Extract credentials using module
        credentials_data = self.credentials_module.extract(llm_output)
        credentials = credentials_data.to_list() if credentials_data else []
        
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
    
