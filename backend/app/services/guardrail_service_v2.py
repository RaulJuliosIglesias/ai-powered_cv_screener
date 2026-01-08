"""
Zero-Shot Guardrail Service v2.

Replaces fragile regex-based guardrails with ML-based zero-shot classification.

Benefits over regex (v1):
- No hardcoded keyword lists to maintain
- Understands semantic meaning, not just keywords
- Fewer false positives (e.g., "game developer" is now correctly allowed)
- Fewer false negatives (catches creative off-topic queries)
- FREE via HuggingFace Inference API

Model: MoritzLaurer/deberta-v3-base-zeroshot-v2.0
Rate Limit: 30K requests/hour
"""
import logging
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from app.providers.huggingface_client import get_huggingface_client, HuggingFaceClient
from app.services.guardrail_service import GuardrailService, GuardrailResult

logger = logging.getLogger(__name__)


@dataclass
class ZeroShotGuardrailResult:
    """Result of zero-shot guardrail check."""
    is_allowed: bool
    rejection_message: Optional[str]
    confidence: float
    reason: str
    method: str  # "zero_shot" | "regex_fallback" | "permissive"
    classification_scores: Dict[str, float] = None
    latency_ms: float = 0.0


class GuardrailServiceV2:
    """
    Enhanced guardrails using zero-shot classification.
    
    How it works:
    1. Classify query against CV-related vs off-topic labels
    2. If CV-related score > threshold, ALLOW
    3. If off-topic score > threshold, REJECT
    4. Falls back to regex guardrails if HuggingFace unavailable
    
    Labels for classification:
    - "question about job candidates, CVs, or resumes"
    - "question about work experience or professional skills"
    - "off-topic question not related to hiring or recruitment"
    
    Usage:
        service = GuardrailServiceV2()
        result = await service.check(query="Who has Python experience?")
        if result.is_allowed:
            # Process query
    """
    
    # Classification labels
    CV_RELATED_LABELS = [
        "question about job candidates, CVs, or resumes",
        "question about work experience, skills, or qualifications",
        "question about hiring, recruitment, or job matching"
    ]
    
    OFF_TOPIC_LABELS = [
        "off-topic question not related to hiring or recruitment",
        "question about weather, food, entertainment, or general knowledge"
    ]
    
    # Thresholds
    THRESHOLD_CV_RELATED = 0.5  # Min score to be considered CV-related
    THRESHOLD_OFF_TOPIC = 0.6   # Min score to be rejected as off-topic
    
    # Standard rejection message
    REJECTION_MESSAGE = (
        "I can only help with CV screening and candidate analysis. "
        "Please ask a question about the uploaded CVs."
    )
    
    def __init__(
        self,
        hf_client: Optional[HuggingFaceClient] = None,
        legacy_guardrails: Optional[GuardrailService] = None,
        enabled: bool = True
    ):
        """
        Initialize zero-shot guardrail service.
        
        Args:
            hf_client: HuggingFace client (uses singleton if None)
            legacy_guardrails: Fallback regex guardrails (creates if None)
            enabled: Whether zero-shot is enabled (falls back to regex if False)
        """
        self.hf_client = hf_client or get_huggingface_client()
        self.legacy_guardrails = legacy_guardrails or GuardrailService()
        self.enabled = enabled
        self.model = self.hf_client.config.ZEROSHOT_MODEL
        
        # All labels for classification
        self.all_labels = self.CV_RELATED_LABELS + self.OFF_TOPIC_LABELS
        
        logger.info(
            f"GuardrailServiceV2 initialized: "
            f"model={self.model}, enabled={enabled}, "
            f"hf_available={self.hf_client.is_available}"
        )
    
    async def check(
        self,
        question: str,
        has_cvs: bool = False
    ) -> ZeroShotGuardrailResult:
        """
        Check if a question is allowed using zero-shot classification.
        
        Args:
            question: User's question
            has_cvs: Whether CVs are loaded in session
            
        Returns:
            ZeroShotGuardrailResult with classification details
        """
        start_time = time.perf_counter()
        
        # Empty question check
        if not question or not question.strip():
            return ZeroShotGuardrailResult(
                is_allowed=False,
                rejection_message="Please enter a question about the CVs.",
                confidence=1.0,
                reason="empty_question",
                method="validation",
                latency_ms=0.0
            )
        
        question = question.strip()
        
        # Very short questions - let through if CVs loaded
        if len(question.split()) < 3:
            if has_cvs:
                return ZeroShotGuardrailResult(
                    is_allowed=True,
                    rejection_message=None,
                    confidence=0.7,
                    reason="short_query_with_cvs",
                    method="permissive",
                    latency_ms=(time.perf_counter() - start_time) * 1000
                )
        
        # Try zero-shot classification
        if self.enabled and self.hf_client.is_available:
            try:
                result = await self._check_with_zero_shot(question, has_cvs, start_time)
                return result
            except Exception as e:
                logger.warning(f"Zero-shot classification failed: {e}, using regex fallback")
        
        # Fallback to regex guardrails
        return await self._check_with_regex_fallback(question, has_cvs, start_time)
    
    async def _check_with_zero_shot(
        self,
        question: str,
        has_cvs: bool,
        start_time: float
    ) -> ZeroShotGuardrailResult:
        """Perform zero-shot classification check."""
        
        # Classify question
        result = await self.hf_client.zero_shot_classification(
            text=question,
            candidate_labels=self.all_labels,
            multi_label=True  # Allow multiple labels
        )
        
        # Parse scores
        labels = result.get("labels", [])
        scores = result.get("scores", [])
        
        score_dict = dict(zip(labels, scores))
        
        # Calculate aggregate scores
        cv_related_score = max(
            score_dict.get(label, 0.0) for label in self.CV_RELATED_LABELS
        )
        off_topic_score = max(
            score_dict.get(label, 0.0) for label in self.OFF_TOPIC_LABELS
        )
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        # Decision logic
        if cv_related_score > self.THRESHOLD_CV_RELATED:
            # Clearly CV-related
            logger.debug(
                f"[GUARDRAIL v2] ALLOWED: '{question[:50]}...' "
                f"(cv_score={cv_related_score:.2f})"
            )
            return ZeroShotGuardrailResult(
                is_allowed=True,
                rejection_message=None,
                confidence=cv_related_score,
                reason="cv_related_high_confidence",
                method="zero_shot",
                classification_scores=score_dict,
                latency_ms=latency_ms
            )
        
        if off_topic_score > self.THRESHOLD_OFF_TOPIC and not has_cvs:
            # Clearly off-topic (only reject if no CVs loaded)
            logger.info(
                f"[GUARDRAIL v2] REJECTED: '{question[:50]}...' "
                f"(off_topic_score={off_topic_score:.2f})"
            )
            return ZeroShotGuardrailResult(
                is_allowed=False,
                rejection_message=self.REJECTION_MESSAGE,
                confidence=off_topic_score,
                reason="off_topic_high_confidence",
                method="zero_shot",
                classification_scores=score_dict,
                latency_ms=latency_ms
            )
        
        # Ambiguous - allow if CVs loaded, otherwise be conservative
        if has_cvs:
            logger.debug(
                f"[GUARDRAIL v2] ALLOWED (permissive with CVs): '{question[:50]}...' "
                f"(cv={cv_related_score:.2f}, off_topic={off_topic_score:.2f})"
            )
            return ZeroShotGuardrailResult(
                is_allowed=True,
                rejection_message=None,
                confidence=max(cv_related_score, 0.5),
                reason="permissive_with_cvs",
                method="zero_shot",
                classification_scores=score_dict,
                latency_ms=latency_ms
            )
        
        # No CVs and ambiguous - allow but with lower confidence
        logger.debug(
            f"[GUARDRAIL v2] ALLOWED (default): '{question[:50]}...' "
            f"(cv={cv_related_score:.2f}, off_topic={off_topic_score:.2f})"
        )
        return ZeroShotGuardrailResult(
            is_allowed=True,
            rejection_message=None,
            confidence=cv_related_score,
            reason="default_allow",
            method="zero_shot",
            classification_scores=score_dict,
            latency_ms=latency_ms
        )
    
    async def _check_with_regex_fallback(
        self,
        question: str,
        has_cvs: bool,
        start_time: float
    ) -> ZeroShotGuardrailResult:
        """Fallback to regex-based guardrails."""
        
        legacy_result = self.legacy_guardrails.check(question, has_cvs=has_cvs)
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        return ZeroShotGuardrailResult(
            is_allowed=legacy_result.is_allowed,
            rejection_message=legacy_result.rejection_message,
            confidence=legacy_result.confidence,
            reason=legacy_result.reason or "regex_check",
            method="regex_fallback",
            latency_ms=latency_ms
        )
    
    def to_legacy_result(self, result: ZeroShotGuardrailResult) -> GuardrailResult:
        """Convert to legacy GuardrailResult for backward compatibility."""
        return GuardrailResult(
            is_allowed=result.is_allowed,
            rejection_message=result.rejection_message,
            confidence=result.confidence,
            reason=result.reason
        )


# =============================================================================
# Singleton Instance
# =============================================================================

_guardrail_service_v2: Optional[GuardrailServiceV2] = None


def get_guardrail_service_v2(enabled: bool = True) -> GuardrailServiceV2:
    """Get singleton instance of GuardrailServiceV2."""
    global _guardrail_service_v2
    if _guardrail_service_v2 is None:
        _guardrail_service_v2 = GuardrailServiceV2(enabled=enabled)
    return _guardrail_service_v2


def reset_guardrail_service_v2():
    """Reset singleton (for testing)."""
    global _guardrail_service_v2
    _guardrail_service_v2 = None
