"""
Suggestions after a RANKING query.
"""
from .base import Suggestion, SuggestionCategory

RANKING_SUGGESTIONS = [
    # Explore top picks - Priority 1
    Suggestion(
        text="¿Por qué {candidate_name} está en el top del ranking?",
        category=SuggestionCategory.RANKING,
        requires_candidate=True,
        priority=1
    ),
    Suggestion(
        text="Dame el perfil completo del candidato #1",
        category=SuggestionCategory.RANKING,
        priority=1
    ),
    Suggestion(
        text="Compara el #1 vs #2 del ranking",
        category=SuggestionCategory.RANKING,
        min_cvs=2,
        priority=1
    ),
    
    # Refine ranking - Priority 1
    Suggestion(
        text="¿Cómo cambia el ranking si priorizamos {skill}?",
        category=SuggestionCategory.RANKING,
        requires_skill=True,
        min_cvs=2,
        priority=1
    ),
    Suggestion(
        text="Ranking excluyendo candidatos sin experiencia senior",
        category=SuggestionCategory.RANKING,
        min_cvs=3,
        priority=2
    ),
    
    # Risk assessment - Priority 1
    Suggestion(
        text="¿Hay red flags en el top 3?",
        category=SuggestionCategory.RANKING,
        min_cvs=3,
        priority=1
    ),
    Suggestion(
        text="Análisis de riesgos del candidato #1",
        category=SuggestionCategory.RANKING,
        priority=1
    ),
    Suggestion(
        text="¿Qué gaps tienen los candidatos top?",
        category=SuggestionCategory.RANKING,
        min_cvs=2,
        priority=2
    ),
    
    # Team building - Priority 2
    Suggestion(
        text="¿Puedo armar un equipo con el top 3?",
        category=SuggestionCategory.RANKING,
        min_cvs=3,
        priority=2
    ),
    Suggestion(
        text="¿Son complementarios los top candidatos?",
        category=SuggestionCategory.RANKING,
        min_cvs=2,
        priority=2
    ),
    
    # Job match - Priority 2
    Suggestion(
        text="Match del #1 con rol de {role}",
        category=SuggestionCategory.RANKING,
        requires_role=True,
        priority=2
    ),
    Suggestion(
        text="¿Quién del top 3 encaja mejor para {role}?",
        category=SuggestionCategory.RANKING,
        requires_role=True,
        min_cvs=3,
        priority=2
    ),
    
    # Deep dive - Priority 2
    Suggestion(
        text="¿Cuál es la trayectoria de carrera de {candidate_name}?",
        category=SuggestionCategory.RANKING,
        requires_candidate=True,
        priority=2
    ),
    Suggestion(
        text="¿Qué certificaciones tiene el top pick?",
        category=SuggestionCategory.RANKING,
        priority=3
    ),
]
