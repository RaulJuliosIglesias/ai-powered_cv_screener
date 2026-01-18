"""
TEAM OVERVIEW MODULE

Provides executive summary of the proposed team:
- Team composition summary
- Key metrics (total experience, avg tenure, etc.)
- Team strengths and potential
- Quick recommendation
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


@dataclass
class TeamOverviewData:
    """Data structure for team overview."""
    team_size: int = 0
    total_experience_years: float = 0.0
    average_experience: float = 0.0
    average_tenure: float = 0.0
    experience_range: str = ""
    seniority_summary: str = ""
    team_members_summary: List[Dict[str, Any]] = field(default_factory=list)
    key_strengths: List[str] = field(default_factory=list)
    recommendation: str = ""
    team_score: float = 0.0
    formation_reasoning: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "team_size": self.team_size,
            "total_experience_years": self.total_experience_years,
            "average_experience": self.average_experience,
            "average_tenure": self.average_tenure,
            "experience_range": self.experience_range,
            "seniority_summary": self.seniority_summary,
            "team_members_summary": self.team_members_summary,
            "key_strengths": self.key_strengths,
            "recommendation": self.recommendation,
            "team_score": self.team_score,
            "formation_reasoning": self.formation_reasoning
        }


class TeamOverviewModule:
    """Generates executive overview of proposed team."""
    
    def generate(
        self,
        team_members: List[Dict[str, Any]],
        query: str = ""
    ) -> TeamOverviewData:
        """
        Generate team overview.
        
        Args:
            team_members: List of team member data
            query: Original query for context
            
        Returns:
            TeamOverviewData with overview
        """
        logger.info(f"[TEAM_OVERVIEW] Generating overview for {len(team_members)} members")
        
        if not team_members:
            return TeamOverviewData()
        
        # Calculate metrics
        experiences = []
        tenures = []
        seniorities = []
        members_summary = []
        
        for member in team_members:
            name = member.get("candidate_name", member.get("name", "Unknown"))
            exp = member.get("experience", member.get("experience_years", 0)) or 0
            tenure = member.get("avg_tenure", 0) or 0
            seniority = member.get("seniority", "mid") or "mid"
            role = member.get("role_name", "Team Member")
            fit_score = member.get("fit_score", 85)
            strengths = member.get("strengths", [])[:2]
            
            experiences.append(exp)
            tenures.append(tenure)
            seniorities.append(seniority.lower())
            
            members_summary.append({
                "name": name,
                "role": role,
                "experience_years": exp,
                "seniority": seniority,
                "fit_score": fit_score,
                "key_strength": strengths[0] if strengths else "Experienced professional"
            })
        
        total_exp = sum(experiences)
        avg_exp = total_exp / len(experiences) if experiences else 0
        avg_tenure = sum(tenures) / len(tenures) if tenures else 0
        
        # Experience range
        if experiences:
            min_exp, max_exp = min(experiences), max(experiences)
            exp_range = f"{min_exp:.0f}-{max_exp:.0f} years"
        else:
            exp_range = "N/A"
        
        # Seniority summary
        senior_count = sum(1 for s in seniorities if s in ["senior", "lead", "principal", "director"])
        mid_count = sum(1 for s in seniorities if s in ["mid", "intermediate"])
        junior_count = len(seniorities) - senior_count - mid_count
        
        if senior_count >= len(seniorities) // 2:
            seniority_summary = "Senior-heavy team with strong leadership"
        elif junior_count >= len(seniorities) // 2:
            seniority_summary = "Junior-focused team with growth potential"
        else:
            seniority_summary = "Balanced mix of experience levels"
        
        # Key strengths
        key_strengths = self._extract_team_strengths(team_members, total_exp, avg_tenure)
        
        # Calculate team score
        team_score = self._calculate_team_score(
            experiences, tenures, seniorities, len(team_members)
        )
        
        # Generate recommendation
        recommendation = self._generate_recommendation(
            team_members, team_score, seniority_summary
        )
        
        # Formation reasoning
        reasoning = self._generate_reasoning(team_members, query)
        
        logger.info(f"[TEAM_OVERVIEW] Team score: {team_score:.0f}%, Total exp: {total_exp:.0f} years")
        
        return TeamOverviewData(
            team_size=len(team_members),
            total_experience_years=total_exp,
            average_experience=avg_exp,
            average_tenure=avg_tenure,
            experience_range=exp_range,
            seniority_summary=seniority_summary,
            team_members_summary=members_summary,
            key_strengths=key_strengths,
            recommendation=recommendation,
            team_score=team_score,
            formation_reasoning=reasoning
        )
    
    def _extract_team_strengths(
        self, 
        team_members: List[Dict], 
        total_exp: float,
        avg_tenure: float
    ) -> List[str]:
        """Extract key team strengths."""
        strengths = []
        
        if total_exp >= 30:
            strengths.append(f"💪 {total_exp:.0f} years combined experience")
        elif total_exp >= 15:
            strengths.append(f"📈 Solid {total_exp:.0f} years combined experience")
        
        if avg_tenure >= 3:
            strengths.append(f"🔒 Strong stability ({avg_tenure:.1f}y avg tenure)")
        
        # Collect unique skills across team
        all_skills = set()
        for member in team_members:
            for skill in member.get("matching_skills", []) or []:
                all_skills.add(skill)
        
        if len(all_skills) >= 10:
            strengths.append(f"🎯 Diverse skillset ({len(all_skills)}+ skills)")
        elif len(all_skills) >= 5:
            strengths.append(f"🎯 Good skill coverage ({len(all_skills)} skills)")
        
        # Check for leadership
        has_senior = any(
            m.get("seniority", "").lower() in ["senior", "lead", "principal", "director"]
            for m in team_members
        )
        if has_senior:
            strengths.append("👔 Senior leadership presence")
        
        return strengths[:4]
    
    def _calculate_team_score(
        self,
        experiences: List[float],
        tenures: List[float],
        seniorities: List[str],
        team_size: int
    ) -> float:
        """Calculate overall team score (0-100)."""
        score = 50.0  # Base score
        
        # Experience factor (+20 max)
        total_exp = sum(experiences)
        if total_exp >= 50:
            score += 20
        elif total_exp >= 30:
            score += 15
        elif total_exp >= 15:
            score += 10
        elif total_exp >= 5:
            score += 5
        
        # Tenure stability factor (+15 max)
        avg_tenure = sum(tenures) / len(tenures) if tenures else 0
        if avg_tenure >= 4:
            score += 15
        elif avg_tenure >= 2.5:
            score += 10
        elif avg_tenure >= 1.5:
            score += 5
        
        # Seniority balance factor (+15 max)
        senior_count = sum(1 for s in seniorities if s in ["senior", "lead", "principal"])
        if senior_count >= 1 and senior_count < len(seniorities):
            score += 15  # Good balance
        elif senior_count >= 1:
            score += 10  # All senior
        else:
            score += 5   # No senior
        
        return min(100, score)
    
    def _generate_recommendation(
        self,
        team_members: List[Dict],
        team_score: float,
        seniority_summary: str
    ) -> str:
        """Generate recommendation text."""
        if team_score >= 85:
            return "✅ **Highly Recommended** - Excellent team composition with strong experience and skill coverage"
        elif team_score >= 70:
            return "✅ **Recommended** - Solid team with good balance of skills and experience"
        elif team_score >= 55:
            return "⚡ **Conditionally Recommended** - Good foundation, may benefit from additional expertise"
        else:
            return "⚠️ **Review Recommended** - Consider augmenting team with additional experience"
    
    def _generate_reasoning(self, team_members: List[Dict], query: str) -> str:
        """Generate reasoning for team formation."""
        if not team_members:
            return ""
        
        names = [m.get("candidate_name", m.get("name", ""))[:20] for m in team_members]
        names_str = ", ".join(names[:3])
        
        # Count experience levels
        senior = sum(1 for m in team_members 
                    if (m.get("experience", 0) or 0) >= 10 or 
                    m.get("seniority", "").lower() in ["senior", "lead", "principal"])
        
        if senior >= 2:
            return f"Selected {names_str} for their senior expertise and proven track records."
        elif senior == 1:
            return f"Built around senior leadership with {names_str} providing complementary skills."
        else:
            return f"Assembled {names_str} based on combined skills and growth potential."
    
    def format(self, data: TeamOverviewData) -> str:
        """Format overview as markdown."""
        if not data or data.team_size == 0:
            return ""
        
        lines = ["## 📋 Team Overview\n"]
        
        # Key metrics in a clean format
        lines.append("| Metric | Value |")
        lines.append("|:-------|------:|")
        lines.append(f"| **Team Size** | {data.team_size} members |")
        lines.append(f"| **Total Experience** | {data.total_experience_years:.0f} years |")
        lines.append(f"| **Avg Experience** | {data.average_experience:.1f} years |")
        lines.append(f"| **Experience Range** | {data.experience_range} |")
        lines.append(f"| **Team Score** | {data.team_score:.0f}% |")
        lines.append("")
        
        # Seniority summary
        lines.append(f"**Composition:** {data.seniority_summary}")
        lines.append("")
        
        # Recommendation
        lines.append(data.recommendation)
        lines.append("")
        
        # Key strengths
        if data.key_strengths:
            lines.append("### Key Team Strengths")
            for strength in data.key_strengths:
                lines.append(f"- {strength}")
        
        return "\n".join(lines)
