"""
TEAM COMPOSITION MODULE

Assigns candidates to team roles.
Used by: TeamBuildStructure
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TeamAssignment:
    """Single candidate assignment to a role."""
    role_name: str
    candidate_name: str
    cv_id: str
    fit_score: float
    strengths: List[str] = field(default_factory=list)
    matching_skills: List[str] = field(default_factory=list)


@dataclass
class TeamCompositionData:
    """Container for team composition."""
    assignments: List[TeamAssignment] = field(default_factory=list)
    unassigned_roles: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "assignments": [
                {
                    "role_name": a.role_name,
                    "candidate_name": a.candidate_name,
                    "cv_id": a.cv_id,
                    "fit_score": a.fit_score,
                    "strengths": a.strengths,
                    "matching_skills": a.matching_skills
                }
                for a in self.assignments
            ],
            "unassigned_roles": self.unassigned_roles
        }


class TeamCompositionModule:
    """Module for composing teams by assigning candidates to roles."""
    
    def compose(
        self,
        roles: List[Dict[str, Any]],
        chunks: List[Dict[str, Any]]
    ) -> Optional[TeamCompositionData]:
        """Compose team by assigning candidates to roles."""
        if not roles or not chunks:
            return None
        
        # Group chunks by candidate
        candidates = self._group_by_candidate(chunks)
        
        assignments = []
        assigned_candidates = set()
        unassigned_roles = []
        
        # For each role, find best matching candidate
        for role in roles:
            role_name = role.get("role_name", "Developer")
            required_skills = role.get("required_skills", [])
            count = role.get("count", 1)
            
            for _ in range(count):
                best_match = None
                best_score = 0
                
                for cv_id, data in candidates.items():
                    if cv_id in assigned_candidates:
                        continue
                    
                    score, matching = self._calculate_fit(data, required_skills)
                    if score > best_score:
                        best_score = score
                        best_match = (cv_id, data, matching)
                
                if best_match:
                    cv_id, data, matching = best_match
                    assigned_candidates.add(cv_id)
                    
                    assignments.append(TeamAssignment(
                        role_name=role_name,
                        candidate_name=data["name"],
                        cv_id=cv_id,
                        fit_score=round(best_score, 1),
                        strengths=self._get_strengths(data),
                        matching_skills=matching
                    ))
                else:
                    unassigned_roles.append(role_name)
        
        logger.info(f"[TEAM_COMPOSITION_MODULE] Assigned {len(assignments)} roles")
        
        return TeamCompositionData(
            assignments=assignments,
            unassigned_roles=unassigned_roles
        )
    
    def _group_by_candidate(self, chunks: List[Dict[str, Any]]) -> Dict[str, Dict]:
        """Group chunks by candidate."""
        candidates = {}
        
        for chunk in chunks:
            meta = chunk.get("metadata", {})
            cv_id = chunk.get("cv_id", "") or meta.get("cv_id", "")
            
            if not cv_id or cv_id in candidates:
                continue
            
            skills = set()
            skills_str = meta.get("skills", "")
            if skills_str:
                for skill in skills_str.split(","):
                    skill = skill.strip().lower()
                    if skill:
                        skills.add(skill)
            
            candidates[cv_id] = {
                "name": meta.get("candidate_name", "Unknown"),
                "cv_id": cv_id,
                "skills": skills,
                "experience": meta.get("total_experience_years", 0),
                "seniority": meta.get("seniority_level", "mid"),
                "current_role": meta.get("current_role", "")
            }
        
        return candidates
    
    def _calculate_fit(
        self,
        candidate: Dict,
        required_skills: List[str]
    ) -> tuple[float, List[str]]:
        """Calculate fit score for a candidate."""
        if not required_skills:
            return 50.0, []
        
        candidate_skills = candidate.get("skills", set())
        matching = []
        
        for skill in required_skills:
            skill_lower = skill.lower()
            for cs in candidate_skills:
                if skill_lower in cs or cs in skill_lower:
                    matching.append(skill)
                    break
        
        # Base score from skill match
        skill_score = (len(matching) / len(required_skills)) * 70
        
        # Bonus for experience
        exp = candidate.get("experience", 0)
        exp_bonus = min(20, exp * 2)
        
        # Bonus for seniority
        seniority = candidate.get("seniority", "").lower()
        seniority_bonus = {"senior": 10, "lead": 10, "mid": 5}.get(seniority, 0)
        
        total = skill_score + exp_bonus + seniority_bonus
        return min(100, total), matching
    
    def _get_strengths(self, candidate: Dict) -> List[str]:
        """Get candidate strengths."""
        strengths = []
        
        exp = candidate.get("experience", 0)
        if exp >= 5:
            strengths.append(f"{exp:.0f} years experience")
        
        role = candidate.get("current_role", "")
        if role:
            strengths.append(role)
        
        return strengths[:2]
    
    def format(self, data: TeamCompositionData) -> str:
        """Format team composition into markdown."""
        if not data:
            return ""
        
        lines = ["### 🏗️ Proposed Team Composition", ""]
        
        if data.assignments:
            lines.extend([
                "| Role | Candidate | Fit | Key Skills |",
                "|:-----|:----------|:---:|:-----------|",
            ])
            
            for a in data.assignments:
                skills = ", ".join(a.matching_skills[:3]) or "-"
                lines.append(
                    f"| **{a.role_name}** | [📄](cv:{a.cv_id}) {a.candidate_name} | "
                    f"{a.fit_score:.0f}% | {skills} |"
                )
        
        if data.unassigned_roles:
            lines.append("")
            lines.append(f"⚠️ **Unfilled roles:** {', '.join(data.unassigned_roles)}")
        
        return "\n".join(lines)
