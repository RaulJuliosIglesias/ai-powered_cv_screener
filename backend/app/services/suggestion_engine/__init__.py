"""
Suggestion Engine - Dynamic contextual suggestions.

Usage:
    from app.services.suggestion_engine import get_suggestion_engine
    
    engine = get_suggestion_engine()
    suggestions = engine.get_suggestions(messages, cv_names, num_cvs)
"""
from .engine import SuggestionEngine, get_suggestion_engine
from .context_extractor import ContextExtractor, ExtractedContext
from .suggestion_selector import SuggestionSelector
from .template_filler import TemplateFiller
from .banks.base import Suggestion, SuggestionCategory, SuggestionBank

__all__ = [
    "SuggestionEngine",
    "get_suggestion_engine",
    "ContextExtractor",
    "ExtractedContext",
    "SuggestionSelector",
    "TemplateFiller",
    "Suggestion",
    "SuggestionCategory",
    "SuggestionBank",
]
