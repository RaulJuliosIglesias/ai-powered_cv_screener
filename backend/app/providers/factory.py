from typing import Optional
from app.config import settings, Mode
from app.providers.base import EmbeddingProvider, VectorStoreProvider, LLMProvider


class ProviderFactory:
    """Factory for creating providers based on mode."""
    
    _instances = {}
    
    @classmethod
    def get_embedding_provider(cls, mode: Mode) -> EmbeddingProvider:
        key = f"embedding_{mode}"
        
        if key not in cls._instances:
            if mode == Mode.CLOUD:
                from app.providers.cloud.embeddings import OpenRouterEmbeddingProvider
                cls._instances[key] = OpenRouterEmbeddingProvider()
            else:
                from app.providers.local.embeddings import LocalEmbeddingProvider
                cls._instances[key] = LocalEmbeddingProvider()
        
        return cls._instances[key]
    
    @classmethod
    def get_vector_store(cls, mode: Mode) -> VectorStoreProvider:
        key = f"vector_{mode}"
        
        if key not in cls._instances:
            if mode == Mode.CLOUD:
                from app.providers.cloud.vector_store import SupabaseVectorStore
                cls._instances[key] = SupabaseVectorStore()
            else:
                from app.providers.local.vector_store import SimpleVectorStore
                cls._instances[key] = SimpleVectorStore()
        
        return cls._instances[key]
    
    @classmethod
    def get_llm_provider(cls, mode: Mode, model: str) -> LLMProvider:
        """
        Get LLM provider configured for specific model.
        
        Args:
            mode: Operating mode (LOCAL or CLOUD)
            model: Model ID to use (required)
        
        Returns:
            LLMProvider instance configured for the specified model
        """
        if not model:
            raise ValueError("model parameter is required")
        
        # Create unique key per model to cache instances
        key = f"llm_{mode}_{model}"
        
        if key not in cls._instances:
            from app.providers.cloud.llm import OpenRouterLLMProvider
            cls._instances[key] = OpenRouterLLMProvider(model=model)
        
        return cls._instances[key]
    
    @classmethod
    def get_rag_service(
        cls,
        mode: Mode,
        use_langchain: Optional[bool] = None,
        understanding_model: Optional[str] = None,
        generation_model: Optional[str] = None
    ):
        """
        Get RAG service based on configuration.
        
        Args:
            mode: LOCAL or CLOUD mode
            use_langchain: Override settings.use_langchain if provided
            understanding_model: Model for query understanding step
            generation_model: Model for response generation step
        
        Returns:
            RAGServiceV3 or LangChainRAGService
        """
        should_use_langchain = use_langchain if use_langchain is not None else settings.use_langchain
        
        # V5 is the new default - LangChain version is deprecated
        from app.services.rag_service_v5 import RAGServiceV5
        return RAGServiceV5.from_factory(mode)
    
    @classmethod
    def clear_instances(cls):
        """Clear all cached provider instances."""
        cls._instances.clear()
