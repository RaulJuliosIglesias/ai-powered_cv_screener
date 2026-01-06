"""
Suggestions after a JOB_MATCH query.
"""
from .base import Suggestion, SuggestionCategory

JOB_MATCH_SUGGESTIONS = [
    # Explore matches - Priority 1
    Suggestion(
        text="Why does {candidate_name} have the best match?",
        category=SuggestionCategory.JOB_MATCH,
        requires_candidate=True,
        priority=1
    ),
    Suggestion(
        text="What is the best match candidate missing?",
        category=SuggestionCategory.JOB_MATCH,
        priority=1
    ),
    Suggestion(
        text="Gap analysis details for {candidate_name}",
        category=SuggestionCategory.JOB_MATCH,
        requires_candidate=True,
        priority=1
    ),
    
    # Modify requirements - Priority 1
    Suggestion(
        text="How does the match change if we remove the {skill} requirement?",
        category=SuggestionCategory.JOB_MATCH,
        requires_skill=True,
        priority=1
    ),
    Suggestion(
        text="Match considering nice-to-have skills",
        category=SuggestionCategory.JOB_MATCH,
        priority=2
    ),
    Suggestion(
        text="Find candidates who can grow into the role",
        category=SuggestionCategory.JOB_MATCH,
        priority=2
    ),
    
    # Risk assessment - Priority 2
    Suggestion(
        text="Red flags for candidates with best match",
        category=SuggestionCategory.JOB_MATCH,
        priority=2
    ),
    Suggestion(
        text="Does any candidate have very short experience?",
        category=SuggestionCategory.JOB_MATCH,
        priority=2
    ),
    
    # Shortlist - Priority 1
    Suggestion(
        text="Create a shortlist of 3 candidates",
        category=SuggestionCategory.JOB_MATCH,
        min_cvs=3,
        priority=1
    ),
    Suggestion(
        text="Compare the top 2 matches",
        category=SuggestionCategory.JOB_MATCH,
        min_cvs=2,
        priority=1
    ),
    Suggestion(
        text="Who can start the soonest?",
        category=SuggestionCategory.JOB_MATCH,
        priority=3
    ),
    
    # Deep dive - Priority 2
    Suggestion(
        text="Full profile of the best match",
        category=SuggestionCategory.JOB_MATCH,
        priority=2
    ),
]
