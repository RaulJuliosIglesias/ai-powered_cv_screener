"""
Suggestions for first query (no previous context).
"""
from .base import Suggestion, SuggestionCategory

INITIAL_SUGGESTIONS = [
    # Overview - Priority 1
    Suggestion(
        text="Resumen general del talent pool",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        priority=1
    ),
    Suggestion(
        text="¿Qué tecnologías dominan los candidatos?",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        priority=1
    ),
    Suggestion(
        text="¿Cuántos candidatos tienen experiencia senior?",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        priority=1
    ),
    
    # Single candidate - Priority 1
    Suggestion(
        text="Dame el perfil completo de {candidate_name}",
        category=SuggestionCategory.INITIAL,
        requires_candidate=True,
        priority=1
    ),
    
    # Ranking - Priority 1
    Suggestion(
        text="Ranking de candidatos por experiencia",
        category=SuggestionCategory.INITIAL,
        min_cvs=3,
        requires_multiple_cvs=True,
        priority=1
    ),
    Suggestion(
        text="¿Quién tiene más experiencia total?",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        priority=1
    ),
    
    # Search - Priority 2
    Suggestion(
        text="¿Quién tiene experiencia con Python?",
        category=SuggestionCategory.INITIAL,
        min_cvs=1,
        priority=2
    ),
    Suggestion(
        text="¿Hay candidatos con experiencia en startups?",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        priority=2
    ),
    Suggestion(
        text="Buscar candidatos con experiencia en liderazgo",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        priority=2
    ),
    Suggestion(
        text="¿Quién tiene experiencia con React o frontend?",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        priority=2
    ),
    
    # Comparison - Priority 2
    Suggestion(
        text="Comparar los dos candidatos más experimentados",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        requires_multiple_cvs=True,
        priority=2
    ),
    
    # Risk - Priority 3
    Suggestion(
        text="¿Hay candidatos con red flags de estabilidad?",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        priority=3
    ),
    
    # Skills - Priority 2
    Suggestion(
        text="¿Cuáles son los skills más comunes?",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        priority=2
    ),
    Suggestion(
        text="¿Quién tiene el perfil más diverso?",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        priority=3
    ),
    
    # Education - Priority 3
    Suggestion(
        text="¿Qué nivel educativo tienen los candidatos?",
        category=SuggestionCategory.INITIAL,
        min_cvs=2,
        priority=3
    ),
]
