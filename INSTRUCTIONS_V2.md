# CV Screener RAG Chatbot — Technical Specification v2
# Dual Mode Architecture: Local + Cloud

## Project Overview

Build an AI-powered CV screening application with **switchable backend modes**:
- **LOCAL MODE**: ChromaDB + SentenceTransformers + Gemini (Google AI Studio)
- **CLOUD MODE**: Supabase pgvector + OpenRouter embeddings + OpenRouter LLM

Users can toggle between modes via UI to compare performance and choose the best option.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React)                               │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  ┌─────────────┐  ┌──────────────────────────────────────────────┐    │  │
│  │  │ MODE SWITCH │  │              METRICS BAR                     │    │  │
│  │  │ ○ Local     │  │  Embed: 52ms | Search: 8ms | LLM: 823ms     │    │  │
│  │  │ ● Cloud     │  │  Total: 883ms | Mode: cloud                 │    │  │
│  │  └─────────────┘  └──────────────────────────────────────────────┘    │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                     │                                       │
│                                     ▼                                       │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         CHAT INTERFACE                                │  │
│  │  [Upload CVs] [Ask questions] [View sources]                         │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BACKEND (FastAPI)                                 │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                        PROVIDER FACTORY                               │  │
│  │                                                                       │  │
│  │   mode = request.query_params["mode"]  # "local" | "cloud"            │  │
│  │                        │                                              │  │
│  │                        ▼                                              │  │
│  │   ┌─────────────────────────────────────────────────────────────┐     │  │
│  │   │              ABSTRACT INTERFACES                            │     │  │
│  │   │  EmbeddingProvider | VectorStoreProvider | LLMProvider      │     │  │
│  │   └─────────────────────────────────────────────────────────────┘     │  │
│  │                        │                                              │  │
│  │          ┌─────────────┴─────────────┐                                │  │
│  │          ▼                           ▼                                │  │
│  │   ┌─────────────────┐         ┌─────────────────┐                     │  │
│  │   │   LOCAL MODE    │         │   CLOUD MODE    │                     │  │
│  │   ├─────────────────┤         ├─────────────────┤                     │  │
│  │   │ SentenceTransf. │         │ OpenRouter      │                     │  │
│  │   │ ChromaDB        │         │ Supabase        │                     │  │
│  │   │ Gemini (Google) │         │ OpenRouter LLM  │                     │  │
│  │   └─────────────────┘         └─────────────────┘                     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         RAG SERVICE                                   │  │
│  │   Unified interface regardless of mode                                │  │
│  │   - index_cvs(pdfs) → extracts, chunks, embeds, stores                │  │
│  │   - query(question) → retrieves, generates, returns with sources      │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Shared (Both Modes)
| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Runtime | Python | 3.11+ | Backend language |
| Framework | FastAPI | 0.109+ | REST API |
| PDF Extraction | pdfplumber | 0.10+ | Text from PDFs |
| Validation | Pydantic | 2.0+ | Data validation |
| Frontend | React + Vite | 18+ / 5+ | UI |
| Styling | TailwindCSS | 3+ | CSS framework |

### Local Mode Stack
| Component | Technology | Purpose |
|-----------|------------|---------|
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) | Local embedding generation |
| Vector Store | ChromaDB | Local vector database |
| LLM | Google Gemini (gemini-1.5-flash) | Response generation |

### Cloud Mode Stack
| Component | Technology | Purpose |
|-----------|------------|---------|
| Embeddings | OpenRouter (nomic-ai/nomic-embed-text-v1.5) | API-based embeddings |
| Vector Store | Supabase pgvector | Cloud PostgreSQL with vectors |
| LLM | OpenRouter (google/gemini-2.0-flash-exp:free) | API-based LLM |

---

## Project Structure

```
cv-screener/
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                      # FastAPI entry point
│   │   ├── config.py                    # Environment & settings
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes.py                # All API endpoints
│   │   │   └── dependencies.py          # Dependency injection
│   │   │
│   │   ├── providers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py                  # Abstract interfaces
│   │   │   ├── factory.py               # Provider factory
│   │   │   │
│   │   │   ├── local/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── embeddings.py        # SentenceTransformers
│   │   │   │   ├── vector_store.py      # ChromaDB
│   │   │   │   └── llm.py               # Gemini (Google AI Studio)
│   │   │   │
│   │   │   └── cloud/
│   │   │       ├── __init__.py
│   │   │       ├── embeddings.py        # OpenRouter embeddings
│   │   │       ├── vector_store.py      # Supabase pgvector
│   │   │       └── llm.py               # OpenRouter LLM
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── pdf_service.py           # PDF text extraction
│   │   │   ├── chunking_service.py      # Text chunking logic
│   │   │   └── rag_service.py           # Main RAG orchestration
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── schemas.py               # Pydantic models
│   │   │
│   │   ├── prompts/
│   │   │   ├── __init__.py
│   │   │   └── templates.py             # LLM prompt templates
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── metrics.py               # Performance tracking
│   │       └── exceptions.py            # Custom exceptions
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_providers.py
│   │   ├── test_rag_service.py
│   │   └── test_api.py
│   │
│   ├── uploads/                         # Temporary PDF storage
│   ├── chroma_db/                       # Local ChromaDB persistence
│   ├── requirements.txt
│   ├── .env.example
│   └── .env
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Layout.jsx
│   │   │   ├── ModeSwitch.jsx           # Local/Cloud toggle
│   │   │   ├── MetricsBar.jsx           # Performance display
│   │   │   ├── UploadZone.jsx
│   │   │   ├── ProcessingStatus.jsx
│   │   │   ├── CVList.jsx
│   │   │   ├── ChatWindow.jsx
│   │   │   ├── MessageList.jsx
│   │   │   ├── Message.jsx
│   │   │   ├── SourceBadge.jsx
│   │   │   └── ChatInput.jsx
│   │   │
│   │   ├── hooks/
│   │   │   ├── useChat.js
│   │   │   ├── useUpload.js
│   │   │   └── useMode.js               # Mode state management
│   │   │
│   │   ├── services/
│   │   │   └── api.js
│   │   │
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   │
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
│
├── supabase/
│   └── migrations/
│       └── 001_create_cv_embeddings.sql
│
├── cvs/                                 # The 30 generated CV PDFs
│   └── *.pdf
│
└── README.md
```

---

## Environment Variables

```bash
# .env

# ============================================
# DEFAULT MODE
# ============================================
DEFAULT_MODE=local                       # "local" | "cloud"

# ============================================
# LOCAL MODE CONFIGURATION
# ============================================
# Google AI Studio (for Gemini LLM)
GOOGLE_API_KEY=AIzaSy...

# ChromaDB
CHROMA_PERSIST_DIR=./chroma_db
CHROMA_COLLECTION_NAME=cv_collection

# Local embeddings model (auto-downloaded)
LOCAL_EMBEDDING_MODEL=all-MiniLM-L6-v2

# ============================================
# CLOUD MODE CONFIGURATION
# ============================================
# OpenRouter (for embeddings + LLM)
OPENROUTER_API_KEY=sk-or-v1-...

# Supabase (for pgvector)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# ============================================
# SHARED CONFIGURATION
# ============================================
# Server
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:5173

# Limits
MAX_FILE_SIZE_MB=10
MAX_FILES_PER_UPLOAD=50

# Logging
LOG_LEVEL=INFO
```

---

## Supabase Setup

### 1. Create Supabase Project
Go to https://supabase.com and create a new project.

### 2. Enable pgvector Extension
Run in SQL Editor:

```sql
-- Enable vector extension
create extension if not exists vector;
```

### 3. Create Tables and Functions

```sql
-- ============================================
-- CV EMBEDDINGS TABLE
-- ============================================
create table cv_embeddings (
  id uuid primary key default gen_random_uuid(),
  cv_id text not null,
  filename text not null,
  chunk_index integer not null,
  content text not null,
  embedding vector(768),                 -- 768 dimensions for nomic-embed
  metadata jsonb default '{}',
  created_at timestamptz default now(),
  
  -- Unique constraint to prevent duplicates
  unique(cv_id, chunk_index)
);

-- Index for fast vector similarity search
create index cv_embeddings_embedding_idx 
on cv_embeddings 
using ivfflat (embedding vector_cosine_ops)
with (lists = 100);

-- Index for filtering by cv_id
create index cv_embeddings_cv_id_idx on cv_embeddings(cv_id);

-- ============================================
-- CV METADATA TABLE (optional, for listing)
-- ============================================
create table cvs (
  id text primary key,
  filename text not null,
  indexed_at timestamptz default now(),
  chunk_count integer default 0,
  metadata jsonb default '{}'
);

-- ============================================
-- VECTOR SEARCH FUNCTION
-- ============================================
create or replace function match_cv_embeddings(
  query_embedding vector(768),
  match_count int default 5,
  match_threshold float default 0.3
)
returns table (
  id uuid,
  cv_id text,
  filename text,
  chunk_index integer,
  content text,
  metadata jsonb,
  similarity float
)
language sql stable
as $$
  select
    cv_embeddings.id,
    cv_embeddings.cv_id,
    cv_embeddings.filename,
    cv_embeddings.chunk_index,
    cv_embeddings.content,
    cv_embeddings.metadata,
    1 - (cv_embeddings.embedding <=> query_embedding) as similarity
  from cv_embeddings
  where 1 - (cv_embeddings.embedding <=> query_embedding) > match_threshold
  order by cv_embeddings.embedding <=> query_embedding
  limit match_count;
$$;

-- ============================================
-- DELETE CV FUNCTION
-- ============================================
create or replace function delete_cv(target_cv_id text)
returns void
language sql
as $$
  delete from cv_embeddings where cv_id = target_cv_id;
  delete from cvs where id = target_cv_id;
$$;
```

### 4. Get Credentials
- **SUPABASE_URL**: Project Settings → API → Project URL
- **SUPABASE_SERVICE_KEY**: Project Settings → API → service_role key (secret)

---

## Backend Implementation

### 1. Configuration (app/config.py)

```python
from pydantic_settings import BaseSettings
from enum import Enum
from typing import Optional

class Mode(str, Enum):
    LOCAL = "local"
    CLOUD = "cloud"

class Settings(BaseSettings):
    # Mode
    default_mode: Mode = Mode.LOCAL
    
    # Local mode
    google_api_key: Optional[str] = None
    chroma_persist_dir: str = "./chroma_db"
    chroma_collection_name: str = "cv_collection"
    local_embedding_model: str = "all-MiniLM-L6-v2"
    
    # Cloud mode
    openrouter_api_key: Optional[str] = None
    supabase_url: Optional[str] = None
    supabase_service_key: Optional[str] = None
    
    # Shared
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173"
    max_file_size_mb: int = 10
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
```

### 2. Abstract Interfaces (app/providers/base.py)

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class EmbeddingResult:
    embeddings: List[List[float]]
    tokens_used: int
    latency_ms: float

@dataclass
class SearchResult:
    id: str
    cv_id: str
    filename: str
    content: str
    similarity: float
    metadata: Dict[str, Any]

@dataclass
class LLMResult:
    text: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float

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
```

### 3. Local Mode - Embeddings (app/providers/local/embeddings.py)

```python
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
```

### 4. Local Mode - Vector Store (app/providers/local/vector_store.py)

```python
import time
from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings as ChromaSettings
from app.providers.base import VectorStoreProvider, SearchResult
from app.config import settings

class ChromaVectorStore(VectorStoreProvider):
    """Local vector store using ChromaDB."""
    
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name=settings.chroma_collection_name,
            metadata={"hnsw:space": "cosine"}
        )
    
    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ) -> None:
        if not documents:
            return
        
        self.collection.add(
            ids=[doc["id"] for doc in documents],
            embeddings=embeddings,
            documents=[doc["content"] for doc in documents],
            metadatas=[{
                "cv_id": doc["cv_id"],
                "filename": doc["filename"],
                "chunk_index": doc["chunk_index"],
                **doc.get("metadata", {})
            } for doc in documents]
        )
    
    async def search(
        self,
        embedding: List[float],
        k: int = 5,
        threshold: float = 0.3
    ) -> List[SearchResult]:
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=k,
            include=["documents", "metadatas", "distances"]
        )
        
        search_results = []
        for i in range(len(results["ids"][0])):
            # ChromaDB returns distances, convert to similarity
            distance = results["distances"][0][i]
            similarity = 1 - distance  # For cosine distance
            
            if similarity >= threshold:
                metadata = results["metadatas"][0][i]
                search_results.append(SearchResult(
                    id=results["ids"][0][i],
                    cv_id=metadata.get("cv_id", ""),
                    filename=metadata.get("filename", ""),
                    content=results["documents"][0][i],
                    similarity=similarity,
                    metadata=metadata
                ))
        
        return search_results
    
    async def delete_cv(self, cv_id: str) -> bool:
        try:
            # Get all IDs for this CV
            results = self.collection.get(
                where={"cv_id": cv_id},
                include=[]
            )
            if results["ids"]:
                self.collection.delete(ids=results["ids"])
            return True
        except Exception:
            return False
    
    async def list_cvs(self) -> List[Dict[str, Any]]:
        # Get all unique CVs
        results = self.collection.get(include=["metadatas"])
        
        cvs = {}
        for metadata in results["metadatas"]:
            cv_id = metadata.get("cv_id")
            if cv_id and cv_id not in cvs:
                cvs[cv_id] = {
                    "id": cv_id,
                    "filename": metadata.get("filename", ""),
                    "chunk_count": 0
                }
            if cv_id:
                cvs[cv_id]["chunk_count"] += 1
        
        return list(cvs.values())
    
    async def get_stats(self) -> Dict[str, Any]:
        count = self.collection.count()
        cvs = await self.list_cvs()
        return {
            "total_chunks": count,
            "total_cvs": len(cvs),
            "storage_type": "local_chromadb"
        }
```

### 5. Local Mode - LLM (app/providers/local/llm.py)

```python
import time
from typing import Optional
import google.generativeai as genai
from app.providers.base import LLMProvider, LLMResult
from app.config import settings

class GeminiLLMProvider(LLMProvider):
    """LLM provider using Google Gemini via AI Studio."""
    
    def __init__(self):
        genai.configure(api_key=settings.google_api_key)
        self.model = genai.GenerativeModel("gemini-1.5-flash")
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048
    ) -> LLMResult:
        start = time.perf_counter()
        
        # Combine system prompt with user prompt
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        response = self.model.generate_content(
            full_prompt,
            generation_config=genai.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )
        )
        
        latency = (time.perf_counter() - start) * 1000
        
        # Extract token counts from response
        usage = response.usage_metadata
        
        return LLMResult(
            text=response.text,
            prompt_tokens=usage.prompt_token_count if usage else 0,
            completion_tokens=usage.candidates_token_count if usage else 0,
            latency_ms=latency
        )
```

### 6. Cloud Mode - Embeddings (app/providers/cloud/embeddings.py)

```python
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
```

### 7. Cloud Mode - Vector Store (app/providers/cloud/vector_store.py)

```python
import time
from typing import List, Dict, Any
from supabase import create_client, Client
from app.providers.base import VectorStoreProvider, SearchResult
from app.config import settings

class SupabaseVectorStore(VectorStoreProvider):
    """Cloud vector store using Supabase pgvector."""
    
    def __init__(self):
        self.client: Client = create_client(
            settings.supabase_url,
            settings.supabase_service_key
        )
    
    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ) -> None:
        if not documents:
            return
        
        records = []
        for doc, embedding in zip(documents, embeddings):
            records.append({
                "cv_id": doc["cv_id"],
                "filename": doc["filename"],
                "chunk_index": doc["chunk_index"],
                "content": doc["content"],
                "embedding": embedding,
                "metadata": doc.get("metadata", {})
            })
        
        # Upsert to handle duplicates
        self.client.table("cv_embeddings").upsert(
            records,
            on_conflict="cv_id,chunk_index"
        ).execute()
        
        # Update CVs table
        unique_cvs = {}
        for doc in documents:
            cv_id = doc["cv_id"]
            if cv_id not in unique_cvs:
                unique_cvs[cv_id] = {
                    "id": cv_id,
                    "filename": doc["filename"],
                    "chunk_count": 0
                }
            unique_cvs[cv_id]["chunk_count"] += 1
        
        for cv_data in unique_cvs.values():
            self.client.table("cvs").upsert(cv_data).execute()
    
    async def search(
        self,
        embedding: List[float],
        k: int = 5,
        threshold: float = 0.3
    ) -> List[SearchResult]:
        response = self.client.rpc(
            "match_cv_embeddings",
            {
                "query_embedding": embedding,
                "match_count": k,
                "match_threshold": threshold
            }
        ).execute()
        
        results = []
        for row in response.data:
            results.append(SearchResult(
                id=row["id"],
                cv_id=row["cv_id"],
                filename=row["filename"],
                content=row["content"],
                similarity=row["similarity"],
                metadata=row.get("metadata", {})
            ))
        
        return results
    
    async def delete_cv(self, cv_id: str) -> bool:
        try:
            self.client.rpc("delete_cv", {"target_cv_id": cv_id}).execute()
            return True
        except Exception:
            return False
    
    async def list_cvs(self) -> List[Dict[str, Any]]:
        response = self.client.table("cvs").select("*").execute()
        return response.data
    
    async def get_stats(self) -> Dict[str, Any]:
        chunks = self.client.table("cv_embeddings").select("id", count="exact").execute()
        cvs = self.client.table("cvs").select("id", count="exact").execute()
        
        return {
            "total_chunks": chunks.count,
            "total_cvs": cvs.count,
            "storage_type": "supabase_pgvector"
        }
```

### 8. Cloud Mode - LLM (app/providers/cloud/llm.py)

```python
import time
from typing import Optional
import httpx
from app.providers.base import LLMProvider, LLMResult
from app.config import settings

class OpenRouterLLMProvider(LLMProvider):
    """LLM provider using OpenRouter API."""
    
    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.base_url = "https://openrouter.ai/api/v1"
        self.model = "google/gemini-2.0-flash-exp:free"
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048
    ) -> LLMResult:
        start = time.perf_counter()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
            )
            response.raise_for_status()
            data = response.json()
        
        latency = (time.perf_counter() - start) * 1000
        
        usage = data.get("usage", {})
        
        return LLMResult(
            text=data["choices"][0]["message"]["content"],
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            latency_ms=latency
        )
```

### 9. Provider Factory (app/providers/factory.py)

```python
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
```

### 10. RAG Service (app/services/rag_service.py)

```python
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from app.config import Mode, settings
from app.providers.factory import ProviderFactory
from app.providers.base import SearchResult
from app.prompts.templates import SYSTEM_PROMPT, QUERY_TEMPLATE

@dataclass
class RAGResponse:
    answer: str
    sources: List[Dict[str, Any]]
    metrics: Dict[str, float]
    mode: str

class RAGService:
    """Main RAG orchestration service."""
    
    def __init__(self, mode: Mode):
        self.mode = mode
        self.embedder = ProviderFactory.get_embedding_provider(mode)
        self.vector_store = ProviderFactory.get_vector_store(mode)
        self.llm = ProviderFactory.get_llm_provider(mode)
    
    async def index_documents(
        self,
        documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Index documents into the vector store."""
        if not documents:
            return {"indexed": 0, "errors": []}
        
        metrics = {}
        start = time.perf_counter()
        
        # Generate embeddings
        texts = [doc["content"] for doc in documents]
        embed_result = await self.embedder.embed_texts(texts)
        metrics["embedding_ms"] = embed_result.latency_ms
        
        # Store in vector store
        t0 = time.perf_counter()
        await self.vector_store.add_documents(documents, embed_result.embeddings)
        metrics["storage_ms"] = (time.perf_counter() - t0) * 1000
        
        metrics["total_ms"] = (time.perf_counter() - start) * 1000
        
        return {
            "indexed": len(documents),
            "tokens_used": embed_result.tokens_used,
            "metrics": metrics
        }
    
    async def query(
        self,
        question: str,
        k: int = 5,
        threshold: float = 0.3
    ) -> RAGResponse:
        """Query the RAG system."""
        metrics = {}
        
        # 1. Embed the question
        embed_result = await self.embedder.embed_query(question)
        metrics["embedding_ms"] = embed_result.latency_ms
        query_embedding = embed_result.embeddings[0]
        
        # 2. Search for relevant chunks
        t0 = time.perf_counter()
        search_results = await self.vector_store.search(
            query_embedding, k=k, threshold=threshold
        )
        metrics["search_ms"] = (time.perf_counter() - t0) * 1000
        
        # 3. Build context from results
        if not search_results:
            return RAGResponse(
                answer="I couldn't find any relevant information in the CVs to answer your question.",
                sources=[],
                metrics=metrics,
                mode=self.mode.value
            )
        
        context = self._build_context(search_results)
        
        # 4. Generate response
        prompt = QUERY_TEMPLATE.format(context=context, question=question)
        llm_result = await self.llm.generate(prompt, system_prompt=SYSTEM_PROMPT)
        metrics["llm_ms"] = llm_result.latency_ms
        
        # 5. Extract unique sources
        sources = self._extract_sources(search_results)
        
        metrics["total_ms"] = sum(metrics.values())
        metrics["prompt_tokens"] = llm_result.prompt_tokens
        metrics["completion_tokens"] = llm_result.completion_tokens
        
        return RAGResponse(
            answer=llm_result.text,
            sources=sources,
            metrics=metrics,
            mode=self.mode.value
        )
    
    def _build_context(self, results: List[SearchResult]) -> str:
        """Build context string from search results."""
        context_parts = []
        for i, result in enumerate(results, 1):
            context_parts.append(
                f"[Source {i}: {result.filename}]\n{result.content}"
            )
        return "\n\n---\n\n".join(context_parts)
    
    def _extract_sources(self, results: List[SearchResult]) -> List[Dict[str, Any]]:
        """Extract unique sources from results."""
        seen = set()
        sources = []
        for result in results:
            if result.cv_id not in seen:
                seen.add(result.cv_id)
                sources.append({
                    "cv_id": result.cv_id,
                    "filename": result.filename,
                    "relevance": round(result.similarity, 3)
                })
        return sources
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        store_stats = await self.vector_store.get_stats()
        return {
            "mode": self.mode.value,
            **store_stats
        }
```

### 11. Prompt Templates (app/prompts/templates.py)

```python
SYSTEM_PROMPT = """You are a CV screening assistant. Your ONLY job is to answer questions about candidate CVs that have been provided to you.

CRITICAL RULES:
1. ONLY use information from the provided CV excerpts. Never invent or assume information.
2. If the information is not in the provided CVs, say "I don't have information about that in the uploaded CVs."
3. Always cite which CV(s) your information comes from using the filename.
4. Be specific: include names, years of experience, company names, and specific skills when available.
5. If asked to compare candidates, create structured comparisons with clear criteria.
6. Never provide information about candidates that isn't explicitly stated in their CV.
7. If multiple CVs are relevant, mention all of them.

RESPONSE FORMAT:
- Start with a direct answer to the question
- List relevant candidates with specific details from their CVs
- Always mention the source filename(s) at the end

Remember: You can ONLY know what's in the CVs. No external knowledge about companies, technologies, or general career advice unless specifically asked."""

QUERY_TEMPLATE = """Based on the following CV excerpts, answer the user's question.

=== CV EXCERPTS ===
{context}
=== END CV EXCERPTS ===

User Question: {question}

Instructions:
1. Only use information from the CV excerpts above
2. If the answer isn't in the excerpts, clearly state that
3. Cite the candidate names and CV filenames
4. Be specific with details (years, companies, skills)

Answer:"""

GROUNDING_CHECK_TEMPLATE = """Review the following response for accuracy:

ORIGINAL CONTEXT:
{context}

GENERATED RESPONSE:
{response}

Check if the response:
1. Contains only information present in the context
2. Correctly attributes information to the right candidates
3. Does not make assumptions or add external information

If there are issues, list them. If the response is accurate, respond with "VERIFIED".

Verification:"""
```

### 12. API Routes (app/api/routes.py)

```python
import uuid
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Query, HTTPException, BackgroundTasks
from pydantic import BaseModel
from app.config import Mode, settings
from app.services.rag_service import RAGService
from app.services.pdf_service import PDFService
from app.services.chunking_service import ChunkingService

router = APIRouter(prefix="/api", tags=["CV Screener"])

# Request/Response Models
class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    sources: List[dict]
    conversation_id: str
    metrics: dict
    mode: str

class UploadResponse(BaseModel):
    job_id: str
    files_received: int
    status: str

class StatusResponse(BaseModel):
    job_id: str
    status: str
    total_files: int
    processed_files: int
    errors: List[str]

# In-memory job tracking (use Redis in production)
jobs = {}

# Endpoints
@router.post("/upload", response_model=UploadResponse)
async def upload_cvs(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    mode: Mode = Query(default=settings.default_mode)
):
    """Upload CV PDFs for processing."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    # Validate files
    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file.filename}. Only PDF files are accepted."
            )
    
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "processing",
        "total_files": len(files),
        "processed_files": 0,
        "errors": []
    }
    
    # Process in background
    background_tasks.add_task(process_cvs, job_id, files, mode)
    
    return UploadResponse(
        job_id=job_id,
        files_received=len(files),
        status="processing"
    )

async def process_cvs(job_id: str, files: List[UploadFile], mode: Mode):
    """Background task to process uploaded CVs."""
    pdf_service = PDFService()
    chunking_service = ChunkingService()
    rag_service = RAGService(mode)
    
    for file in files:
        try:
            # Read PDF content
            content = await file.read()
            
            # Extract text
            text = pdf_service.extract_text(content, file.filename)
            
            # Create chunks
            chunks = chunking_service.chunk_cv(
                text=text,
                cv_id=f"cv_{uuid.uuid4().hex[:8]}",
                filename=file.filename
            )
            
            # Index chunks
            await rag_service.index_documents(chunks)
            
            jobs[job_id]["processed_files"] += 1
            
        except Exception as e:
            jobs[job_id]["errors"].append(f"{file.filename}: {str(e)}")
    
    jobs[job_id]["status"] = "completed" if not jobs[job_id]["errors"] else "completed_with_errors"

@router.get("/status/{job_id}", response_model=StatusResponse)
async def get_status(job_id: str):
    """Check processing status."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    return StatusResponse(
        job_id=job_id,
        status=job["status"],
        total_files=job["total_files"],
        processed_files=job["processed_files"],
        errors=job["errors"]
    )

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    mode: Mode = Query(default=settings.default_mode)
):
    """Send a question and get RAG-powered response."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    rag_service = RAGService(mode)
    
    # Check if there are any CVs indexed
    stats = await rag_service.get_stats()
    if stats.get("total_cvs", 0) == 0:
        raise HTTPException(
            status_code=404,
            detail="No CVs indexed. Please upload CVs first."
        )
    
    result = await rag_service.query(request.message)
    
    return ChatResponse(
        response=result.answer,
        sources=result.sources,
        conversation_id=request.conversation_id or str(uuid.uuid4()),
        metrics=result.metrics,
        mode=result.mode
    )

@router.get("/cvs")
async def list_cvs(mode: Mode = Query(default=settings.default_mode)):
    """List all indexed CVs."""
    rag_service = RAGService(mode)
    vector_store = rag_service.vector_store
    cvs = await vector_store.list_cvs()
    return {"total": len(cvs), "cvs": cvs}

@router.delete("/cvs/{cv_id}")
async def delete_cv(
    cv_id: str,
    mode: Mode = Query(default=settings.default_mode)
):
    """Delete a CV from the index."""
    rag_service = RAGService(mode)
    success = await rag_service.vector_store.delete_cv(cv_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="CV not found")
    
    return {"success": True, "message": f"CV {cv_id} deleted"}

@router.get("/stats")
async def get_stats(mode: Mode = Query(default=settings.default_mode)):
    """Get system statistics."""
    rag_service = RAGService(mode)
    return await rag_service.get_stats()

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "default_mode": settings.default_mode}
```

### 13. PDF Service (app/services/pdf_service.py)

```python
import io
import pdfplumber

class PDFService:
    """Service for extracting text from PDF files."""
    
    def extract_text(self, content: bytes, filename: str) -> str:
        """Extract text from PDF bytes."""
        text_parts = []
        
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        
        full_text = "\n\n".join(text_parts)
        
        if not full_text.strip():
            raise ValueError(f"Could not extract text from {filename}")
        
        return self._clean_text(full_text)
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        # Remove excessive whitespace
        import re
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        text = text.strip()
        return text
```

### 14. Chunking Service (app/services/chunking_service.py)

```python
import re
from typing import List, Dict, Any

class ChunkingService:
    """Service for chunking CV text into meaningful sections."""
    
    # Common CV section headers
    SECTION_PATTERNS = [
        (r"(?i)(professional\s+)?summary", "summary"),
        (r"(?i)(work\s+)?experience", "experience"),
        (r"(?i)education", "education"),
        (r"(?i)skills", "skills"),
        (r"(?i)certifications?", "certifications"),
        (r"(?i)languages?", "languages"),
        (r"(?i)projects?", "projects"),
        (r"(?i)contact(\s+info(rmation)?)?", "contact"),
    ]
    
    def chunk_cv(
        self,
        text: str,
        cv_id: str,
        filename: str
    ) -> List[Dict[str, Any]]:
        """Chunk CV text into meaningful sections."""
        # Try section-based chunking first
        sections = self._extract_sections(text)
        
        if sections:
            chunks = []
            for i, (section_type, content) in enumerate(sections):
                if content.strip():
                    chunks.append({
                        "id": f"{cv_id}_chunk_{i}",
                        "cv_id": cv_id,
                        "filename": filename,
                        "chunk_index": i,
                        "content": content.strip(),
                        "metadata": {
                            "section_type": section_type
                        }
                    })
            return chunks
        
        # Fallback: chunk the entire CV as one piece
        # (CVs are usually small enough)
        return [{
            "id": f"{cv_id}_chunk_0",
            "cv_id": cv_id,
            "filename": filename,
            "chunk_index": 0,
            "content": text.strip(),
            "metadata": {
                "section_type": "full_cv"
            }
        }]
    
    def _extract_sections(self, text: str) -> List[tuple]:
        """Extract sections from CV text."""
        # Find all section headers and their positions
        section_positions = []
        
        for pattern, section_type in self.SECTION_PATTERNS:
            for match in re.finditer(pattern, text):
                section_positions.append((match.start(), section_type, match.group()))
        
        if not section_positions:
            return []
        
        # Sort by position
        section_positions.sort(key=lambda x: x[0])
        
        # Extract content between sections
        sections = []
        
        # Add header/contact info (content before first section)
        first_pos = section_positions[0][0]
        if first_pos > 50:  # Has substantial content before first section
            sections.append(("header", text[:first_pos]))
        
        # Extract each section's content
        for i, (pos, section_type, header) in enumerate(section_positions):
            # Find end of this section (start of next, or end of text)
            if i + 1 < len(section_positions):
                end_pos = section_positions[i + 1][0]
            else:
                end_pos = len(text)
            
            content = text[pos:end_pos]
            sections.append((section_type, content))
        
        return sections
```

### 15. Main Application (app/main.py)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.routes import router

app = FastAPI(
    title="CV Screener API",
    description="RAG-powered CV screening with dual mode (Local/Cloud)",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router)

@app.get("/")
async def root():
    return {
        "name": "CV Screener API",
        "version": "1.0.0",
        "default_mode": settings.default_mode,
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
```

---

## Frontend Implementation

### 1. Mode Switch Component (src/components/ModeSwitch.jsx)

```jsx
import React from 'react';

export default function ModeSwitch({ mode, onModeChange, disabled }) {
  return (
    <div className="flex items-center gap-4 p-3 bg-gray-100 rounded-lg">
      <span className="text-sm font-medium text-gray-700">Mode:</span>
      
      <div className="flex rounded-md shadow-sm">
        <button
          onClick={() => onModeChange('local')}
          disabled={disabled}
          className={`px-4 py-2 text-sm font-medium rounded-l-md border ${
            mode === 'local'
              ? 'bg-blue-600 text-white border-blue-600'
              : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
          } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          🖥️ Local
        </button>
        <button
          onClick={() => onModeChange('cloud')}
          disabled={disabled}
          className={`px-4 py-2 text-sm font-medium rounded-r-md border-t border-b border-r ${
            mode === 'cloud'
              ? 'bg-blue-600 text-white border-blue-600'
              : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
          } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          ☁️ Cloud
        </button>
      </div>
      
      <span className="text-xs text-gray-500">
        {mode === 'local' ? 'ChromaDB + Gemini' : 'Supabase + OpenRouter'}
      </span>
    </div>
  );
}
```

### 2. Metrics Bar Component (src/components/MetricsBar.jsx)

```jsx
import React from 'react';

export default function MetricsBar({ metrics, mode }) {
  if (!metrics) return null;
  
  const formatMs = (ms) => {
    if (ms === undefined || ms === null) return '-';
    return `${Math.round(ms)}ms`;
  };
  
  return (
    <div className="flex items-center gap-4 px-4 py-2 bg-gray-900 text-gray-300 text-xs font-mono">
      <span className="flex items-center gap-1">
        <span className="text-gray-500">Embed:</span>
        <span className="text-green-400">{formatMs(metrics.embedding_ms)}</span>
      </span>
      
      <span className="text-gray-600">|</span>
      
      <span className="flex items-center gap-1">
        <span className="text-gray-500">Search:</span>
        <span className="text-blue-400">{formatMs(metrics.search_ms)}</span>
      </span>
      
      <span className="text-gray-600">|</span>
      
      <span className="flex items-center gap-1">
        <span className="text-gray-500">LLM:</span>
        <span className="text-purple-400">{formatMs(metrics.llm_ms)}</span>
      </span>
      
      <span className="text-gray-600">|</span>
      
      <span className="flex items-center gap-1">
        <span className="text-gray-500">Total:</span>
        <span className="text-yellow-400 font-bold">{formatMs(metrics.total_ms)}</span>
      </span>
      
      <span className="ml-auto flex items-center gap-1">
        <span className="text-gray-500">Mode:</span>
        <span className={mode === 'local' ? 'text-cyan-400' : 'text-orange-400'}>
          {mode}
        </span>
      </span>
      
      {metrics.prompt_tokens && (
        <>
          <span className="text-gray-600">|</span>
          <span className="flex items-center gap-1">
            <span className="text-gray-500">Tokens:</span>
            <span className="text-gray-400">
              {metrics.prompt_tokens + (metrics.completion_tokens || 0)}
            </span>
          </span>
        </>
      )}
    </div>
  );
}
```

### 3. API Service (src/services/api.js)

```javascript
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
});

export async function uploadCVs(files, mode = 'local') {
  const formData = new FormData();
  files.forEach(file => formData.append('files', file));
  
  const response = await api.post(`/api/upload?mode=${mode}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
}

export async function getStatus(jobId) {
  const response = await api.get(`/api/status/${jobId}`);
  return response.data;
}

export async function sendMessage(message, mode = 'local', conversationId = null) {
  const response = await api.post(`/api/chat?mode=${mode}`, {
    message,
    conversation_id: conversationId,
  });
  return response.data;
}

export async function listCVs(mode = 'local') {
  const response = await api.get(`/api/cvs?mode=${mode}`);
  return response.data;
}

export async function deleteCV(cvId, mode = 'local') {
  const response = await api.delete(`/api/cvs/${cvId}?mode=${mode}`);
  return response.data;
}

export async function getStats(mode = 'local') {
  const response = await api.get(`/api/stats?mode=${mode}`);
  return response.data;
}

export default api;
```

### 4. useChat Hook (src/hooks/useChat.js)

```javascript
import { useState, useCallback } from 'react';
import { sendMessage } from '../services/api';

export default function useChat(mode) {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [lastMetrics, setLastMetrics] = useState(null);
  const [conversationId, setConversationId] = useState(null);
  
  const send = useCallback(async (text) => {
    if (!text.trim() || isLoading) return;
    
    // Add user message
    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: text,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    
    try {
      const response = await sendMessage(text, mode, conversationId);
      
      // Add assistant message
      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: response.response,
        sources: response.sources,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, assistantMessage]);
      
      // Update metrics
      setLastMetrics(response.metrics);
      setConversationId(response.conversation_id);
      
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: `Error: ${error.response?.data?.detail || error.message}`,
        isError: true,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, [mode, conversationId, isLoading]);
  
  const clear = useCallback(() => {
    setMessages([]);
    setLastMetrics(null);
    setConversationId(null);
  }, []);
  
  return {
    messages,
    isLoading,
    lastMetrics,
    send,
    clear,
  };
}
```

---

## Dependencies

### requirements.txt

```
# Core
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6
pydantic==2.5.3
pydantic-settings==2.1.0
python-dotenv==1.0.0

# PDF Processing
pdfplumber==0.10.3

# Local Mode
sentence-transformers==2.2.2
chromadb==0.4.22
google-generativeai==0.3.2

# Cloud Mode
httpx==0.26.0
supabase==2.3.4

# Utilities
tenacity==8.2.3

# Testing
pytest==7.4.4
pytest-asyncio==0.23.3
```

### package.json

```json
{
  "name": "cv-screener-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "axios": "^1.6.5",
    "react-dropzone": "^14.2.3",
    "react-markdown": "^9.0.1",
    "lucide-react": "^0.312.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.1",
    "autoprefixer": "^10.4.17",
    "postcss": "^8.4.33",
    "tailwindcss": "^3.4.1",
    "vite": "^5.0.12"
  }
}
```

---

## Quick Start

```bash
# 1. Clone and setup backend
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 3. Start backend
uvicorn app.main:app --reload

# 4. Setup frontend (new terminal)
cd frontend
npm install
npm run dev

# 5. Open http://localhost:5173
```

---

## Testing the Modes

```bash
# Test Local Mode
curl "http://localhost:8000/api/stats?mode=local"

# Test Cloud Mode
curl "http://localhost:8000/api/stats?mode=cloud"

# Upload CVs (Local)
curl -X POST "http://localhost:8000/api/upload?mode=local" \
  -F "files=@cv1.pdf" -F "files=@cv2.pdf"

# Chat (Cloud)
curl -X POST "http://localhost:8000/api/chat?mode=cloud" \
  -H "Content-Type: application/json" \
  -d '{"message": "Who has Python experience?"}'
```

---

## Success Criteria

- [ ] Mode switch toggles between Local and Cloud
- [ ] Metrics bar shows timing for each stage
- [ ] Local mode works offline (except LLM)
- [ ] Cloud mode uses Supabase + OpenRouter
- [ ] Both modes return consistent response format
- [ ] Sources are displayed correctly
- [ ] Performance can be compared between modes