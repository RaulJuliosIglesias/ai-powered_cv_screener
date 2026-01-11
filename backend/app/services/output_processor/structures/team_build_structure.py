"""
TEAM BUILD STRUCTURE V2

Enhanced structure for composing teams from available candidates.
Now includes rich visual modules:

MODULES:
- ThinkingModule: AI reasoning process
- TeamOverviewModule: Executive summary with metrics
- TeamMemberCardsModule: Individual member profiles
- TeamSynergyModule: How members complement each other
- SkillMatrixModule: Visual skill coverage matrix
- TeamRiskModule: Potential risks and gaps
- ConclusionModule: Final recommendation

This structure is used when user asks for team building:
- "build a team with the top 3"
- "make a team from these candidates"
- "form a project team"
"""

import logging
import re
from typing import Dict, Any, List, Optional

from ..modules import ThinkingModule, ConclusionModule, AnalysisModule
from ..modules.team_requirements_module import TeamRequirementsModule
from ..modules.team_composition_module import TeamCompositionModule, TeamCompositionData, TeamAssignment
from ..modules.skill_coverage_module import SkillCoverageModule
from ..modules.team_risk_module import TeamRiskModule
from ..modules.team_overview_module import TeamOverviewModule
from ..modules.team_member_cards_module import TeamMemberCardsModule
from ..modules.team_synergy_module import TeamSynergyModule
from ..modules.skill_matrix_module import SkillMatrixModule

logger = logging.getLogger(__name__)


class TeamBuildStructure:
    """
    Assembles the Team Build Structure V2 with rich visual modules.
    """
    
    def __init__(self):
        self.thinking_module = ThinkingModule()
        self.analysis_module = AnalysisModule()
        self.conclusion_module = ConclusionModule()
        # New enhanced modules
        self.overview_module = TeamOverviewModule()
        self.member_cards_module = TeamMemberCardsModule()
        self.synergy_module = TeamSynergyModule()
        self.skill_matrix_module = SkillMatrixModule()
        self.risk_module = TeamRiskModule()
    
    def assemble(
        self,
        llm_output: str,
        chunks: List[Dict[str, Any]],
        query: str = "",
        conversation_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Assemble all components of Team Build Structure V2."""
        logger.info("[TEAM_BUILD_STRUCTURE_V2] Assembling enhanced team composition")
        
        # Extract thinking
        thinking = self.thinking_module.extract(llm_output)
        
        # Build team from chunks
        team_members = self._build_team_from_chunks(chunks, query)
        
        logger.info(f"[TEAM_BUILD_STRUCTURE_V2] Built team with {len(team_members)} members")
        
        # Generate all module outputs
        # 1. Team Overview - Executive summary
        overview_data = self.overview_module.generate(team_members, query)
        
        # 2. Member Cards - Individual profiles  
        cards_data = self.member_cards_module.create_cards(team_members)
        
        # 3. Team Synergy - How they complement each other
        synergy_data = self.synergy_module.analyze(team_members, chunks)
        
        # 4. Skill Matrix - Visual skill coverage
        matrix_data = self.skill_matrix_module.build(team_members)
        
        # 5. Risk Analysis
        risk_data = self._analyze_team_risks(team_members, synergy_data)
        
        # 6. Direct Answer - Clear summary
        direct_answer = self._generate_direct_answer(team_members, overview_data, query)
        
        # 7. Conclusion
        conclusion = self._generate_conclusion(team_members, overview_data, synergy_data)
        
        # Build formatted outputs for display
        formatted_overview = self.overview_module.format(overview_data)
        formatted_cards = self.member_cards_module.format(cards_data)
        formatted_synergy = self.synergy_module.format(synergy_data)
        formatted_matrix = self.skill_matrix_module.format(matrix_data)
        
        logger.info(f"[TEAM_BUILD_STRUCTURE_V2] Assembly complete")
        
        return {
            "structure_type": "team_build",
            "query": query,
            "thinking": thinking,
            "direct_answer": direct_answer,
            
            # Rich data for frontend
            "team_overview": overview_data.to_dict() if overview_data else None,
            "team_members": cards_data.to_dict() if cards_data else None,
            "team_synergy": synergy_data.to_dict() if synergy_data else None,
            "skill_matrix": matrix_data.to_dict() if matrix_data else None,
            "team_risks": risk_data,
            
            # Formatted markdown for fallback display
            "formatted_overview": formatted_overview,
            "formatted_members": formatted_cards,
            "formatted_synergy": formatted_synergy,
            "formatted_matrix": formatted_matrix,
            
            # Legacy fields for compatibility
            "team_composition": {
                "assignments": [m for m in team_members],
                "unassigned_roles": []
            },
            "total_assigned": len(team_members),
            "conclusion": conclusion,
            "analysis": self._generate_analysis(team_members, synergy_data),
            "raw_content": llm_output
        }
    
    def _build_team_from_chunks(
        self, 
        chunks: List[Dict[str, Any]], 
        query: str
    ) -> List[Dict[str, Any]]:
        """
        Build team member list from chunks.
        
        PHASE 6.4 FIX: Ensure we extract candidates even when cv_id is in different locations.
        """
        # Group chunks by candidate
        candidates = {}
        
        logger.info(f"[TEAM_BUILD] Processing {len(chunks)} chunks for team building")
        
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            # PHASE 6.4: Try multiple locations for cv_id
            cv_id = (
                chunk.get("cv_id") or 
                meta.get("cv_id") or 
                chunk.get("id") or 
                meta.get("id") or
                ""
            )
            
            if not cv_id:
                # Try to generate from candidate name if available
                candidate_name = meta.get("candidate_name", "")
                if candidate_name:
                    cv_id = f"cv_{hash(candidate_name) % 100000:05d}"
                    logger.debug(f"[TEAM_BUILD] Generated cv_id for {candidate_name}: {cv_id}")
                else:
                    continue
            
            if cv_id not in candidates:
                # Extract skills
                skills = set()
                skills_str = meta.get("skills", "")
                if skills_str:
                    for skill in skills_str.split(","):
                        skill = skill.strip()
                        if skill and len(skill) > 1:
                            skills.add(skill)
                
                candidates[cv_id] = {
                    "cv_id": cv_id,
                    "candidate_name": meta.get("candidate_name", "Unknown"),
                    "name": meta.get("candidate_name", "Unknown"),
                    "experience": meta.get("total_experience_years", 0) or 0,
                    "experience_years": meta.get("total_experience_years", 0) or 0,
                    "avg_tenure": meta.get("avg_tenure_years", 0) or 0,
                    "seniority": meta.get("seniority_level", "mid") or "mid",
                    "current_role": meta.get("current_role", ""),
                    "skills": list(skills),  # Convert set to list for JSON
                    "matching_skills": list(skills)[:10],
                    "job_hopping_score": meta.get("job_hopping_score", 0.3),
                    "_skills_set": skills  # Keep set for internal use
                }
            else:
                # Update with best values
                exp = meta.get("total_experience_years", 0) or 0
                if exp > candidates[cv_id]["experience"]:
                    candidates[cv_id]["experience"] = exp
                    candidates[cv_id]["experience_years"] = exp
                
                # Add more skills using internal set
                skills_str = meta.get("skills", "")
                if skills_str:
                    for skill in skills_str.split(","):
                        skill = skill.strip()
                        if skill and len(skill) > 1:
                            candidates[cv_id]["_skills_set"].add(skill)
                            if len(candidates[cv_id]["matching_skills"]) < 10:
                                if skill not in candidates[cv_id]["matching_skills"]:
                                    candidates[cv_id]["matching_skills"].append(skill)
        
        # Convert internal sets to lists and remove _skills_set before returning
        for cv_id, cand in candidates.items():
            if "_skills_set" in cand:
                cand["skills"] = list(cand["_skills_set"])
                del cand["_skills_set"]
        
        # Sort by experience
        sorted_candidates = sorted(
            candidates.values(),
            key=lambda x: x["experience"],
            reverse=True
        )
        
        # Determine team size from query
        team_size = 3  # default
        size_match = re.search(r'top\s*(\d+)|best\s*(\d+)|(\d+)\s*(member|candidate|person)', query.lower())
        if size_match:
            for g in size_match.groups():
                if g and g.isdigit():
                    team_size = int(g)
                    break
        
        # Take top N
        team = sorted_candidates[:team_size]
        
        # Assign roles based on experience
        for idx, member in enumerate(team):
            exp = member["experience"]
            seniority = (member.get("seniority") or "mid").lower()
            
            if exp >= 15 or seniority in ["principal", "director", "executive"]:
                role = "Team Lead"
            elif exp >= 10 or seniority in ["senior", "lead"]:
                role = "Senior Member"
            elif exp >= 5:
                role = "Core Member"
            else:
                role = "Team Member"
            
            member["role_name"] = role
            member["fit_score"] = max(70, 100 - (idx * 5))
            member["strengths"] = self._extract_strengths(member)
        
        return team
    
    def _extract_strengths(self, member: Dict) -> List[str]:
        """Extract member strengths."""
        strengths = []
        
        exp = member.get("experience", 0)
        if exp >= 15:
            strengths.append(f"{exp:.0f} years of executive experience")
        elif exp >= 10:
            strengths.append(f"{exp:.0f} years of senior experience")
        elif exp > 0:
            strengths.append(f"{exp:.0f} years experience")
        
        tenure = member.get("avg_tenure", 0)
        if tenure >= 4:
            strengths.append(f"Excellent stability ({tenure:.1f}y avg tenure)")
        elif tenure >= 2.5:
            strengths.append(f"Good stability ({tenure:.1f}y avg tenure)")
        
        hop_score = member.get("job_hopping_score", 0.5)
        if hop_score < 0.2:
            strengths.append("Strong job retention")
        
        seniority = member.get("seniority", "")
        if seniority and seniority.lower() not in ["mid", "unknown", ""]:
            strengths.append(f"{seniority.title()} level professional")
        
        return strengths[:3]
    
    def _analyze_team_risks(
        self, 
        team_members: List[Dict], 
        synergy_data
    ) -> Dict[str, Any]:
        """Analyze potential team risks."""
        risks = []
        mitigations = []
        
        # Check experience distribution
        experiences = [m.get("experience", 0) for m in team_members]
        if all(exp < 5 for exp in experiences):
            risks.append({
                "type": "experience",
                "severity": "medium",
                "description": "All team members have less than 5 years experience",
                "icon": "⚠️"
            })
            mitigations.append("Consider adding a senior mentor or advisor")
        
        # Check for single point of failure
        if len(team_members) > 0:
            max_exp = max(experiences) if experiences else 0
            others_exp = sum(experiences) - max_exp
            if max_exp > others_exp * 2 and len(team_members) > 1:
                risks.append({
                    "type": "dependency",
                    "severity": "low",
                    "description": "Heavy reliance on most experienced member",
                    "icon": "⚡"
                })
                mitigations.append("Ensure knowledge transfer and documentation")
        
        # Check skill gaps from synergy
        if synergy_data and synergy_data.potential_gaps:
            for gap in synergy_data.potential_gaps[:2]:
                risks.append({
                    "type": "skill_gap",
                    "severity": "low",
                    "description": gap,
                    "icon": "📋"
                })
        
        # Overall risk level
        if len(risks) >= 3:
            overall = "medium"
        elif len(risks) >= 1:
            overall = "low"
        else:
            overall = "minimal"
        
        return {
            "risks": risks,
            "mitigations": mitigations,
            "overall_risk_level": overall,
            "risk_count": len(risks)
        }
    
    def _generate_direct_answer(
        self, 
        team_members: List[Dict],
        overview_data,
        query: str
    ) -> str:
        """Generate clear direct answer with FULL candidate names and details."""
        if not team_members:
            return "Unable to form a team from the available candidates."
        
        total_exp = sum(m.get("experience", 0) for m in team_members)
        score = overview_data.team_score if overview_data else 75
        
        # Build header
        lines = [
            f"## ✅ Proposed Team of {len(team_members)}",
            "",
            f"**Combined Experience:** {total_exp:.0f} years | **Team Score:** {score:.0f}%",
            "",
            "### Team Members",
            "",
        ]
        
        # Add each member with FULL details
        for idx, member in enumerate(team_members, 1):
            name = member.get("candidate_name", member.get("name", "Unknown"))
            cv_id = member.get("cv_id", "")
            role = member.get("role_name", "Team Member")
            exp = member.get("experience", 0)
            current_role = member.get("current_role", "")
            # PHASE 3.3 FIX: Ensure fit_score is clamped 0-100
            fit_score = max(0, min(100, member.get("fit_score", 80)))
            
            # Clean name (remove job title suffixes)
            for suffix in [" Research", " Associate", " UX", " Lab", " Manager"]:
                if name.endswith(suffix):
                    name = name[:-len(suffix)].strip()
            
            # Create CV reference link
            cv_link = f"[📄](cv:{cv_id})" if cv_id else "📄"
            
            lines.append(f"**{idx}. {cv_link} {name}** - {role}")
            lines.append(f"   - Experience: {exp:.0f} years | Fit: {fit_score:.0f}%")
            
            if current_role:
                lines.append(f"   - Current: {current_role}")
            
            # Add top skills if available
            skills = member.get("matching_skills", member.get("skills", []))[:3]
            if skills:
                lines.append(f"   - Skills: {', '.join(skills)}")
            
            lines.append("")
        
        # Add recommendation if available
        if overview_data and overview_data.recommendation:
            lines.extend([
                "### Recommendation",
                overview_data.recommendation
            ])
        
        return "\n".join(lines)
    
    def _generate_conclusion(
        self, 
        team_members: List[Dict],
        overview_data,
        synergy_data
    ) -> str:
        """Generate conclusion text."""
        if not team_members:
            return "No team could be formed."
        
        parts = []
        
        # Team summary
        total_exp = sum(m.get("experience", 0) for m in team_members)
        parts.append(f"This {len(team_members)}-member team brings {total_exp:.0f} years of combined experience.")
        
        # Synergy highlight
        if synergy_data and synergy_data.synergy_highlights:
            parts.append(synergy_data.synergy_highlights[0].replace("🎯 ", "").replace("🤝 ", "").replace("🌟 ", ""))
        
        # Recommendation
        if overview_data:
            if overview_data.team_score >= 80:
                parts.append("This is a well-balanced team ready for complex challenges.")
            elif overview_data.team_score >= 65:
                parts.append("This team has good potential with complementary skills.")
            else:
                parts.append("Consider augmenting this team for larger projects.")
        
        return " ".join(parts)
    
    def _generate_analysis(
        self, 
        team_members: List[Dict],
        synergy_data
    ) -> str:
        """Generate analysis text."""
        if not team_members:
            return ""
        
        lines = []
        
        # Experience analysis
        experiences = [m.get("experience", 0) for m in team_members]
        avg_exp = sum(experiences) / len(experiences) if experiences else 0
        lines.append(f"**Experience Distribution:** Average {avg_exp:.1f} years per member")
        
        # Skill coverage
        all_skills = set()
        for m in team_members:
            all_skills.update(m.get("matching_skills", []) or m.get("skills", []))
        if all_skills:
            lines.append(f"**Skill Coverage:** {len(all_skills)} unique skills identified")
        
        # Synergy
        if synergy_data and synergy_data.shared_skills:
            lines.append(f"**Collaboration Areas:** {', '.join(synergy_data.shared_skills[:3])}")
        
        return "\n".join(lines)
    
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
