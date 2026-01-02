from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional
import os


class Settings(BaseSettings):
    # API Keys
    openai_api_key: str = ""
    google_api_key: str = ""
    
    # Server Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173"
    
    # File Upload Limits
    max_file_size_mb: int = 10
    max_files_per_upload: int = 50
    
    # Rate Limiting
    rate_limit_rpm: int = 60
    rate_limit_tpm: int = 100000
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "app.log"
    
    # ChromaDB Configuration
    chroma_persist_dir: str = "./chroma_db"
    chroma_collection_name: str = "cv_collection"
    
    # Embeddings
    use_local_embeddings: bool = False
    embedding_model: str = "text-embedding-3-small"
    
    # LLM Configuration
    llm_model: str = "gemini-1.5-flash"
    llm_temperature: float = 0.1
    llm_max_tokens: int = 2048
    
    # RAG Configuration
    retrieval_k: int = 8
    retrieval_score_threshold: float = 0.5
    
    # Optional: LangSmith
    enable_langsmith: bool = False
    langsmith_api_key: Optional[str] = None
    langsmith_project: str = "cv-screener"
    
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
