"""
Suggestions after a RISK ASSESSMENT / RED FLAGS query.
"""
from .base import Suggestion, SuggestionCategory

RISK_ASSESSMENT_SUGGESTIONS = [
    # Mitigation - Priority 1
    Suggestion(
        text="How can we mitigate the identified risks?",
        category=SuggestionCategory.RISK_ASSESSMENT,
        priority=1
    ),
    Suggestion(
        text="Are these red flags critical for the role?",
        category=SuggestionCategory.RISK_ASSESSMENT,
        priority=1
    ),
    
    # Comparison - Priority 1
    Suggestion(
        text="Compare {candidate_name}'s risks vs other candidates",
        category=SuggestionCategory.RISK_ASSESSMENT,
        requires_candidate=True,
        min_cvs=2,
        priority=1
    ),
    Suggestion(
        text="Who has fewer red flags?",
        category=SuggestionCategory.RISK_ASSESSMENT,
        min_cvs=2,
        priority=1
    ),
    
    # Deep dive - Priority 2
    Suggestion(
        text="Investigate the employment gap in detail",
        category=SuggestionCategory.RISK_ASSESSMENT,
        priority=2
    ),
    Suggestion(
        text="Is there an explanation for the job hopping in the CV?",
        category=SuggestionCategory.RISK_ASSESSMENT,
        priority=2
    ),
    Suggestion(
        text="Verify the declared credentials",
        category=SuggestionCategory.RISK_ASSESSMENT,
        priority=2
    ),
    
    # Alternatives - Priority 1
    Suggestion(
        text="Find candidates without these red flags",
        category=SuggestionCategory.RISK_ASSESSMENT,
        min_cvs=2,
        priority=1
    ),
    Suggestion(
        text="Other candidates with similar profile but more stable?",
        category=SuggestionCategory.RISK_ASSESSMENT,
        min_cvs=2,
        priority=1
    ),
    
    # Positive aspects - Priority 2
    Suggestion(
        text="What positive aspects does {candidate_name} have?",
        category=SuggestionCategory.RISK_ASSESSMENT,
        requires_candidate=True,
        priority=2
    ),
    Suggestion(
        text="See full profile of {candidate_name}",
        category=SuggestionCategory.RISK_ASSESSMENT,
        requires_candidate=True,
        priority=2
    ),
    
    # Context - Priority 3
    Suggestion(
        text="How common is this pattern in the industry?",
        category=SuggestionCategory.RISK_ASSESSMENT,
        priority=3
    ),
]
