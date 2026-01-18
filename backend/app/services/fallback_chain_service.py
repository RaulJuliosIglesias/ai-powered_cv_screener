"""
Fallback Chain Service - Automatic model failover for reliability.

V8 Feature: Auto-switch to backup models when primary fails or is rate-limited.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, Generic, List, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')


class FailureReason(Enum):
    """Reasons for model failure."""
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    API_ERROR = "api_error"
    INVALID_RESPONSE = "invalid_response"
    UNKNOWN = "unknown"


@dataclass
class ModelHealth:
    """Track health status of a model."""
    model_id: str
    consecutive_failures: int = 0
    last_failure_time: Optional[datetime] = None
    last_failure_reason: Optional[FailureReason] = None
    total_failures: int = 0
    total_successes: int = 0
    cooldown_until: Optional[datetime] = None
    
    @property
    def is_healthy(self) -> bool:
        """Check if model is healthy (not in cooldown)."""
        if self.cooldown_until and datetime.utcnow() < self.cooldown_until:
            return False
        return True
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.total_failures + self.total_successes
        if total == 0:
            return 1.0
        return self.total_successes / total
    
    def record_success(self):
        """Record a successful call."""
        self.consecutive_failures = 0
        self.total_successes += 1
        self.cooldown_until = None
    
    def record_failure(self, reason: FailureReason, cooldown_seconds: int = 60):
        """Record a failed call."""
        self.consecutive_failures += 1
        self.total_failures += 1
        self.last_failure_time = datetime.utcnow()
        self.last_failure_reason = reason
        
        # Apply exponential cooldown based on consecutive failures
        cooldown = cooldown_seconds * (2 ** min(self.consecutive_failures - 1, 5))
        self.cooldown_until = datetime.utcnow() + timedelta(seconds=cooldown)
        
        logger.warning(
            f"[FALLBACK] Model {self.model_id} failed ({reason.value}). "
            f"Consecutive: {self.consecutive_failures}, Cooldown: {cooldown}s"
        )


@dataclass
class FallbackResult(Generic[T]):
    """Result from fallback chain execution."""
    success: bool
    result: Optional[T] = None
    model_used: Optional[str] = None
    attempts: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    used_fallback: bool = False


# Default fallback chains for different use cases
FALLBACK_CHAINS = {
    'generation': [
        "google/gemini-2.0-flash-exp:free",      # Primary (fast, free)
        "meta-llama/llama-3.1-8b-instruct:free", # Fallback 1 (free)
        "google/gemma-2-9b-it:free",             # Fallback 2 (free)
        "microsoft/phi-3-medium-128k-instruct:free", # Fallback 3 (free)
    ],
    'understanding': [
        "google/gemini-2.0-flash-exp:free",
        "meta-llama/llama-3.1-8b-instruct:free",
        "google/gemma-2-9b-it:free",
    ],
    'reranking': [
        "google/gemini-2.0-flash-exp:free",
        "meta-llama/llama-3.1-8b-instruct:free",
        "google/gemma-2-9b-it:free",
    ],
    'verification': [
        "google/gemini-2.0-flash-exp:free",
        "meta-llama/llama-3.1-8b-instruct:free",
    ],
}


class FallbackChainService:
    """Service for managing model fallback chains."""
    
    def __init__(self):
        self._model_health: Dict[str, ModelHealth] = {}
        self._chains = FALLBACK_CHAINS.copy()
    
    def get_model_health(self, model_id: str) -> ModelHealth:
        """Get or create health tracker for a model."""
        if model_id not in self._model_health:
            self._model_health[model_id] = ModelHealth(model_id=model_id)
        return self._model_health[model_id]
    
    def get_chain(self, chain_type: str, primary_model: Optional[str] = None) -> List[str]:
        """Get fallback chain for a given type.
        
        Args:
            chain_type: Type of chain (generation, understanding, etc.)
            primary_model: Optional override for primary model
            
        Returns:
            List of model IDs in fallback order
        """
        chain = self._chains.get(chain_type, self._chains['generation']).copy()
        
        # If primary model specified and not in chain, add it first
        if primary_model and primary_model not in chain:
            chain.insert(0, primary_model)
        elif primary_model and primary_model in chain:
            # Move primary to front
            chain.remove(primary_model)
            chain.insert(0, primary_model)
        
        return chain
    
    def get_next_healthy_model(
        self, 
        chain_type: str, 
        primary_model: Optional[str] = None,
        exclude: Optional[List[str]] = None
    ) -> Optional[str]:
        """Get the next healthy model from the chain.
        
        Args:
            chain_type: Type of chain
            primary_model: Preferred primary model
            exclude: Models to exclude
            
        Returns:
            Next healthy model ID or None if all unhealthy
        """
        exclude = exclude or []
        chain = self.get_chain(chain_type, primary_model)
        
        for model_id in chain:
            if model_id in exclude:
                continue
            health = self.get_model_health(model_id)
            if health.is_healthy:
                return model_id
        
        # All models unhealthy, return first one anyway (with warning)
        for model_id in chain:
            if model_id not in exclude:
                logger.warning(f"[FALLBACK] All models unhealthy, using {model_id} anyway")
                return model_id
        
        return None
    
    async def execute_with_fallback(
        self,
        chain_type: str,
        operation: Callable,
        primary_model: Optional[str] = None,
        max_attempts: int = 3,
        timeout: float = 60.0
    ) -> FallbackResult:
        """Execute an operation with automatic fallback.
        
        Args:
            chain_type: Type of chain to use
            operation: Async callable that takes model_id as first arg
            primary_model: Preferred primary model
            max_attempts: Maximum number of models to try
            timeout: Timeout per attempt in seconds
            
        Returns:
            FallbackResult with outcome
        """
        chain = self.get_chain(chain_type, primary_model)
        errors = []
        used_models = []
        
        for attempt, model_id in enumerate(chain[:max_attempts]):
            health = self.get_model_health(model_id)
            
            # Skip unhealthy models unless it's our last option
            if not health.is_healthy and attempt < len(chain) - 1:
                logger.info(f"[FALLBACK] Skipping unhealthy model {model_id}")
                continue
            
            used_models.append(model_id)
            
            try:
                logger.info(f"[FALLBACK] Trying model {model_id} (attempt {attempt + 1})")
                
                result = await asyncio.wait_for(
                    operation(model_id),
                    timeout=timeout
                )
                
                # Success!
                health.record_success()
                
                return FallbackResult(
                    success=True,
                    result=result,
                    model_used=model_id,
                    attempts=len(used_models),
                    errors=errors,
                    used_fallback=attempt > 0
                )
                
            except asyncio.TimeoutError:
                error_info = {
                    "model": model_id,
                    "reason": FailureReason.TIMEOUT.value,
                    "message": f"Timeout after {timeout}s"
                }
                errors.append(error_info)
                health.record_failure(FailureReason.TIMEOUT)
                logger.warning(f"[FALLBACK] {model_id} timed out")
                
            except Exception as e:
                error_str = str(e).lower()
                
                # Detect failure reason
                if "rate" in error_str or "429" in error_str or "quota" in error_str:
                    reason = FailureReason.RATE_LIMIT
                    cooldown = 120  # Longer cooldown for rate limits
                elif "timeout" in error_str:
                    reason = FailureReason.TIMEOUT
                    cooldown = 30
                elif "invalid" in error_str or "parse" in error_str:
                    reason = FailureReason.INVALID_RESPONSE
                    cooldown = 10
                else:
                    reason = FailureReason.API_ERROR
                    cooldown = 60
                
                error_info = {
                    "model": model_id,
                    "reason": reason.value,
                    "message": str(e)[:200]
                }
                errors.append(error_info)
                health.record_failure(reason, cooldown)
                logger.warning(f"[FALLBACK] {model_id} failed: {reason.value} - {str(e)[:100]}")
        
        # All attempts failed
        return FallbackResult(
            success=False,
            result=None,
            model_used=None,
            attempts=len(used_models),
            errors=errors,
            used_fallback=len(used_models) > 1
        )
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of all tracked models."""
        return {
            model_id: {
                "healthy": health.is_healthy,
                "consecutive_failures": health.consecutive_failures,
                "success_rate": round(health.success_rate, 2),
                "last_failure": health.last_failure_reason.value if health.last_failure_reason else None,
                "cooldown_remaining": (
                    (health.cooldown_until - datetime.utcnow()).total_seconds()
                    if health.cooldown_until and health.cooldown_until > datetime.utcnow()
                    else 0
                )
            }
            for model_id, health in self._model_health.items()
        }
    
    def reset_model(self, model_id: str):
        """Reset health status for a model."""
        if model_id in self._model_health:
            del self._model_health[model_id]
            logger.info(f"[FALLBACK] Reset health for {model_id}")
    
    def reset_all(self):
        """Reset all model health statuses."""
        self._model_health.clear()
        logger.info("[FALLBACK] Reset all model health statuses")


# Singleton instance
_fallback_service: Optional[FallbackChainService] = None


def get_fallback_service() -> FallbackChainService:
    """Get singleton fallback chain service instance."""
    global _fallback_service
    if _fallback_service is None:
        _fallback_service = FallbackChainService()
    return _fallback_service
