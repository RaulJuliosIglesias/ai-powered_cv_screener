"""
Base classes for suggestion banks.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List


class SuggestionCategory(str, Enum):
    """Maps to query_type from Orchestrator."""
    INITIAL = "initial"           # No previous context
    SEARCH = "search"
    RANKING = "ranking"
    COMPARISON = "comparison"
    JOB_MATCH = "job_match"
    TEAM_BUILD = "team_build"
    SINGLE_CANDIDATE = "single_candidate"
    RISK_ASSESSMENT = "risk_assessment"  # red_flags
    VERIFICATION = "verification"
    SUMMARY = "summary"


@dataclass
class Suggestion:
    """
    A single suggestion template.
    
    Placeholders:
    - {candidate_name} - Will be filled with mentioned candidate
    - {skill} - Will be filled with mentioned skill
    - {role} - Will be filled with mentioned role
    - {num_cvs} - Will be filled with CV count
    """
    text: str
    category: SuggestionCategory
    
    # Placeholder requirements
    requires_candidate: bool = False   # Needs {candidate_name}
    requires_skill: bool = False       # Needs {skill}
    requires_role: bool = False        # Needs {role}
    requires_multiple_cvs: bool = False  # Needs >1 CVs
    
    # Filtering
    min_cvs: int = 1                   # Minimum CVs to show this
    priority: int = 1                  # 1=high, 2=medium, 3=low
    
    # Tracking
    id: str = ""                       # Auto-generated for dedup
    
    def __post_init__(self):
        # Auto-generate ID from text hash
        if not self.id:
            self.id = f"sug_{abs(hash(self.text)) % 100000:05d}"


@dataclass
class SuggestionBank:
    """
    A collection of suggestions for a specific category.
    """
    category: SuggestionCategory
    suggestions: List[Suggestion] = field(default_factory=list)
    
    def get_applicable(
        self,
        num_cvs: int,
        has_candidate: bool,
        has_skill: bool,
        has_role: bool
    ) -> List[Suggestion]:
        """
        Filter suggestions that can be filled with available context.
        """
        applicable = []
        for s in self.suggestions:
            # Check CV requirement
            if s.min_cvs > num_cvs:
                continue
            if s.requires_multiple_cvs and num_cvs < 2:
                continue
            
            # Check placeholder requirements
            if s.requires_candidate and not has_candidate:
                continue
            if s.requires_skill and not has_skill:
                continue
            if s.requires_role and not has_role:
                continue
            
            applicable.append(s)
        
        return applicable
