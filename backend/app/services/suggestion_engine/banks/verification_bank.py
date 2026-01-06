"""
Suggestions after a VERIFICATION query.
"""
from .base import Suggestion, SuggestionCategory

VERIFICATION_SUGGESTIONS = [
    # More verification - Priority 1
    Suggestion(
        text="Verify another claim from {candidate_name}",
        category=SuggestionCategory.VERIFICATION,
        requires_candidate=True,
        priority=1
    ),
    Suggestion(
        text="Are the experience dates consistent?",
        category=SuggestionCategory.VERIFICATION,
        priority=1
    ),
    Suggestion(
        text="Verify the declared education level",
        category=SuggestionCategory.VERIFICATION,
        priority=1
    ),
    
    # Risk - Priority 1
    Suggestion(
        text="Are there other inconsistencies in the CV?",
        category=SuggestionCategory.VERIFICATION,
        priority=1
    ),
    Suggestion(
        text="Full red flags analysis",
        category=SuggestionCategory.VERIFICATION,
        priority=1
    ),
    
    # Compare - Priority 2
    Suggestion(
        text="Compare credentials with other candidates",
        category=SuggestionCategory.VERIFICATION,
        min_cvs=2,
        priority=2
    ),
    
    # Profile - Priority 2
    Suggestion(
        text="See full profile of {candidate_name}",
        category=SuggestionCategory.VERIFICATION,
        requires_candidate=True,
        priority=2
    ),
    
    # Skills verification - Priority 2
    Suggestion(
        text="Is there evidence of the declared skills?",
        category=SuggestionCategory.VERIFICATION,
        priority=2
    ),
    
    # Experience verification - Priority 3
    Suggestion(
        text="Verify total years of experience",
        category=SuggestionCategory.VERIFICATION,
        priority=3
    ),
    Suggestion(
        text="Are job titles consistent with responsibilities?",
        category=SuggestionCategory.VERIFICATION,
        priority=3
    ),
]
