"""
Suggestions after a VERIFICATION query.
"""
from .base import Suggestion, SuggestionCategory

VERIFICATION_SUGGESTIONS = [
    # More verification - Priority 1
    Suggestion(
        text="Verificar otra claim de {candidate_name}",
        category=SuggestionCategory.VERIFICATION,
        requires_candidate=True,
        priority=1
    ),
    Suggestion(
        text="¿Las fechas de experiencia son coherentes?",
        category=SuggestionCategory.VERIFICATION,
        priority=1
    ),
    Suggestion(
        text="Verificar nivel de educación declarado",
        category=SuggestionCategory.VERIFICATION,
        priority=1
    ),
    
    # Risk - Priority 1
    Suggestion(
        text="¿Hay otras inconsistencias en el CV?",
        category=SuggestionCategory.VERIFICATION,
        priority=1
    ),
    Suggestion(
        text="Análisis completo de red flags",
        category=SuggestionCategory.VERIFICATION,
        priority=1
    ),
    
    # Compare - Priority 2
    Suggestion(
        text="Comparar credenciales con otros candidatos",
        category=SuggestionCategory.VERIFICATION,
        min_cvs=2,
        priority=2
    ),
    
    # Profile - Priority 2
    Suggestion(
        text="Ver perfil completo de {candidate_name}",
        category=SuggestionCategory.VERIFICATION,
        requires_candidate=True,
        priority=2
    ),
    
    # Skills verification - Priority 2
    Suggestion(
        text="¿Tiene evidencia de los skills declarados?",
        category=SuggestionCategory.VERIFICATION,
        priority=2
    ),
    
    # Experience verification - Priority 3
    Suggestion(
        text="Verificar años de experiencia totales",
        category=SuggestionCategory.VERIFICATION,
        priority=3
    ),
    Suggestion(
        text="¿Los títulos de puesto son consistentes con las responsabilidades?",
        category=SuggestionCategory.VERIFICATION,
        priority=3
    ),
]
