"""Error handling utilities for RAG services."""
import logging
from functools import wraps
from typing import Any, Callable, TypeVar

import httpx

logger = logging.getLogger(__name__)

T = TypeVar('T')


def with_fallback(fallback_value: Any = None, log_error: bool = True):
    """
    Decorator for functions that should return fallback on error.
    
    Usage:
        @with_fallback(fallback_value=[], log_error=True)
        async def risky_operation():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except httpx.TimeoutException as e:
                if log_error:
                    logger.warning(f"{func.__name__} timeout: {e}. Using fallback: {fallback_value}")
                return fallback_value
            except httpx.HTTPError as e:
                if log_error:
                    logger.warning(f"{func.__name__} HTTP error: {e}. Using fallback: {fallback_value}")
                return fallback_value
            except Exception as e:
                if log_error:
                    logger.error(f"{func.__name__} unexpected error: {e}. Using fallback: {fallback_value}")
                return fallback_value
        return wrapper
    return decorator


class GracefulDegradation:
    """Manages graceful degradation of RAG features."""
    
    def __init__(self):
        self.disabled_features = set()
    
    def disable_feature(self, feature: str, reason: str):
        """Temporarily disable a feature."""
        self.disabled_features.add(feature)
        logger.warning(f"Feature '{feature}' disabled: {reason}")
    
    def is_enabled(self, feature: str) -> bool:
        """Check if feature is enabled."""
        return feature not in self.disabled_features
    
    def enable_feature(self, feature: str):
        """Re-enable a feature."""
        self.disabled_features.discard(feature)
        logger.info(f"Feature '{feature}' re-enabled")


# Global instance
degradation = GracefulDegradation()
