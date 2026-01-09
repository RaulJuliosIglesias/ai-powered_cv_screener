"""
TEAM SYNERGY MODULE

Analyzes how team members complement each other:
- Skill overlap vs unique skills
- Experience distribution
- Seniority balance
- Potential collaboration areas
"""

import logging
from typing import Dict, Any, List, Set
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TeamSynergyData:
    """Data structure for team synergy analysis."""
    total_unique_skills: int = 0
    shared_skills: List[str] = field(default_factory=list)
    unique_skills_by_member: Dict[str, List[str]] = field(default_factory=dict)
    skill_coverage_score: float = 0.0
    experience_balance: str = "balanced"
    seniority_distribution: Dict[str, int] = field(default_factory=dict)
    collaboration_areas: List[Dict[str, Any]] = field(default_factory=list)
    team_diversity_score: float = 0.0
    potential_gaps: List[str] = field(default_factory=list)
    synergy_highlights: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_unique_skills": self.total_unique_skills,
            "shared_skills": self.shared_skills,
            "unique_skills_by_member": self.unique_skills_by_member,
            "skill_coverage_score": self.skill_coverage_score,
            "experience_balance": self.experience_balance,
            "seniority_distribution": self.seniority_distribution,
            "collaboration_areas": self.collaboration_areas,
            "team_diversity_score": self.team_diversity_score,
            "potential_gaps": self.potential_gaps,
            "synergy_highlights": self.synergy_highlights
        }


class TeamSynergyModule:
    """Analyzes synergies between team members."""
    
    def analyze(
        self,
        team_members: List[Dict[str, Any]],
        chunks: List[Dict[str, Any]] = None
    ) -> TeamSynergyData:
        """
        Analyze team synergies.
        
        Args:
            team_members: List of team member data with skills, experience, etc.
            chunks: Original CV chunks for additional context
            
        Returns:
            TeamSynergyData with synergy analysis
        """
        logger.info(f"[TEAM_SYNERGY] Analyzing synergy for {len(team_members)} members")
        
        if not team_members:
            return TeamSynergyData()
        
        # Collect all skills per member
        member_skills: Dict[str, Set[str]] = {}
        member_experience: Dict[str, float] = {}
        member_seniority: Dict[str, str] = {}
        
        for member in team_members:
            name = member.get("candidate_name", member.get("name", "Unknown"))
            skills = set(member.get("matching_skills", []) or member.get("skills", []))
            
            # Also extract from strengths if available
            for strength in member.get("strengths", []):
                if isinstance(strength, str) and not any(x in strength.lower() for x in ["year", "tenure", "level"]):
                    skills.add(strength)
            
            member_skills[name] = skills
            member_experience[name] = member.get("experience", member.get("experience_years", 0)) or 0
            member_seniority[name] = member.get("seniority", "mid")
        
        # Calculate skill overlap and uniqueness
        all_skills: Set[str] = set()
        for skills in member_skills.values():
            all_skills.update(skills)
        
        # Find shared skills (skills that 2+ members have)
        skill_count: Dict[str, int] = {}
        for skills in member_skills.values():
            for skill in skills:
                skill_count[skill] = skill_count.get(skill, 0) + 1
        
        shared_skills = [s for s, c in skill_count.items() if c >= 2]
        
        # Find unique skills per member
        unique_by_member: Dict[str, List[str]] = {}
        for name, skills in member_skills.items():
            unique = [s for s in skills if skill_count.get(s, 0) == 1]
            unique_by_member[name] = unique
        
        # Calculate seniority distribution
        seniority_dist: Dict[str, int] = {"junior": 0, "mid": 0, "senior": 0, "lead": 0}
        for sen in member_seniority.values():
            sen_lower = sen.lower() if sen else "mid"
            if "junior" in sen_lower or "entry" in sen_lower:
                seniority_dist["junior"] += 1
            elif "senior" in sen_lower or "principal" in sen_lower or "lead" in sen_lower:
                seniority_dist["senior"] += 1
            else:
                seniority_dist["mid"] += 1
        
        # Analyze experience balance
        experiences = list(member_experience.values())
        if experiences:
            avg_exp = sum(experiences) / len(experiences)
            exp_range = max(experiences) - min(experiences) if len(experiences) > 1 else 0
            
            if exp_range > 15:
                exp_balance = "diverse"
            elif exp_range > 5:
                exp_balance = "balanced"
            else:
                exp_balance = "homogeneous"
        else:
            exp_balance = "unknown"
        
        # Calculate diversity score (0-100)
        unique_skill_count = sum(len(u) for u in unique_by_member.values())
        total_skills = len(all_skills) if all_skills else 1
        diversity_score = min(100, (unique_skill_count / total_skills) * 100 + len(shared_skills) * 5)
        
        # Generate collaboration areas
        collaboration_areas = self._find_collaboration_areas(member_skills, shared_skills)
        
        # Generate synergy highlights
        highlights = self._generate_highlights(
            team_members, member_skills, shared_skills, 
            unique_by_member, exp_balance, seniority_dist
        )
        
        # Identify potential gaps
        gaps = self._identify_gaps(all_skills, seniority_dist, experiences)
        
        # Calculate overall coverage score
        coverage_score = min(100, len(all_skills) * 3 + len(shared_skills) * 10)
        
        logger.info(f"[TEAM_SYNERGY] Found {len(all_skills)} unique skills, {len(shared_skills)} shared")
        
        return TeamSynergyData(
            total_unique_skills=len(all_skills),
            shared_skills=shared_skills[:10],  # Top 10
            unique_skills_by_member=unique_by_member,
            skill_coverage_score=coverage_score,
            experience_balance=exp_balance,
            seniority_distribution=seniority_dist,
            collaboration_areas=collaboration_areas[:5],
            team_diversity_score=diversity_score,
            potential_gaps=gaps,
            synergy_highlights=highlights
        )
    
    def _find_collaboration_areas(
        self, 
        member_skills: Dict[str, Set[str]], 
        shared_skills: List[str]
    ) -> List[Dict[str, Any]]:
        """Find areas where team members can collaborate."""
        areas = []
        
        for skill in shared_skills[:5]:
            members_with_skill = [
                name for name, skills in member_skills.items() 
                if skill in skills
            ]
            if len(members_with_skill) >= 2:
                areas.append({
                    "skill": skill,
                    "members": members_with_skill,
                    "collaboration_potential": "high" if len(members_with_skill) >= 2 else "medium"
                })
        
        return areas
    
    def _generate_highlights(
        self,
        team_members: List[Dict],
        member_skills: Dict[str, Set[str]],
        shared_skills: List[str],
        unique_by_member: Dict[str, List[str]],
        exp_balance: str,
        seniority_dist: Dict[str, int]
    ) -> List[str]:
        """Generate synergy highlights."""
        highlights = []
        
        # Experience highlight
        total_exp = sum(m.get("experience", m.get("experience_years", 0)) or 0 for m in team_members)
        if total_exp > 0:
            highlights.append(f"🎯 Combined {total_exp:.0f} years of experience")
        
        # Shared skills highlight
        if shared_skills:
            highlights.append(f"🤝 Strong overlap in: {', '.join(shared_skills[:3])}")
        
        # Diversity highlight
        total_unique = sum(len(u) for u in unique_by_member.values())
        if total_unique > 0:
            highlights.append(f"🌟 {total_unique} unique skills across the team")
        
        # Seniority highlight
        if seniority_dist.get("senior", 0) >= 1 and seniority_dist.get("mid", 0) >= 1:
            highlights.append("⚖️ Good mix of senior leadership and mid-level execution")
        
        # Experience balance
        if exp_balance == "diverse":
            highlights.append("📊 Diverse experience levels enable mentorship opportunities")
        elif exp_balance == "balanced":
            highlights.append("📊 Well-balanced experience distribution")
        
        return highlights[:5]
    
    def _identify_gaps(
        self,
        all_skills: Set[str],
        seniority_dist: Dict[str, int],
        experiences: List[float]
    ) -> List[str]:
        """Identify potential team gaps."""
        gaps = []
        
        # Check for missing common skills
        common_skills = {"python", "javascript", "sql", "communication", "leadership", "project management"}
        missing_common = common_skills - {s.lower() for s in all_skills}
        
        # Only flag as gap if it seems relevant
        if len(all_skills) < 5:
            gaps.append("Limited skill diversity - consider broadening team expertise")
        
        # Seniority gaps
        if seniority_dist.get("senior", 0) == 0 and len(experiences) > 2:
            gaps.append("No senior leadership - may need experienced guidance")
        
        if all(exp < 3 for exp in experiences) and experiences:
            gaps.append("All team members are relatively junior")
        
        return gaps[:3]
    
    def format(self, data: TeamSynergyData) -> str:
        """Format synergy data as markdown."""
        if not data or data.total_unique_skills == 0:
            return ""
        
        lines = ["## 🔗 Team Synergy Analysis\n"]
        
        # Highlights
        if data.synergy_highlights:
            for highlight in data.synergy_highlights:
                lines.append(f"- {highlight}")
            lines.append("")
        
        # Skill coverage
        lines.append(f"**Skill Coverage:** {data.skill_coverage_score:.0f}% | **Diversity Score:** {data.team_diversity_score:.0f}%")
        lines.append("")
        
        # Shared skills
        if data.shared_skills:
            lines.append(f"**Shared Expertise:** {', '.join(data.shared_skills)}")
            lines.append("")
        
        # Collaboration areas
        if data.collaboration_areas:
            lines.append("### Collaboration Opportunities")
            for area in data.collaboration_areas:
                members = ", ".join(area["members"])
                lines.append(f"- **{area['skill']}**: {members}")
            lines.append("")
        
        # Gaps
        if data.potential_gaps:
            lines.append("### ⚠️ Areas to Address")
            for gap in data.potential_gaps:
                lines.append(f"- {gap}")
        
        return "\n".join(lines)
