import time
from typing import List
from sentence_transformers import SentenceTransformer
from app.providers.base import EmbeddingProvider, EmbeddingResult
from app.config import settings


class LocalEmbeddingProvider(EmbeddingProvider):
    """Local embeddings using SentenceTransformers."""
    
    def __init__(self):
        self._model = None
        self._model_name = settings.local_embedding_model
    
    @property
    def model(self) -> SentenceTransformer:
        """Lazy load the model."""
        if self._model is None:
            self._model = SentenceTransformer(self._model_name)
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
