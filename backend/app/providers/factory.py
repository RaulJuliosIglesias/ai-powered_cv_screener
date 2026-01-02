from app.config import settings, Mode
from app.providers.base import EmbeddingProvider, VectorStoreProvider, LLMProvider


class ProviderFactory:
    """Factory for creating providers based on mode."""
    
    _instances = {}
    
    @classmethod
    def get_embedding_provider(cls, mode: Mode) -> EmbeddingProvider:
        key = f"embedding_{mode}"
        
        if key not in cls._instances:
            if mode == Mode.LOCAL:
                from app.providers.local.embeddings import LocalEmbeddingProvider
                cls._instances[key] = LocalEmbeddingProvider()
            else:
                from app.providers.cloud.embeddings import OpenRouterEmbeddingProvider
                cls._instances[key] = OpenRouterEmbeddingProvider()
        
        return cls._instances[key]
    
    @classmethod
    def get_vector_store(cls, mode: Mode) -> VectorStoreProvider:
        key = f"vector_{mode}"
        
        if key not in cls._instances:
            if mode == Mode.LOCAL:
                from app.providers.local.vector_store import ChromaVectorStore
                cls._instances[key] = ChromaVectorStore()
            else:
                from app.providers.cloud.vector_store import SupabaseVectorStore
                cls._instances[key] = SupabaseVectorStore()
        
        return cls._instances[key]
    
    @classmethod
    def get_llm_provider(cls, mode: Mode) -> LLMProvider:
        key = f"llm_{mode}"
        
        if key not in cls._instances:
            if mode == Mode.LOCAL:
                from app.providers.local.llm import GeminiLLMProvider
                cls._instances[key] = GeminiLLMProvider()
            else:
                from app.providers.cloud.llm import OpenRouterLLMProvider
                cls._instances[key] = OpenRouterLLMProvider()
        
        return cls._instances[key]
    
    @classmethod
    def clear_instances(cls):
        """Clear all cached provider instances."""
        cls._instances.clear()
