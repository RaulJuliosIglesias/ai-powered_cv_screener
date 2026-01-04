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
    # IMPORTANT: These patterns should NOT match valid CV-related queries
    # like "game developer", "game designer", "game artist", etc.
    OFF_TOPIC_PATTERNS = [
        # Food/Cooking
        r"\b(receta|recipe|cocina(?! developer| engineer| artist))\b",
        r"\b(ingrediente|ingredient|comida|plato|dish)\b",
        r"\b(tarta|cake|pastel|pizza|sopa|soup|ensalada|salad)\b",
        # Weather
        r"\b(clima|weather|temperatura|temperature|lluvia|rain|nieve|snow)\b",
        # Entertainment (exclude job roles like "film director", "game developer")
        r"\b(película|movie)(?! director| producer| editor)\b",
        r"\b(música|music|canción|song|cantante|singer|banda|band|concierto|concert)\b",
        r"\b(libro|book|novela|novel)(?! editor| publisher)\b",
        # NOTE: Removed "game" pattern - "game developer", "game designer", "game artist" are valid job roles
        # Sports (as entertainment, not profession)
        r"\b(deporte|fútbol|soccer|baloncesto|basketball)\b",
        r"\b(tenis|tennis|golf|natación|swimming|maratón|marathon)\b",
        # Politics/Religion
        r"\b(política|politic|elección|election|voto|vote)\b",
        r"\b(religión|religion|iglesia|church|dios|god)\b",
        # Travel/Geography (as tourism, not business)
        r"\b(vacaciones|vacation|turismo|tourism)\b",
        # Health (non-work related)
        r"\b(dieta|diet|gimnasio|gym)\b",
        # Humor
        r"\b(chiste|joke|gracioso|funny|meme)\b",
        # General knowledge questions (not about CVs)
        r"\b(capital de|capital of|cuántos habitantes|how many people)\b",
        # Math/Science homework (not CV analysis)
        r"\b(ecuación|equation|fórmula matemática)\b",
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
    
    def check(self, question: str, has_cvs: bool = False) -> GuardrailResult:
        """
        Check if a question is allowed (CV-related).
        
        Args:
            question: The user's question
            has_cvs: Whether CVs are loaded in the session
            
        Returns:
            GuardrailResult with is_allowed and optional rejection message
            
        Note:
            When has_cvs=True, guardrail is more permissive - only rejects
            obviously off-topic patterns (weather, food, politics).
            Ambiguous queries are allowed so LLM can interpret them.
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
        
        # Check 1: Too short (but only if no CV keywords)
        if len(question.split()) < self.MIN_QUESTION_LENGTH:
            if not (words & self.CV_KEYWORDS):
                return GuardrailResult(
                    is_allowed=False,
                    rejection_message="Please ask a more specific question about the candidates or CVs.",
                    confidence=0.8,
                    reason="too_short"
                )
        
        # Check 2: If CVs are loaded, be permissive - only block obvious off-topic
        if has_cvs:
            # With CVs loaded, only check for obviously off-topic patterns
            # Let LLM handle ambiguous queries like "best artist" 
            for pattern in self._compiled_patterns:
                if pattern.search(question_lower):
                    logger.info(f"Guardrail: Rejected off-topic (CVs loaded but clear off-topic pattern)")
                    return GuardrailResult(
                        is_allowed=False,
                        rejection_message="I can only help with CV screening and candidate analysis. Please ask a question about the uploaded CVs.",
                        confidence=0.95,
                        reason="off_topic_pattern"
                    )
            
            # Allow everything else when CVs are present
            logger.debug(f"Guardrail: Allowed (CVs loaded, permissive mode)")
            return GuardrailResult(
                is_allowed=True,
                confidence=0.9,
                reason="cvs_loaded_permissive"
            )
        
        # Check 3: Contains CV keywords → ALLOW IMMEDIATELY (before off-topic check)
        # This ensures "game developer", "full stack", etc. are always allowed
        if words & self.CV_KEYWORDS:
            logger.debug(f"Guardrail: Allowed (CV keywords found: {words & self.CV_KEYWORDS})")
            return GuardrailResult(
                is_allowed=True,
                confidence=0.95,
                reason="cv_keywords"
            )
        
        # Check 4: Question words that suggest CV analysis
        analysis_patterns = [
            r"\b(who|quién|cuál|cual|which|what|qué|compare|comparar)\b",
            r"\b(best|mejor|top|rank|ranking|suitable|adecuado)\b",
            r"\b(experience|experiencia|skill|habilidad|background)\b",
            r"\b(why|porque|porqué|reason|razón|sentido|sense)\b",
            r"\b(technical|técnico|técnica|programming|programación|programacion)\b",
            r"\b(frontend|front-end|backend|fullstack|full-stack|stack|webgl)\b",
            r"\b(developer|engineer|designer|artist|manager|director)\b",
            r"\b(game|mobile|web|cloud|data|ai|ml)\b",
        ]
        for pattern in analysis_patterns:
            if re.search(pattern, question_lower):
                logger.debug(f"Guardrail: Allowed (analysis pattern: {pattern})")
                return GuardrailResult(
                    is_allowed=True,
                    confidence=0.8,
                    reason="analysis_pattern"
                )
        
        # Check 5: Off-topic patterns - ONLY if no CV-related content found
        for pattern in self._compiled_patterns:
            if pattern.search(question_lower):
                logger.info(f"Guardrail: Rejected off-topic question (pattern match)")
                return GuardrailResult(
                    is_allowed=False,
                    rejection_message="I can only help with CV screening and candidate analysis. Please ask a question about the uploaded CVs.",
                    confidence=0.95,
                    reason="off_topic_pattern"
                )
        
        # Default: Allow but with lower confidence
        # The LLM will handle truly off-topic questions that slip through
        logger.debug(f"Guardrail: Allowed (default, no clear off-topic signal)")
        return GuardrailResult(
            is_allowed=True,
            confidence=0.6,
            reason="default_allow"
        )
    
    async def check_async(self, question: str, has_cvs: bool = False) -> GuardrailResult:
        """Async wrapper for check method."""
        return self.check(question, has_cvs=has_cvs)
    
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
