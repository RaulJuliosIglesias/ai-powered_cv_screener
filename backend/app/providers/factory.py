from app.config import settings, Mode
from app.providers.base import EmbeddingProvider, VectorStoreProvider, LLMProvider


class ProviderFactory:
    """Factory for creating providers based on mode."""
    
    _instances = {}
    
    @classmethod
    def get_embedding_provider(cls, mode: Mode) -> EmbeddingProvider:
        key = f"embedding_{mode}"
        
        if key not in cls._instances:
            # Always use local embeddings (hash-based fallback works without external deps)
            from app.providers.local.embeddings import LocalEmbeddingProvider
            cls._instances[key] = LocalEmbeddingProvider()
        
        return cls._instances[key]
    
    @classmethod
    def get_vector_store(cls, mode: Mode) -> VectorStoreProvider:
        key = f"vector_{mode}"
        
        if key not in cls._instances:
            # Always use local vector store (SimpleVectorStore with JSON persistence)
            from app.providers.local.vector_store import SimpleVectorStore
            cls._instances[key] = SimpleVectorStore()
        
        return cls._instances[key]
    
    @classmethod
    def get_llm_provider(cls, mode: Mode = None) -> LLMProvider:
        # Always use OpenRouter (supports multiple models)
        key = "llm_openrouter"
        
        if key not in cls._instances:
            from app.providers.cloud.llm import OpenRouterLLMProvider
            cls._instances[key] = OpenRouterLLMProvider()
        
        return cls._instances[key]
    
    @classmethod
    def clear_instances(cls):
        """Clear all cached provider instances."""
        cls._instances.clear()
