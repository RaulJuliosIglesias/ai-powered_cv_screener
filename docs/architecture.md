# CV Screener - Architecture Documentation

## System Overview: Dual Mode Architecture

The CV Screener supports **two switchable backend modes**: Local and Cloud. Users can toggle between modes via the UI to compare performance.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (React + Vite)                        │
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
│  │   │ SentenceTransf. │         │ OpenRouter API  │                     │  │
│  │   │ ChromaDB        │         │ Supabase        │                     │  │
│  │   │ Gemini (Google) │         │ OpenRouter LLM  │                     │  │
│  │   └─────────────────┘         └─────────────────┘                     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         RAG SERVICE                                   │  │
│  │   Unified interface regardless of mode                                │  │
│  │   - index_documents(chunks) → embeds and stores                       │  │
│  │   - query(question) → retrieves, generates, returns with sources      │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Technology Stack

### Local Mode
| Component | Technology | Purpose |
|-----------|------------|---------|
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) | Local embedding generation (384 dims) |
| Vector Store | ChromaDB | Local persistent vector database |
| LLM | Google Gemini (gemini-1.5-flash) | Response generation via Google AI Studio |

### Cloud Mode
| Component | Technology | Purpose |
|-----------|------------|---------|
| Embeddings | OpenRouter (nomic-embed-text-v1.5) | API-based embeddings (768 dims) |
| Vector Store | Supabase pgvector | Cloud PostgreSQL with vector extension |
| LLM | OpenRouter (gemini-2.0-flash-exp:free) | API-based LLM |

### Shared Components
| Component | Technology | Purpose |
|-----------|------------|---------|
| Backend | FastAPI + Python 3.11+ | REST API |
| PDF Extraction | pdfplumber | Text extraction from PDFs |
| Frontend | React 18 + Vite | User interface |
| Styling | TailwindCSS | CSS framework |

## Component Details

### Frontend (React + Vite)

**Key Components:**
- `App.jsx` - Main application state management with mode switching
- `ModeSwitch.jsx` - Toggle between Local/Cloud modes
- `MetricsBar.jsx` - Real-time performance metrics display
- `UploadZone.jsx` - Drag & drop file upload
- `ProcessingStatus.jsx` - Real-time processing feedback
- `CVList.jsx` - Sidebar with indexed CVs
- `ChatWindow.jsx` - Chat interface container
- `Message.jsx` - Message bubbles with source citations

**Custom Hooks:**
- `useMode.js` - Mode state management with localStorage persistence
- `useChat.js` - Chat state with metrics tracking
- `useUpload.js` - File upload and processing status

### Backend (FastAPI)

**Directory Structure:**
```
backend/app/
├── api/
│   └── routes_v2.py          # API endpoints with ?mode= parameter
├── providers/
│   ├── base.py               # Abstract interfaces
│   ├── factory.py            # Provider factory (singleton pattern)
│   ├── local/
│   │   ├── embeddings.py     # SentenceTransformers
│   │   ├── vector_store.py   # ChromaDB
│   │   └── llm.py            # Google Gemini
│   └── cloud/
│       ├── embeddings.py     # OpenRouter embeddings
│       ├── vector_store.py   # Supabase pgvector
│       └── llm.py            # OpenRouter LLM
├── services/
│   ├── chunking_service.py   # CV text chunking by sections
│   └── rag_service_v2.py     # RAG orchestration
├── prompts/
│   └── templates.py          # LLM prompt templates
└── config.py                 # Settings with Mode enum
```

### Provider Factory Pattern

```python
class ProviderFactory:
    @classmethod
    def get_embedding_provider(cls, mode: Mode) -> EmbeddingProvider:
        if mode == Mode.LOCAL:
            return LocalEmbeddingProvider()  # SentenceTransformers
        else:
            return OpenRouterEmbeddingProvider()  # OpenRouter API
```

## Data Flow

### Upload Flow
```
PDF Files → pdfplumber → Text Extraction → ChunkingService
                                               │
                                    ┌──────────┴──────────┐
                                    ▼                     ▼
                              LOCAL MODE             CLOUD MODE
                                    │                     │
                         SentenceTransformers      OpenRouter API
                                    │                     │
                              ChromaDB             Supabase pgvector
```

### Query Flow
```
User Question + Mode
        │
        ▼
┌───────────────────────────────────────────────────────────┐
│                     RAG Service                           │
│  1. Embed query (mode-specific provider)                  │
│  2. Vector search (mode-specific store)                   │
│  3. Build prompt with context                             │
│  4. Generate response (mode-specific LLM)                 │
│  5. Return answer + sources + metrics                     │
└───────────────────────────────────────────────────────────┘
        │
        ▼
Response with:
- Answer text
- Source citations (cv_id, filename, relevance)
- Performance metrics (embedding_ms, search_ms, llm_ms, total_ms)
- Mode indicator
```

## Database Schemas

### Local Mode (ChromaDB)
- Collection: `cv_collection`
- Embedding dimensions: 384 (all-MiniLM-L6-v2)
- Distance metric: Cosine

### Cloud Mode (Supabase pgvector)
```sql
-- cv_embeddings table
create table cv_embeddings (
  id uuid primary key,
  cv_id text not null,
  filename text not null,
  chunk_index integer not null,
  content text not null,
  embedding vector(768),  -- nomic-embed dimensions
  metadata jsonb,
  created_at timestamptz,
  unique(cv_id, chunk_index)
);

-- Vector similarity search function
create function match_cv_embeddings(
  query_embedding vector(768),
  match_count int,
  match_threshold float
) returns table (...);
```

## API Endpoints

All endpoints accept `?mode=local` or `?mode=cloud`:

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/upload` | Upload PDF files |
| GET | `/api/status/{job_id}` | Check processing status |
| POST | `/api/chat` | Send query, get RAG response |
| GET | `/api/cvs` | List indexed CVs |
| DELETE | `/api/cvs/{cv_id}` | Remove a CV |
| GET | `/api/stats` | Get system statistics |
| GET | `/api/health` | Health check |

## Security Considerations

1. **API Keys:** Stored in `.env`, excluded via `.gitignore`
2. **Service Keys:** Supabase service_role key for server-side only
3. **CORS:** Restricted to frontend origin
4. **Input Validation:** Pydantic models for all requests

## Performance Comparison

| Metric | Local Mode | Cloud Mode |
|--------|------------|------------|
| Embedding latency | ~50-100ms | ~200-500ms |
| Search latency | ~5-20ms | ~50-200ms |
| LLM latency | ~500-2000ms | ~800-3000ms |
| Offline capable | Yes (except LLM) | No |
| Storage | Local disk | Cloud (Supabase) |
| Cost | Free (local compute) | API usage costs |

## Scaling Considerations

For production:
- Replace in-memory job storage with Redis
- Add authentication/authorization
- Implement request queuing for large uploads
- Add caching layer for frequent queries
- Consider dedicated vector database (Pinecone, Weaviate) for scale
