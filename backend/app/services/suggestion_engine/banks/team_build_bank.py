"""
Suggestions after a TEAM_BUILD query.
"""
from .base import Suggestion, SuggestionCategory

TEAM_BUILD_SUGGESTIONS = [
    # Team analysis - Priority 1
    Suggestion(
        text="What skills is the proposed team missing?",
        category=SuggestionCategory.TEAM_BUILD,
        priority=1
    ),
    Suggestion(
        text="Is there a risk of single point of failure?",
        category=SuggestionCategory.TEAM_BUILD,
        priority=1
    ),
    Suggestion(
        text="Is the team balanced in seniority?",
        category=SuggestionCategory.TEAM_BUILD,
        priority=1
    ),
    
    # Alternatives - Priority 1
    Suggestion(
        text="Propose an alternative team",
        category=SuggestionCategory.TEAM_BUILD,
        min_cvs=4,
        priority=1
    ),
    Suggestion(
        text="Who could replace {candidate_name}?",
        category=SuggestionCategory.TEAM_BUILD,
        requires_candidate=True,
        priority=1
    ),
    Suggestion(
        text="Add one more member to the team",
        category=SuggestionCategory.TEAM_BUILD,
        priority=2
    ),
    
    # Deep dive - Priority 2
    Suggestion(
        text="How would they work together on a real project?",
        category=SuggestionCategory.TEAM_BUILD,
        priority=2
    ),
    Suggestion(
        text="Culture/soft skills analysis for team fit",
        category=SuggestionCategory.TEAM_BUILD,
        priority=2
    ),
    Suggestion(
        text="Are there potential skills overlap conflicts?",
        category=SuggestionCategory.TEAM_BUILD,
        priority=2
    ),
    
    # Individual profiles - Priority 2
    Suggestion(
        text="Detailed profile of the proposed leader",
        category=SuggestionCategory.TEAM_BUILD,
        priority=2
    ),
    Suggestion(
        text="Red flags for team members",
        category=SuggestionCategory.TEAM_BUILD,
        priority=2
    ),
    
    # Coverage - Priority 3
    Suggestion(
        text="Do they cover all the required technologies?",
        category=SuggestionCategory.TEAM_BUILD,
        priority=3
    ),
]
