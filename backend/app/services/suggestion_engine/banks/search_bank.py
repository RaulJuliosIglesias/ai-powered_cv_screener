"""
Suggestions after a SEARCH query.
"""
from .base import Suggestion, SuggestionCategory

SEARCH_SUGGESTIONS = [
    # Refine search - Priority 1
    Suggestion(
        text="How many years of experience do they have with {skill}?",
        category=SuggestionCategory.SEARCH,
        requires_skill=True,
        priority=1
    ),
    Suggestion(
        text="Who has senior-level {skill} experience?",
        category=SuggestionCategory.SEARCH,
        requires_skill=True,
        priority=1
    ),
    Suggestion(
        text="Find candidates with {skill} and leadership experience",
        category=SuggestionCategory.SEARCH,
        requires_skill=True,
        priority=1
    ),
    
    # Pivot to ranking - Priority 1
    Suggestion(
        text="Rank candidates with {skill} by total experience",
        category=SuggestionCategory.SEARCH,
        requires_skill=True,
        min_cvs=2,
        priority=1
    ),
    
    # Pivot to comparison - Priority 1
    Suggestion(
        text="Compare the top two candidates with {skill}",
        category=SuggestionCategory.SEARCH,
        requires_skill=True,
        min_cvs=2,
        priority=1
    ),
    
    # Deep dive - Priority 1
    Suggestion(
        text="Give me the full profile of {candidate_name}",
        category=SuggestionCategory.SEARCH,
        requires_candidate=True,
        priority=1
    ),
    Suggestion(
        text="What other technologies does {candidate_name} know?",
        category=SuggestionCategory.SEARCH,
        requires_candidate=True,
        priority=2
    ),
    
    # Certifications - Priority 2
    Suggestion(
        text="Does anyone have certifications in {skill}?",
        category=SuggestionCategory.SEARCH,
        requires_skill=True,
        priority=2
    ),
    
    # Expand - Priority 2
    Suggestion(
        text="What other technologies do these candidates know?",
        category=SuggestionCategory.SEARCH,
        priority=2
    ),
    Suggestion(
        text="Who has similar experience but in a different stack?",
        category=SuggestionCategory.SEARCH,
        min_cvs=2,
        priority=2
    ),
    Suggestion(
        text="Find candidates with skills complementary to {skill}",
        category=SuggestionCategory.SEARCH,
        requires_skill=True,
        min_cvs=2,
        priority=2
    ),
    
    # Risk analysis - Priority 2
    Suggestion(
        text="Are there red flags for candidates with {skill}?",
        category=SuggestionCategory.SEARCH,
        requires_skill=True,
        min_cvs=2,
        priority=2
    ),
    
    # Alternatives - Priority 3
    Suggestion(
        text="Are there candidates who could learn {skill} quickly?",
        category=SuggestionCategory.SEARCH,
        requires_skill=True,
        min_cvs=2,
        priority=3
    ),
    Suggestion(
        text="Candidates with alternative technologies to {skill}",
        category=SuggestionCategory.SEARCH,
        requires_skill=True,
        priority=3
    ),
]
