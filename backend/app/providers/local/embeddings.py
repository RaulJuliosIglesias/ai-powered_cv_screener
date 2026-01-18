"""
Local Embedding Provider with multiple backends.

This module provides semantic embeddings with fallback options:
1. sentence-transformers (all-MiniLM-L6-v2) - 384 dims
2. OpenRouter API (nomic-embed-text) - 768 dims  
3. Hash-based fallback (for development only)
"""
import asyncio
import hashlib
import logging
import math
import os
import time
from typing import List

import httpx

from app.providers.base import EmbeddingProvider, EmbeddingResult

logger = logging.getLogger(__name__)


class OpenRouterEmbeddings:
    """Embeddings via OpenRouter API using nomic-embed-text model."""
    
    MODEL = "nomic-ai/nomic-embed-text-v1.5"
    DIMENSIONS = 768
    
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not set")
        self.client = httpx.Client(timeout=30.0)
    
    def encode(self, texts: List[str], **kwargs) -> List[List[float]]:
        """Generate embeddings via API."""
        if isinstance(texts, str):
            texts = [texts]
        
        from app.providers.base import get_openrouter_url
        response = self.client.post(
            get_openrouter_url("embeddings"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": self.MODEL,
                "input": texts
            }
        )
        response.raise_for_status()
        data = response.json()
        
        # Sort by index to ensure correct order
        embeddings = sorted(data["data"], key=lambda x: x["index"])
        return [e["embedding"] for e in embeddings]


class HashEmbeddings:
    """Simple hash-based embeddings for development/fallback."""
    
    DIMENSIONS = 384
    
    def encode(self, texts: List[str], **kwargs) -> List[List[float]]:
        if isinstance(texts, str):
            texts = [texts]
        return [self._embed_single(t) for t in texts]
    
    def _embed_single(self, text: str) -> List[float]:
        words = text.lower().split()
        embedding = [0.0] * self.DIMENSIONS
        
        for i, word in enumerate(words):
            h = hashlib.md5(word.encode()).hexdigest()
            for j in range(0, min(32, len(h)), 2):
                idx = int(h[j:j+2], 16) % self.DIMENSIONS
                val = (int(h[j:j+2], 16) - 128) / 128.0
                embedding[idx] += val * (1.0 / (1 + i * 0.1))
        
        norm = math.sqrt(sum(x*x for x in embedding)) or 1.0
        return [x / norm for x in embedding]


def _load_embedding_model():
    """Load the best available embedding model."""
    
    # Option 1: Try sentence-transformers
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("✅ Using sentence-transformers (all-MiniLM-L6-v2)")
        return model, 384, "sentence-transformers"
    except Exception as e:
        logger.warning(f"sentence-transformers unavailable: {e}")
    
    # Option 2: Try OpenRouter API
    try:
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        if api_key:
            model = OpenRouterEmbeddings()
            # Test it works
            test = model.encode(["test"])
            if len(test[0]) == 768:
                logger.info("✅ Using OpenRouter API (nomic-embed-text)")
                return model, 768, "openrouter"
    except Exception as e:
        logger.warning(f"OpenRouter embeddings unavailable: {e}")
    
    # Option 3: Hash fallback
    logger.warning("⚠️ Using hash-based embeddings (limited accuracy)")
    return HashEmbeddings(), 384, "hash-fallback"


class LocalEmbeddingProvider(EmbeddingProvider):
    """
    Local embeddings with multiple backend options.
    
    Automatically selects the best available backend:
    1. sentence-transformers (preferred, fully local)
    2. OpenRouter API (cloud fallback, requires API key)
    3. Hash-based (development fallback, limited accuracy)
    """
    
    def __init__(self):
        self._model = None
        self._dimensions = 384
        self._backend = None
        logger.info("LocalEmbeddingProvider initializing...")
    
    def _ensure_model(self):
        """Lazy load the embedding model."""
        if self._model is None:
            self._model, self._dimensions, self._backend = _load_embedding_model()
    
    @property
    def model(self):
        self._ensure_model()
        return self._model
    
    @property
    def dimensions(self) -> int:
        self._ensure_model()
        return self._dimensions
    
    @property
    def backend_name(self) -> str:
        self._ensure_model()
        return self._backend
    
    def _encode_sync(self, texts: List[str]) -> List:
        """Synchronous encoding - runs in thread pool to avoid blocking event loop."""
        if hasattr(self._model, 'encode'):
            result = self._model.encode(
                texts,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True
            )
            return result.tolist() if hasattr(result, 'tolist') else result
        else:
            return self._model(texts)
    
    async def embed_texts(self, texts: List[str]) -> EmbeddingResult:
        """Generate embeddings for a list of texts.
        
        Uses asyncio.to_thread() to run encoding in a thread pool,
        avoiding blocking the event loop during CPU-intensive operations.
        """
        if not texts:
            return EmbeddingResult(embeddings=[], tokens_used=0, latency_ms=0)
        
        start = time.perf_counter()
        self._ensure_model()
        
        # Run encoding in thread pool to avoid blocking
        embeddings = await asyncio.to_thread(self._encode_sync, texts)
        
        latency = (time.perf_counter() - start) * 1000
        tokens_used = sum(len(t.split()) for t in texts)
        
        logger.debug(f"Embedded {len(texts)} texts in {latency:.1f}ms via {self._backend}")
        
        return EmbeddingResult(
            embeddings=embeddings,
            tokens_used=tokens_used,
            latency_ms=latency
        )
    
    def _encode_query_sync(self, query: str):
        """Synchronous query encoding - runs in thread pool."""
        if hasattr(self._model, 'encode'):
            result = self._model.encode(
                query,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True
            )
            return result.tolist() if hasattr(result, 'tolist') else result
        else:
            embeddings = self._model.encode([query])
            return embeddings[0]
    
    async def embed_query(self, query: str) -> EmbeddingResult:
        """Generate embedding for a single query.
        
        Uses asyncio.to_thread() to avoid blocking the event loop.
        """
        start = time.perf_counter()
        self._ensure_model()
        
        # Run encoding in thread pool to avoid blocking
        embedding = await asyncio.to_thread(self._encode_query_sync, query)
        
        latency = (time.perf_counter() - start) * 1000
        
        return EmbeddingResult(
            embeddings=[embedding],
            tokens_used=len(query.split()),
            latency_ms=latency
        )
