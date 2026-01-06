"""
Suggestions after a RANKING query.
"""
from .base import Suggestion, SuggestionCategory

RANKING_SUGGESTIONS = [
    # Explore top picks - Priority 1
    Suggestion(
        text="Why is {candidate_name} at the top of the ranking?",
        category=SuggestionCategory.RANKING,
        requires_candidate=True,
        priority=1
    ),
    Suggestion(
        text="Give me the full profile of the #1 candidate",
        category=SuggestionCategory.RANKING,
        priority=1
    ),
    Suggestion(
        text="Compare #1 vs #2 in the ranking",
        category=SuggestionCategory.RANKING,
        min_cvs=2,
        priority=1
    ),
    
    # Refine ranking - Priority 1
    Suggestion(
        text="How does the ranking change if we prioritize {skill}?",
        category=SuggestionCategory.RANKING,
        requires_skill=True,
        min_cvs=2,
        priority=1
    ),
    Suggestion(
        text="Ranking excluding candidates without senior experience",
        category=SuggestionCategory.RANKING,
        min_cvs=3,
        priority=2
    ),
    
    # Risk assessment - Priority 1
    Suggestion(
        text="Are there red flags in the top 3?",
        category=SuggestionCategory.RANKING,
        min_cvs=3,
        priority=1
    ),
    Suggestion(
        text="Risk analysis for the #1 candidate",
        category=SuggestionCategory.RANKING,
        priority=1
    ),
    Suggestion(
        text="What gaps do the top candidates have?",
        category=SuggestionCategory.RANKING,
        min_cvs=2,
        priority=2
    ),
    
    # Team building - Priority 2
    Suggestion(
        text="Can I build a team with the top 3?",
        category=SuggestionCategory.RANKING,
        min_cvs=3,
        priority=2
    ),
    Suggestion(
        text="Are the top candidates complementary?",
        category=SuggestionCategory.RANKING,
        min_cvs=2,
        priority=2
    ),
    
    # Job match - Priority 2
    Suggestion(
        text="Match #1 against the {role} role",
        category=SuggestionCategory.RANKING,
        requires_role=True,
        priority=2
    ),
    Suggestion(
        text="Who in the top 3 fits best for {role}?",
        category=SuggestionCategory.RANKING,
        requires_role=True,
        min_cvs=3,
        priority=2
    ),
    
    # Deep dive - Priority 2
    Suggestion(
        text="What is {candidate_name}'s career trajectory?",
        category=SuggestionCategory.RANKING,
        requires_candidate=True,
        priority=2
    ),
    Suggestion(
        text="What certifications does the top pick have?",
        category=SuggestionCategory.RANKING,
        priority=3
    ),
]
