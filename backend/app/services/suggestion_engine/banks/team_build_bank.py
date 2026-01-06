"""
Suggestions after a TEAM_BUILD query.
"""
from .base import Suggestion, SuggestionCategory

TEAM_BUILD_SUGGESTIONS = [
    # Team analysis - Priority 1
    Suggestion(
        text="¿Qué skills le faltan al equipo propuesto?",
        category=SuggestionCategory.TEAM_BUILD,
        priority=1
    ),
    Suggestion(
        text="¿Hay riesgo de single point of failure?",
        category=SuggestionCategory.TEAM_BUILD,
        priority=1
    ),
    Suggestion(
        text="¿El equipo está balanceado en seniority?",
        category=SuggestionCategory.TEAM_BUILD,
        priority=1
    ),
    
    # Alternatives - Priority 1
    Suggestion(
        text="Proponer un equipo alternativo",
        category=SuggestionCategory.TEAM_BUILD,
        min_cvs=4,
        priority=1
    ),
    Suggestion(
        text="¿Quién podría reemplazar a {candidate_name}?",
        category=SuggestionCategory.TEAM_BUILD,
        requires_candidate=True,
        priority=1
    ),
    Suggestion(
        text="Agregar un miembro más al equipo",
        category=SuggestionCategory.TEAM_BUILD,
        priority=2
    ),
    
    # Deep dive - Priority 2
    Suggestion(
        text="¿Cómo trabajarían juntos en un proyecto real?",
        category=SuggestionCategory.TEAM_BUILD,
        priority=2
    ),
    Suggestion(
        text="Análisis de cultura/soft skills para team fit",
        category=SuggestionCategory.TEAM_BUILD,
        priority=2
    ),
    Suggestion(
        text="¿Hay conflictos potenciales de skills overlap?",
        category=SuggestionCategory.TEAM_BUILD,
        priority=2
    ),
    
    # Individual profiles - Priority 2
    Suggestion(
        text="Perfil detallado del líder propuesto",
        category=SuggestionCategory.TEAM_BUILD,
        priority=2
    ),
    Suggestion(
        text="Red flags de los miembros del equipo",
        category=SuggestionCategory.TEAM_BUILD,
        priority=2
    ),
    
    # Coverage - Priority 3
    Suggestion(
        text="¿Cubren todas las tecnologías necesarias?",
        category=SuggestionCategory.TEAM_BUILD,
        priority=3
    ),
]
