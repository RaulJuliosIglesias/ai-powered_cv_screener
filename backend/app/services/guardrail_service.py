"""
Guardrail Service for CV Screener.

This module provides pre-LLM filtering to detect and reject off-topic questions
that are not related to CV screening or candidate analysis.
"""
import re
import logging
from typing import Tuple, Optional, Set
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GuardrailResult:
    """Result of guardrail check."""
    is_allowed: bool
    rejection_message: Optional[str] = None
    confidence: float = 1.0
    reason: Optional[str] = None


class GuardrailService:
    """
    Pre-LLM filter to detect off-topic questions.
    
    Uses a combination of:
    1. Keyword matching for CV-related terms
    2. Pattern matching for known off-topic categories
    3. Semantic similarity (optional, using embeddings)
    """
    
    # Keywords that indicate CV/recruitment related questions
    CV_KEYWORDS: Set[str] = {
        # English
        "candidate", "candidates", "cv", "cvs", "resume", "resumes",
        "experience", "experienced", "skill", "skills", "education",
        "job", "jobs", "hire", "hiring", "recruit", "recruitment",
        "qualified", "qualification", "qualifications",
        "senior", "junior", "mid-level", "entry-level",
        "developer", "engineer", "manager", "analyst", "designer",
        "years", "year", "background", "profile", "profiles",
        "compare", "comparison", "rank", "ranking", "best", "top",
        "fit", "suitable", "match", "matches",
        "python", "java", "javascript", "react", "angular", "sql",
        "leadership", "team", "project", "management",
        "salary", "remote", "work", "company", "position",
        "interview", "shortlist", "recommendation", "select", "choose",
        "list", "from", "create", "make", "find", "show", "get",
        # Technical skills
        "programming", "programacion", "programación", "technical", "técnica", "técnico",
        "frontend", "front-end", "backend", "back-end", "fullstack", "full-stack",
        "stack", "framework", "library", "code", "coding", "software",
        # Conversation continuations
        "sentido", "sense", "coherente", "coherent", "porque", "why", "porque",
        "analizar", "analyze", "criterio", "criteria", "mejor", "best",
        # Spanish
        "candidato", "candidatos", "currículum", "experiencia",
        "habilidad", "habilidades", "educación", "trabajo",
        "contratar", "reclutamiento", "calificado", "perfil",
        "comparar", "ranking", "mejor", "adecuado",
        "entrevista", "recomendación", "seleccionar", "elegir",
        "lista", "crear", "mostrar"
    }
    
    # Patterns that indicate off-topic questions
    OFF_TOPIC_PATTERNS = [
        # Food/Cooking
        r"\b(receta|recipe|cocina|cook|ingrediente|ingredient|comida|food|plato|dish)\b",
        r"\b(tarta|cake|pastel|pizza|sopa|soup|ensalada|salad)\b",
        # Weather
        r"\b(clima|weather|temperatura|temperature|lluvia|rain|sol|sun|nieve|snow)\b",
        # Entertainment
        r"\b(película|movie|film|serie|series|actor|actress|actriz)\b",
        r"\b(música|music|canción|song|cantante|singer|banda|band|concierto|concert)\b",
        r"\b(libro|book|novela|novel|autor|author)\b",
        r"\b(juego|game|videojuego|videogame|gaming)\b",
        # Sports
        r"\b(deporte|sport|fútbol|football|soccer|baloncesto|basketball)\b",
        r"\b(tenis|tennis|golf|natación|swimming|maratón|marathon)\b",
        # Politics/Religion
        r"\b(política|politic|elección|election|voto|vote|partido|party)\b",
        r"\b(religión|religion|iglesia|church|dios|god|fe|faith)\b",
        # Travel/Geography
        r"\b(viaje|travel|vacaciones|vacation|turismo|tourism|hotel)\b",
        # Health (non-work related)
        r"\b(dieta|diet|ejercicio|exercise|gimnasio|gym|médico|doctor)\b",
        # Humor
        r"\b(chiste|joke|gracioso|funny|humor|meme)\b",
        # General knowledge
        r"\b(capital de|capital of|cuántos|how many|qué es|what is)\b",
        # Math/Science (non-CV)
        r"\b(calcular|calculate|ecuación|equation|fórmula|formula)\b",
    ]
    
    # Minimum question length to be meaningful
    MIN_QUESTION_LENGTH = 3
    
    # Compiled patterns for efficiency
    _compiled_patterns = None
    
    def __init__(self):
        """Initialize the guardrail service."""
        self._compile_patterns()
        logger.info("GuardrailService initialized")
    
    def _compile_patterns(self):
        """Compile regex patterns for efficiency."""
        if self._compiled_patterns is None:
            self._compiled_patterns = [
                re.compile(pattern, re.IGNORECASE)
                for pattern in self.OFF_TOPIC_PATTERNS
            ]
    
    def check(self, question: str) -> GuardrailResult:
        """
        Check if a question is allowed (CV-related).
        
        Args:
            question: The user's question
            
        Returns:
            GuardrailResult with is_allowed and optional rejection message
        """
        if not question or not question.strip():
            return GuardrailResult(
                is_allowed=False,
                rejection_message="Please enter a question about the CVs.",
                confidence=1.0,
                reason="empty_question"
            )
        
        question_lower = question.lower().strip()
        words = set(re.findall(r'\w+', question_lower))
        
        # Check 1: Too short
        if len(question.split()) < self.MIN_QUESTION_LENGTH:
            # Very short questions without CV keywords are suspicious
            if not (words & self.CV_KEYWORDS):
                return GuardrailResult(
                    is_allowed=False,
                    rejection_message="Please ask a more specific question about the candidates or CVs.",
                    confidence=0.8,
                    reason="too_short"
                )
        
        # Check 2: Off-topic patterns
        for pattern in self._compiled_patterns:
            if pattern.search(question_lower):
                logger.info(f"Guardrail: Rejected off-topic question (pattern match)")
                return GuardrailResult(
                    is_allowed=False,
                    rejection_message="I can only help with CV screening and candidate analysis. Please ask a question about the uploaded CVs.",
                    confidence=0.95,
                    reason="off_topic_pattern"
                )
        
        # Check 3: Contains CV keywords → definitely allowed
        if words & self.CV_KEYWORDS:
            logger.debug(f"Guardrail: Allowed (CV keywords found)")
            return GuardrailResult(
                is_allowed=True,
                confidence=0.95,
                reason="cv_keywords"
            )
        
        # Check 4: Question words that suggest analysis or conversation continuation
        analysis_patterns = [
            r"\b(who|quién|cuál|cual|which|what|qué|compare|comparar)\b",
            r"\b(best|mejor|top|rank|ranking|suitable|adecuado)\b",
            r"\b(experience|experiencia|skill|habilidad|background)\b",
            r"\b(why|porque|porqué|reason|razón|sentido|sense)\b",
            r"\b(technical|técnico|técnica|programming|programación|programacion)\b",
            r"\b(frontend|front-end|backend|fullstack|full-stack|stack)\b",
        ]
        for pattern in analysis_patterns:
            if re.search(pattern, question_lower):
                logger.debug(f"Guardrail: Allowed (analysis pattern)")
                return GuardrailResult(
                    is_allowed=True,
                    confidence=0.8,
                    reason="analysis_pattern"
                )
        
        # Default: Allow but with lower confidence
        # The LLM will handle truly off-topic questions that slip through
        logger.debug(f"Guardrail: Allowed (default, no clear off-topic signal)")
        return GuardrailResult(
            is_allowed=True,
            confidence=0.6,
            reason="default_allow"
        )
    
    async def check_async(self, question: str) -> GuardrailResult:
        """Async wrapper for check method."""
        return self.check(question)
    
    def is_cv_related(self, question: str) -> Tuple[bool, Optional[str]]:
        """
        Legacy method for backward compatibility.
        
        Returns:
            Tuple of (is_related, rejection_message or None)
        """
        result = self.check(question)
        return result.is_allowed, result.rejection_message


# Singleton instance
_guardrail_service: Optional[GuardrailService] = None


def get_guardrail_service() -> GuardrailService:
    """Get singleton instance of GuardrailService."""
    global _guardrail_service
    if _guardrail_service is None:
        _guardrail_service = GuardrailService()
    return _guardrail_service
