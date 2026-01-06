"""
TEAM REQUIREMENTS MODULE

Extracts team role requirements from query.
Used by: TeamBuildStructure
"""

import logging
import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TeamRole:
    """Single team role requirement."""
    role_name: str
    required_skills: List[str] = field(default_factory=list)
    seniority: str = "mid"
    count: int = 1


@dataclass
class TeamRequirementsData:
    """Container for team requirements."""
    roles: List[TeamRole] = field(default_factory=list)
    project_context: str = ""
    total_headcount: int = 0
    
    def to_dict(self) -> Dict:
        return {
            "roles": [
                {
                    "role_name": r.role_name,
                    "required_skills": r.required_skills,
                    "seniority": r.seniority,
                    "count": r.count
                }
                for r in self.roles
            ],
            "project_context": self.project_context,
            "total_headcount": self.total_headcount
        }


class TeamRequirementsModule:
    """Module for extracting team role requirements."""
    
    ROLE_PATTERNS = {
        'backend': ['Python', 'Java', 'Node.js', 'API', 'Database'],
        'frontend': ['React', 'Vue', 'Angular', 'JavaScript', 'CSS'],
        'fullstack': ['React', 'Node.js', 'Python', 'JavaScript'],
        'devops': ['AWS', 'Docker', 'Kubernetes', 'CI/CD', 'Terraform'],
        'data': ['Python', 'SQL', 'Machine Learning', 'Analytics'],
        'mobile': ['iOS', 'Android', 'React Native', 'Flutter'],
        'qa': ['Testing', 'Automation', 'Selenium', 'QA'],
        'lead': ['Architecture', 'Leadership', 'Management'],
    }
    
    def extract(
        self,
        query: str,
        llm_output: str = ""
    ) -> Optional[TeamRequirementsData]:
        """Extract team requirements from query."""
        if not query and not llm_output:
            return None
        
        roles = []
        text = query + " " + llm_output
        
        # Extract headcount
        count_match = re.search(r'(\d+)\s*(?:person|people|developer|engineer|member)', text, re.IGNORECASE)
        total_count = int(count_match.group(1)) if count_match else 3
        
        # Extract project context
        project_context = self._extract_project_context(text)
        
        # Extract specific roles mentioned
        roles = self._extract_roles(text)
        
        # If no specific roles, infer from context
        if not roles:
            roles = self._infer_roles(text, total_count)
        
        total_headcount = sum(r.count for r in roles)
        
        logger.info(f"[TEAM_REQUIREMENTS_MODULE] Extracted {len(roles)} roles, {total_headcount} headcount")
        
        return TeamRequirementsData(
            roles=roles,
            project_context=project_context,
            total_headcount=total_headcount
        )
    
    def _extract_project_context(self, text: str) -> str:
        """Extract project context from text."""
        patterns = [
            r'(?:for|to build|for building)\s+(?:a\s+)?([^,.\n]+)',
            r'(?:project|product|app|application)[:\s]+([^,.\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()[:100]
        
        return ""
    
    def _extract_roles(self, text: str) -> List[TeamRole]:
        """Extract explicitly mentioned roles."""
        roles = []
        text_lower = text.lower()
        
        # Pattern: "2 backend developers", "1 frontend engineer"
        role_pattern = r'(\d+)\s*(senior|junior|mid|lead)?\s*(backend|frontend|fullstack|devops|data|mobile|qa)\s*(?:developer|engineer)?'
        
        for match in re.finditer(role_pattern, text_lower):
            count = int(match.group(1))
            seniority = match.group(2) or "mid"
            role_type = match.group(3)
            
            role_name = f"{seniority.title()} {role_type.title()} Developer"
            skills = self.ROLE_PATTERNS.get(role_type, [])
            
            roles.append(TeamRole(
                role_name=role_name,
                required_skills=skills,
                seniority=seniority,
                count=count
            ))
        
        return roles
    
    def _infer_roles(self, text: str, total_count: int) -> List[TeamRole]:
        """Infer roles when not explicitly specified."""
        roles = []
        text_lower = text.lower()
        
        # Detect project type
        if any(kw in text_lower for kw in ['web', 'website', 'app', 'application']):
            # Standard web team
            roles.append(TeamRole(
                role_name="Backend Developer",
                required_skills=self.ROLE_PATTERNS['backend'],
                seniority="mid",
                count=max(1, total_count // 3)
            ))
            roles.append(TeamRole(
                role_name="Frontend Developer",
                required_skills=self.ROLE_PATTERNS['frontend'],
                seniority="mid",
                count=max(1, total_count // 3)
            ))
            remaining = total_count - sum(r.count for r in roles)
            if remaining > 0:
                roles.append(TeamRole(
                    role_name="Fullstack Developer",
                    required_skills=self.ROLE_PATTERNS['fullstack'],
                    seniority="senior",
                    count=remaining
                ))
        else:
            # Generic team
            roles.append(TeamRole(
                role_name="Software Developer",
                required_skills=['Programming', 'Problem Solving'],
                seniority="mid",
                count=total_count
            ))
        
        return roles
    
    def format(self, data: TeamRequirementsData) -> str:
        """Format team requirements into markdown."""
        if not data or not data.roles:
            return ""
        
        lines = ["### 👥 Team Requirements", ""]
        
        if data.project_context:
            lines.append(f"**Project:** {data.project_context}")
            lines.append("")
        
        lines.append(f"**Total Headcount:** {data.total_headcount}")
        lines.append("")
        
        for role in data.roles:
            skills_str = ", ".join(role.required_skills[:4])
            lines.append(f"- **{role.count}x {role.role_name}** ({role.seniority})")
            lines.append(f"  - Skills: {skills_str}")
        
        return "\n".join(lines)
