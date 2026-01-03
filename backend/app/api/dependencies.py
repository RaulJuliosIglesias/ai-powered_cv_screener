from functools import lru_cache
from typing import Generator

from app.config import get_settings, Settings
from app.services.pdf_service import PDFService
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStoreService
from app.services.rag_service_v5 import RAGServiceV5
from app.services.guardrails_service import GuardrailsService
from app.utils.monitoring import UsageTracker, QueryLogger, RateLimiter


# Singleton instances
_pdf_service = None
_embedding_service = None
_vector_store = None
_rag_service = None
_guardrails_service = None
_usage_tracker = None
_query_logger = None
_rate_limiter = None


def get_pdf_service() -> PDFService:
    """Get PDF service singleton."""
    global _pdf_service
    if _pdf_service is None:
        _pdf_service = PDFService()
    return _pdf_service


def get_embedding_service() -> EmbeddingService:
    """Get embedding service singleton."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


def get_vector_store() -> VectorStoreService:
    """Get vector store singleton."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStoreService()
    return _vector_store


def get_rag_service() -> RAGServiceV5:
    """Get RAG service singleton."""
    global _rag_service
    if _rag_service is None:
        from app.config import settings
        _rag_service = RAGServiceV5.from_factory(settings.default_mode)
    return _rag_service


def get_guardrails_service() -> GuardrailsService:
    """Get guardrails service singleton."""
    global _guardrails_service
    if _guardrails_service is None:
        _guardrails_service = GuardrailsService()
    return _guardrails_service


def get_usage_tracker() -> UsageTracker:
    """Get usage tracker singleton."""
    global _usage_tracker
    if _usage_tracker is None:
        _usage_tracker = UsageTracker()
    return _usage_tracker


def get_query_logger() -> QueryLogger:
    """Get query logger singleton."""
    global _query_logger
    if _query_logger is None:
        _query_logger = QueryLogger()
    return _query_logger


def get_rate_limiter() -> RateLimiter:
    """Get rate limiter singleton."""
    global _rate_limiter
    if _rate_limiter is None:
        settings = get_settings()
        _rate_limiter = RateLimiter(
            max_requests_per_minute=settings.rate_limit_rpm,
            max_tokens_per_minute=settings.rate_limit_tpm,
        )
    return _rate_limiter
