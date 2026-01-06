"""
Suggestions after viewing a SINGLE CANDIDATE profile.
"""
from .base import Suggestion, SuggestionCategory

SINGLE_CANDIDATE_SUGGESTIONS = [
    # Risk assessment - Priority 1
    Suggestion(
        text="Are there red flags for {candidate_name}?",
        category=SuggestionCategory.SINGLE_CANDIDATE,
        requires_candidate=True,
        priority=1
    ),
    Suggestion(
        text="Job stability analysis for {candidate_name}",
        category=SuggestionCategory.SINGLE_CANDIDATE,
        requires_candidate=True,
        priority=1
    ),
    Suggestion(
        text="Does this candidate have significant employment gaps?",
        category=SuggestionCategory.SINGLE_CANDIDATE,
        priority=1
    ),
    
    # Verification - Priority 2
    Suggestion(
        text="Verify {candidate_name}'s certifications",
        category=SuggestionCategory.SINGLE_CANDIDATE,
        requires_candidate=True,
        priority=2
    ),
    Suggestion(
        text="Is the declared experience consistent?",
        category=SuggestionCategory.SINGLE_CANDIDATE,
        priority=2
    ),
    
    # Comparison - Priority 1
    Suggestion(
        text="Compare {candidate_name} with a similar candidate",
        category=SuggestionCategory.SINGLE_CANDIDATE,
        requires_candidate=True,
        min_cvs=2,
        priority=1
    ),
    Suggestion(
        text="Who else has a similar profile?",
        category=SuggestionCategory.SINGLE_CANDIDATE,
        min_cvs=2,
        priority=1
    ),
    
    # Job matching - Priority 1
    Suggestion(
        text="What roles would be ideal for {candidate_name}?",
        category=SuggestionCategory.SINGLE_CANDIDATE,
        requires_candidate=True,
        priority=1
    ),
    Suggestion(
        text="Match {candidate_name} for {role} role",
        category=SuggestionCategory.SINGLE_CANDIDATE,
        requires_candidate=True,
        requires_role=True,
        priority=2
    ),
    
    # Explore further - Priority 2
    Suggestion(
        text="What unique skills does {candidate_name} have?",
        category=SuggestionCategory.SINGLE_CANDIDATE,
        requires_candidate=True,
        priority=2
    ),
    Suggestion(
        text="Career trajectory of {candidate_name}",
        category=SuggestionCategory.SINGLE_CANDIDATE,
        requires_candidate=True,
        priority=2
    ),
    Suggestion(
        text="Could {candidate_name} grow within the company?",
        category=SuggestionCategory.SINGLE_CANDIDATE,
        requires_candidate=True,
        priority=2
    ),
    
    # Ranking context - Priority 2
    Suggestion(
        text="Where does {candidate_name} rank vs the others?",
        category=SuggestionCategory.SINGLE_CANDIDATE,
        requires_candidate=True,
        min_cvs=2,
        priority=2
    ),
    
    # Technical - Priority 3
    Suggestion(
        text="What notable projects are in their experience?",
        category=SuggestionCategory.SINGLE_CANDIDATE,
        priority=3
    ),
]
