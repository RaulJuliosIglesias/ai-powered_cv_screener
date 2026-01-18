"""
Suggestion Banks - Collections of suggestions by category.
"""
from .base import Suggestion, SuggestionBank, SuggestionCategory
from .comparison_bank import COMPARISON_SUGGESTIONS
from .initial_bank import INITIAL_SUGGESTIONS
from .job_match_bank import JOB_MATCH_SUGGESTIONS
from .ranking_bank import RANKING_SUGGESTIONS
from .risk_assessment_bank import RISK_ASSESSMENT_SUGGESTIONS
from .search_bank import SEARCH_SUGGESTIONS
from .single_candidate_bank import SINGLE_CANDIDATE_SUGGESTIONS
from .summary_bank import SUMMARY_SUGGESTIONS
from .team_build_bank import TEAM_BUILD_SUGGESTIONS
from .verification_bank import VERIFICATION_SUGGESTIONS

# All banks mapping
ALL_BANKS = {
    SuggestionCategory.INITIAL: INITIAL_SUGGESTIONS,
    SuggestionCategory.SEARCH: SEARCH_SUGGESTIONS,
    SuggestionCategory.RANKING: RANKING_SUGGESTIONS,
    SuggestionCategory.COMPARISON: COMPARISON_SUGGESTIONS,
    SuggestionCategory.JOB_MATCH: JOB_MATCH_SUGGESTIONS,
    SuggestionCategory.TEAM_BUILD: TEAM_BUILD_SUGGESTIONS,
    SuggestionCategory.SINGLE_CANDIDATE: SINGLE_CANDIDATE_SUGGESTIONS,
    SuggestionCategory.RISK_ASSESSMENT: RISK_ASSESSMENT_SUGGESTIONS,
    SuggestionCategory.VERIFICATION: VERIFICATION_SUGGESTIONS,
    SuggestionCategory.SUMMARY: SUMMARY_SUGGESTIONS,
}

__all__ = [
    "Suggestion",
    "SuggestionCategory",
    "SuggestionBank",
    "ALL_BANKS",
    "INITIAL_SUGGESTIONS",
    "SEARCH_SUGGESTIONS",
    "RANKING_SUGGESTIONS",
    "COMPARISON_SUGGESTIONS",
    "JOB_MATCH_SUGGESTIONS",
    "TEAM_BUILD_SUGGESTIONS",
    "SINGLE_CANDIDATE_SUGGESTIONS",
    "RISK_ASSESSMENT_SUGGESTIONS",
    "VERIFICATION_SUGGESTIONS",
    "SUMMARY_SUGGESTIONS",
]
