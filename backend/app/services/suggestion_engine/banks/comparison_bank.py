"""
Suggestions after a COMPARISON query.
"""
from .base import Suggestion, SuggestionCategory

COMPARISON_SUGGESTIONS = [
    # Deep dive on winner - Priority 1
    Suggestion(
        text="Give me more details about the comparison winner",
        category=SuggestionCategory.COMPARISON,
        priority=1
    ),
    Suggestion(
        text="What red flags does {candidate_name} have?",
        category=SuggestionCategory.COMPARISON,
        requires_candidate=True,
        priority=1
    ),
    Suggestion(
        text="Full profile of {candidate_name}",
        category=SuggestionCategory.COMPARISON,
        requires_candidate=True,
        priority=1
    ),
    
    # Expand comparison - Priority 1
    Suggestion(
        text="Add a third candidate to the comparison",
        category=SuggestionCategory.COMPARISON,
        min_cvs=3,
        priority=1
    ),
    Suggestion(
        text="Compare focusing only on {skill}",
        category=SuggestionCategory.COMPARISON,
        requires_skill=True,
        priority=1
    ),
    Suggestion(
        text="Who has a better career trajectory?",
        category=SuggestionCategory.COMPARISON,
        priority=1
    ),
    
    # Verification - Priority 2
    Suggestion(
        text="Verify the certifications of both candidates",
        category=SuggestionCategory.COMPARISON,
        priority=2
    ),
    Suggestion(
        text="Does the declared experience match the dates?",
        category=SuggestionCategory.COMPARISON,
        priority=2
    ),
    
    # Decision support - Priority 1
    Suggestion(
        text="Which one would you hire for {role}?",
        category=SuggestionCategory.COMPARISON,
        requires_role=True,
        priority=1
    ),
    Suggestion(
        text="Executive summary of the comparison",
        category=SuggestionCategory.COMPARISON,
        priority=2
    ),
    Suggestion(
        text="Pros and cons of each candidate",
        category=SuggestionCategory.COMPARISON,
        priority=1
    ),
    
    # Risk analysis - Priority 2
    Suggestion(
        text="Who has fewer red flags?",
        category=SuggestionCategory.COMPARISON,
        priority=2
    ),
    Suggestion(
        text="Job stability analysis for both candidates",
        category=SuggestionCategory.COMPARISON,
        priority=2
    ),
    
    # Skills - Priority 3
    Suggestion(
        text="Who has more up-to-date skills?",
        category=SuggestionCategory.COMPARISON,
        priority=3
    ),
]
