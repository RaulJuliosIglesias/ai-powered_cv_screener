"""
SKILL MATRIX MODULE

Creates a visual skill matrix showing:
- Each team member's skills
- Skill levels/proficiency indicators
- Coverage visualization
- Complementary skills identification
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set

logger = logging.getLogger(__name__)


@dataclass
class SkillMatrixData:
    """Data structure for skill matrix visualization."""
    matrix: List[Dict[str, Any]] = field(default_factory=list)
    all_skills: List[str] = field(default_factory=list)
    members: List[str] = field(default_factory=list)
    skill_categories: Dict[str, List[str]] = field(default_factory=dict)
    coverage_by_skill: Dict[str, int] = field(default_factory=dict)
    member_skill_counts: Dict[str, int] = field(default_factory=dict)
    strongest_areas: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "matrix": self.matrix,
            "all_skills": self.all_skills,
            "members": self.members,
            "skill_categories": self.skill_categories,
            "coverage_by_skill": self.coverage_by_skill,
            "member_skill_counts": self.member_skill_counts,
            "strongest_areas": self.strongest_areas
        }


class SkillMatrixModule:
    """Creates skill matrix visualization data."""
    
    SKILL_CATEGORIES = {
        "technical": {
            "python", "javascript", "java", "c++", "sql", "react", "node",
            "aws", "docker", "kubernetes", "git", "api", "database", "cloud",
            "machine learning", "ai", "data science", "typescript", "html", "css"
        },
        "leadership": {
            "leadership", "management", "team lead", "director", "mentor",
            "coaching", "strategy", "vision", "decision making"
        },
        "communication": {
            "communication", "presentation", "writing", "public speaking",
            "negotiation", "stakeholder management", "client facing"
        },
        "analytical": {
            "analysis", "research", "problem solving", "critical thinking",
            "data analysis", "statistics", "modeling", "optimization"
        },
        "project": {
            "project management", "agile", "scrum", "kanban", "planning",
            "budgeting", "timeline", "delivery", "coordination"
        }
    }
    
    def build(
        self,
        team_members: List[Dict[str, Any]],
        max_skills: int = 15
    ) -> SkillMatrixData:
        """
        Build a skill matrix for the team.
        
        Args:
            team_members: List of team member data
            max_skills: Maximum skills to include in matrix
            
        Returns:
            SkillMatrixData with matrix visualization data
        """
        logger.info(f"[SKILL_MATRIX] Building matrix for {len(team_members)} members")
        
        if not team_members:
            return SkillMatrixData()
        
        # Extract all skills and member info
        member_skills: Dict[str, Set[str]] = {}
        all_skills_set: Set[str] = set()
        
        for member in team_members:
            name = member.get("candidate_name", member.get("name", "Unknown"))
            # Clean name - remove suffixes
            for suffix in [" Research", " Associate", " UX", " Lab", " Manager"]:
                if name.endswith(suffix):
                    name = name[:-len(suffix)].strip()
            
            skills = set()
            
            # Get skills from various sources
            for skill in member.get("matching_skills", []) or []:
                if skill:
                    skills.add(skill.lower().strip())
            
            for skill in member.get("skills", []) or []:
                if isinstance(skill, str) and skill:
                    skills.add(skill.lower().strip())
            
            # Extract from strengths (but not experience/tenure phrases)
            for strength in member.get("strengths", []) or []:
                if isinstance(strength, str):
                    # Skip if it's about years or tenure
                    if not any(x in strength.lower() for x in ["year", "tenure", "level", "experience"]):
                        skills.add(strength.lower().strip())
            
            member_skills[name] = skills
            all_skills_set.update(skills)
        
        # Sort skills by coverage (most common first)
        skill_coverage: Dict[str, int] = {}
        for skill in all_skills_set:
            count = sum(1 for ms in member_skills.values() if skill in ms)
            skill_coverage[skill] = count
        
        sorted_skills = sorted(
            all_skills_set, 
            key=lambda s: (skill_coverage.get(s, 0), s),
            reverse=True
        )[:max_skills]
        
        # Categorize skills
        categorized: Dict[str, List[str]] = {cat: [] for cat in self.SKILL_CATEGORIES}
        categorized["other"] = []
        
        for skill in sorted_skills:
            categorized_flag = False
            for cat, cat_skills in self.SKILL_CATEGORIES.items():
                if any(cs in skill for cs in cat_skills):
                    categorized[cat].append(skill)
                    categorized_flag = True
                    break
            if not categorized_flag:
                categorized["other"].append(skill)
        
        # Remove empty categories
        categorized = {k: v for k, v in categorized.items() if v}
        
        # Build matrix rows
        matrix = []
        members_list = list(member_skills.keys())
        
        for skill in sorted_skills:
            row = {
                "skill": skill,
                "coverage": skill_coverage.get(skill, 0),
                "members": {}
            }
            for name in members_list:
                has_skill = skill in member_skills.get(name, set())
                row["members"][name] = {
                    "has_skill": has_skill,
                    "indicator": "✓" if has_skill else "·"
                }
            matrix.append(row)
        
        # Calculate member skill counts
        member_counts = {name: len(skills) for name, skills in member_skills.items()}
        
        # Find strongest areas (skills with 2+ members)
        strongest = [s for s, c in skill_coverage.items() if c >= 2][:5]
        
        logger.info(f"[SKILL_MATRIX] Created matrix with {len(sorted_skills)} skills, {len(members_list)} members")
        
        return SkillMatrixData(
            matrix=matrix,
            all_skills=sorted_skills,
            members=members_list,
            skill_categories=categorized,
            coverage_by_skill=skill_coverage,
            member_skill_counts=member_counts,
            strongest_areas=strongest
        )
    
    def format(self, data: SkillMatrixData) -> str:
        """Format skill matrix as markdown table."""
        if not data or not data.matrix:
            return ""
        
        lines = ["## 📊 Team Skills Matrix\n"]
        
        # Header
        header = "| Skill |"
        separator = "|:------|"
        for member in data.members:
            # Shorten name for display
            short_name = member.split()[0] if member else "?"
            header += f" {short_name} |"
            separator += ":---:|"
        header += " Coverage |"
        separator += ":---:|"
        
        lines.append(header)
        lines.append(separator)
        
        # Rows
        for row in data.matrix[:12]:  # Limit to 12 skills for readability
            skill_name = row["skill"].title()[:20]
            line = f"| **{skill_name}** |"
            
            for member in data.members:
                indicator = row["members"].get(member, {}).get("indicator", "·")
                line += f" {indicator} |"
            
            coverage = row["coverage"]
            coverage_bar = "●" * coverage + "○" * (len(data.members) - coverage)
            line += f" {coverage_bar} |"
            
            lines.append(line)
        
        lines.append("")
        
        # Legend
        lines.append("*✓ = Has skill | · = Not listed*")
        
        # Strongest areas
        if data.strongest_areas:
            lines.append("")
            lines.append(f"**🎯 Team Strengths:** {', '.join(s.title() for s in data.strongest_areas)}")
        
        return "\n".join(lines)
