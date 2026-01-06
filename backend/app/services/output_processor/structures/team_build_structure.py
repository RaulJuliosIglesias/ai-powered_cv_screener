"""
TEAM BUILD STRUCTURE

Structure for composing teams from available candidates.
Combines MODULES:
- ThinkingModule
- TeamRequirementsModule
- TeamCompositionModule
- SkillCoverageModule
- TeamRiskModule
- ConclusionModule

This structure is used when user asks for team building:
- "build a team of 3 developers"
- "form a project team"
- "assemble a team for this project"
"""

import logging
from typing import Dict, Any, List, Optional

from ..modules import ThinkingModule, ConclusionModule, AnalysisModule
from ..modules.team_requirements_module import TeamRequirementsModule
from ..modules.team_composition_module import TeamCompositionModule
from ..modules.skill_coverage_module import SkillCoverageModule
from ..modules.team_risk_module import TeamRiskModule

logger = logging.getLogger(__name__)


class TeamBuildStructure:
    """
    Assembles the Team Build Structure using modules.
    """
    
    def __init__(self):
        self.thinking_module = ThinkingModule()
        self.analysis_module = AnalysisModule()
        self.team_requirements_module = TeamRequirementsModule()
        self.team_composition_module = TeamCompositionModule()
        self.skill_coverage_module = SkillCoverageModule()
        self.team_risk_module = TeamRiskModule()
        self.conclusion_module = ConclusionModule()
    
    def assemble(
        self,
        llm_output: str,
        chunks: List[Dict[str, Any]],
        query: str = ""
    ) -> Dict[str, Any]:
        """Assemble all components of Team Build Structure."""
        logger.info("[TEAM_BUILD_STRUCTURE] Assembling team composition")
        
        # Extract thinking
        thinking = self.thinking_module.extract(llm_output)
        
        # Extract team requirements
        requirements_data = self.team_requirements_module.extract(
            query=query,
            llm_output=llm_output
        )
        
        # Compose team
        roles = requirements_data.to_dict()["roles"] if requirements_data else []
        composition_data = self.team_composition_module.compose(
            roles=roles,
            chunks=chunks
        )
        
        # Analyze skill coverage
        assignments = composition_data.to_dict()["assignments"] if composition_data else []
        all_required_skills = []
        for role in roles:
            all_required_skills.extend(role.get("required_skills", []))
        
        coverage_data = self.skill_coverage_module.analyze(
            assignments=assignments,
            required_skills=all_required_skills
        )
        
        # Analyze team risks
        coverage_dict = coverage_data.to_dict() if coverage_data else {}
        risk_data = self.team_risk_module.analyze(
            assignments=assignments,
            skill_coverage=coverage_dict
        )
        
        # Extract conclusion
        conclusion = self.conclusion_module.extract(llm_output)
        
        # Extract analysis
        analysis = self.analysis_module.extract(llm_output, "", conclusion or "")
        
        return {
            "structure_type": "team_build",
            "query": query,
            "thinking": thinking,
            "analysis": analysis,
            "team_requirements": requirements_data.to_dict() if requirements_data else None,
            "team_composition": composition_data.to_dict() if composition_data else None,
            "skill_coverage": coverage_data.to_dict() if coverage_data else None,
            "team_risks": risk_data.to_dict() if risk_data else None,
            "total_assigned": len(assignments),
            "conclusion": conclusion,
            "raw_content": llm_output
        }
