"""
Selects and prioritizes suggestions based on context.
"""
import random
import logging
from typing import List, Set, Dict

from .banks.base import Suggestion, SuggestionCategory
from .context_extractor import ExtractedContext

logger = logging.getLogger(__name__)


class SuggestionSelector:
    """
    Selects appropriate suggestions based on extracted context.
    
    Implements:
    - Query type → Bank mapping
    - Deduplication (tracks used suggestions per session)
    - Priority-based selection
    - Fallback to generic suggestions
    """
    
    # Map query_type to suggestion category
    QUERY_TYPE_MAP: Dict[str, SuggestionCategory] = {
        "single_candidate": SuggestionCategory.SINGLE_CANDIDATE,
        "red_flags": SuggestionCategory.RISK_ASSESSMENT,
        "risk_assessment": SuggestionCategory.RISK_ASSESSMENT,
        "comparison": SuggestionCategory.COMPARISON,
        "search": SuggestionCategory.SEARCH,
        "ranking": SuggestionCategory.RANKING,
        "job_match": SuggestionCategory.JOB_MATCH,
        "team_build": SuggestionCategory.TEAM_BUILD,
        "verification": SuggestionCategory.VERIFICATION,
        "summary": SuggestionCategory.SUMMARY,
        "initial": SuggestionCategory.INITIAL,
    }
    
    def __init__(self, banks: Dict[SuggestionCategory, List[Suggestion]]):
        """
        Args:
            banks: Dict mapping category to list of suggestions
        """
        self.banks = banks
        self._used_ids: Set[str] = set()  # Track used suggestion IDs
    
    def select(
        self,
        context: ExtractedContext,
        count: int = 4
    ) -> List[Suggestion]:
        """
        Select suggestions based on context.
        
        Algorithm:
        1. Determine target category from last_query_type
        2. Filter applicable suggestions (placeholders can be filled)
        3. Remove already used suggestions
        4. Sort by priority
        5. Select top N
        6. Fallback to INITIAL if not enough
        
        Args:
            context: Extracted context from conversation
            count: Number of suggestions to return
            
        Returns:
            List of selected Suggestion objects
        """
        # Determine category from last query type
        category = self.QUERY_TYPE_MAP.get(
            context.last_query_type,
            SuggestionCategory.INITIAL
        )
        
        # Get bank for this category
        bank = self.banks.get(category, [])
        
        # Check what placeholders we can fill
        has_candidate = len(context.mentioned_candidates) > 0
        has_skill = len(context.mentioned_skills) > 0
        has_role = len(context.mentioned_roles) > 0 or has_skill
        
        # Filter applicable suggestions
        applicable = []
        for s in bank:
            # Check min_cvs
            if s.min_cvs > context.num_cvs:
                continue
            if s.requires_multiple_cvs and context.num_cvs < 2:
                continue
            
            # Check placeholder requirements
            if s.requires_candidate and not has_candidate:
                continue
            if s.requires_skill and not has_skill:
                continue
            if s.requires_role and not has_role:
                continue
            
            # Check not already used
            if s.id in self._used_ids:
                continue
            
            applicable.append(s)
        
        # Sort by priority (lower = higher priority)
        applicable.sort(key=lambda x: x.priority)
        
        # Select with some randomization within priority groups
        selected = []
        by_priority: Dict[int, List[Suggestion]] = {}
        
        for s in applicable:
            if s.priority not in by_priority:
                by_priority[s.priority] = []
            by_priority[s.priority].append(s)
        
        for priority in sorted(by_priority.keys()):
            group = by_priority[priority]
            random.shuffle(group)
            for s in group:
                if len(selected) >= count:
                    break
                selected.append(s)
                self._used_ids.add(s.id)
            if len(selected) >= count:
                break
        
        # Fallback to INITIAL bank if not enough
        if len(selected) < count:
            initial_bank = self.banks.get(SuggestionCategory.INITIAL, [])
            for s in initial_bank:
                if s.id in self._used_ids:
                    continue
                if s.min_cvs > context.num_cvs:
                    continue
                if s.requires_candidate and not has_candidate:
                    continue
                if s.requires_multiple_cvs and context.num_cvs < 2:
                    continue
                
                selected.append(s)
                self._used_ids.add(s.id)
                if len(selected) >= count:
                    break
        
        logger.info(
            f"[SUGGESTION_SELECTOR] Selected {len(selected)} suggestions "
            f"from category={category.value}"
        )
        
        return selected
    
    def reset(self):
        """Reset used suggestions (call on new session)."""
        self._used_ids.clear()
