"""
Suggestions after a COMPARISON query.
"""
from .base import Suggestion, SuggestionCategory

COMPARISON_SUGGESTIONS = [
    # Deep dive on winner - Priority 1
    Suggestion(
        text="Dame más detalles del ganador de la comparación",
        category=SuggestionCategory.COMPARISON,
        priority=1
    ),
    Suggestion(
        text="¿Qué red flags tiene {candidate_name}?",
        category=SuggestionCategory.COMPARISON,
        requires_candidate=True,
        priority=1
    ),
    Suggestion(
        text="Perfil completo de {candidate_name}",
        category=SuggestionCategory.COMPARISON,
        requires_candidate=True,
        priority=1
    ),
    
    # Expand comparison - Priority 1
    Suggestion(
        text="Añadir un tercer candidato a la comparación",
        category=SuggestionCategory.COMPARISON,
        min_cvs=3,
        priority=1
    ),
    Suggestion(
        text="Comparar enfocándose solo en {skill}",
        category=SuggestionCategory.COMPARISON,
        requires_skill=True,
        priority=1
    ),
    Suggestion(
        text="¿Quién tiene mejor trayectoria profesional?",
        category=SuggestionCategory.COMPARISON,
        priority=1
    ),
    
    # Verification - Priority 2
    Suggestion(
        text="Verificar las certificaciones de ambos",
        category=SuggestionCategory.COMPARISON,
        priority=2
    ),
    Suggestion(
        text="¿Coincide la experiencia declarada con las fechas?",
        category=SuggestionCategory.COMPARISON,
        priority=2
    ),
    
    # Decision support - Priority 1
    Suggestion(
        text="¿Cuál contratarías para {role}?",
        category=SuggestionCategory.COMPARISON,
        requires_role=True,
        priority=1
    ),
    Suggestion(
        text="Resumen ejecutivo de la comparación",
        category=SuggestionCategory.COMPARISON,
        priority=2
    ),
    Suggestion(
        text="Pros y contras de cada candidato",
        category=SuggestionCategory.COMPARISON,
        priority=1
    ),
    
    # Risk analysis - Priority 2
    Suggestion(
        text="¿Quién tiene menos red flags?",
        category=SuggestionCategory.COMPARISON,
        priority=2
    ),
    Suggestion(
        text="Análisis de estabilidad laboral de ambos",
        category=SuggestionCategory.COMPARISON,
        priority=2
    ),
    
    # Skills - Priority 3
    Suggestion(
        text="¿Quién tiene skills más actualizados?",
        category=SuggestionCategory.COMPARISON,
        priority=3
    ),
]
