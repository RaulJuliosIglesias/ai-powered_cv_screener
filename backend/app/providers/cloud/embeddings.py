import time
from typing import List
import httpx
from app.providers.base import EmbeddingProvider, EmbeddingResult
from app.config import settings


class OpenRouterEmbeddingProvider(EmbeddingProvider):
    """Cloud embeddings using OpenRouter API."""
    
    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = "nomic-ai/nomic-embed-text-v1.5"
    
    @property
    def dimensions(self) -> int:
        return 768  # nomic-embed outputs 768 dimensions
    
    async def embed_texts(self, texts: List[str]) -> EmbeddingResult:
        start = time.perf_counter()
        
        # Add task prefix for better results
        prefixed_texts = [f"search_document: {t}" for t in texts]
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "input": prefixed_texts
                }
            )
            response.raise_for_status()
            data = response.json()
        
        latency = (time.perf_counter() - start) * 1000
        
        embeddings = [item["embedding"] for item in data["data"]]
        tokens_used = data.get("usage", {}).get("total_tokens", 0)
        
        return EmbeddingResult(
            embeddings=embeddings,
            tokens_used=tokens_used,
            latency_ms=latency
        )
    
    async def embed_query(self, query: str) -> EmbeddingResult:
        start = time.perf_counter()
        
        # Add task prefix for queries
        prefixed_query = f"search_query: {query}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "input": [prefixed_query]
                }
            )
            response.raise_for_status()
            data = response.json()
        
        latency = (time.perf_counter() - start) * 1000
        
        return EmbeddingResult(
            embeddings=[data["data"][0]["embedding"]],
            tokens_used=data.get("usage", {}).get("total_tokens", 0),
            latency_ms=latency
        )
