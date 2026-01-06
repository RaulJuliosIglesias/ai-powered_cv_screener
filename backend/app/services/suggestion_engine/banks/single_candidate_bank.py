"""
Suggestions after viewing a SINGLE CANDIDATE profile.
"""
from .base import Suggestion, SuggestionCategory

SINGLE_CANDIDATE_SUGGESTIONS = [
    # Risk assessment - Priority 1
    Suggestion(
        text="¿Hay red flags para {candidate_name}?",
        category=SuggestionCategory.SINGLE_CANDIDATE,
        requires_candidate=True,
        priority=1
    ),
    Suggestion(
        text="Análisis de estabilidad laboral de {candidate_name}",
        category=SuggestionCategory.SINGLE_CANDIDATE,
        requires_candidate=True,
        priority=1
    ),
    Suggestion(
        text="¿Tiene gaps de empleo significativos?",
        category=SuggestionCategory.SINGLE_CANDIDATE,
        priority=1
    ),
    
    # Verification - Priority 2
    Suggestion(
        text="Verificar certificaciones de {candidate_name}",
        category=SuggestionCategory.SINGLE_CANDIDATE,
        requires_candidate=True,
        priority=2
    ),
    Suggestion(
        text="¿La experiencia declarada es coherente?",
        category=SuggestionCategory.SINGLE_CANDIDATE,
        priority=2
    ),
    
    # Comparison - Priority 1
    Suggestion(
        text="Comparar {candidate_name} con otro candidato similar",
        category=SuggestionCategory.SINGLE_CANDIDATE,
        requires_candidate=True,
        min_cvs=2,
        priority=1
    ),
    Suggestion(
        text="¿Quién más tiene un perfil similar?",
        category=SuggestionCategory.SINGLE_CANDIDATE,
        min_cvs=2,
        priority=1
    ),
    
    # Job matching - Priority 1
    Suggestion(
        text="¿Para qué roles sería ideal {candidate_name}?",
        category=SuggestionCategory.SINGLE_CANDIDATE,
        requires_candidate=True,
        priority=1
    ),
    Suggestion(
        text="Match de {candidate_name} para rol de {role}",
        category=SuggestionCategory.SINGLE_CANDIDATE,
        requires_candidate=True,
        requires_role=True,
        priority=2
    ),
    
    # Explore further - Priority 2
    Suggestion(
        text="¿Qué skills únicos tiene {candidate_name}?",
        category=SuggestionCategory.SINGLE_CANDIDATE,
        requires_candidate=True,
        priority=2
    ),
    Suggestion(
        text="Trayectoria de carrera de {candidate_name}",
        category=SuggestionCategory.SINGLE_CANDIDATE,
        requires_candidate=True,
        priority=2
    ),
    Suggestion(
        text="¿{candidate_name} podría crecer en la empresa?",
        category=SuggestionCategory.SINGLE_CANDIDATE,
        requires_candidate=True,
        priority=2
    ),
    
    # Ranking context - Priority 2
    Suggestion(
        text="¿Dónde rankea {candidate_name} vs los demás?",
        category=SuggestionCategory.SINGLE_CANDIDATE,
        requires_candidate=True,
        min_cvs=2,
        priority=2
    ),
    
    # Technical - Priority 3
    Suggestion(
        text="¿Qué proyectos destacados tiene en su experiencia?",
        category=SuggestionCategory.SINGLE_CANDIDATE,
        priority=3
    ),
]
