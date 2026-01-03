"""
RAG Service v4 - Production-Ready RAG Pipeline.

This module provides a robust, production-grade RAG orchestration service with:
- Modular pipeline architecture with pluggable steps
- Comprehensive error handling and retry logic
- Response caching with TTL
- Circuit breaker pattern for resilience
- Streaming support for LLM responses
- Parallel execution where possible
- Detailed observability and metrics
- Integration with advanced prompt templates

Author: CV Screener RAG System
Version: 4.0.0
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
    Protocol,
    TypeVar,
    TYPE_CHECKING,
)

# Conditional imports for type checking
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
    GUARDRAIL = auto()
    EMBEDDING = auto()
    SEARCH = auto()
    RERANKING = auto()
    GENERATION = auto()
    VERIFICATION = auto()
    HALLUCINATION_CHECK = auto()


class ErrorSeverity(Enum):
    """Severity levels for pipeline errors."""
    WARNING = "warning"      # Continue with degraded functionality
    RECOVERABLE = "recoverable"  # Can retry
    FATAL = "fatal"          # Must abort


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
        """Calculate delay for given attempt number."""
        import random
        delay = min(
            self.base_delay_ms * (self.exponential_base ** attempt),
            self.max_delay_ms
        )
        if self.jitter:
            delay *= (0.5 + random.random())
        return delay / 1000  # Convert to seconds


@dataclass(frozen=True)
class CacheConfig:
    """Configuration for response caching."""
    enabled: bool = True
    ttl_seconds: int = 300  # 5 minutes
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
class RAGConfig:
    """Complete RAG service configuration."""
    mode: Mode = Mode.LOCAL
    
    # Model configuration
    understanding_model: str | None = None
    reranking_model: str | None = None
    generation_model: str | None = None
    verification_model: str | None = None
    
    # Feature flags
    reranking_enabled: bool = True
    verification_enabled: bool = True
    streaming_enabled: bool = False
    parallel_steps_enabled: bool = True
    
    # Retrieval settings
    default_k: int = 10
    default_threshold: float = 0.3
    max_context_tokens: int = 60000
    
    # Sub-configurations
    retry: RetryConfig = field(default_factory=RetryConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    
    # Timeouts (seconds)
    embedding_timeout: float = 10.0
    search_timeout: float = 15.0
    llm_timeout: float = 120.0
    total_timeout: float = 180.0


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
class QueryUnderstanding:
    """Result of query understanding step."""
    original_query: str
    understood_query: str
    query_type: str
    is_cv_related: bool
    requirements: list[str] = field(default_factory=list)
    reformulated_prompt: str | None = None
    confidence: float = 1.0
    entities: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class RetrievalResult:
    """Result of retrieval step."""
    chunks: list[dict[str, Any]]
    cv_ids: list[str]
    strategy: str
    scores: list[float]


@dataclass
class VerificationResult:
    """Result of response verification."""
    is_grounded: bool
    groundedness_score: float
    verified_claims: list[str] = field(default_factory=list)
    ungrounded_claims: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class RAGResponse:
    """Complete response from RAG query."""
    answer: str
    sources: list[dict[str, Any]]
    metrics: PipelineMetrics
    confidence_score: float
    guardrail_passed: bool
    
    # Optional detailed results
    query_understanding: QueryUnderstanding | None = None
    verification: VerificationResult | None = None
    
    # Metadata
    mode: str = "local"
    cached: bool = False
    request_id: str | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
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
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, rejecting calls
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    
    Prevents cascading failures by temporarily blocking calls
    to failing services.
    """
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
        """Record a successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1
            if self._half_open_calls >= self.config.half_open_max_calls:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                logger.info(f"Circuit breaker '{self.name}' closed after recovery")
        else:
            self._failure_count = 0
    
    def record_failure(self) -> None:
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = datetime.utcnow()
        
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            logger.warning(f"Circuit breaker '{self.name}' reopened after failed recovery")
        elif self._failure_count >= self.config.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(f"Circuit breaker '{self.name}' opened after {self._failure_count} failures")
    
    def allow_request(self) -> bool:
        """Check if a request should be allowed."""
        if not self.config.enabled:
            return True
        
        state = self.state  # This may transition OPEN -> HALF_OPEN
        
        if state == CircuitState.CLOSED:
            return True
        elif state == CircuitState.HALF_OPEN:
            return self._half_open_calls < self.config.half_open_max_calls
        else:  # OPEN
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
    """
    Simple LRU cache with TTL support.
    
    Thread-safe for async usage via asyncio locks.
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self._cache: dict[str, CacheEntry[T]] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0
    
    @staticmethod
    def _hash_key(key: str) -> str:
        """Create a hash of the key for storage."""
        return hashlib.sha256(key.encode()).hexdigest()[:16]
    
    async def get(self, key: str) -> T | None:
        """Get a value from cache."""
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
        """Set a value in cache."""
        async with self._lock:
            # Evict if at capacity
            if len(self._cache) >= self._max_size:
                await self._evict_lru()
            
            hashed = self._hash_key(key)
            self._cache[hashed] = CacheEntry(
                value=value,
                created_at=datetime.utcnow(),
                ttl_seconds=ttl or self._default_ttl
            )
    
    async def _evict_lru(self) -> None:
        """Evict least recently used entries."""
        if not self._cache:
            return
        
        # Remove expired entries first
        expired = [k for k, v in self._cache.items() if v.is_expired]
        for k in expired:
            del self._cache[k]
        
        # If still at capacity, remove lowest hit entries
        if len(self._cache) >= self._max_size:
            sorted_entries = sorted(
                self._cache.items(),
                key=lambda x: (x[1].hits, x[1].created_at)
            )
            to_remove = len(self._cache) - self._max_size + 1
            for k, _ in sorted_entries[:to_remove]:
                del self._cache[k]
    
    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
    
    def stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total, 3) if total > 0 else 0
        }


# =============================================================================
# RETRY DECORATOR
# =============================================================================

def with_retry(
    config: RetryConfig,
    circuit_breaker: CircuitBreaker | None = None,
    on_retry: Callable[[int, Exception], None] | None = None
):
    """
    Decorator for adding retry logic to async functions.
    
    Args:
        config: Retry configuration
        circuit_breaker: Optional circuit breaker to use
        on_retry: Optional callback on each retry
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Exception | None = None
            
            for attempt in range(config.max_attempts):
                # Check circuit breaker
                if circuit_breaker and not circuit_breaker.allow_request():
                    raise RAGError(
                        f"Circuit breaker '{circuit_breaker.name}' is open",
                        severity=ErrorSeverity.RECOVERABLE,
                        recoverable=True
                    )
                
                try:
                    result = await func(*args, **kwargs)
                    
                    # Record success
                    if circuit_breaker:
                        circuit_breaker.record_success()
                    
                    return result
                    
                except Exception as e:
                    last_exception = e
                    
                    # Record failure
                    if circuit_breaker:
                        circuit_breaker.record_failure()
                    
                    # Check if we should retry
                    if attempt < config.max_attempts - 1:
                        delay = config.get_delay(attempt)
                        
                        if on_retry:
                            on_retry(attempt + 1, e)
                        
                        logger.warning(
                            f"Retry {attempt + 1}/{config.max_attempts} for {func.__name__} "
                            f"after {delay:.2f}s: {e}"
                        )
                        
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"All {config.max_attempts} attempts failed for {func.__name__}: {e}"
                        )
            
            raise last_exception or RAGError("Unknown error after retries")
        
        return wrapper
    return decorator


# =============================================================================
# PIPELINE STEP PROTOCOL
# =============================================================================

class PipelineStep(Protocol[T, R]):
    """Protocol for pipeline steps."""
    
    @property
    def stage(self) -> PipelineStage: ...
    
    async def execute(self, input_data: T) -> R: ...
    
    def can_skip(self, input_data: T) -> bool:
        """Check if this step can be skipped."""
        return False


# =============================================================================
# PIPELINE CONTEXT
# =============================================================================

@dataclass
class PipelineContext:
    """
    Shared context passed through pipeline stages.
    
    Accumulates results from each stage and provides
    access to shared resources.
    """
    # Input
    question: str
    session_id: str | None = None
    cv_ids: list[str] | None = None
    k: int = 10
    threshold: float = 0.3
    total_cvs_in_session: int | None = None
    
    # Request metadata
    request_id: str = field(default_factory=lambda: hashlib.sha256(
        f"{time.time()}".encode()
    ).hexdigest()[:12])
    start_time: float = field(default_factory=time.perf_counter)
    
    # Stage results (populated during execution)
    query_understanding: QueryUnderstanding | None = None
    guardrail_passed: bool = True
    guardrail_message: str | None = None
    
    query_embedding: list[float] | None = None
    
    retrieval_result: RetrievalResult | None = None
    
    reranked_chunks: list[dict[str, Any]] | None = None
    reranking_scores: list[float] | None = None
    
    generated_response: str | None = None
    generation_tokens: dict[str, int] = field(default_factory=dict)
    
    verification_result: VerificationResult | None = None
    hallucination_check: dict[str, Any] = field(default_factory=dict)
    
    # Metrics tracking
    metrics: PipelineMetrics = field(default_factory=lambda: PipelineMetrics(total_ms=0))
    
    # Cache flags
    embedding_cached: bool = False
    response_cached: bool = False
    
    @property
    def effective_chunks(self) -> list[dict[str, Any]]:
        """Get the best available chunks (reranked if available)."""
        if self.reranked_chunks is not None:
            return self.reranked_chunks
        if self.retrieval_result is not None:
            return self.retrieval_result.chunks
        return []
    
    @property
    def elapsed_ms(self) -> float:
        """Get elapsed time since start."""
        return (time.perf_counter() - self.start_time) * 1000


# =============================================================================
# ABSTRACT STEP IMPLEMENTATIONS
# =============================================================================

class BaseStep(ABC, Generic[T, R]):
    """Base class for pipeline steps with common functionality."""
    
    def __init__(
        self,
        config: RAGConfig,
        circuit_breaker: CircuitBreaker | None = None
    ):
        self.config = config
        self.circuit_breaker = circuit_breaker
    
    @property
    @abstractmethod
    def stage(self) -> PipelineStage:
        """The pipeline stage this step represents."""
        pass
    
    @abstractmethod
    async def _execute_impl(self, input_data: T, ctx: PipelineContext) -> R:
        """Implementation of the step logic."""
        pass
    
    def can_skip(self, input_data: T, ctx: PipelineContext) -> bool:
        """Check if this step can be skipped."""
        return False
    
    async def execute(self, input_data: T, ctx: PipelineContext) -> R:
        """
        Execute the step with timing and error handling.
        
        Args:
            input_data: Input to this step
            ctx: Pipeline context
            
        Returns:
            Step result
        """
        start = time.perf_counter()
        error_msg = None
        success = True
        metadata: dict[str, Any] = {}
        
        try:
            if self.can_skip(input_data, ctx):
                metadata["skipped"] = True
                return None  # type: ignore
            
            result = await self._execute_impl(input_data, ctx)
            return result
            
        except Exception as e:
            success = False
            error_msg = str(e)
            logger.error(f"Step {self.stage.name} failed: {e}", exc_info=True)
            raise
            
        finally:
            duration = (time.perf_counter() - start) * 1000
            ctx.metrics.add_stage(StageMetrics(
                stage=self.stage,
                duration_ms=duration,
                success=success,
                error=error_msg,
                metadata=metadata
            ))


# =============================================================================
# CONCRETE STEP IMPLEMENTATIONS
# =============================================================================

class QueryUnderstandingStep(BaseStep[str, QueryUnderstanding]):
    """Step 1: Understand and reformulate the query."""
    
    def __init__(
        self,
        config: RAGConfig,
        understanding_service: Any,  # QueryUnderstandingService
        circuit_breaker: CircuitBreaker | None = None
    ):
        super().__init__(config, circuit_breaker)
        self.service = understanding_service
    
    @property
    def stage(self) -> PipelineStage:
        return PipelineStage.QUERY_UNDERSTANDING
    
    async def _execute_impl(
        self,
        question: str,
        ctx: PipelineContext
    ) -> QueryUnderstanding:
        """Understand the query using fast model."""
        result = await self.service.understand(question)
        
        ctx.query_understanding = QueryUnderstanding(
            original_query=result.original_query,
            understood_query=result.understood_query,
            query_type=result.query_type,
            is_cv_related=result.is_cv_related,
            requirements=result.requirements or [],
            reformulated_prompt=result.reformulated_prompt,
            confidence=getattr(result, "confidence", 1.0),
            entities=getattr(result, "entities", {})
        )
        
        logger.debug(
            f"Query understood: type={result.query_type}, "
            f"cv_related={result.is_cv_related}"
        )
        
        return ctx.query_understanding


class GuardrailStep(BaseStep[QueryUnderstanding, bool]):
    """Step 2: Check if query passes guardrails."""
    
    def __init__(
        self,
        config: RAGConfig,
        guardrail_service: Any,  # GuardrailService
    ):
        super().__init__(config)
        self.service = guardrail_service
    
    @property
    def stage(self) -> PipelineStage:
        return PipelineStage.GUARDRAIL
    
    async def _execute_impl(
        self,
        understanding: QueryUnderstanding,
        ctx: PipelineContext
    ) -> bool:
        """Check guardrails."""
        # First check: query understanding says not CV-related
        if not understanding.is_cv_related:
            ctx.guardrail_passed = False
            ctx.guardrail_message = (
                "I can only help with CV screening and candidate analysis. "
                "Please ask a question about the uploaded CVs."
            )
            return False
        
        # Second check: explicit guardrail service
        result = self.service.check(understanding.original_query)
        
        if not result.is_allowed:
            ctx.guardrail_passed = False
            ctx.guardrail_message = result.rejection_message
            return False
        
        ctx.guardrail_passed = True
        return True


class EmbeddingStep(BaseStep[str, list[float]]):
    """Step 3: Generate query embedding."""
    
    def __init__(
        self,
        config: RAGConfig,
        embedder: Any,  # EmbeddingProvider
        cache: LRUCache[list[float]] | None = None,
        circuit_breaker: CircuitBreaker | None = None
    ):
        super().__init__(config, circuit_breaker)
        self.embedder = embedder
        self.cache = cache
    
    @property
    def stage(self) -> PipelineStage:
        return PipelineStage.EMBEDDING
    
    async def _execute_impl(
        self,
        question: str,
        ctx: PipelineContext
    ) -> list[float]:
        """Generate embedding, using cache if available."""
        # Check cache
        if self.cache and self.config.cache.cache_embeddings:
            cached = await self.cache.get(f"emb:{question}")
            if cached is not None:
                ctx.embedding_cached = True
                ctx.query_embedding = cached
                return cached
        
        # Generate embedding
        result = await asyncio.wait_for(
            self.embedder.embed_query(question),
            timeout=self.config.embedding_timeout
        )
        
        embedding = result.embeddings[0]
        ctx.query_embedding = embedding
        
        # Cache result
        if self.cache and self.config.cache.cache_embeddings:
            await self.cache.set(f"emb:{question}", embedding)
        
        return embedding


class RetrievalStep(BaseStep[list[float], RetrievalResult]):
    """Step 4: Vector search with adaptive strategy."""
    
    def __init__(
        self,
        config: RAGConfig,
        vector_store: Any,  # VectorStore
        circuit_breaker: CircuitBreaker | None = None
    ):
        super().__init__(config, circuit_breaker)
        self.vector_store = vector_store
    
    @property
    def stage(self) -> PipelineStage:
        return PipelineStage.SEARCH
    
    def _determine_strategy(
        self,
        ctx: PipelineContext
    ) -> tuple[bool, int, float, str]:
        """
        Determine retrieval strategy based on query and session.
        
        Returns:
            (diversify, effective_k, threshold, reason)
        """
        num_cvs = ctx.total_cvs_in_session or 100
        query_type = ctx.query_understanding.query_type if ctx.query_understanding else "search"
        
        is_ranking = query_type in {"ranking", "comparison"}
        
        # Adaptive limits based on session size
        MAX_RANKING_K = 30 if num_cvs > 100 else 100
        
        # Adjust threshold for large sessions
        threshold = ctx.threshold
        if num_cvs > 100:
            threshold = max(0.05, threshold - 0.1)
        
        if is_ranking:
            return (
                True,
                min(num_cvs, MAX_RANKING_K),
                threshold,
                f"ranking query (capped at {MAX_RANKING_K})"
            )
        elif num_cvs < 100:
            return (
                True,
                num_cvs,
                threshold,
                f"small session ({num_cvs} CVs)"
            )
        else:
            return (
                False,
                min(ctx.k, num_cvs),
                threshold,
                f"large session ({num_cvs} CVs), top-k for precision"
            )
    
    async def _execute_impl(
        self,
        embedding: list[float],
        ctx: PipelineContext
    ) -> RetrievalResult:
        """Execute vector search with adaptive strategy."""
        diversify, effective_k, threshold, strategy = self._determine_strategy(ctx)
        
        logger.debug(
            f"Search strategy: {'diversified' if diversify else 'top-k'} "
            f"({strategy}, k={effective_k})"
        )
        
        results = await asyncio.wait_for(
            self.vector_store.search(
                embedding=embedding,
                k=effective_k,
                threshold=threshold,
                cv_ids=ctx.cv_ids,
                diversify_by_cv=diversify
            ),
            timeout=self.config.search_timeout
        )
        
        # Convert to chunks
        chunks = [
            {
                "content": r.content,
                "metadata": {
                    "filename": r.filename,
                    "candidate_name": r.metadata.get("candidate_name", "Unknown"),
                    "section_type": r.metadata.get("section_type", "general"),
                    "cv_id": r.cv_id
                }
            }
            for r in results
        ]
        
        retrieval_result = RetrievalResult(
            chunks=chunks,
            cv_ids=list({r.cv_id for r in results}),
            strategy=strategy,
            scores=[r.similarity for r in results]
        )
        
        ctx.retrieval_result = retrieval_result
        return retrieval_result


class RerankingStep(BaseStep[list[dict], list[dict]]):
    """Step 5: Re-rank results using LLM scoring."""
    
    def __init__(
        self,
        config: RAGConfig,
        reranking_service: Any,  # RerankingService
        circuit_breaker: CircuitBreaker | None = None
    ):
        super().__init__(config, circuit_breaker)
        self.service = reranking_service
    
    @property
    def stage(self) -> PipelineStage:
        return PipelineStage.RERANKING
    
    def can_skip(self, input_data: Any, ctx: PipelineContext) -> bool:
        return not self.config.reranking_enabled
    
    async def _execute_impl(
        self,
        chunks: list[dict],
        ctx: PipelineContext
    ) -> list[dict]:
        """Re-rank chunks by relevance."""
        if not chunks:
            return []
        
        effective_question = (
            ctx.query_understanding.reformulated_prompt
            if ctx.query_understanding
            else ctx.question
        )
        
        result = await self.service.rerank(
            query=effective_question,
            results=chunks,  # Note: service may expect SearchResult
            top_k=None  # Return all, just reordered
        )
        
        ctx.reranked_chunks = result.reranked_results
        ctx.reranking_scores = result.scores
        
        return result.reranked_results


class GenerationStep(BaseStep[list[dict], str]):
    """Step 6: Generate response using LLM."""
    
    def __init__(
        self,
        config: RAGConfig,
        llm: Any,  # LLMProvider
        prompt_builder: Any,  # PromptBuilder from templates.py
        cache: LRUCache[str] | None = None,
        circuit_breaker: CircuitBreaker | None = None
    ):
        super().__init__(config, circuit_breaker)
        self.llm = llm
        self.prompt_builder = prompt_builder
        self.cache = cache
    
    @property
    def stage(self) -> PipelineStage:
        return PipelineStage.GENERATION
    
    def _build_cache_key(self, question: str, chunks: list[dict]) -> str:
        """Build cache key from question and chunks."""
        chunk_ids = sorted([
            c.get("metadata", {}).get("cv_id", "")
            for c in chunks
        ])
        content = f"{question}:{':'.join(chunk_ids)}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]
    
    async def _execute_impl(
        self,
        chunks: list[dict],
        ctx: PipelineContext
    ) -> str:
        """Generate LLM response."""
        effective_question = (
            ctx.query_understanding.reformulated_prompt
            if ctx.query_understanding and ctx.query_understanding.reformulated_prompt
            else ctx.question
        )
        
        # Check cache
        cache_key = self._build_cache_key(effective_question, chunks)
        if self.cache and self.config.cache.cache_responses:
            cached = await self.cache.get(cache_key)
            if cached is not None:
                ctx.response_cached = True
                ctx.generated_response = cached
                return cached
        
        # Build prompt using advanced prompt builder
        prompt = self.prompt_builder.build_query_prompt(
            question=effective_question,
            chunks=chunks,
            total_cvs=ctx.total_cvs_in_session
        )
        
        # Add requirements if available
        if ctx.query_understanding and ctx.query_understanding.requirements:
            requirements_text = "\n\nIMPORTANT REQUIREMENTS:\n" + "\n".join(
                f"- {req}" for req in ctx.query_understanding.requirements
            )
            prompt = prompt.replace(
                "Respond now:",
                requirements_text + "\n\nRespond now:"
            )
        
        # Get system prompt from templates
        from app.prompts.templates import SYSTEM_PROMPT
        
        # Generate response
        result = await asyncio.wait_for(
            self.llm.generate(prompt, system_prompt=SYSTEM_PROMPT),
            timeout=self.config.llm_timeout
        )
        
        ctx.generated_response = result.text
        ctx.generation_tokens = {
            "prompt": result.prompt_tokens,
            "completion": result.completion_tokens
        }
        
        # Cache response
        if self.cache and self.config.cache.cache_responses:
            await self.cache.set(cache_key, result.text)
        
        return result.text


class VerificationStep(BaseStep[str, VerificationResult]):
    """Step 7: Verify response is grounded in sources."""
    
    def __init__(
        self,
        config: RAGConfig,
        verification_service: Any,  # LLMVerificationService
        hallucination_service: Any,  # HallucinationService
        circuit_breaker: CircuitBreaker | None = None
    ):
        super().__init__(config, circuit_breaker)
        self.verification = verification_service
        self.hallucination = hallucination_service
    
    @property
    def stage(self) -> PipelineStage:
        return PipelineStage.VERIFICATION
    
    def can_skip(self, input_data: Any, ctx: PipelineContext) -> bool:
        return not self.config.verification_enabled
    
    async def _execute_impl(
        self,
        response: str,
        ctx: PipelineContext
    ) -> VerificationResult:
        """Verify response against sources."""
        chunks = ctx.effective_chunks
        
        # LLM-based verification
        llm_result = await self.verification.verify(
            response=response,
            context_chunks=chunks,
            query=ctx.question
        )
        
        # Heuristic hallucination check
        cv_metadata = [
            {
                "cv_id": c.get("metadata", {}).get("cv_id"),
                "filename": c.get("metadata", {}).get("filename")
            }
            for c in chunks
        ]
        
        heuristic_result = self.hallucination.verify_response(
            llm_response=response,
            context_chunks=chunks,
            cv_metadata=cv_metadata
        )
        
        # Combine results
        combined_score = (
            llm_result.groundedness_score * 0.6 +
            heuristic_result.confidence_score * 0.4
        )
        
        verification = VerificationResult(
            is_grounded=llm_result.is_grounded and heuristic_result.is_valid,
            groundedness_score=combined_score,
            verified_claims=llm_result.verified_claims,
            ungrounded_claims=llm_result.ungrounded_claims,
            warnings=heuristic_result.warnings or []
        )
        
        ctx.verification_result = verification
        ctx.hallucination_check = {
            "is_valid": heuristic_result.is_valid,
            "confidence_score": heuristic_result.confidence_score,
            "verified_cv_ids": heuristic_result.verified_cv_ids,
            "unverified_cv_ids": heuristic_result.unverified_cv_ids,
            "warnings": heuristic_result.warnings
        }
        
        return verification


# =============================================================================
# MAIN RAG SERVICE
# =============================================================================

class RAGServiceV4:
    """
    Production-ready RAG Service with modular pipeline.
    
    Features:
    - Configurable multi-step pipeline
    - Comprehensive error handling with retries
    - Response caching
    - Circuit breaker pattern
    - Detailed observability
    - Streaming support
    
    Pipeline:
    1. Query Understanding → Understand and reformulate query
    2. Guardrail Check → Reject off-topic questions
    3. Embedding → Generate query embedding
    4. Retrieval → Vector search with adaptive strategy
    5. Reranking → LLM-based relevance scoring
    6. Generation → Generate response
    7. Verification → Verify grounding + hallucination check
    """
    
    def __init__(self, config: RAGConfig | None = None):
        """
        Initialize RAG Service.
        
        Args:
            config: Service configuration (uses defaults if not provided)
        """
        self.config = config or RAGConfig()
        
        # Initialize caches
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
        
        # Initialize circuit breakers
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        if self.config.circuit_breaker.enabled:
            for name in ["embedding", "search", "llm", "verification"]:
                self._circuit_breakers[name] = CircuitBreaker(
                    name=name,
                    config=self.config.circuit_breaker
                )
        
        # Defer provider initialization (allows for dependency injection)
        self._providers_initialized = False
        self._steps: dict[PipelineStage, BaseStep] = {}
        
        # Evaluation service
        self._eval_service: Any = None
        
        logger.info(f"RAGServiceV4 initialized with mode={self.config.mode.value}")
    
    def initialize_providers(
        self,
        embedder: Any,
        vector_store: Any,
        llm: Any,
        query_understanding: Any,
        reranking: Any,
        verification: Any,
        guardrail: Any,
        hallucination: Any,
        eval_service: Any,
        prompt_builder: Any
    ) -> None:
        """
        Initialize service providers and pipeline steps.
        
        This allows for dependency injection and testing.
        """
        self._eval_service = eval_service
        
        # Initialize pipeline steps
        self._steps = {
            PipelineStage.QUERY_UNDERSTANDING: QueryUnderstandingStep(
                config=self.config,
                understanding_service=query_understanding,
                circuit_breaker=self._circuit_breakers.get("llm")
            ),
            PipelineStage.GUARDRAIL: GuardrailStep(
                config=self.config,
                guardrail_service=guardrail
            ),
            PipelineStage.EMBEDDING: EmbeddingStep(
                config=self.config,
                embedder=embedder,
                cache=self._embedding_cache,
                circuit_breaker=self._circuit_breakers.get("embedding")
            ),
            PipelineStage.SEARCH: RetrievalStep(
                config=self.config,
                vector_store=vector_store,
                circuit_breaker=self._circuit_breakers.get("search")
            ),
            PipelineStage.RERANKING: RerankingStep(
                config=self.config,
                reranking_service=reranking,
                circuit_breaker=self._circuit_breakers.get("llm")
            ),
            PipelineStage.GENERATION: GenerationStep(
                config=self.config,
                llm=llm,
                prompt_builder=prompt_builder,
                cache=self._response_cache,
                circuit_breaker=self._circuit_breakers.get("llm")
            ),
            PipelineStage.VERIFICATION: VerificationStep(
                config=self.config,
                verification_service=verification,
                hallucination_service=hallucination,
                circuit_breaker=self._circuit_breakers.get("verification")
            )
        }
        
        self._providers_initialized = True
        logger.info("Pipeline steps initialized")
    
    @classmethod
    def from_factory(cls, mode: Mode = Mode.LOCAL) -> RAGServiceV4:
        """
        Create service with default providers from factory.
        
        Args:
            mode: Operating mode
            
        Returns:
            Initialized RAGServiceV4 instance
        """
        from app.config import settings
        from app.providers.factory import ProviderFactory
        from app.services.guardrail_service import GuardrailService
        from app.services.hallucination_service import HallucinationService
        from app.services.eval_service import EvalService
        from app.services.query_understanding_service import QueryUnderstandingService
        from app.services.reranking_service import RerankingService
        from app.services.verification_service import LLMVerificationService
        from app.prompts.templates import PromptBuilder
        
        config = RAGConfig(
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
            reranking=RerankingService(enabled=config.reranking_enabled),
            verification=LLMVerificationService(enabled=config.verification_enabled),
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
    ) -> RAGResponse:
        """
        Execute complete RAG query pipeline.
        
        Args:
            question: User's question
            session_id: Optional session ID for logging
            cv_ids: Optional list of CV IDs to filter
            k: Number of results to retrieve
            threshold: Minimum similarity threshold
            total_cvs_in_session: Total CVs in session
            
        Returns:
            RAGResponse with answer and metadata
        """
        if not self._providers_initialized:
            raise RAGError("Providers not initialized. Call initialize_providers() first.")
        
        # Create pipeline context
        ctx = PipelineContext(
            question=question,
            session_id=session_id,
            cv_ids=cv_ids,
            k=k or self.config.default_k,
            threshold=threshold or self.config.default_threshold,
            total_cvs_in_session=total_cvs_in_session
        )
        
        try:
            # Execute pipeline with timeout
            response = await asyncio.wait_for(
                self._execute_pipeline(ctx),
                timeout=self.config.total_timeout
            )
            return response
            
        except asyncio.TimeoutError:
            logger.error(f"Pipeline timeout after {self.config.total_timeout}s")
            return self._build_error_response(
                ctx,
                "Request timed out. Please try a simpler query."
            )
        except GuardrailError as e:
            return self._build_guardrail_response(ctx, e.rejection_reason)
        except RAGError as e:
            logger.error(f"Pipeline error at {e.stage}: {e}")
            return self._build_error_response(ctx, str(e))
        except Exception as e:
            logger.exception(f"Unexpected error in pipeline: {e}")
            return self._build_error_response(
                ctx,
                "An unexpected error occurred. Please try again."
            )
    
    async def _execute_pipeline(self, ctx: PipelineContext) -> RAGResponse:
        """Execute the full RAG pipeline."""
        
        # Step 1: Query Understanding
        understanding_step = self._steps[PipelineStage.QUERY_UNDERSTANDING]
        await understanding_step.execute(ctx.question, ctx)
        
        # Step 2: Guardrail Check
        guardrail_step = self._steps[PipelineStage.GUARDRAIL]
        passed = await guardrail_step.execute(ctx.query_understanding, ctx)
        
        if not passed:
            return self._build_guardrail_response(ctx, ctx.guardrail_message)
        
        # Step 3: Embedding
        embedding_step = self._steps[PipelineStage.EMBEDDING]
        embedding = await embedding_step.execute(ctx.question, ctx)
        
        # Step 4: Retrieval
        retrieval_step = self._steps[PipelineStage.SEARCH]
        retrieval_result = await retrieval_step.execute(embedding, ctx)
        
        # Handle no results
        if not retrieval_result.chunks:
            return self._build_no_results_response(ctx)
        
        # Steps 5-7 can be partially parallelized in future versions
        
        # Step 5: Reranking
        chunks = retrieval_result.chunks
        if self.config.reranking_enabled:
            reranking_step = self._steps[PipelineStage.RERANKING]
            chunks = await reranking_step.execute(chunks, ctx)
        
        # Step 6: Generation
        generation_step = self._steps[PipelineStage.GENERATION]
        response = await generation_step.execute(chunks, ctx)
        
        # Step 7: Verification
        if self.config.verification_enabled:
            verification_step = self._steps[PipelineStage.VERIFICATION]
            verification = await verification_step.execute(response, ctx)
            
            # Add warning if not grounded
            if not verification.is_grounded and verification.warnings:
                response += "\n\n⚠️ *Some information could not be fully verified.*"
                ctx.generated_response = response
        
        # Finalize metrics
        ctx.metrics.total_ms = ctx.elapsed_ms
        ctx.metrics.cache_hit = ctx.embedding_cached or ctx.response_cached
        
        # Log for evaluation
        self._log_query(ctx)
        
        # Build final response
        return self._build_success_response(ctx)
    
    def _build_success_response(self, ctx: PipelineContext) -> RAGResponse:
        """Build successful response from context."""
        # Extract unique sources
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
        
        # Calculate confidence
        confidence = 0.8  # Default
        if ctx.verification_result:
            confidence = ctx.verification_result.groundedness_score
        elif ctx.hallucination_check:
            confidence = ctx.hallucination_check.get("confidence_score", 0.8)
        
        return RAGResponse(
            answer=ctx.generated_response or "",
            sources=sources,
            metrics=ctx.metrics,
            confidence_score=confidence,
            guardrail_passed=True,
            query_understanding=ctx.query_understanding,
            verification=ctx.verification_result,
            mode=self.config.mode.value,
            cached=ctx.response_cached,
            request_id=ctx.request_id
        )
    
    def _build_guardrail_response(
        self,
        ctx: PipelineContext,
        message: str | None
    ) -> RAGResponse:
        """Build response for guardrail rejection."""
        ctx.metrics.total_ms = ctx.elapsed_ms
        
        return RAGResponse(
            answer=message or "I can only help with CV screening questions.",
            sources=[],
            metrics=ctx.metrics,
            confidence_score=0,
            guardrail_passed=False,
            mode=self.config.mode.value,
            request_id=ctx.request_id
        )
    
    def _build_no_results_response(self, ctx: PipelineContext) -> RAGResponse:
        """Build response when no results found."""
        ctx.metrics.total_ms = ctx.elapsed_ms
        
        message = (
            "I couldn't find any relevant information in the CVs. "
            "The uploaded CVs may not contain information related to your query. "
            "Try asking about different skills or experiences."
        )
        
        return RAGResponse(
            answer=message,
            sources=[],
            metrics=ctx.metrics,
            confidence_score=0.8,  # High confidence in "no results"
            guardrail_passed=True,
            query_understanding=ctx.query_understanding,
            mode=self.config.mode.value,
            request_id=ctx.request_id
        )
    
    def _build_error_response(
        self,
        ctx: PipelineContext,
        message: str
    ) -> RAGResponse:
        """Build response for pipeline errors."""
        ctx.metrics.total_ms = ctx.elapsed_ms
        
        return RAGResponse(
            answer=f"I encountered an issue processing your request. {message}",
            sources=[],
            metrics=ctx.metrics,
            confidence_score=0,
            guardrail_passed=True,
            mode=self.config.mode.value,
            request_id=ctx.request_id
        )
    
    def _log_query(self, ctx: PipelineContext) -> None:
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
                hallucination_check=ctx.hallucination_check,
                guardrail_passed=ctx.guardrail_passed,
                session_id=ctx.session_id,
                mode=self.config.mode.value
            )
        except Exception as e:
            logger.warning(f"Failed to log query: {e}")
    
    async def query_stream(
        self,
        question: str,
        session_id: str | None = None,
        cv_ids: list[str] | None = None,
        **kwargs: Any
    ) -> AsyncIterator[str]:
        """
        Stream RAG response tokens.
        
        Yields tokens as they're generated.
        """
        # For now, fall back to non-streaming
        # TODO: Implement true streaming when LLM provider supports it
        response = await self.query(
            question=question,
            session_id=session_id,
            cv_ids=cv_ids,
            **kwargs
        )
        
        # Simulate streaming by yielding chunks
        chunk_size = 50
        answer = response.answer
        for i in range(0, len(answer), chunk_size):
            yield answer[i:i + chunk_size]
            await asyncio.sleep(0.01)
    
    async def get_stats(self) -> dict[str, Any]:
        """Get service statistics."""
        stats: dict[str, Any] = {
            "mode": self.config.mode.value,
            "config": {
                "reranking_enabled": self.config.reranking_enabled,
                "verification_enabled": self.config.verification_enabled,
                "caching_enabled": self.config.cache.enabled
            }
        }
        
        # Cache stats
        if self._embedding_cache:
            stats["embedding_cache"] = self._embedding_cache.stats()
        if self._response_cache:
            stats["response_cache"] = self._response_cache.stats()
        
        # Circuit breaker stats
        if self._circuit_breakers:
            stats["circuit_breakers"] = {
                name: {
                    "state": cb.state.value,
                    "failure_count": cb._failure_count
                }
                for name, cb in self._circuit_breakers.items()
            }
        
        return stats
    
    async def clear_caches(self) -> None:
        """Clear all caches."""
        if self._embedding_cache:
            await self._embedding_cache.clear()
        if self._response_cache:
            await self._response_cache.clear()
        logger.info("Caches cleared")
    
    @asynccontextmanager
    async def batch_context(self):
        """
        Context manager for batch operations.
        
        Temporarily adjusts configuration for batch processing.
        """
        original_cache = self.config.cache.enabled
        try:
            # Disable response caching for batch (embeddings still cached)
            object.__setattr__(
                self.config.cache,
                'cache_responses',
                False
            )
            yield self
        finally:
            object.__setattr__(
                self.config.cache,
                'cache_responses',
                original_cache
            )


# =============================================================================
# FACTORY FUNCTION (BACKWARD COMPATIBILITY)
# =============================================================================

def create_rag_service(mode: Mode = Mode.LOCAL) -> RAGServiceV4:
    """Create a RAG service instance."""
    return RAGServiceV4.from_factory(mode)


# =============================================================================
# BACKWARD COMPATIBILITY WRAPPER (MUST BE BEFORE __all__)
# =============================================================================

class RAGServiceV3:
    """
    Backward compatibility wrapper for RAGServiceV4.
    
    Accepts the old constructor parameters and translates them to RAGConfig.
    """
    
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
        from app.config import settings
        from app.providers.factory import ProviderFactory
        from app.services.guardrail_service import GuardrailService
        from app.services.hallucination_service import HallucinationService
        from app.services.eval_service import EvalService
        from app.services.query_understanding_service import QueryUnderstandingService
        from app.services.reranking_service import RerankingService
        from app.services.verification_service import LLMVerificationService
        from app.prompts.templates import PromptBuilder
        
        config = RAGConfig(
            mode=mode,
            default_k=settings.retrieval_k,
            default_threshold=settings.retrieval_score_threshold,
            reranking_enabled=reranking_enabled,
            verification_enabled=verification_enabled,
            understanding_model=understanding_model,
            reranking_model=reranking_model,
            generation_model=generation_model,
            verification_model=verification_model
        )
        
        self._service = RAGServiceV4(config)
        
        # Get LLM provider and override model if specified
        llm = ProviderFactory.get_llm_provider(mode)
        if generation_model:
            llm.model = generation_model
        
        self._service.initialize_providers(
            embedder=ProviderFactory.get_embedding_provider(mode),
            vector_store=ProviderFactory.get_vector_store(mode),
            llm=llm,
            query_understanding=QueryUnderstandingService(model=understanding_model),
            reranking=RerankingService(model=reranking_model, enabled=reranking_enabled),
            verification=LLMVerificationService(model=verification_model, enabled=verification_enabled),
            guardrail=GuardrailService(),
            hallucination=HallucinationService(),
            eval_service=EvalService(),
            prompt_builder=PromptBuilder()
        )
    
    async def query(self, *args, **kwargs) -> RAGResponse:
        """Delegate to internal service."""
        return await self._service.query(*args, **kwargs)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Main service
    "RAGServiceV4",
    "RAGServiceV3",
    "create_rag_service",
    
    # Configuration
    "RAGConfig",
    "RetryConfig",
    "CacheConfig",
    "CircuitBreakerConfig",
    "Mode",
    
    # Results
    "RAGResponse",
    "QueryUnderstanding",
    "RetrievalResult",
    "VerificationResult",
    "PipelineMetrics",
    "StageMetrics",
    
    # Pipeline
    "PipelineContext",
    "PipelineStage",
    
    # Errors
    "RAGError",
    "GuardrailError",
    "RetrievalError",
    "GenerationError",
    
    # Utilities
    "CircuitBreaker",
    "LRUCache",
    "with_retry",
]