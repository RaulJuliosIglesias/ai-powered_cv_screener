"""
Suggestions after a RISK ASSESSMENT / RED FLAGS query.
"""
from .base import Suggestion, SuggestionCategory

RISK_ASSESSMENT_SUGGESTIONS = [
    # Mitigation - Priority 1
    Suggestion(
        text="¿Cómo mitigar los riesgos identificados?",
        category=SuggestionCategory.RISK_ASSESSMENT,
        priority=1
    ),
    Suggestion(
        text="¿Son críticos estos red flags para el rol?",
        category=SuggestionCategory.RISK_ASSESSMENT,
        priority=1
    ),
    
    # Comparison - Priority 1
    Suggestion(
        text="Comparar riesgos de {candidate_name} vs otros candidatos",
        category=SuggestionCategory.RISK_ASSESSMENT,
        requires_candidate=True,
        min_cvs=2,
        priority=1
    ),
    Suggestion(
        text="¿Quién tiene menos red flags?",
        category=SuggestionCategory.RISK_ASSESSMENT,
        min_cvs=2,
        priority=1
    ),
    
    # Deep dive - Priority 2
    Suggestion(
        text="Investigar el gap de empleo en detalle",
        category=SuggestionCategory.RISK_ASSESSMENT,
        priority=2
    ),
    Suggestion(
        text="¿El job hopping tiene explicación en el CV?",
        category=SuggestionCategory.RISK_ASSESSMENT,
        priority=2
    ),
    Suggestion(
        text="Verificar las credenciales declaradas",
        category=SuggestionCategory.RISK_ASSESSMENT,
        priority=2
    ),
    
    # Alternatives - Priority 1
    Suggestion(
        text="Buscar candidatos sin estos red flags",
        category=SuggestionCategory.RISK_ASSESSMENT,
        min_cvs=2,
        priority=1
    ),
    Suggestion(
        text="¿Otros candidatos con perfil similar pero más estable?",
        category=SuggestionCategory.RISK_ASSESSMENT,
        min_cvs=2,
        priority=1
    ),
    
    # Positive aspects - Priority 2
    Suggestion(
        text="¿Qué aspectos positivos tiene {candidate_name}?",
        category=SuggestionCategory.RISK_ASSESSMENT,
        requires_candidate=True,
        priority=2
    ),
    Suggestion(
        text="Ver perfil completo de {candidate_name}",
        category=SuggestionCategory.RISK_ASSESSMENT,
        requires_candidate=True,
        priority=2
    ),
    
    # Context - Priority 3
    Suggestion(
        text="¿Qué tan común es este patrón en la industria?",
        category=SuggestionCategory.RISK_ASSESSMENT,
        priority=3
    ),
]
