"""
Extracts contextual information from conversation history.

REUTILIZA la infraestructura existente de get_conversation_history().
"""
import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set

logger = logging.getLogger(__name__)


# Technical skills taxonomy (simplified version)
COMMON_SKILLS = {
    "python", "javascript", "typescript", "java", "c++", "c#", "go", "rust", "ruby", "php",
    "react", "vue", "angular", "svelte", "nextjs", "nodejs", "express", "django", "flask", "fastapi",
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "graphql", "rest", "api",
    "docker", "kubernetes", "aws", "azure", "gcp", "terraform", "jenkins", "ci/cd",
    "git", "linux", "agile", "scrum", "microservices", "machine learning", "ml", "ai",
    "tensorflow", "pytorch", "pandas", "numpy", "sql", "nosql", "html", "css", "sass",
    "spring", "hibernate", ".net", "unity", "unreal", "blender", "maya", "3d", "2d",
    "figma", "sketch", "photoshop", "illustrator", "ui", "ux", "frontend", "backend", "fullstack",
}


@dataclass
class ExtractedContext:
    """
    Context extracted from conversation history.
    
    This is what the SuggestionSelector uses to pick suggestions.
    """
    # Query type info
    last_query_type: str = "initial"      # From structured_output.structure_type
    query_types_in_session: Set[str] = field(default_factory=set)
    
    # Entities mentioned
    mentioned_candidates: List[str] = field(default_factory=list)
    mentioned_skills: List[str] = field(default_factory=list)
    mentioned_roles: List[str] = field(default_factory=list)
    
    # Session info
    num_cvs: int = 0
    cv_names: List[str] = field(default_factory=list)
    
    # Analysis
    num_messages: int = 0
    is_first_query: bool = True


class ContextExtractor:
    """
    Extracts context from conversation history and session data.
    
    REUTILIZA:
    - conversation_history from get_conversation_history()
    - structured_output from ChatMessage (contains structure_type)
    """
    
    # CV reference pattern: **[Name](cv:cv_xxx)**
    CV_REFERENCE_PATTERN = re.compile(
        r'\*\*\[([^\]]+)\]\(cv:cv_[a-f0-9]+\)\*\*',
        re.IGNORECASE
    )
    
    # Alternative pattern: [📄](cv:cv_xxx) **Name**
    CV_ICON_PATTERN = re.compile(
        r'\[📄\]\(cv:cv_[a-f0-9]+\)\s*\*\*([^*]+)\*\*',
        re.IGNORECASE
    )
    
    # Simple name pattern in bold: **Name**
    BOLD_NAME_PATTERN = re.compile(
        r'\*\*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\*\*'
    )
    
    def __init__(self):
        self.all_skills = COMMON_SKILLS
        
        # Common role keywords
        self.role_keywords = {
            "backend", "frontend", "fullstack", "devops", "data",
            "senior", "junior", "lead", "manager", "architect",
            "engineer", "developer", "analyst", "designer"
        }
    
    def extract(
        self,
        messages: List[Dict],
        cv_names: List[str],
        num_cvs: int
    ) -> ExtractedContext:
        """
        Extract context from conversation history.
        
        Args:
            messages: From get_conversation_history() - list of dicts with role/content
            cv_names: Names of CVs in session
            num_cvs: Number of CVs in session
            
        Returns:
            ExtractedContext with all extracted information
        """
        context = ExtractedContext(
            num_cvs=num_cvs,
            cv_names=cv_names,
            num_messages=len(messages),
            is_first_query=len(messages) == 0
        )
        
        if not messages:
            return context
        
        # Process messages in reverse (most recent first)
        for i, msg in enumerate(reversed(messages)):
            content = msg.get("content", "")
            role = msg.get("role", "")
            structured_output = msg.get("structured_output") or {}
            
            # Extract query_type from structured_output
            if structured_output:
                structure_type = structured_output.get("structure_type")
                if structure_type:
                    context.query_types_in_session.add(structure_type)
                    if i == 0 and role == "assistant":  # Most recent
                        context.last_query_type = structure_type
            
            # Extract candidates from assistant responses
            if role == "assistant":
                candidates = self._extract_candidates(content)
                for c in candidates:
                    if c not in context.mentioned_candidates:
                        context.mentioned_candidates.append(c)
            
            # Extract skills and roles from user queries
            if role == "user":
                skills = self._extract_skills(content)
                for s in skills:
                    if s not in context.mentioned_skills:
                        context.mentioned_skills.append(s)
                
                roles = self._extract_roles(content)
                for r in roles:
                    if r not in context.mentioned_roles:
                        context.mentioned_roles.append(r)
        
        # For initial queries, add all CV names as mentioned candidates
        # This enables candidate-specific suggestions even in new chats
        if context.is_first_query:
            context.mentioned_candidates.extend(cv_names)
        else:
            # For ongoing conversations, only add new names
            for name in cv_names:
                if name not in context.mentioned_candidates:
                    context.mentioned_candidates.append(name)
        
        # Limit lists to most recent/relevant
        context.mentioned_candidates = context.mentioned_candidates[:5]
        context.mentioned_skills = context.mentioned_skills[:5]
        context.mentioned_roles = context.mentioned_roles[:3]
        
        logger.info(
            f"[SUGGESTION_ENGINE] Extracted context: "
            f"last_type={context.last_query_type}, "
            f"candidates={len(context.mentioned_candidates)}, "
            f"skills={len(context.mentioned_skills)}"
        )
        
        return context
    
    def _extract_candidates(self, text: str) -> List[str]:
        """Extract candidate names from response text."""
        candidates = []
        
        # Pattern 1: **[Name](cv:cv_xxx)**
        for match in self.CV_REFERENCE_PATTERN.finditer(text):
            name = match.group(1).strip()
            if name and name not in candidates:
                candidates.append(name)
        
        # Pattern 2: [📄](cv:cv_xxx) **Name**
        for match in self.CV_ICON_PATTERN.finditer(text):
            name = match.group(1).strip()
            if name and name not in candidates:
                candidates.append(name)
        
        # Pattern 3: **Name** (bold names that look like person names)
        for match in self.BOLD_NAME_PATTERN.finditer(text):
            name = match.group(1).strip()
            # Filter out common non-name phrases
            if name and name not in candidates and len(name) < 40:
                if not any(word in name.lower() for word in ['summary', 'analysis', 'conclusion', 'candidate']):
                    candidates.append(name)
        
        return candidates
    
    def _extract_skills(self, text: str) -> List[str]:
        """Extract skill names from query text."""
        text_lower = text.lower()
        found = []
        
        for skill in self.all_skills:
            # Word boundary check
            pattern = rf'\b{re.escape(skill)}\b'
            if re.search(pattern, text_lower):
                found.append(skill)
        
        return found
    
    def _extract_roles(self, text: str) -> List[str]:
        """Extract role mentions from query text."""
        text_lower = text.lower()
        found = []
        
        # Common role patterns
        role_patterns = [
            r'\b(backend\s+developer)\b',
            r'\b(frontend\s+developer)\b',
            r'\b(fullstack\s+developer)\b',
            r'\b(full\s+stack\s+developer)\b',
            r'\b(senior\s+engineer)\b',
            r'\b(senior\s+developer)\b',
            r'\b(tech\s+lead)\b',
            r'\b(team\s+lead)\b',
            r'\b(data\s+scientist)\b',
            r'\b(data\s+engineer)\b',
            r'\b(devops\s+engineer)\b',
            r'\b(software\s+architect)\b',
            r'\b(ml\s+engineer)\b',
            r'\b(machine\s+learning\s+engineer)\b',
            r'\b(product\s+manager)\b',
            r'\b(project\s+manager)\b',
            r'\b(ui\s+designer)\b',
            r'\b(ux\s+designer)\b',
            r'\b(3d\s+artist)\b',
        ]
        
        for pattern in role_patterns:
            match = re.search(pattern, text_lower)
            if match:
                role = match.group(1).title()
                if role not in found:
                    found.append(role)
        
        return found
