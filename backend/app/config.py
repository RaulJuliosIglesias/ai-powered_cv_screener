from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
from enum import Enum
import os


class Mode(str, Enum):
    """Backend mode selection."""
    LOCAL = "local"
    CLOUD = "cloud"


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Default Mode
    default_mode: Mode = Mode.LOCAL
    
    # ============================================
    # HUGGINGFACE CONFIGURATION (FREE - v7 Features)
    # ============================================
    huggingface_api_key: Optional[str] = None
    
    # Model configuration
    hf_nli_model: str = "microsoft/deberta-v3-base-mnli"
    hf_reranker_model: str = "BAAI/bge-reranker-base"
    hf_zeroshot_model: str = "MoritzLaurer/deberta-v3-base-zeroshot-v2.0"
    
    # Feature flags for v7 services
    use_hf_guardrails: bool = True  # Zero-shot guardrails
    use_hf_reranker: bool = True    # Cross-encoder reranking
    use_hf_nli: bool = True         # NLI verification
    use_ragas_eval: bool = True     # RAGAS evaluation logging
    
    # ============================================
    # LOCAL MODE CONFIGURATION
    # ============================================
    # Google AI Studio (for Gemini LLM)
    google_api_key: Optional[str] = None
    
    # ChromaDB
    chroma_persist_dir: str = "./chroma_db"
    chroma_collection_name: str = "cv_collection"
    
    # Local embeddings model (auto-downloaded)
    local_embedding_model: str = "all-MiniLM-L6-v2"
    
    # ============================================
    # CLOUD MODE CONFIGURATION
    # ============================================
    # OpenRouter (for embeddings + LLM)
    openrouter_api_key: Optional[str] = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    
    # HTTP Headers for API calls
    http_referer: str = "https://cv-screener.local"
    app_title: str = "CV Screener RAG"
    
    # Supabase (for pgvector + storage)
    supabase_url: Optional[str] = None
    supabase_service_key: Optional[str] = None
    supabase_bucket_name: str = "cv-pdfs"
    
    # ============================================
    # LANGCHAIN CONFIGURATION
    # ============================================
    use_langchain: bool = False  # Set to True to use LangChain RAG service
    
    # ============================================
    # SHARED CONFIGURATION
    # ============================================
    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:6001"
    
    # File limits
    max_file_size_mb: int = 10
    max_files_per_upload: int = 50
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "app.log"
    
    # RAG - Adaptive Retrieval Strategy
    retrieval_k: int = 50  # For top-k global (search/filter queries): multiple chunks per CV
    retrieval_score_threshold: float = 0.15  # Balanced threshold for quality vs coverage
    # Note: For ranking/comparison queries, k is automatically set to total_cvs_in_session
    
    # Adaptive retrieval configuration
    ranking_retrieval_percentage: float = 0.2  # Retrieve 20% of CVs for ranking queries
    min_ranking_k: int = 10  # Minimum CVs to retrieve for ranking
    
    # LLM
    llm_temperature: float = 0.1
    llm_max_tokens: int = 4096  # Increased for longer structured responses
    
    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


class TimeoutConfig:
    """Centralized timeout configuration (in seconds)."""
    
    # HTTP Request Timeouts
    HTTP_SHORT: float = 20.0      # Quick operations (embeddings, simple queries)
    HTTP_MEDIUM: float = 30.0     # Standard LLM calls
    HTTP_LONG: float = 60.0       # Complex reasoning, reflection
    HTTP_VERY_LONG: float = 90.0  # Multi-step operations
    
    # Pipeline Stage Timeouts (from RAG v5)
    EMBEDDING: float = 10.0
    SEARCH: float = 20.0
    LLM: float = 120.0
    REASONING: float = 90.0
    TOTAL: float = 240.0
    
    @classmethod
    def get_timeout(cls, operation: str) -> float:
        """Get timeout for operation type."""
        mapping = {
            'embedding': cls.EMBEDDING,
            'search': cls.SEARCH,
            'llm': cls.LLM,
            'reasoning': cls.REASONING,
            'total': cls.TOTAL,
            'short': cls.HTTP_SHORT,
            'medium': cls.HTTP_MEDIUM,
            'long': cls.HTTP_LONG,
        }
        return mapping.get(operation, cls.HTTP_MEDIUM)


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Global instances
timeouts = TimeoutConfig()


settings = Settings()
