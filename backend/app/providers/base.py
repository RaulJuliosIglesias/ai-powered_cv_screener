from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class EmbeddingResult:
    """Result from embedding generation."""
    embeddings: List[List[float]]
    tokens_used: int
    latency_ms: float


@dataclass
class SearchResult:
    """Result from vector search."""
    id: str
    cv_id: str
    filename: str
    content: str
    similarity: float
    metadata: Dict[str, Any]


@dataclass
class LLMResult:
    """Result from LLM generation."""
    text: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    metadata: Dict[str, Any] = None


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""
    
    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> EmbeddingResult:
        """Generate embeddings for multiple texts."""
        pass
    
    @abstractmethod
    async def embed_query(self, query: str) -> EmbeddingResult:
        """Generate embedding for a single query."""
        pass
    
    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return embedding dimensions."""
        pass


class VectorStoreProvider(ABC):
    """Abstract base class for vector store providers."""
    
    @abstractmethod
    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ) -> None:
        """Add documents with their embeddings to the store."""
        pass
    
    @abstractmethod
    async def search(
        self,
        embedding: List[float],
        k: int = 5,
        threshold: float = 0.3
    ) -> List[SearchResult]:
        """Search for similar documents."""
        pass
    
    @abstractmethod
    async def delete_cv(self, cv_id: str) -> bool:
        """Delete all chunks for a CV."""
        pass
    
    @abstractmethod
    async def list_cvs(self) -> List[Dict[str, Any]]:
        """List all indexed CVs."""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        pass


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048
    ) -> LLMResult:
        """Generate a response from the LLM."""
        pass
