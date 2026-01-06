"""
Suggestions after a SUMMARY query.
"""
from .base import Suggestion, SuggestionCategory

SUMMARY_SUGGESTIONS = [
    # Drill down - Priority 1
    Suggestion(
        text="Ver candidatos con {skill}",
        category=SuggestionCategory.SUMMARY,
        requires_skill=True,
        priority=1
    ),
    Suggestion(
        text="Listar solo candidatos senior",
        category=SuggestionCategory.SUMMARY,
        priority=1
    ),
    Suggestion(
        text="¿Quiénes tienen más de 5 años de experiencia?",
        category=SuggestionCategory.SUMMARY,
        priority=1
    ),
    
    # Ranking - Priority 1
    Suggestion(
        text="Ranking de los mejores candidatos",
        category=SuggestionCategory.SUMMARY,
        min_cvs=2,
        priority=1
    ),
    Suggestion(
        text="Top 3 para rol de {role}",
        category=SuggestionCategory.SUMMARY,
        requires_role=True,
        min_cvs=3,
        priority=1
    ),
    
    # Team - Priority 2
    Suggestion(
        text="¿Puedo armar un equipo completo?",
        category=SuggestionCategory.SUMMARY,
        min_cvs=3,
        priority=2
    ),
    
    # Individual - Priority 2
    Suggestion(
        text="Perfil del candidato más experimentado",
        category=SuggestionCategory.SUMMARY,
        priority=2
    ),
    Suggestion(
        text="¿Quién tiene el perfil más único?",
        category=SuggestionCategory.SUMMARY,
        priority=2
    ),
    
    # Skills analysis - Priority 2
    Suggestion(
        text="¿Qué skills están más representados?",
        category=SuggestionCategory.SUMMARY,
        priority=2
    ),
    Suggestion(
        text="¿Hay gaps de skills en el pool?",
        category=SuggestionCategory.SUMMARY,
        priority=2
    ),
    
    # Comparison - Priority 3
    Suggestion(
        text="Comparar los dos mejores perfiles",
        category=SuggestionCategory.SUMMARY,
        min_cvs=2,
        priority=3
    ),
]
