import time
import logging
import hashlib
import math
from typing import List
from app.providers.base import EmbeddingProvider, EmbeddingResult
from app.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 384


class SimpleHashEmbedding:
    """Simple hash-based embedding as fallback when PyTorch/ONNX unavailable."""
    
    def __call__(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_single(text) for text in texts]
    
    def _embed_single(self, text: str) -> List[float]:
        """Create a simple hash-based embedding vector."""
        words = text.lower().split()
        embedding = [0.0] * EMBEDDING_DIM
        
        for i, word in enumerate(words):
            # Hash each word to get indices and values
            h = hashlib.md5(word.encode()).hexdigest()
            for j in range(0, min(32, len(h)), 2):
                idx = int(h[j:j+2], 16) % EMBEDDING_DIM
                val = (int(h[j:j+2], 16) - 128) / 128.0
                embedding[idx] += val * (1.0 / (1 + i * 0.1))  # Position decay
        
        # Normalize
        norm = math.sqrt(sum(x*x for x in embedding)) or 1.0
        return [x / norm for x in embedding]


def _get_embedding_function():
    """Get embedding function, trying ONNX first, then sentence-transformers, then fallback."""
    # Try ChromaDB's ONNX embeddings first
    try:
        from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
        fn = ONNXMiniLM_L6_V2()
        logger.info("Using ONNX embeddings")
        return fn
    except Exception as e:
        logger.warning(f"ONNX embeddings not available: {e}")
    
    # Try sentence-transformers
    try:
        from sentence_transformers import SentenceTransformer
        fn = SentenceTransformer(settings.local_embedding_model)
        logger.info("Using sentence-transformers embeddings")
        return fn
    except Exception as e:
        logger.warning(f"sentence-transformers not available: {e}")
    
    # Fallback to simple hash embeddings
    logger.warning("Using fallback hash-based embeddings (less accurate but functional)")
    return SimpleHashEmbedding()


class LocalEmbeddingProvider(EmbeddingProvider):
    """Local embeddings with multiple fallback options."""
    
    def __init__(self):
        self._model = None
        self._model_type = None
    
    @property
    def model(self):
        """Lazy load the model."""
        if self._model is None:
            self._model = _get_embedding_function()
            self._model_type = type(self._model).__name__
        return self._model
    
    @property
    def dimensions(self) -> int:
        return EMBEDDING_DIM
    
    async def embed_texts(self, texts: List[str]) -> EmbeddingResult:
        start = time.perf_counter()
        
        model = self.model
        if hasattr(model, 'encode'):
            # SentenceTransformer
            embeddings = model.encode(texts, show_progress_bar=False, convert_to_numpy=True).tolist()
        else:
            # ONNX or SimpleHashEmbedding (both are callable)
            embeddings = model(texts)
        
        latency = (time.perf_counter() - start) * 1000
        
        return EmbeddingResult(
            embeddings=embeddings,
            tokens_used=sum(len(t.split()) for t in texts),
            latency_ms=latency
        )
    
    async def embed_query(self, query: str) -> EmbeddingResult:
        start = time.perf_counter()
        
        model = self.model
        if hasattr(model, 'encode'):
            embedding = model.encode(query, show_progress_bar=False, convert_to_numpy=True).tolist()
        else:
            embeddings = model([query])
            embedding = embeddings[0]
        
        latency = (time.perf_counter() - start) * 1000
        
        return EmbeddingResult(
            embeddings=[embedding],
            tokens_used=len(query.split()),
            latency_ms=latency
        )
