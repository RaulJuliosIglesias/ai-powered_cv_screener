import time
import logging
from typing import List
from app.providers.base import EmbeddingProvider, EmbeddingResult
from app.config import settings

logger = logging.getLogger(__name__)

# Lazy import to avoid DLL errors on Windows
SentenceTransformer = None

def _get_sentence_transformer():
    """Lazy load SentenceTransformer to handle import errors gracefully."""
    global SentenceTransformer
    if SentenceTransformer is None:
        try:
            from sentence_transformers import SentenceTransformer as ST
            SentenceTransformer = ST
        except OSError as e:
            logger.error(f"Failed to load sentence_transformers (PyTorch DLL error): {e}")
            raise RuntimeError(
                "PyTorch failed to load. This is a Windows DLL issue. "
                "Try running: pip uninstall torch -y && pip install torch --index-url https://download.pytorch.org/whl/cpu"
            ) from e
    return SentenceTransformer


class LocalEmbeddingProvider(EmbeddingProvider):
    """Local embeddings using SentenceTransformers."""
    
    def __init__(self):
        self._model = None
        self._model_name = settings.local_embedding_model
    
    @property
    def model(self):
        """Lazy load the model."""
        if self._model is None:
            ST = _get_sentence_transformer()
            self._model = ST(self._model_name)
        return self._model
    
    @property
    def dimensions(self) -> int:
        return 384  # all-MiniLM-L6-v2 outputs 384 dimensions
    
    async def embed_texts(self, texts: List[str]) -> EmbeddingResult:
        start = time.perf_counter()
        
        embeddings = self.model.encode(
            texts,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        
        latency = (time.perf_counter() - start) * 1000
        
        return EmbeddingResult(
            embeddings=embeddings.tolist(),
            tokens_used=sum(len(t.split()) for t in texts),  # Approximate
            latency_ms=latency
        )
    
    async def embed_query(self, query: str) -> EmbeddingResult:
        start = time.perf_counter()
        
        embedding = self.model.encode(
            query,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        
        latency = (time.perf_counter() - start) * 1000
        
        return EmbeddingResult(
            embeddings=[embedding.tolist()],
            tokens_used=len(query.split()),
            latency_ms=latency
        )
