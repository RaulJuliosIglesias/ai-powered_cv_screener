"""
TEAM MEMBER CARDS MODULE

Creates individual member cards for visual display:
- Profile summary
- Key metrics
- Top skills
- Role assignment
- Contribution to team
"""

import logging
from typing import Dict, Any, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TeamMemberCard:
    """Individual team member card data."""
    name: str = ""
    cv_id: str = ""
    role: str = "Team Member"
    experience_years: float = 0.0
    seniority: str = "mid"
    avg_tenure: float = 0.0
    top_skills: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    fit_score: float = 0.0
    contribution: str = ""
    badge: str = ""
    rank: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "cv_id": self.cv_id,
            "role": self.role,
            "experience_years": self.experience_years,
            "seniority": self.seniority,
            "avg_tenure": self.avg_tenure,
            "top_skills": self.top_skills,
            "strengths": self.strengths,
            "fit_score": self.fit_score,
            "contribution": self.contribution,
            "badge": self.badge,
            "rank": self.rank
        }


@dataclass 
class TeamMemberCardsData:
    """Collection of team member cards."""
    cards: List[TeamMemberCard] = field(default_factory=list)
    total_members: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cards": [c.to_dict() for c in self.cards],
            "total_members": self.total_members
        }


class TeamMemberCardsModule:
    """Creates visual member cards for the team."""
    
    BADGES = {
        "most_experienced": "🏆 Most Experienced",
        "most_stable": "🔒 Most Stable", 
        "diverse_skills": "🌟 Skill Diversity",
        "senior_lead": "👔 Senior Leader",
        "rising_star": "⭐ Rising Star"
    }
    
    def create_cards(
        self,
        team_members: List[Dict[str, Any]]
    ) -> TeamMemberCardsData:
        """
        Create member cards from team data.
        
        Args:
            team_members: List of team member data
            
        Returns:
            TeamMemberCardsData with individual cards
        """
        logger.info(f"[TEAM_CARDS] Creating cards for {len(team_members)} members")
        
        if not team_members:
            return TeamMemberCardsData()
        
        cards = []
        
        # Find who gets special badges
        most_exp_idx = 0
        most_exp = 0
        most_stable_idx = 0
        most_stable = 0
        most_skills_idx = 0
        most_skills = 0
        
        for idx, member in enumerate(team_members):
            exp = member.get("experience", member.get("experience_years", 0)) or 0
            tenure = member.get("avg_tenure", 0) or 0
            skills = len(member.get("matching_skills", []) or member.get("skills", []))
            
            if exp > most_exp:
                most_exp = exp
                most_exp_idx = idx
            if tenure > most_stable:
                most_stable = tenure
                most_stable_idx = idx
            if skills > most_skills:
                most_skills = skills
                most_skills_idx = idx
        
        for idx, member in enumerate(team_members):
            name = member.get("candidate_name", member.get("name", "Unknown"))
            
            # Clean name
            for suffix in [" Research", " Associate", " UX", " Lab", " Manager", " Developer"]:
                if name.endswith(suffix):
                    name = name[:-len(suffix)].strip()
            
            exp = member.get("experience", member.get("experience_years", 0)) or 0
            tenure = member.get("avg_tenure", 0) or 0
            seniority = member.get("seniority", "mid") or "mid"
            role = member.get("role_name", "Team Member")
            fit_score = member.get("fit_score", 85)
            
            # Get skills
            skills = list(member.get("matching_skills", []) or member.get("skills", []))[:5]
            
            # Get strengths
            strengths = list(member.get("strengths", []))[:3]
            
            # Determine badge
            badge = ""
            if idx == most_exp_idx and most_exp >= 10:
                badge = self.BADGES["most_experienced"]
            elif idx == most_stable_idx and most_stable >= 3:
                badge = self.BADGES["most_stable"]
            elif seniority.lower() in ["senior", "lead", "principal", "director"]:
                badge = self.BADGES["senior_lead"]
            elif idx == most_skills_idx and most_skills >= 5:
                badge = self.BADGES["diverse_skills"]
            elif exp < 5 and fit_score >= 80:
                badge = self.BADGES["rising_star"]
            
            # Generate contribution text
            contribution = self._generate_contribution(
                name, exp, seniority, skills, role
            )
            
            card = TeamMemberCard(
                name=name,
                cv_id=member.get("cv_id", ""),
                role=role,
                experience_years=exp,
                seniority=seniority,
                avg_tenure=tenure,
                top_skills=skills,
                strengths=strengths,
                fit_score=fit_score,
                contribution=contribution,
                badge=badge,
                rank=idx + 1
            )
            cards.append(card)
        
        logger.info(f"[TEAM_CARDS] Created {len(cards)} member cards")
        
        return TeamMemberCardsData(
            cards=cards,
            total_members=len(cards)
        )
    
    def _generate_contribution(
        self,
        name: str,
        exp: float,
        seniority: str,
        skills: List[str],
        role: str
    ) -> str:
        """Generate contribution description."""
        first_name = name.split()[0] if name else "This member"
        
        if exp >= 15:
            return f"{first_name} brings executive-level expertise and strategic vision to the team."
        elif exp >= 10:
            return f"{first_name} provides senior leadership and mentorship capabilities."
        elif exp >= 5:
            return f"{first_name} contributes solid mid-level expertise and reliable execution."
        else:
            return f"{first_name} adds fresh perspective and growth potential to the team."
    
    def format(self, data: TeamMemberCardsData) -> str:
        """Format member cards as markdown."""
        if not data or not data.cards:
            return ""
        
        lines = ["## 👥 Proposed Team Members\n"]
        
        for card in data.cards:
            lines.append(f"### #{card.rank} {card.name}")
            if card.badge:
                lines.append(f"*{card.badge}*")
            lines.append("")
            
            lines.append(f"**Role:** {card.role}")
            lines.append(f"**Experience:** {card.experience_years:.0f} years | **Seniority:** {card.seniority.title()}")
            lines.append(f"**Fit Score:** {card.fit_score:.0f}%")
            lines.append("")
            
            if card.top_skills:
                lines.append(f"**Skills:** {', '.join(card.top_skills)}")
            
            if card.strengths:
                lines.append(f"**Strengths:** {', '.join(card.strengths)}")
            
            lines.append("")
            lines.append(f"*{card.contribution}*")
            lines.append("")
            lines.append("---")
            lines.append("")
        
        return "\n".join(lines)
