"""
Suggestions after a SEARCH query.
"""
from .base import Suggestion, SuggestionCategory

SEARCH_SUGGESTIONS = [
    # Refine search - Priority 1
    Suggestion(
        text="¿Cuántos años de experiencia tienen con {skill}?",
        category=SuggestionCategory.SEARCH,
        requires_skill=True,
        priority=1
    ),
    Suggestion(
        text="¿Quién tiene nivel senior en {skill}?",
        category=SuggestionCategory.SEARCH,
        requires_skill=True,
        priority=1
    ),
    Suggestion(
        text="Buscar candidatos con {skill} y experiencia en liderazgo",
        category=SuggestionCategory.SEARCH,
        requires_skill=True,
        priority=1
    ),
    
    # Pivot to ranking - Priority 1
    Suggestion(
        text="Rankear los que tienen {skill} por experiencia total",
        category=SuggestionCategory.SEARCH,
        requires_skill=True,
        min_cvs=2,
        priority=1
    ),
    
    # Pivot to comparison - Priority 1
    Suggestion(
        text="Comparar los dos mejores candidatos con {skill}",
        category=SuggestionCategory.SEARCH,
        requires_skill=True,
        min_cvs=2,
        priority=1
    ),
    
    # Deep dive - Priority 1
    Suggestion(
        text="Dame el perfil completo de {candidate_name}",
        category=SuggestionCategory.SEARCH,
        requires_candidate=True,
        priority=1
    ),
    Suggestion(
        text="¿Qué otras tecnologías domina {candidate_name}?",
        category=SuggestionCategory.SEARCH,
        requires_candidate=True,
        priority=2
    ),
    
    # Certifications - Priority 2
    Suggestion(
        text="¿Alguno tiene certificaciones en {skill}?",
        category=SuggestionCategory.SEARCH,
        requires_skill=True,
        priority=2
    ),
    
    # Expand - Priority 2
    Suggestion(
        text="¿Qué otras tecnologías conocen estos candidatos?",
        category=SuggestionCategory.SEARCH,
        priority=2
    ),
    Suggestion(
        text="¿Quién tiene experiencia similar pero en otro stack?",
        category=SuggestionCategory.SEARCH,
        min_cvs=2,
        priority=2
    ),
    Suggestion(
        text="Buscar candidatos con skills complementarios a {skill}",
        category=SuggestionCategory.SEARCH,
        requires_skill=True,
        min_cvs=2,
        priority=2
    ),
    
    # Risk analysis - Priority 2
    Suggestion(
        text="¿Hay red flags en los candidatos con {skill}?",
        category=SuggestionCategory.SEARCH,
        requires_skill=True,
        min_cvs=2,
        priority=2
    ),
    
    # Alternatives - Priority 3
    Suggestion(
        text="¿Hay candidatos que podrían aprender {skill} rápido?",
        category=SuggestionCategory.SEARCH,
        requires_skill=True,
        min_cvs=2,
        priority=3
    ),
    Suggestion(
        text="Candidatos con tecnologías alternativas a {skill}",
        category=SuggestionCategory.SEARCH,
        requires_skill=True,
        priority=3
    ),
]
