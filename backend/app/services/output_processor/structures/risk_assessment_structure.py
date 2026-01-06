"""
RISK ASSESSMENT STRUCTURE

Complete structure for risk-focused queries.
Combines MODULES:
- ThinkingModule
- Risk Analysis (text paragraph)
- RiskTableModule  ← SAME REUSABLE MODULE as SingleCandidateStructure
- ConclusionModule (Assessment)

This structure is used when user asks specifically about risks:
- "give me risks about X"
- "what are the red flags for X"
- "any concerns about X"
"""

import logging
from typing import Dict, Any, List

from ..modules import ThinkingModule, ConclusionModule
from ..modules.risk_table_module import RiskTableModule

logger = logging.getLogger(__name__)


class RiskAssessmentStructure:
    """
    Assembles the Risk Assessment Structure using modules.
    
    This STRUCTURE uses the SAME RiskTableModule as SingleCandidateStructure,
    demonstrating module reusability.
    """
    
    def __init__(self):
        self.thinking_module = ThinkingModule()
        self.risk_table_module = RiskTableModule()  # SAME REUSABLE MODULE!
        self.conclusion_module = ConclusionModule()
    
    def assemble(
        self,
        llm_output: str,
        chunks: List[Dict[str, Any]],
        candidate_name: str,
        cv_id: str
    ) -> Dict[str, Any]:
        """
        Assemble Risk Assessment Structure.
        
        Args:
            llm_output: Raw LLM response
            chunks: CV chunks with metadata
            candidate_name: Name of the candidate
            cv_id: CV identifier
            
        Returns:
            dict with structure_type and all components for frontend
        """
        logger.info(f"[RISK_ASSESSMENT_STRUCTURE] Assembling for {candidate_name}")
        
        # Extract thinking from LLM output
        thinking = self.thinking_module.extract(llm_output)
        
        # Use RiskTableModule to generate risk assessment table and analysis
        risk_table_data = self.risk_table_module.extract(chunks, candidate_name, cv_id)
        
        # The risk analysis text comes from the module
        risk_analysis = ""
        if risk_table_data:
            risk_analysis = risk_table_data.analysis_text
        
        # Extract conclusion/assessment from LLM output
        conclusion = self.conclusion_module.extract(llm_output)
        
        # If no conclusion from LLM, use the module's analysis
        if not conclusion and risk_table_data:
            conclusion = risk_table_data.analysis_text
        
        return {
            "structure_type": "risk_assessment",
            "candidate_name": candidate_name,
            "cv_id": cv_id,
            "thinking": thinking,
            "risk_analysis": risk_analysis,
            "risk_table": risk_table_data.to_dict() if risk_table_data else None,
            "assessment": conclusion,
            "raw_content": llm_output
        }
