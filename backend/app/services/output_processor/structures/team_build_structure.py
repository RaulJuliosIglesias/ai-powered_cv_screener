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
        query: str = "",
        conversation_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Assemble all components of Team Build Structure."""
        logger.info("[TEAM_BUILD_STRUCTURE] Assembling team composition")
        
        # Extract thinking
        thinking = self.thinking_module.extract(llm_output)
        
        # Check if query mentions specific team size (e.g., "top 3", "these 3")
        query_lower = query.lower()
        is_simple_team_query = any(phrase in query_lower for phrase in [
            'top 3', 'top three', 'these 3', 'best 3', 'top 5', 'top five'
        ])
        
        if is_simple_team_query:
            # SIMPLE MODE: Analyze available candidates as a team without role assignment
            logger.info("[TEAM_BUILD_STRUCTURE] Simple team query - analyzing available candidates")
            composition_data = self._analyze_simple_team(chunks, query)
            requirements_data = None
            coverage_data = None
            risk_data = None
        else:
            # ROLE-BASED MODE: Traditional team building with role assignment
            logger.info("[TEAM_BUILD_STRUCTURE] Role-based team query")
            requirements_data = self.team_requirements_module.extract(
                query=query,
                llm_output=llm_output
            )
            
            roles = requirements_data.to_dict()["roles"] if requirements_data else []
            composition_data = self.team_composition_module.compose(
                roles=roles,
                chunks=chunks
            )
            
            assignments = composition_data.to_dict()["assignments"] if composition_data else []
            all_required_skills = []
            for role in roles:
                all_required_skills.extend(role.get("required_skills", []))
            
            coverage_data = self.skill_coverage_module.analyze(
                assignments=assignments,
                required_skills=all_required_skills
            )
            
            coverage_dict = coverage_data.to_dict() if coverage_data else {}
            risk_data = self.team_risk_module.analyze(
                assignments=assignments,
                skill_coverage=coverage_dict
            )
        
        # Extract conclusion and analysis
        conclusion = self.conclusion_module.extract(llm_output)
        analysis = self.analysis_module.extract(llm_output, "", conclusion or "")
        
        assignments = composition_data.to_dict()["assignments"] if composition_data else []
        
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
    
    def _analyze_simple_team(self, chunks: List[Dict[str, Any]], query: str) -> Any:
        """
        Analyze available candidates as a team without role assignment.
        For queries like 'Can I build a team with the top 3?'
        """
        from ..modules.team_composition_module import TeamCompositionData, TeamAssignment
        
        # Group and rank candidates by experience
        candidates = self._group_and_rank_candidates(chunks)
        
        # Take top N candidates (default 3)
        import re
        team_size = 3
        size_match = re.search(r'top (\d+)|best (\d+)', query.lower())
        if size_match:
            team_size = int(size_match.group(1) or size_match.group(2))
        
        top_candidates = list(candidates.items())[:team_size]
        
        # Create assignments without specific roles
        assignments = []
        for idx, (cv_id, data) in enumerate(top_candidates):
            # Assign generic role based on seniority/experience
            exp = data.get("experience", 0)
            seniority = data.get("seniority", "").lower()
            
            if exp >= 10 or seniority in ["senior", "lead", "principal"]:
                role = "Senior Team Member"
            elif exp >= 5:
                role = "Mid-Level Team Member"
            else:
                role = "Team Member"
            
            assignments.append(TeamAssignment(
                role_name=role,
                candidate_name=data["name"],
                cv_id=cv_id,
                fit_score=100.0 - (idx * 5),  # Top ranked gets 100%, second 95%, etc.
                strengths=self._get_candidate_strengths(data),
                matching_skills=list(data.get("skills", set()))[:5]
            ))
        
        logger.info(f"[TEAM_BUILD_STRUCTURE] Created simple team with {len(assignments)} members")
        
        return TeamCompositionData(
            assignments=assignments,
            unassigned_roles=[]
        )
    
    def _group_and_rank_candidates(self, chunks: List[Dict[str, Any]]) -> Dict[str, Dict]:
        """Group chunks by candidate and rank by experience."""
        candidates = {}
        
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            cv_id = chunk.get("cv_id", "") or meta.get("cv_id", "")
            
            if not cv_id:
                continue
            
            if cv_id not in candidates:
                skills = set()
                skills_str = meta.get("skills", "")
                if skills_str:
                    for skill in skills_str.split(","):
                        skill = skill.strip()
                        if skill:
                            skills.add(skill)
                
                candidates[cv_id] = {
                    "name": meta.get("candidate_name", "Unknown"),
                    "cv_id": cv_id,
                    "skills": skills,
                    "experience": meta.get("total_experience_years", 0),
                    "avg_tenure": meta.get("avg_tenure_years", 0),
                    "seniority": meta.get("seniority_level", "mid"),
                    "current_role": meta.get("current_role", "")
                }
            else:
                # Update with max experience across chunks
                if meta.get("total_experience_years", 0) > candidates[cv_id]["experience"]:
                    candidates[cv_id]["experience"] = meta.get("total_experience_years", 0)
        
        # Sort by experience (descending)
        sorted_candidates = dict(sorted(
            candidates.items(),
            key=lambda x: x[1]["experience"],
            reverse=True
        ))
        
        return sorted_candidates
    
    def _get_candidate_strengths(self, candidate: Dict) -> List[str]:
        """Extract candidate strengths."""
        strengths = []
        
        exp = candidate.get("experience", 0)
        if exp > 0:
            strengths.append(f"{exp:.0f} years experience")
        
        tenure = candidate.get("avg_tenure", 0)
        if tenure >= 3:
            strengths.append(f"Stable career ({tenure:.1f}y avg tenure)")
        
        seniority = candidate.get("seniority", "")
        if seniority:
            strengths.append(f"{seniority} level")
        
        role = candidate.get("current_role", "")
        if role and len(strengths) < 3:
            strengths.append(role)
        
        return strengths[:3]
