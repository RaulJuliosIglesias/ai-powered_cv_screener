"""
Semantic Cache Service - Cache responses by query similarity.

V8 Feature: Speed up repeated/similar queries by caching responses.
Uses embedding similarity to match queries, not exact string matching.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """A cached query-response pair."""
    query: str
    query_embedding: List[float]
    response: Dict[str, Any]
    session_id: str
    created_at: datetime
    ttl_seconds: int
    hits: int = 0
    last_hit: Optional[datetime] = None
    
    @property
    def is_expired(self) -> bool:
        elapsed = (datetime.utcnow() - self.created_at).total_seconds()
        return elapsed >= self.ttl_seconds
    
    def record_hit(self):
        self.hits += 1
        self.last_hit = datetime.utcnow()


@dataclass
class CacheHit:
    """Result of a cache lookup."""
    found: bool
    entry: Optional[CacheEntry] = None
    similarity: float = 0.0
    cache_age_seconds: float = 0.0


class SemanticCacheService:
    """Service for semantic caching of query responses."""
    
    def __init__(
        self,
        similarity_threshold: float = 0.95,
        ttl_seconds: int = 3600,
        max_entries: int = 1000,
        max_entries_per_session: int = 100
    ):
        """Initialize semantic cache.
        
        Args:
            similarity_threshold: Minimum cosine similarity for cache hit (0.95 = very similar)
            ttl_seconds: Time-to-live for cache entries in seconds
            max_entries: Maximum total cache entries
            max_entries_per_session: Maximum entries per session
        """
        self.similarity_threshold = similarity_threshold
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self.max_entries_per_session = max_entries_per_session
        
        # Cache storage: session_id -> list of entries
        self._cache: Dict[str, List[CacheEntry]] = {}
        
        # Stats
        self._total_hits = 0
        self._total_misses = 0
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        a_np = np.array(a)
        b_np = np.array(b)
        
        dot_product = np.dot(a_np, b_np)
        norm_a = np.linalg.norm(a_np)
        norm_b = np.linalg.norm(b_np)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(dot_product / (norm_a * norm_b))
    
    def lookup(
        self,
        query: str,
        query_embedding: List[float],
        session_id: str
    ) -> CacheHit:
        """Look up a query in the cache.
        
        Args:
            query: The query string
            query_embedding: Embedding vector for the query
            session_id: Session to search in
            
        Returns:
            CacheHit with result
        """
        session_cache = self._cache.get(session_id, [])
        
        if not session_cache:
            self._total_misses += 1
            return CacheHit(found=False)
        
        # Find most similar cached query
        best_match: Optional[CacheEntry] = None
        best_similarity = 0.0
        
        for entry in session_cache:
            # Skip expired entries
            if entry.is_expired:
                continue
            
            similarity = self._cosine_similarity(query_embedding, entry.query_embedding)
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = entry
        
        # Check if best match exceeds threshold
        if best_match and best_similarity >= self.similarity_threshold:
            best_match.record_hit()
            self._total_hits += 1
            
            cache_age = (datetime.utcnow() - best_match.created_at).total_seconds()
            
            logger.info(
                f"[SEMANTIC_CACHE] HIT! similarity={best_similarity:.3f}, "
                f"age={cache_age:.1f}s, hits={best_match.hits}"
            )
            
            return CacheHit(
                found=True,
                entry=best_match,
                similarity=best_similarity,
                cache_age_seconds=cache_age
            )
        
        self._total_misses += 1
        logger.debug(
            f"[SEMANTIC_CACHE] MISS. best_similarity={best_similarity:.3f}, "
            f"threshold={self.similarity_threshold}"
        )
        
        return CacheHit(found=False, similarity=best_similarity)
    
    def store(
        self,
        query: str,
        query_embedding: List[float],
        response: Dict[str, Any],
        session_id: str,
        ttl_override: Optional[int] = None
    ) -> bool:
        """Store a query-response pair in cache.
        
        Args:
            query: The query string
            query_embedding: Embedding vector for the query
            response: The response to cache
            session_id: Session ID
            ttl_override: Optional TTL override in seconds
            
        Returns:
            True if stored successfully
        """
        # Initialize session cache if needed
        if session_id not in self._cache:
            self._cache[session_id] = []
        
        session_cache = self._cache[session_id]
        
        # Check session limit
        if len(session_cache) >= self.max_entries_per_session:
            # Remove oldest/least used entry
            self._evict_from_session(session_id)
        
        # Check total limit
        total_entries = sum(len(entries) for entries in self._cache.values())
        if total_entries >= self.max_entries:
            self._evict_global()
        
        # Create and store entry
        entry = CacheEntry(
            query=query,
            query_embedding=query_embedding,
            response=response,
            session_id=session_id,
            created_at=datetime.utcnow(),
            ttl_seconds=ttl_override or self.ttl_seconds
        )
        
        session_cache.append(entry)
        
        logger.info(
            f"[SEMANTIC_CACHE] Stored entry for session {session_id}. "
            f"Session entries: {len(session_cache)}"
        )
        
        return True
    
    def _evict_from_session(self, session_id: str):
        """Evict least valuable entry from a session."""
        session_cache = self._cache.get(session_id, [])
        if not session_cache:
            return
        
        # Remove expired entries first
        original_len = len(session_cache)
        session_cache[:] = [e for e in session_cache if not e.is_expired]
        
        if len(session_cache) < original_len:
            logger.debug(f"[SEMANTIC_CACHE] Evicted {original_len - len(session_cache)} expired entries")
            return
        
        # Remove entry with lowest score (hits / age)
        def entry_value(e: CacheEntry) -> float:
            age = (datetime.utcnow() - e.created_at).total_seconds() + 1
            return e.hits / age
        
        min_entry = min(session_cache, key=entry_value)
        session_cache.remove(min_entry)
        logger.debug(f"[SEMANTIC_CACHE] Evicted entry with {min_entry.hits} hits")
    
    def _evict_global(self):
        """Evict entries globally to stay under max_entries."""
        # Collect all entries with session info
        all_entries: List[Tuple[str, CacheEntry]] = []
        for session_id, entries in self._cache.items():
            for entry in entries:
                all_entries.append((session_id, entry))
        
        # Remove expired
        for session_id, entry in all_entries:
            if entry.is_expired:
                self._cache[session_id].remove(entry)
        
        # Recalculate total
        total = sum(len(entries) for entries in self._cache.values())
        
        if total < self.max_entries:
            return
        
        # Remove lowest value entries
        to_remove = total - self.max_entries + 10  # Remove a few extra
        
        def entry_value(item: Tuple[str, CacheEntry]) -> float:
            e = item[1]
            age = (datetime.utcnow() - e.created_at).total_seconds() + 1
            return e.hits / age
        
        all_entries = [(sid, e) for sid, entries in self._cache.items() for e in entries]
        all_entries.sort(key=entry_value)
        
        for session_id, entry in all_entries[:to_remove]:
            if entry in self._cache.get(session_id, []):
                self._cache[session_id].remove(entry)
        
        logger.info(f"[SEMANTIC_CACHE] Global eviction: removed {to_remove} entries")
    
    def invalidate_session(self, session_id: str):
        """Invalidate all cache entries for a session."""
        if session_id in self._cache:
            count = len(self._cache[session_id])
            del self._cache[session_id]
            logger.info(f"[SEMANTIC_CACHE] Invalidated {count} entries for session {session_id}")
    
    def invalidate_all(self):
        """Clear entire cache."""
        total = sum(len(entries) for entries in self._cache.values())
        self._cache.clear()
        logger.info(f"[SEMANTIC_CACHE] Cleared all {total} entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_entries = sum(len(entries) for entries in self._cache.values())
        expired_entries = sum(
            1 for entries in self._cache.values() 
            for e in entries if e.is_expired
        )
        
        total_requests = self._total_hits + self._total_misses
        hit_rate = self._total_hits / total_requests if total_requests > 0 else 0.0
        
        return {
            "total_entries": total_entries,
            "expired_entries": expired_entries,
            "sessions_cached": len(self._cache),
            "total_hits": self._total_hits,
            "total_misses": self._total_misses,
            "hit_rate": round(hit_rate, 3),
            "similarity_threshold": self.similarity_threshold,
            "ttl_seconds": self.ttl_seconds,
            "max_entries": self.max_entries
        }


# Configuration
CACHE_CONFIG = {
    'similarity_threshold': 0.95,
    'ttl_seconds': 3600,  # 1 hour
    'max_entries': 1000,
    'max_entries_per_session': 100
}

# Singleton instance
_semantic_cache: Optional[SemanticCacheService] = None


def get_semantic_cache() -> SemanticCacheService:
    """Get singleton semantic cache instance."""
    global _semantic_cache
    if _semantic_cache is None:
        _semantic_cache = SemanticCacheService(**CACHE_CONFIG)
    return _semantic_cache
