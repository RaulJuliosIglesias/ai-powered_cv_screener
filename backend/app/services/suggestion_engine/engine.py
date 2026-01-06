"""
Main SuggestionEngine - Entry point for suggestion generation.
"""
import logging
from typing import List, Dict, Optional

from .context_extractor import ContextExtractor, ExtractedContext
from .suggestion_selector import SuggestionSelector
from .template_filler import TemplateFiller
from .banks import ALL_BANKS, SuggestionCategory

logger = logging.getLogger(__name__)


class SuggestionEngine:
    """
    Main engine for generating contextual suggestions.
    
    REUTILIZA:
    - get_conversation_history() from SessionManager
    - structure_type from StructuredOutput
    
    Usage:
        engine = SuggestionEngine()
        suggestions = engine.get_suggestions(
            messages=mgr.get_conversation_history(session_id),
            cv_names=["Juan", "María"],
            num_cvs=2
        )
    """
    
    def __init__(self):
        self.extractor = ContextExtractor()
        self.filler = TemplateFiller()
        self.selector = SuggestionSelector(ALL_BANKS)
        
        # Count total suggestions
        total = sum(len(b) for b in ALL_BANKS.values())
        logger.info(f"[SUGGESTION_ENGINE] Initialized with {total} total suggestions across {len(ALL_BANKS)} banks")
    
    def get_suggestions(
        self,
        messages: List[Dict],
        cv_names: List[str],
        num_cvs: int,
        count: int = 4
    ) -> List[str]:
        """
        Generate contextual suggestions.
        
        Args:
            messages: From get_conversation_history()
            cv_names: Names of CVs in session
            num_cvs: Number of CVs
            count: Number of suggestions to return
            
        Returns:
            List of suggestion strings ready to display
        """
        # Extract context
        context = self.extractor.extract(
            messages=messages,
            cv_names=cv_names,
            num_cvs=num_cvs
        )
        
        # Select suggestions (get extra in case some can't be filled)
        suggestions = self.selector.select(context, count=count + 2)
        
        # Fill templates
        filled = self.filler.fill(suggestions, context)
        
        # Ensure we return exactly 'count' suggestions
        filled = filled[:count]
        
        logger.info(
            f"[SUGGESTION_ENGINE] Generated {len(filled)} suggestions "
            f"for query_type={context.last_query_type}, "
            f"candidates={len(context.mentioned_candidates)}, "
            f"skills={len(context.mentioned_skills)}"
        )
        
        return filled
    
    def reset(self):
        """Reset state for new session."""
        self.selector.reset()
        logger.info("[SUGGESTION_ENGINE] Reset for new session")


# Singleton instance
_engine: Optional[SuggestionEngine] = None

def get_suggestion_engine() -> SuggestionEngine:
    """Get or create singleton SuggestionEngine."""
    global _engine
    if _engine is None:
        _engine = SuggestionEngine()
    return _engine
