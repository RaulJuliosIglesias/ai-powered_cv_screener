"""
V7 Services Integration Module.

Provides unified access to all v7 enhancements:
- Cross-Encoder Reranking (100x faster than LLM)
- NLI Verification (hallucination detection)
- Zero-Shot Guardrails (ML-based filtering)
- RAGAS Evaluation (quality metrics)

This module serves as the integration layer between the existing
RAG v5/v6 pipeline and the new v7 services.

Usage:
    from app.services.v7_integration import V7Services
    
    v7 = V7Services()
    
    # Use individual services
    rerank_result = await v7.rerank(query, documents)
    verification = await v7.verify_response(response, context)
    guardrail = await v7.check_guardrail(query)
    metrics = await v7.evaluate(query, response, context)
"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.config import settings
from app.providers.huggingface_client import get_huggingface_client
from app.services.guardrail_service_v2 import GuardrailServiceV2, ZeroShotGuardrailResult, get_guardrail_service_v2
from app.services.nli_verification_service import (
    NLIVerificationService,
    VerificationResult,
    get_nli_verification_service,
)
from app.services.ragas_evaluation_service import RAGASEvaluationService, RAGASMetrics, get_ragas_evaluation_service
from app.services.reranking_service_v2 import (
    CrossEncoderRerankingService,
    CrossEncoderRerankResult,
    get_cross_encoder_reranking_service,
)

logger = logging.getLogger(__name__)


@dataclass
class V7Config:
    """Configuration for v7 services."""
    use_cross_encoder_reranking: bool = True
    use_nli_verification: bool = True
    use_zero_shot_guardrails: bool = True
    use_ragas_evaluation: bool = True
    llm_reranker_model: Optional[str] = None  # Fallback model for reranking
    
    @classmethod
    def from_settings(cls) -> "V7Config":
        """Create config from application settings."""
        return cls(
            use_cross_encoder_reranking=getattr(settings, 'use_hf_reranker', True),
            use_nli_verification=getattr(settings, 'use_hf_nli', True),
            use_zero_shot_guardrails=getattr(settings, 'use_hf_guardrails', True),
            use_ragas_evaluation=getattr(settings, 'use_ragas_eval', True)
        )


class V7Services:
    """
    Unified interface for all v7 RAG enhancements.
    
    Provides:
    - Automatic initialization of all v7 services
    - Feature flag control from settings
    - Graceful fallback when services unavailable
    - Logging and metrics collection
    
    Example:
        v7 = V7Services()
        
        # Check if services are available
        if v7.is_available:
            result = await v7.rerank(query, docs)
    """
    
    def __init__(self, config: Optional[V7Config] = None):
        """
        Initialize v7 services.
        
        Args:
            config: Optional configuration (uses settings if None)
        """
        self.config = config or V7Config.from_settings()
        
        # Initialize HuggingFace client
        self._hf_client = get_huggingface_client()
        
        # Initialize services based on config
        self._reranker: Optional[CrossEncoderRerankingService] = None
        self._verifier: Optional[NLIVerificationService] = None
        self._guardrails: Optional[GuardrailServiceV2] = None
        self._evaluator: Optional[RAGASEvaluationService] = None
        
        self._init_services()
        
        logger.info(
            f"V7Services initialized: "
            f"reranker={self._reranker is not None}, "
            f"verifier={self._verifier is not None}, "
            f"guardrails={self._guardrails is not None}, "
            f"evaluator={self._evaluator is not None}, "
            f"hf_available={self._hf_client.is_available}"
        )
    
    def _init_services(self):
        """Initialize individual services based on config."""
        if self.config.use_cross_encoder_reranking:
            self._reranker = get_cross_encoder_reranking_service(
                llm_model=self.config.llm_reranker_model,
                enabled=True
            )
        
        if self.config.use_nli_verification:
            self._verifier = get_nli_verification_service(enabled=True)
        
        if self.config.use_zero_shot_guardrails:
            self._guardrails = get_guardrail_service_v2(enabled=True)
        
        if self.config.use_ragas_evaluation:
            self._evaluator = get_ragas_evaluation_service(log_evaluations=True)
    
    @property
    def is_available(self) -> bool:
        """Check if HuggingFace services are available."""
        return self._hf_client.is_available
    
    @property
    def reranker(self) -> Optional[CrossEncoderRerankingService]:
        """Get cross-encoder reranking service."""
        return self._reranker
    
    @property
    def verifier(self) -> Optional[NLIVerificationService]:
        """Get NLI verification service."""
        return self._verifier
    
    @property
    def guardrails(self) -> Optional[GuardrailServiceV2]:
        """Get zero-shot guardrails service."""
        return self._guardrails
    
    @property
    def evaluator(self) -> Optional[RAGASEvaluationService]:
        """Get RAGAS evaluation service."""
        return self._evaluator
    
    # =========================================================================
    # Convenience Methods
    # =========================================================================
    
    async def rerank(
        self,
        query: str,
        results: List[Any],
        top_k: Optional[int] = None
    ) -> CrossEncoderRerankResult:
        """
        Rerank search results using cross-encoder.
        
        Falls back to returning original order if service unavailable.
        """
        if self._reranker:
            return await self._reranker.rerank(query, results, top_k)
        
        # Fallback: return original order
        return CrossEncoderRerankResult(
            original_results=results,
            reranked_results=results[:top_k] if top_k else results,
            scores={},
            latency_ms=0,
            model_used="none",
            method="disabled",
            enabled=False
        )
    
    async def verify_response(
        self,
        response: str,
        context_chunks: List[str],
        claims: Optional[List[str]] = None
    ) -> VerificationResult:
        """
        Verify claims in response using NLI.
        
        Returns neutral result if service unavailable.
        """
        if self._verifier:
            return await self._verifier.verify_response(response, context_chunks, claims)
        
        # Fallback: neutral result
        return VerificationResult(
            claims=[],
            faithfulness_score=1.0,
            hallucination_count=0,
            supported_count=0,
            unsupported_count=0,
            latency_ms=0,
            method="disabled"
        )
    
    async def check_guardrail(
        self,
        question: str,
        has_cvs: bool = False
    ) -> ZeroShotGuardrailResult:
        """
        Check if question passes guardrails.
        
        Falls back to legacy regex guardrails if service unavailable.
        """
        if self._guardrails:
            return await self._guardrails.check(question, has_cvs)
        
        # Fallback: allow everything
        return ZeroShotGuardrailResult(
            is_allowed=True,
            rejection_message=None,
            confidence=0.5,
            reason="service_unavailable",
            method="disabled"
        )
    
    async def evaluate(
        self,
        query: str,
        response: str,
        context_chunks: List[str],
        session_id: Optional[str] = None,
        query_type: Optional[str] = None
    ) -> RAGASMetrics:
        """
        Evaluate response quality using RAGAS metrics.
        
        Returns neutral metrics if service unavailable.
        """
        if self._evaluator:
            return await self._evaluator.evaluate(
                query, response, context_chunks, session_id, query_type
            )
        
        # Fallback: neutral metrics
        return RAGASMetrics(
            faithfulness=0.5,
            answer_relevancy=0.5,
            context_relevancy=0.5,
            context_precision=0.5,
            overall_score=0.5,
            latency_ms=0
        )
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all v7 services."""
        return {
            "huggingface_available": self._hf_client.is_available,
            "services": {
                "cross_encoder_reranking": {
                    "enabled": self.config.use_cross_encoder_reranking,
                    "initialized": self._reranker is not None
                },
                "nli_verification": {
                    "enabled": self.config.use_nli_verification,
                    "initialized": self._verifier is not None
                },
                "zero_shot_guardrails": {
                    "enabled": self.config.use_zero_shot_guardrails,
                    "initialized": self._guardrails is not None
                },
                "ragas_evaluation": {
                    "enabled": self.config.use_ragas_evaluation,
                    "initialized": self._evaluator is not None
                }
            }
        }


# =============================================================================
# Singleton Instance
# =============================================================================

_v7_services: Optional[V7Services] = None


def get_v7_services() -> V7Services:
    """Get singleton instance of V7Services."""
    global _v7_services
    if _v7_services is None:
        _v7_services = V7Services()
    return _v7_services


def reset_v7_services():
    """Reset singleton (for testing)."""
    global _v7_services
    _v7_services = None
