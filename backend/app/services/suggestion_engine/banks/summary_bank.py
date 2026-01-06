"""
Suggestions after a SUMMARY query.
"""
from .base import Suggestion, SuggestionCategory

SUMMARY_SUGGESTIONS = [
    # Drill down - Priority 1
    Suggestion(
        text="Show candidates with {skill}",
        category=SuggestionCategory.SUMMARY,
        requires_skill=True,
        priority=1
    ),
    Suggestion(
        text="List only senior candidates",
        category=SuggestionCategory.SUMMARY,
        priority=1
    ),
    Suggestion(
        text="Who has more than 5 years of experience?",
        category=SuggestionCategory.SUMMARY,
        priority=1
    ),
    
    # Ranking - Priority 1
    Suggestion(
        text="Rank the best candidates",
        category=SuggestionCategory.SUMMARY,
        min_cvs=2,
        priority=1
    ),
    Suggestion(
        text="Top 3 for {role} role",
        category=SuggestionCategory.SUMMARY,
        requires_role=True,
        min_cvs=3,
        priority=1
    ),
    
    # Team - Priority 2
    Suggestion(
        text="Can I build a complete team?",
        category=SuggestionCategory.SUMMARY,
        min_cvs=3,
        priority=2
    ),
    
    # Individual - Priority 2
    Suggestion(
        text="Profile of the most experienced candidate",
        category=SuggestionCategory.SUMMARY,
        priority=2
    ),
    Suggestion(
        text="Who has the most unique profile?",
        category=SuggestionCategory.SUMMARY,
        priority=2
    ),
    
    # Skills analysis - Priority 2
    Suggestion(
        text="What skills are most represented?",
        category=SuggestionCategory.SUMMARY,
        priority=2
    ),
    Suggestion(
        text="Are there skill gaps in the pool?",
        category=SuggestionCategory.SUMMARY,
        priority=2
    ),
    
    # Comparison - Priority 3
    Suggestion(
        text="Compare the two best profiles",
        category=SuggestionCategory.SUMMARY,
        min_cvs=2,
        priority=3
    ),
]
