"""
Suggestions for first query (no previous context).
"""
from .base import Suggestion, SuggestionCategory

INITIAL_SUGGESTIONS = [
    # Overview - Priority 1
    Suggestion(
        text="Give me an overview of the talent pool",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        priority=1
    ),
    Suggestion(
        text="What technologies do the candidates have?",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        priority=1
    ),
    Suggestion(
        text="How many candidates have senior experience?",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        priority=1
    ),
    
    # Single candidate - Priority 1
    Suggestion(
        text="Give me the full profile of {candidate_name}",
        category=SuggestionCategory.INITIAL,
        requires_candidate=True,
        priority=1
    ),
    
    # Ranking - Priority 1
    Suggestion(
        text="Rank candidates by experience",
        category=SuggestionCategory.INITIAL,
        min_cvs=3,
        requires_multiple_cvs=True,
        priority=1
    ),
    Suggestion(
        text="Who has the most total experience?",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        priority=1
    ),
    
    # Search - Priority 2
    Suggestion(
        text="Who has experience with Python?",
        category=SuggestionCategory.INITIAL,
        min_cvs=1,
        priority=2
    ),
    Suggestion(
        text="Are there candidates with startup experience?",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        priority=2
    ),
    Suggestion(
        text="Find candidates with leadership experience",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        priority=2
    ),
    Suggestion(
        text="Who has experience with React or frontend?",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        priority=2
    ),
    
    # Comparison - Priority 2
    Suggestion(
        text="Compare the two most experienced candidates",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        requires_multiple_cvs=True,
        priority=2
    ),
    
    # Risk - Priority 3
    Suggestion(
        text="Are there candidates with stability red flags?",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        priority=3
    ),
    
    # Skills - Priority 2
    Suggestion(
        text="What are the most common skills?",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        priority=2
    ),
    Suggestion(
        text="Who has the most diverse profile?",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        priority=3
    ),
    
    # Education - Priority 3
    Suggestion(
        text="What education level do the candidates have?",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        priority=3
    ),
]
