"""
RAG Service v5 - Advanced RAG Pipeline with Intelligent Reasoning.

Major improvements over v4:
- Multi-Query retrieval with HyDE
- Structured Chain-of-Thought reasoning
- Self-Ask pattern for complex queries
- Claim-level verification
- Iterative refinement
- Entity-aware hybrid search

Author: CV Screener RAG System
Version: 5.0.0
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from functools import wraps
from typing import (
    Any,
    Callable,
    Generic,
    Optional,
    Protocol,
    TypeVar,
    TYPE_CHECKING,
    List,
    Dict,
)

if TYPE_CHECKING:
    from app.providers.base import SearchResult

logger = logging.getLogger(__name__)

# =============================================================================
# TYPE DEFINITIONS
# =============================================================================

T = TypeVar("T")
R = TypeVar("R")


class Mode(Enum):
    """Operating mode for the RAG service."""
    LOCAL = "local"
    CLOUD = "cloud"
    HYBRID = "hybrid"


class PipelineStage(Enum):
    """Stages in the RAG pipeline for tracking and metrics."""
    QUERY_UNDERSTANDING = auto()
    MULTI_QUERY = auto()
    GUARDRAIL = auto()
    EMBEDDING = auto()
    SEARCH = auto()
    RERANKING = auto()
    REASONING = auto()
    GENERATION = auto()
    VERIFICATION = auto()
    CLAIM_VERIFICATION = auto()
    REFINEMENT = auto()


class ErrorSeverity(Enum):
    """Severity levels for pipeline errors."""
    WARNING = "warning"
    RECOVERABLE = "recoverable"
    FATAL = "fatal"


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass(frozen=True)
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay_ms: int = 100
    max_delay_ms: int = 5000
    exponential_base: float = 2.0
    jitter: bool = True
    
    def get_delay(self, attempt: int) -> float:
        import random
        delay = min(
            self.base_delay_ms * (self.exponential_base ** attempt),
            self.max_delay_ms
        )
        if self.jitter:
            delay *= (0.5 + random.random())
        return delay / 1000


@dataclass(frozen=True)
class CacheConfig:
    """Configuration for response caching."""
    enabled: bool = True
    ttl_seconds: int = 300
    max_entries: int = 1000
    cache_embeddings: bool = True
    cache_responses: bool = True


@dataclass(frozen=True)
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    enabled: bool = True
    failure_threshold: int = 5
    recovery_timeout_seconds: int = 30
    half_open_max_calls: int = 3


@dataclass
class RAGConfigV5:
    """Complete RAG v5 service configuration."""
    mode: Mode = Mode.LOCAL
    
    # Model configuration
    understanding_model: str | None = None
    reranking_model: str | None = None
    generation_model: str | None = None
    reasoning_model: str | None = None
    verification_model: str | None = None
    
    # V5 Feature flags
    multi_query_enabled: bool = True
    hyde_enabled: bool = True
    reasoning_enabled: bool = True
    reflection_enabled: bool = True
    claim_verification_enabled: bool = True
    iterative_refinement_enabled: bool = True
    
    # Legacy feature flags
    reranking_enabled: bool = True
    verification_enabled: bool = True
    streaming_enabled: bool = False
    parallel_steps_enabled: bool = True
    
    # Retrieval settings
    default_k: int = 15  # Increased for multi-query fusion
    default_threshold: float = 0.25  # Slightly lower for broader recall
    max_context_tokens: int = 60000
    multi_query_k: int = 10  # k per query variation
    
    # Sub-configurations
    retry: RetryConfig = field(default_factory=RetryConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    
    # Timeouts (seconds)
    embedding_timeout: float = 10.0
    search_timeout: float = 20.0
    llm_timeout: float = 120.0
    reasoning_timeout: float = 90.0
    total_timeout: float = 240.0  # Increased for multi-step reasoning


# =============================================================================
# RESULT TYPES
# =============================================================================

@dataclass
class StageMetrics:
    """Metrics for a single pipeline stage."""
    stage: PipelineStage
    duration_ms: float
    success: bool
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineMetrics:
    """Aggregated metrics for entire pipeline execution."""
    total_ms: float
    stages: list[StageMetrics] = field(default_factory=list)
    cache_hit: bool = False
    retry_count: int = 0
    
    def add_stage(self, stage: StageMetrics) -> None:
        self.stages.append(stage)
    
    def get_stage(self, stage: PipelineStage) -> StageMetrics | None:
        return next((s for s in self.stages if s.stage == stage), None)
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "total_ms": round(self.total_ms, 2),
            "cache_hit": self.cache_hit,
            "retry_count": self.retry_count,
            "stages": {
                s.stage.name.lower(): {
                    "duration_ms": round(s.duration_ms, 2),
                    "success": s.success,
                    **({"error": s.error} if s.error else {}),
                    **s.metadata
                }
                for s in self.stages
            }
        }


@dataclass
class QueryUnderstandingV5:
    """Enhanced query understanding result."""
    original_query: str
    understood_query: str
    query_type: str
    is_cv_related: bool
    requirements: list[str] = field(default_factory=list)
    reformulated_prompt: str | None = None
    confidence: float = 1.0
    entities: dict[str, list[str]] = field(default_factory=dict)
    # V5: Multi-query variations
    query_variations: list[str] = field(default_factory=list)
    hyde_document: str | None = None


@dataclass
class RetrievalResultV5:
    """Enhanced retrieval result."""
    chunks: list[dict[str, Any]]
    cv_ids: list[str]
    strategy: str
    scores: list[float]
    # V5: Track which query found each chunk
    query_sources: dict[str, list[str]] = field(default_factory=dict)


@dataclass 
class VerificationResultV5:
    """Enhanced verification result."""
    is_grounded: bool
    groundedness_score: float
    verified_claims: list[str] = field(default_factory=list)
    unverified_claims: list[str] = field(default_factory=list)
    contradicted_claims: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    # V5: Claim-level details
    claim_verification_score: float = 0.0
    needs_regeneration: bool = False


@dataclass
class RAGResponseV5:
    """Complete response from RAG v5 query."""
    answer: str
    sources: list[dict[str, Any]]
    metrics: PipelineMetrics
    confidence_score: float
    guardrail_passed: bool
    
    # Enhanced results
    query_understanding: QueryUnderstandingV5 | None = None
    verification: VerificationResultV5 | None = None
    reasoning_trace: str | None = None
    
    # Metadata
    mode: str = "local"
    cached: bool = False
    request_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    version: str = "5.0.0"
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "answer": self.answer,
            "sources": self.sources,
            "metrics": self.metrics.to_dict(),
            "confidence_score": round(self.confidence_score, 3),
            "guardrail_passed": self.guardrail_passed,
            "mode": self.mode,
            "cached": self.cached,
            "request_id": self.request_id,
            "timestamp": self.timestamp.isoformat(),
            "version": self.version,
            "reasoning_trace": self.reasoning_trace[:500] if self.reasoning_trace else None
        }


# =============================================================================
# ERROR HANDLING
# =============================================================================

class RAGError(Exception):
    """Base exception for RAG service errors."""
    def __init__(
        self,
        message: str,
        stage: PipelineStage | None = None,
        severity: ErrorSeverity = ErrorSeverity.FATAL,
        cause: Exception | None = None,
        recoverable: bool = False
    ):
        super().__init__(message)
        self.stage = stage
        self.severity = severity
        self.cause = cause
        self.recoverable = recoverable


class GuardrailError(RAGError):
    """Raised when query fails guardrail check."""
    def __init__(self, message: str, rejection_reason: str):
        super().__init__(
            message,
            stage=PipelineStage.GUARDRAIL,
            severity=ErrorSeverity.WARNING,
            recoverable=False
        )
        self.rejection_reason = rejection_reason


class RetrievalError(RAGError):
    """Raised when retrieval fails."""
    def __init__(self, message: str, cause: Exception | None = None):
        super().__init__(
            message,
            stage=PipelineStage.SEARCH,
            severity=ErrorSeverity.RECOVERABLE,
            cause=cause,
            recoverable=True
        )


class GenerationError(RAGError):
    """Raised when LLM generation fails."""
    def __init__(self, message: str, cause: Exception | None = None):
        super().__init__(
            message,
            stage=PipelineStage.GENERATION,
            severity=ErrorSeverity.RECOVERABLE,
            cause=cause,
            recoverable=True
        )


# =============================================================================
# CIRCUIT BREAKER
# =============================================================================

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    name: str
    config: CircuitBreakerConfig
    
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: datetime | None = field(default=None, init=False)
    _half_open_calls: int = field(default=0, init=False)
    
    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if self._should_attempt_recovery():
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
        return self._state
    
    def _should_attempt_recovery(self) -> bool:
        if self._last_failure_time is None:
            return True
        elapsed = (datetime.utcnow() - self._last_failure_time).total_seconds()
        return elapsed >= self.config.recovery_timeout_seconds
    
    def record_success(self) -> None:
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1
            if self._half_open_calls >= self.config.half_open_max_calls:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                logger.info(f"Circuit breaker '{self.name}' closed")
        else:
            self._failure_count = 0
    
    def record_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = datetime.utcnow()
        
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            logger.warning(f"Circuit breaker '{self.name}' reopened")
        elif self._failure_count >= self.config.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(f"Circuit breaker '{self.name}' opened")
    
    def allow_request(self) -> bool:
        if not self.config.enabled:
            return True
        state = self.state
        if state == CircuitState.CLOSED:
            return True
        elif state == CircuitState.HALF_OPEN:
            return self._half_open_calls < self.config.half_open_max_calls
        return False


# =============================================================================
# CACHING
# =============================================================================

@dataclass
class CacheEntry(Generic[T]):
    """A cached value with metadata."""
    value: T
    created_at: datetime
    ttl_seconds: int
    hits: int = 0
    
    @property
    def is_expired(self) -> bool:
        elapsed = (datetime.utcnow() - self.created_at).total_seconds()
        return elapsed >= self.ttl_seconds


class LRUCache(Generic[T]):
    """Simple LRU cache with TTL support."""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self._cache: dict[str, CacheEntry[T]] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0
    
    @staticmethod
    def _hash_key(key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()[:16]
    
    async def get(self, key: str) -> T | None:
        async with self._lock:
            hashed = self._hash_key(key)
            entry = self._cache.get(hashed)
            
            if entry is None:
                self._misses += 1
                return None
            
            if entry.is_expired:
                del self._cache[hashed]
                self._misses += 1
                return None
            
            entry.hits += 1
            self._hits += 1
            return entry.value
    
    async def set(self, key: str, value: T, ttl: int | None = None) -> None:
        async with self._lock:
            if len(self._cache) >= self._max_size:
                await self._evict_lru()
            
            hashed = self._hash_key(key)
            self._cache[hashed] = CacheEntry(
                value=value,
                created_at=datetime.utcnow(),
                ttl_seconds=ttl or self._default_ttl
            )
    
    async def _evict_lru(self) -> None:
        if not self._cache:
            return
        expired = [k for k, v in self._cache.items() if v.is_expired]
        for k in expired:
            del self._cache[k]
        
        if len(self._cache) >= self._max_size:
            sorted_entries = sorted(
                self._cache.items(),
                key=lambda x: (x[1].hits, x[1].created_at)
            )
            to_remove = len(self._cache) - self._max_size + 1
            for k, _ in sorted_entries[:to_remove]:
                del self._cache[k]
    
    async def clear(self) -> None:
        async with self._lock:
            self._cache.clear()
    
    def stats(self) -> dict[str, Any]:
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total, 3) if total > 0 else 0
        }


# =============================================================================
# PIPELINE CONTEXT
# =============================================================================

@dataclass
class PipelineContextV5:
    """Enhanced pipeline context for v5."""
    # Input
    question: str
    session_id: str | None = None
    cv_ids: list[str] | None = None
    k: int = 15
    threshold: float = 0.25
    total_cvs_in_session: int | None = None
    
    # Request metadata
    request_id: str = field(default_factory=lambda: hashlib.sha256(
        f"{time.time()}".encode()
    ).hexdigest()[:12])
    start_time: float = field(default_factory=time.perf_counter)
    
    # Stage results
    query_understanding: QueryUnderstandingV5 | None = None
    guardrail_passed: bool = True
    guardrail_message: str | None = None
    
    # V5: Multi-query embeddings
    query_embeddings: dict[str, list[float]] = field(default_factory=dict)
    hyde_embedding: list[float] | None = None
    
    retrieval_result: RetrievalResultV5 | None = None
    reranked_chunks: list[dict[str, Any]] | None = None
    
    # V5: Reasoning trace
    reasoning_trace: str | None = None
    reasoning_steps: list[dict] = field(default_factory=list)
    
    generated_response: str | None = None
    generation_tokens: dict[str, int] = field(default_factory=dict)
    
    verification_result: VerificationResultV5 | None = None
    
    # V5: Refinement tracking
    refinement_iterations: int = 0
    max_refinements: int = 2
    
    # Metrics
    metrics: PipelineMetrics = field(default_factory=lambda: PipelineMetrics(total_ms=0))
    
    # Cache flags
    embedding_cached: bool = False
    response_cached: bool = False
    
    @property
    def effective_chunks(self) -> list[dict[str, Any]]:
        if self.reranked_chunks is not None:
            return self.reranked_chunks
        if self.retrieval_result is not None:
            return self.retrieval_result.chunks
        return []
    
    @property
    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self.start_time) * 1000


# =============================================================================
# MAIN RAG SERVICE V5
# =============================================================================

class RAGServiceV5:
    """
    Advanced RAG Service v5 with intelligent reasoning.
    
    New Features:
    - Multi-Query: Generate query variations for better recall
    - HyDE: Hypothetical document embeddings for semantic matching
    - Chain-of-Thought: Structured reasoning process
    - Self-Ask: Generate and answer sub-questions
    - Claim Verification: Verify individual claims in response
    - Iterative Refinement: Improve response if verification fails
    
    Pipeline:
    1. Query Understanding → Understand and classify query
    2. Multi-Query Generation → Create query variations + HyDE
    3. Guardrail Check → Reject off-topic questions
    4. Multi-Embedding → Generate embeddings for all queries
    5. Fusion Retrieval → Search with all embeddings, fuse results
    6. Reranking → LLM-based relevance scoring
    7. Reasoning → Chain-of-Thought analysis
    8. Generation → Generate structured response
    9. Claim Verification → Verify each claim
    10. Refinement → Regenerate if too many unverified claims
    """
    
    def __init__(self, config: RAGConfigV5 | None = None):
        self.config = config or RAGConfigV5()
        
        # Caches
        self._embedding_cache: LRUCache[list[float]] | None = None
        self._response_cache: LRUCache[str] | None = None
        
        if self.config.cache.enabled:
            self._embedding_cache = LRUCache(
                max_size=self.config.cache.max_entries,
                default_ttl=self.config.cache.ttl_seconds
            )
            self._response_cache = LRUCache(
                max_size=self.config.cache.max_entries // 2,
                default_ttl=self.config.cache.ttl_seconds
            )
        
        # Circuit breakers
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        if self.config.circuit_breaker.enabled:
            for name in ["embedding", "search", "llm", "reasoning"]:
                self._circuit_breakers[name] = CircuitBreaker(
                    name=name,
                    config=self.config.circuit_breaker
                )
        
        # Services (initialized later)
        self._embedder: Any = None
        self._vector_store: Any = None
        self._llm: Any = None
        self._query_understanding: Any = None
        self._multi_query: Any = None
        self._reranking: Any = None
        self._reasoning: Any = None
        self._claim_verifier: Any = None
        self._guardrail: Any = None
        self._hallucination: Any = None
        self._eval_service: Any = None
        self._prompt_builder: Any = None
        
        self._providers_initialized = False
        
        logger.info(f"RAGServiceV5 initialized with mode={self.config.mode.value}")
    
    def initialize_providers(
        self,
        embedder: Any,
        vector_store: Any,
        llm: Any,
        query_understanding: Any,
        multi_query: Any,
        reranking: Any,
        reasoning: Any,
        claim_verifier: Any,
        guardrail: Any,
        hallucination: Any,
        eval_service: Any,
        prompt_builder: Any
    ) -> None:
        """Initialize service providers."""
        self._embedder = embedder
        self._vector_store = vector_store
        self._llm = llm
        self._query_understanding = query_understanding
        self._multi_query = multi_query
        self._reranking = reranking
        self._reasoning = reasoning
        self._claim_verifier = claim_verifier
        self._guardrail = guardrail
        self._hallucination = hallucination
        self._eval_service = eval_service
        self._prompt_builder = prompt_builder
        
        self._providers_initialized = True
        logger.info("RAGServiceV5 providers initialized")
    
    @classmethod
    def from_factory(cls, mode: Mode = Mode.LOCAL) -> "RAGServiceV5":
        """Create service with default providers."""
        from app.config import settings
        from app.providers.factory import ProviderFactory
        from app.services.guardrail_service import GuardrailService
        from app.services.hallucination_service import HallucinationService
        from app.services.eval_service import EvalService
        from app.services.query_understanding_service import QueryUnderstandingService
        from app.services.reranking_service import RerankingService
        from app.services.multi_query_service import MultiQueryService
        from app.services.reasoning_service import ReasoningService
        from app.services.claim_verifier_service import ClaimVerifierService
        from app.prompts.templates import PromptBuilder
        
        config = RAGConfigV5(
            mode=mode,
            default_k=settings.retrieval_k,
            default_threshold=settings.retrieval_score_threshold
        )
        
        service = cls(config)
        
        service.initialize_providers(
            embedder=ProviderFactory.get_embedding_provider(mode),
            vector_store=ProviderFactory.get_vector_store(mode),
            llm=ProviderFactory.get_llm_provider(mode),
            query_understanding=QueryUnderstandingService(),
            multi_query=MultiQueryService(hyde_enabled=config.hyde_enabled),
            reranking=RerankingService(enabled=config.reranking_enabled),
            reasoning=ReasoningService(reflection_enabled=config.reflection_enabled),
            claim_verifier=ClaimVerifierService(),
            guardrail=GuardrailService(),
            hallucination=HallucinationService(),
            eval_service=EvalService(),
            prompt_builder=PromptBuilder()
        )
        
        return service
    
    async def query(
        self,
        question: str,
        session_id: str | None = None,
        cv_ids: list[str] | None = None,
        k: int | None = None,
        threshold: float | None = None,
        total_cvs_in_session: int | None = None
    ) -> RAGResponseV5:
        """Execute complete RAG v5 query pipeline."""
        if not self._providers_initialized:
            raise RAGError("Providers not initialized")
        
        ctx = PipelineContextV5(
            question=question,
            session_id=session_id,
            cv_ids=cv_ids,
            k=k or self.config.default_k,
            threshold=threshold or self.config.default_threshold,
            total_cvs_in_session=total_cvs_in_session
        )
        
        try:
            response = await asyncio.wait_for(
                self._execute_pipeline(ctx),
                timeout=self.config.total_timeout
            )
            return response
            
        except asyncio.TimeoutError:
            logger.error(f"Pipeline timeout after {self.config.total_timeout}s")
            return self._build_error_response(ctx, "Request timed out")
        except GuardrailError as e:
            return self._build_guardrail_response(ctx, e.rejection_reason)
        except RAGError as e:
            logger.error(f"Pipeline error at {e.stage}: {e}")
            return self._build_error_response(ctx, str(e))
        except Exception as e:
            logger.exception(f"Unexpected error: {e}")
            return self._build_error_response(ctx, "An unexpected error occurred")
    
    async def _execute_pipeline(self, ctx: PipelineContextV5) -> RAGResponseV5:
        """Execute the full RAG v5 pipeline."""
        
        # Stage 1: Query Understanding
        await self._step_query_understanding(ctx)
        
        # Stage 2: Multi-Query Generation (V5)
        if self.config.multi_query_enabled:
            await self._step_multi_query(ctx)
        
        # Stage 3: Guardrail Check
        passed = await self._step_guardrail(ctx)
        if not passed:
            return self._build_guardrail_response(ctx, ctx.guardrail_message)
        
        # Stage 4: Multi-Embedding (V5)
        await self._step_multi_embedding(ctx)
        
        # Stage 5: Fusion Retrieval (V5)
        await self._step_fusion_retrieval(ctx)
        
        if not ctx.retrieval_result or not ctx.retrieval_result.chunks:
            return self._build_no_results_response(ctx)
        
        # Stage 6: Reranking
        if self.config.reranking_enabled:
            await self._step_reranking(ctx)
        
        # Stage 7: Reasoning (V5)
        if self.config.reasoning_enabled:
            await self._step_reasoning(ctx)
        
        # Stage 8: Generation
        await self._step_generation(ctx)
        
        # Stage 9: Claim Verification (V5)
        if self.config.claim_verification_enabled:
            await self._step_claim_verification(ctx)
        
        # Stage 10: Iterative Refinement (V5)
        if self.config.iterative_refinement_enabled:
            await self._step_refinement(ctx)
        
        # Finalize
        ctx.metrics.total_ms = ctx.elapsed_ms
        ctx.metrics.cache_hit = ctx.embedding_cached or ctx.response_cached
        
        self._log_query(ctx)
        
        return self._build_success_response(ctx)
    
    # =========================================================================
    # PIPELINE STEPS
    # =========================================================================
    
    async def _step_query_understanding(self, ctx: PipelineContextV5) -> None:
        """Step 1: Understand the query."""
        start = time.perf_counter()
        try:
            result = await self._query_understanding.understand(ctx.question)
            
            ctx.query_understanding = QueryUnderstandingV5(
                original_query=result.original_query,
                understood_query=result.understood_query,
                query_type=result.query_type,
                is_cv_related=result.is_cv_related,
                requirements=result.requirements or [],
                reformulated_prompt=result.reformulated_prompt,
                confidence=getattr(result, "confidence", 1.0)
            )
            
            ctx.metrics.add_stage(StageMetrics(
                stage=PipelineStage.QUERY_UNDERSTANDING,
                duration_ms=(time.perf_counter() - start) * 1000,
                success=True,
                metadata={"query_type": result.query_type}
            ))
        except Exception as e:
            logger.error(f"Query understanding failed: {e}")
            ctx.metrics.add_stage(StageMetrics(
                stage=PipelineStage.QUERY_UNDERSTANDING,
                duration_ms=(time.perf_counter() - start) * 1000,
                success=False,
                error=str(e)
            ))
    
    async def _step_multi_query(self, ctx: PipelineContextV5) -> None:
        """Step 2: Generate query variations and HyDE."""
        start = time.perf_counter()
        try:
            result = await self._multi_query.generate(ctx.question)
            
            if ctx.query_understanding:
                ctx.query_understanding.query_variations = result.variations
                ctx.query_understanding.hyde_document = result.hyde_document
                ctx.query_understanding.entities = result.entities or {}
            
            ctx.metrics.add_stage(StageMetrics(
                stage=PipelineStage.MULTI_QUERY,
                duration_ms=(time.perf_counter() - start) * 1000,
                success=True,
                metadata={
                    "num_variations": len(result.variations),
                    "hyde_enabled": result.hyde_document is not None
                }
            ))
        except Exception as e:
            logger.error(f"Multi-query generation failed: {e}")
            ctx.metrics.add_stage(StageMetrics(
                stage=PipelineStage.MULTI_QUERY,
                duration_ms=(time.perf_counter() - start) * 1000,
                success=False,
                error=str(e)
            ))
    
    async def _step_guardrail(self, ctx: PipelineContextV5) -> bool:
        """Step 3: Check guardrails."""
        start = time.perf_counter()
        try:
            if ctx.query_understanding and not ctx.query_understanding.is_cv_related:
                ctx.guardrail_passed = False
                ctx.guardrail_message = (
                    "I can only help with CV screening and candidate analysis."
                )
                return False
            
            result = self._guardrail.check(ctx.question)
            
            if not result.is_allowed:
                ctx.guardrail_passed = False
                ctx.guardrail_message = result.rejection_message
                return False
            
            ctx.guardrail_passed = True
            
            ctx.metrics.add_stage(StageMetrics(
                stage=PipelineStage.GUARDRAIL,
                duration_ms=(time.perf_counter() - start) * 1000,
                success=True
            ))
            return True
        except Exception as e:
            logger.error(f"Guardrail check failed: {e}")
            ctx.metrics.add_stage(StageMetrics(
                stage=PipelineStage.GUARDRAIL,
                duration_ms=(time.perf_counter() - start) * 1000,
                success=False,
                error=str(e)
            ))
            return True  # Allow on error
    
    async def _step_multi_embedding(self, ctx: PipelineContextV5) -> None:
        """Step 4: Generate embeddings for all query variations."""
        start = time.perf_counter()
        try:
            queries_to_embed = [ctx.question]
            
            # Add query variations
            if ctx.query_understanding and ctx.query_understanding.query_variations:
                queries_to_embed.extend(ctx.query_understanding.query_variations[:3])
            
            # Generate embeddings (could be parallelized)
            for query in queries_to_embed:
                cache_key = f"emb:{query}"
                
                if self._embedding_cache:
                    cached = await self._embedding_cache.get(cache_key)
                    if cached:
                        ctx.query_embeddings[query] = cached
                        ctx.embedding_cached = True
                        continue
                
                result = await asyncio.wait_for(
                    self._embedder.embed_query(query),
                    timeout=self.config.embedding_timeout
                )
                
                ctx.query_embeddings[query] = result.embeddings[0]
                
                if self._embedding_cache:
                    await self._embedding_cache.set(cache_key, result.embeddings[0])
            
            # Generate HyDE embedding if available
            if (ctx.query_understanding and 
                ctx.query_understanding.hyde_document and 
                self.config.hyde_enabled):
                
                hyde_result = await self._embedder.embed_query(
                    ctx.query_understanding.hyde_document
                )
                ctx.hyde_embedding = hyde_result.embeddings[0]
            
            ctx.metrics.add_stage(StageMetrics(
                stage=PipelineStage.EMBEDDING,
                duration_ms=(time.perf_counter() - start) * 1000,
                success=True,
                metadata={"num_embeddings": len(ctx.query_embeddings)}
            ))
        except Exception as e:
            logger.error(f"Multi-embedding failed: {e}")
            ctx.metrics.add_stage(StageMetrics(
                stage=PipelineStage.EMBEDDING,
                duration_ms=(time.perf_counter() - start) * 1000,
                success=False,
                error=str(e)
            ))
            raise RetrievalError(f"Embedding failed: {e}", cause=e)
    
    async def _step_fusion_retrieval(self, ctx: PipelineContextV5) -> None:
        """Step 5: Search with all embeddings and fuse results."""
        start = time.perf_counter()
        try:
            all_results: dict[str, dict] = {}  # chunk_id -> chunk with max score
            query_sources: dict[str, list[str]] = {}  # chunk_id -> queries that found it
            
            # Search with each embedding
            embeddings_to_search = list(ctx.query_embeddings.items())
            
            # Add HyDE embedding if available
            if ctx.hyde_embedding:
                embeddings_to_search.append(("hyde", ctx.hyde_embedding))
            
            for query_name, embedding in embeddings_to_search:
                results = await asyncio.wait_for(
                    self._vector_store.search(
                        embedding=embedding,
                        k=self.config.multi_query_k,
                        threshold=ctx.threshold,
                        cv_ids=ctx.cv_ids,
                        diversify_by_cv=True
                    ),
                    timeout=self.config.search_timeout
                )
                
                for r in results:
                    chunk_id = r.id
                    
                    if chunk_id not in all_results:
                        all_results[chunk_id] = {
                            "content": r.content,
                            "metadata": {
                                "filename": r.filename,
                                "candidate_name": r.metadata.get("candidate_name", "Unknown"),
                                "section_type": r.metadata.get("section_type", "general"),
                                "cv_id": r.cv_id
                            },
                            "max_score": r.similarity,
                            "query_count": 0
                        }
                        query_sources[chunk_id] = []
                    
                    # Update max score (RRF-like fusion)
                    all_results[chunk_id]["max_score"] = max(
                        all_results[chunk_id]["max_score"],
                        r.similarity
                    )
                    all_results[chunk_id]["query_count"] += 1
                    query_sources[chunk_id].append(query_name)
            
            # Sort by combined score (max_score * query_count boost)
            sorted_chunks = sorted(
                all_results.values(),
                key=lambda x: x["max_score"] * (1 + 0.1 * x["query_count"]),
                reverse=True
            )[:ctx.k]
            
            chunks = [
                {"content": c["content"], "metadata": c["metadata"]}
                for c in sorted_chunks
            ]
            
            cv_ids = list({c["metadata"]["cv_id"] for c in chunks})
            scores = [c["max_score"] for c in sorted_chunks]
            
            ctx.retrieval_result = RetrievalResultV5(
                chunks=chunks,
                cv_ids=cv_ids,
                strategy="multi_query_fusion",
                scores=scores,
                query_sources=query_sources
            )
            
            ctx.metrics.add_stage(StageMetrics(
                stage=PipelineStage.SEARCH,
                duration_ms=(time.perf_counter() - start) * 1000,
                success=True,
                metadata={
                    "num_chunks": len(chunks),
                    "num_cvs": len(cv_ids),
                    "fusion_queries": len(embeddings_to_search)
                }
            ))
        except Exception as e:
            logger.error(f"Fusion retrieval failed: {e}")
            ctx.metrics.add_stage(StageMetrics(
                stage=PipelineStage.SEARCH,
                duration_ms=(time.perf_counter() - start) * 1000,
                success=False,
                error=str(e)
            ))
            raise RetrievalError(f"Retrieval failed: {e}", cause=e)
    
    async def _step_reranking(self, ctx: PipelineContextV5) -> None:
        """Step 6: Rerank chunks."""
        start = time.perf_counter()
        try:
            chunks = ctx.retrieval_result.chunks if ctx.retrieval_result else []
            if not chunks:
                return
            
            effective_question = (
                ctx.query_understanding.reformulated_prompt
                if ctx.query_understanding and ctx.query_understanding.reformulated_prompt
                else ctx.question
            )
            
            result = await self._reranking.rerank(
                query=effective_question,
                results=chunks,
                top_k=None
            )
            
            ctx.reranked_chunks = result.reranked_results
            
            ctx.metrics.add_stage(StageMetrics(
                stage=PipelineStage.RERANKING,
                duration_ms=(time.perf_counter() - start) * 1000,
                success=True
            ))
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            ctx.metrics.add_stage(StageMetrics(
                stage=PipelineStage.RERANKING,
                duration_ms=(time.perf_counter() - start) * 1000,
                success=False,
                error=str(e)
            ))
    
    async def _step_reasoning(self, ctx: PipelineContextV5) -> None:
        """Step 7: Apply structured reasoning."""
        start = time.perf_counter()
        try:
            context_str = self._format_context(ctx.effective_chunks)
            
            result = await asyncio.wait_for(
                self._reasoning.reason(
                    question=ctx.question,
                    context=context_str,
                    total_cvs=ctx.total_cvs_in_session or 0
                ),
                timeout=self.config.reasoning_timeout
            )
            
            ctx.reasoning_trace = result.thinking_trace
            ctx.reasoning_steps = [
                {"type": s.step_type, "content": s.content}
                for s in result.steps
            ]
            
            # If reasoning produced a final answer, use it
            if result.final_answer:
                ctx.generated_response = result.final_answer
            
            ctx.metrics.add_stage(StageMetrics(
                stage=PipelineStage.REASONING,
                duration_ms=(time.perf_counter() - start) * 1000,
                success=True,
                metadata={"num_steps": len(result.steps)}
            ))
        except Exception as e:
            logger.error(f"Reasoning failed: {e}")
            ctx.metrics.add_stage(StageMetrics(
                stage=PipelineStage.REASONING,
                duration_ms=(time.perf_counter() - start) * 1000,
                success=False,
                error=str(e)
            ))
    
    async def _step_generation(self, ctx: PipelineContextV5) -> None:
        """Step 8: Generate response."""
        start = time.perf_counter()
        
        # Skip if reasoning already produced response
        if ctx.generated_response:
            ctx.metrics.add_stage(StageMetrics(
                stage=PipelineStage.GENERATION,
                duration_ms=0,
                success=True,
                metadata={"from_reasoning": True}
            ))
            return
        
        try:
            chunks = ctx.effective_chunks
            
            effective_question = (
                ctx.query_understanding.reformulated_prompt
                if ctx.query_understanding and ctx.query_understanding.reformulated_prompt
                else ctx.question
            )
            
            prompt = self._prompt_builder.build_query_prompt(
                question=effective_question,
                chunks=chunks,
                total_cvs=ctx.total_cvs_in_session
            )
            
            # Add requirements
            if ctx.query_understanding and ctx.query_understanding.requirements:
                requirements_text = "\n\nIMPORTANT REQUIREMENTS:\n" + "\n".join(
                    f"- {req}" for req in ctx.query_understanding.requirements
                )
                prompt = prompt.replace("Respond now:", requirements_text + "\n\nRespond now:")
            
            from app.prompts.templates import SYSTEM_PROMPT
            
            result = await asyncio.wait_for(
                self._llm.generate(prompt, system_prompt=SYSTEM_PROMPT),
                timeout=self.config.llm_timeout
            )
            
            ctx.generated_response = result.text
            ctx.generation_tokens = {
                "prompt": result.prompt_tokens,
                "completion": result.completion_tokens
            }
            
            ctx.metrics.add_stage(StageMetrics(
                stage=PipelineStage.GENERATION,
                duration_ms=(time.perf_counter() - start) * 1000,
                success=True
            ))
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            ctx.metrics.add_stage(StageMetrics(
                stage=PipelineStage.GENERATION,
                duration_ms=(time.perf_counter() - start) * 1000,
                success=False,
                error=str(e)
            ))
            raise GenerationError(f"Generation failed: {e}", cause=e)
    
    async def _step_claim_verification(self, ctx: PipelineContextV5) -> None:
        """Step 9: Verify claims in response."""
        start = time.perf_counter()
        try:
            if not ctx.generated_response:
                return
            
            result = await self._claim_verifier.verify_response(
                response=ctx.generated_response,
                context_chunks=ctx.effective_chunks
            )
            
            ctx.verification_result = VerificationResultV5(
                is_grounded=result.overall_score >= 0.7,
                groundedness_score=result.overall_score,
                verified_claims=[vc.claim.text for vc in result.verified_claims],
                unverified_claims=[uc.claim.text for uc in result.unverified_claims],
                contradicted_claims=[cc.claim.text for cc in result.contradicted_claims],
                claim_verification_score=result.overall_score,
                needs_regeneration=result.needs_regeneration
            )
            
            ctx.metrics.add_stage(StageMetrics(
                stage=PipelineStage.CLAIM_VERIFICATION,
                duration_ms=(time.perf_counter() - start) * 1000,
                success=True,
                metadata={
                    "verified": len(result.verified_claims),
                    "unverified": len(result.unverified_claims),
                    "contradicted": len(result.contradicted_claims)
                }
            ))
        except Exception as e:
            logger.error(f"Claim verification failed: {e}")
            ctx.metrics.add_stage(StageMetrics(
                stage=PipelineStage.CLAIM_VERIFICATION,
                duration_ms=(time.perf_counter() - start) * 1000,
                success=False,
                error=str(e)
            ))
    
    async def _step_refinement(self, ctx: PipelineContextV5) -> None:
        """Step 10: Refine response if verification failed."""
        if not ctx.verification_result or not ctx.verification_result.needs_regeneration:
            return
        
        if ctx.refinement_iterations >= ctx.max_refinements:
            logger.warning("Max refinement iterations reached")
            return
        
        start = time.perf_counter()
        try:
            ctx.refinement_iterations += 1
            
            # Build refinement prompt
            issues = []
            if ctx.verification_result.contradicted_claims:
                issues.append(f"Contradicted claims: {ctx.verification_result.contradicted_claims}")
            if ctx.verification_result.unverified_claims:
                issues.append(f"Unverified claims (remove or verify): {ctx.verification_result.unverified_claims[:3]}")
            
            refinement_prompt = f"""Your previous response had verification issues:
{chr(10).join(issues)}

Please regenerate your response, ensuring ALL claims are supported by the CV data.
If you cannot verify a claim, do not include it.

Original question: {ctx.question}

Context:
{self._format_context(ctx.effective_chunks)[:10000]}

Provide a corrected response:"""
            
            from app.prompts.templates import SYSTEM_PROMPT
            
            result = await self._llm.generate(
                refinement_prompt,
                system_prompt=SYSTEM_PROMPT
            )
            
            ctx.generated_response = result.text
            
            ctx.metrics.add_stage(StageMetrics(
                stage=PipelineStage.REFINEMENT,
                duration_ms=(time.perf_counter() - start) * 1000,
                success=True,
                metadata={"iteration": ctx.refinement_iterations}
            ))
        except Exception as e:
            logger.error(f"Refinement failed: {e}")
            ctx.metrics.add_stage(StageMetrics(
                stage=PipelineStage.REFINEMENT,
                duration_ms=(time.perf_counter() - start) * 1000,
                success=False,
                error=str(e)
            ))
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _format_context(self, chunks: list[dict[str, Any]]) -> str:
        """Format chunks into context string with CV IDs for reference linking."""
        parts = []
        for i, chunk in enumerate(chunks):
            content = chunk.get("content", "")
            metadata = chunk.get("metadata", {})
            cv_id = metadata.get("cv_id", f"cv_{i}")
            filename = metadata.get("filename", "Unknown")
            candidate = metadata.get("candidate_name", "")
            section = metadata.get("section_type", "")
            
            # Format header with CV ID prominently for LLM to use in references
            header = f"[CV {cv_id}: {filename}"
            if candidate:
                header += f" | Candidate: {candidate}"
            if section:
                header += f" | Section: {section}"
            header += "]"
            
            # Add reminder about reference format
            reference_hint = f"(Use **[{candidate or filename}](cv:{cv_id})** to reference this candidate)"
            
            parts.append(f"{header}\n{reference_hint}\n{content}")
        
        return "\n\n---\n\n".join(parts)
    
    def _build_success_response(self, ctx: PipelineContextV5) -> RAGResponseV5:
        """Build successful response with formatted reasoning blocks."""
        sources = []
        seen_ids = set()
        
        for chunk in ctx.effective_chunks:
            cv_id = chunk.get("metadata", {}).get("cv_id")
            if cv_id and cv_id not in seen_ids:
                seen_ids.add(cv_id)
                sources.append({
                    "cv_id": cv_id,
                    "filename": chunk.get("metadata", {}).get("filename", "Unknown")
                })
        
        confidence = 0.8
        if ctx.verification_result:
            confidence = ctx.verification_result.groundedness_score
        
        # Format the final answer with reasoning blocks
        formatted_answer = self._format_answer_with_blocks(ctx)
        
        return RAGResponseV5(
            answer=formatted_answer,
            sources=sources,
            metrics=ctx.metrics,
            confidence_score=confidence,
            guardrail_passed=True,
            query_understanding=ctx.query_understanding,
            verification=ctx.verification_result,
            reasoning_trace=ctx.reasoning_trace,
            mode=self.config.mode.value,
            cached=ctx.response_cached,
            request_id=ctx.request_id
        )
    
    def _format_answer_with_blocks(self, ctx: PipelineContextV5) -> str:
        """Post-process answer to add CV links and proper formatting."""
        answer = ctx.generated_response or ""
        
        # Build candidate name -> cv_id mapping from chunks
        candidate_map = {}
        for chunk in ctx.effective_chunks:
            metadata = chunk.get("metadata", {})
            cv_id = metadata.get("cv_id")
            candidate_name = metadata.get("candidate_name", "")
            filename = metadata.get("filename", "")
            
            if cv_id and candidate_name:
                # Store multiple variations of the name
                candidate_map[candidate_name] = cv_id
                # Also store first name and last name separately
                name_parts = candidate_name.split()
                if len(name_parts) >= 2:
                    candidate_map[name_parts[0]] = cv_id  # First name
                    candidate_map[name_parts[-1]] = cv_id  # Last name
                    candidate_map[f"{name_parts[0]} {name_parts[-1]}"] = cv_id
            elif cv_id and filename:
                # Use filename as fallback
                clean_name = filename.replace('.pdf', '').replace('_', ' ')
                candidate_map[clean_name] = cv_id
        
        # Post-process: Add CV links to candidate names
        answer = self._add_cv_links_to_text(answer, candidate_map)
        
        # Ensure conclusion section is properly formatted
        answer = self._format_conclusion_section(answer)
        
        return answer
    
    def _add_cv_links_to_text(self, text: str, candidate_map: dict[str, str]) -> str:
        """Add CV links to ALL candidate name mentions that don't already have them."""
        import re
        
        if not candidate_map:
            return text
        
        result = text
        
        # Sort by name length (longest first) to avoid partial replacements
        sorted_names = sorted(candidate_map.keys(), key=len, reverse=True)
        
        for name in sorted_names:
            if len(name) < 4:  # Skip very short names
                continue
                
            cv_id = candidate_map[name]
            escaped_name = re.escape(name)
            
            # Pattern: name with word boundaries, NOT already inside [...](...) link
            # We use negative lookbehind for [ and negative lookahead for ](
            # Also skip if already has ** around it with link
            
            # Find all matches and their positions
            pattern = rf'\b{escaped_name}\b'
            matches = list(re.finditer(pattern, result, flags=re.IGNORECASE))
            
            # Process matches in reverse order to preserve positions
            for match in reversed(matches):
                start, end = match.start(), match.end()
                matched_text = match.group(0)
                
                # Get context around the match
                before = result[max(0, start-10):start]
                after = result[end:end+10]
                
                # Skip if already in a link format
                if before.endswith('[') or before.endswith('**['):
                    continue
                if '](cv:' in after[:8]:
                    continue
                # Skip if the match is inside square brackets (check broader context)
                broad_before = result[max(0, start-50):start]
                if '[' in broad_before:
                    last_open = broad_before.rfind('[')
                    last_close = broad_before.rfind(']')
                    if last_open > last_close:
                        # Inside unclosed bracket - likely in a link
                        continue
                
                # Replace this occurrence with linked version
                replacement = f'**[{matched_text}](cv:{cv_id})**'
                result = result[:start] + replacement + result[end:]
        
        # Clean up artifacts
        result = re.sub(r'\*\*\*\*+', '**', result)
        result = re.sub(r'\*\*\s*\*\*', ' ', result)
        result = re.sub(r'\[\*\*\[', '**[', result)  # Fix nested brackets
        result = re.sub(r'\]\*\*\]', ']**', result)
        
        return result
    
    def _format_conclusion_section(self, text: str) -> str:
        """Ensure conclusion section is properly formatted."""
        import re
        
        # Already has :::conclusion
        if ':::conclusion' in text:
            return text
        
        # Look for conclusion markers
        patterns = [
            (r'\n\*\*Conclusi[oó]n:?\*\*\s*\n', '\n\n:::conclusion\n'),
            (r'\n##\s*Conclusi[oó]n\s*\n', '\n\n:::conclusion\n'),
            (r'\n###\s*Conclusi[oó]n\s*\n', '\n\n:::conclusion\n'),
            (r'\nConclusi[oó]n:?\s*\n', '\n\n:::conclusion\n'),
        ]
        
        for pattern, replacement in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
                # Add closing marker at the end if not present
                if ':::conclusion' in text and not text.strip().endswith(':::'):
                    text = text.strip() + '\n:::'
                break
        
        return text
    
    def _build_guardrail_response(
        self,
        ctx: PipelineContextV5,
        message: str | None
    ) -> RAGResponseV5:
        """Build guardrail rejection response."""
        ctx.metrics.total_ms = ctx.elapsed_ms
        
        return RAGResponseV5(
            answer=message or "I can only help with CV screening questions.",
            sources=[],
            metrics=ctx.metrics,
            confidence_score=0,
            guardrail_passed=False,
            mode=self.config.mode.value,
            request_id=ctx.request_id
        )
    
    def _build_no_results_response(self, ctx: PipelineContextV5) -> RAGResponseV5:
        """Build no results response."""
        ctx.metrics.total_ms = ctx.elapsed_ms
        
        return RAGResponseV5(
            answer=(
                "I couldn't find any relevant information in the CVs. "
                "Try asking about different skills or experiences."
            ),
            sources=[],
            metrics=ctx.metrics,
            confidence_score=0.8,
            guardrail_passed=True,
            query_understanding=ctx.query_understanding,
            mode=self.config.mode.value,
            request_id=ctx.request_id
        )
    
    def _build_error_response(
        self,
        ctx: PipelineContextV5,
        message: str
    ) -> RAGResponseV5:
        """Build error response."""
        ctx.metrics.total_ms = ctx.elapsed_ms
        
        return RAGResponseV5(
            answer=f"I encountered an issue: {message}",
            sources=[],
            metrics=ctx.metrics,
            confidence_score=0,
            guardrail_passed=True,
            mode=self.config.mode.value,
            request_id=ctx.request_id
        )
    
    def _log_query(self, ctx: PipelineContextV5) -> None:
        """Log query for evaluation."""
        if not self._eval_service:
            return
        
        try:
            self._eval_service.log_query(
                query=ctx.question,
                response=ctx.generated_response or "",
                sources=[
                    {"cv_id": c.get("metadata", {}).get("cv_id")}
                    for c in ctx.effective_chunks
                ],
                metrics=ctx.metrics.to_dict(),
                guardrail_passed=ctx.guardrail_passed,
                session_id=ctx.session_id,
                mode=self.config.mode.value
            )
        except Exception as e:
            logger.warning(f"Failed to log query: {e}")
    
    async def get_stats(self) -> dict[str, Any]:
        """Get service statistics."""
        stats = {
            "version": "5.0.0",
            "mode": self.config.mode.value,
            "features": {
                "multi_query": self.config.multi_query_enabled,
                "hyde": self.config.hyde_enabled,
                "reasoning": self.config.reasoning_enabled,
                "claim_verification": self.config.claim_verification_enabled,
                "refinement": self.config.iterative_refinement_enabled
            }
        }
        
        if self._embedding_cache:
            stats["embedding_cache"] = self._embedding_cache.stats()
        if self._response_cache:
            stats["response_cache"] = self._response_cache.stats()
        
        return stats
    
    async def clear_caches(self) -> None:
        """Clear all caches."""
        if self._embedding_cache:
            await self._embedding_cache.clear()
        if self._response_cache:
            await self._response_cache.clear()
        logger.info("Caches cleared")
    
    # =========================================================================
    # BACKWARD COMPATIBILITY PROPERTIES
    # =========================================================================
    
    @property
    def vector_store(self):
        """Access to vector store for backward compatibility."""
        return self._vector_store
    
    async def index_documents(self, chunks: List[Dict[str, Any]]) -> None:
        """
        Index documents into the vector store.
        
        This method provides backward compatibility with older code.
        
        Args:
            chunks: List of chunk dictionaries with 'content' and 'metadata'
        """
        if not self._providers_initialized:
            raise RAGError("Providers not initialized")
        
        # Extract texts for embedding
        texts = [chunk.get("content", "") for chunk in chunks]
        
        if not texts:
            return
        
        # Generate embeddings
        result = await self._embedder.embed_texts(texts)
        
        # Add to vector store
        await self._vector_store.add_documents(chunks, result.embeddings)
        
        logger.info(f"Indexed {len(chunks)} chunks")


# =============================================================================
# BACKWARD COMPATIBILITY
# =============================================================================

class RAGServiceV3:
    """Backward compatibility wrapper."""
    
    def __init__(
        self,
        mode: Mode = Mode.LOCAL,
        understanding_model: str | None = None,
        reranking_model: str | None = None,
        generation_model: str | None = None,
        verification_model: str | None = None,
        reranking_enabled: bool = True,
        verification_enabled: bool = True
    ):
        config = RAGConfigV5(
            mode=mode,
            reranking_enabled=reranking_enabled,
            verification_enabled=verification_enabled
        )
        self._service = RAGServiceV5.from_factory(mode)
    
    async def query(self, *args, **kwargs):
        return await self._service.query(*args, **kwargs)


def create_rag_service(mode: Mode = Mode.LOCAL) -> RAGServiceV5:
    """Create a RAG service instance."""
    return RAGServiceV5.from_factory(mode)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Main service
    "RAGServiceV5",
    "RAGServiceV3",
    "create_rag_service",
    
    # Configuration
    "RAGConfigV5",
    "RetryConfig",
    "CacheConfig",
    "CircuitBreakerConfig",
    "Mode",
    
    # Results
    "RAGResponseV5",
    "QueryUnderstandingV5",
    "RetrievalResultV5",
    "VerificationResultV5",
    "PipelineMetrics",
    "StageMetrics",
    
    # Pipeline
    "PipelineContextV5",
    "PipelineStage",
    
    # Errors
    "RAGError",
    "GuardrailError",
    "RetrievalError",
    "GenerationError",
    
    # Utilities
    "CircuitBreaker",
    "LRUCache",
]
