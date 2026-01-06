"""
Suggestions after a JOB_MATCH query.
"""
from .base import Suggestion, SuggestionCategory

JOB_MATCH_SUGGESTIONS = [
    # Explore matches - Priority 1
    Suggestion(
        text="¿Por qué {candidate_name} tiene el mejor match?",
        category=SuggestionCategory.JOB_MATCH,
        requires_candidate=True,
        priority=1
    ),
    Suggestion(
        text="¿Qué le falta al candidato con mejor match?",
        category=SuggestionCategory.JOB_MATCH,
        priority=1
    ),
    Suggestion(
        text="Detalle del gap analysis para {candidate_name}",
        category=SuggestionCategory.JOB_MATCH,
        requires_candidate=True,
        priority=1
    ),
    
    # Modify requirements - Priority 1
    Suggestion(
        text="¿Cómo cambia el match si quitamos el requisito de {skill}?",
        category=SuggestionCategory.JOB_MATCH,
        requires_skill=True,
        priority=1
    ),
    Suggestion(
        text="Match considerando skills nice-to-have",
        category=SuggestionCategory.JOB_MATCH,
        priority=2
    ),
    Suggestion(
        text="Buscar candidatos que puedan crecer hacia el rol",
        category=SuggestionCategory.JOB_MATCH,
        priority=2
    ),
    
    # Risk assessment - Priority 2
    Suggestion(
        text="Red flags de los candidatos con mejor match",
        category=SuggestionCategory.JOB_MATCH,
        priority=2
    ),
    Suggestion(
        text="¿Algún candidato tiene experiencia muy corta?",
        category=SuggestionCategory.JOB_MATCH,
        priority=2
    ),
    
    # Shortlist - Priority 1
    Suggestion(
        text="Crear shortlist de 3 candidatos",
        category=SuggestionCategory.JOB_MATCH,
        min_cvs=3,
        priority=1
    ),
    Suggestion(
        text="Comparar los top 2 matches",
        category=SuggestionCategory.JOB_MATCH,
        min_cvs=2,
        priority=1
    ),
    Suggestion(
        text="¿Quién puede empezar más rápido?",
        category=SuggestionCategory.JOB_MATCH,
        priority=3
    ),
    
    # Deep dive - Priority 2
    Suggestion(
        text="Perfil completo del mejor match",
        category=SuggestionCategory.JOB_MATCH,
        priority=2
    ),
]
