"""
Fills placeholders in suggestion templates with actual values.
"""
import random
import logging
from typing import List

from .banks.base import Suggestion
from .context_extractor import ExtractedContext

logger = logging.getLogger(__name__)


class TemplateFiller:
    """
    Fills placeholders in suggestions with context values.
    
    Placeholders:
    - {candidate_name} → Mentioned candidate name
    - {skill} → Mentioned skill
    - {role} → Mentioned or default role
    - {num_cvs} → Number of CVs
    """
    
    # Default roles to use when none mentioned
    DEFAULT_ROLES = [
        "Backend Developer",
        "Frontend Developer",
        "Senior Engineer",
        "Tech Lead",
        "Data Scientist",
        "Fullstack Developer",
    ]
    
    def fill(
        self,
        suggestions: List[Suggestion],
        context: ExtractedContext
    ) -> List[str]:
        """
        Fill placeholders in suggestions with context values.
        
        Args:
            suggestions: Selected suggestions to fill
            context: Extracted context with values
            
        Returns:
            List of filled suggestion strings
        """
        filled = []
        used_candidates = set()
        used_skills = set()
        
        for suggestion in suggestions:
            text = suggestion.text
            
            # Fill {candidate_name}
            if "{candidate_name}" in text:
                # Try to use a different candidate each time
                available = [c for c in context.mentioned_candidates if c not in used_candidates]
                if not available:
                    available = context.mentioned_candidates or context.cv_names
                
                if available:
                    name = random.choice(available)
                    used_candidates.add(name)
                    text = text.replace("{candidate_name}", name)
                else:
                    # Skip this suggestion if no name available
                    continue
            
            # Fill {skill}
            if "{skill}" in text:
                # Try to use a different skill each time
                available = [s for s in context.mentioned_skills if s not in used_skills]
                if not available:
                    available = context.mentioned_skills
                
                if available:
                    skill = random.choice(available)
                    used_skills.add(skill)
                    text = text.replace("{skill}", skill.title())
                else:
                    # Skip this suggestion if no skill available
                    continue
            
            # Fill {role}
            if "{role}" in text:
                if context.mentioned_roles:
                    role = random.choice(context.mentioned_roles)
                else:
                    role = random.choice(self.DEFAULT_ROLES)
                text = text.replace("{role}", role)
            
            # Fill {num_cvs}
            text = text.replace("{num_cvs}", str(context.num_cvs))
            
            filled.append(text)
        
        logger.info(f"[TEMPLATE_FILLER] Filled {len(filled)} suggestions")
        
        return filled
