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
    
    # Supabase (for pgvector)
    supabase_url: Optional[str] = None
    supabase_service_key: Optional[str] = None
    
    # ============================================
    # SHARED CONFIGURATION
    # ============================================
    # Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:5176"
    
    # File limits
    max_file_size_mb: int = 10
    max_files_per_upload: int = 50
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "app.log"
    
    # RAG
    retrieval_k: int = 5
    retrieval_score_threshold: float = 0.3
    
    # LLM
    llm_temperature: float = 0.1
    llm_max_tokens: int = 2048
    
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


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = Settings()
