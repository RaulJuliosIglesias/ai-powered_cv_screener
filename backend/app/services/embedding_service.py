import asyncio
from typing import List

from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.utils.exceptions import EmbeddingError


class EmbeddingService:
    """Service for generating text embeddings using OpenAI."""
    
    def __init__(self):
        self.settings = get_settings()
        self.client = OpenAI(api_key=self.settings.openai_api_key)
        self.model = self.settings.embedding_model
        self.dimensions = 1536  # text-embedding-3-small dimensions
        self.batch_size = 100
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        try:
            if not text.strip():
                raise EmbeddingError("Cannot generate embedding for empty text")
            
            response = self.client.embeddings.create(
                model=self.model,
                input=text,
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            if isinstance(e, EmbeddingError):
                raise
            raise EmbeddingError(
                f"Failed to generate embedding: {str(e)}",
                details={"text_length": len(text)}
            )
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts in batch."""
        try:
            if not texts:
                return []
            
            # Filter empty texts
            valid_texts = [t for t in texts if t.strip()]
            if not valid_texts:
                raise EmbeddingError("All texts are empty")
            
            embeddings = []
            
            # Process in batches
            for i in range(0, len(valid_texts), self.batch_size):
                batch = valid_texts[i:i + self.batch_size]
                
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch,
                )
                
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)
            
            return embeddings
            
        except Exception as e:
            if isinstance(e, EmbeddingError):
                raise
            raise EmbeddingError(
                f"Failed to generate batch embeddings: {str(e)}",
                details={"batch_size": len(texts)}
            )
    
    async def generate_embedding_async(self, text: str) -> List[float]:
        """Async wrapper for embedding generation."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.generate_embedding, text)
    
    async def generate_embeddings_batch_async(self, texts: List[str]) -> List[List[float]]:
        """Async wrapper for batch embedding generation."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.generate_embeddings_batch, texts)
    
    def get_token_count(self, text: str) -> int:
        """Estimate token count for a text (rough approximation)."""
        # Rough estimate: ~4 characters per token for English text
        return len(text) // 4
    
    def calculate_cost(self, num_tokens: int) -> float:
        """Calculate embedding cost in USD."""
        # text-embedding-3-small: $0.00002 per 1K tokens
        return (num_tokens / 1000) * 0.00002
