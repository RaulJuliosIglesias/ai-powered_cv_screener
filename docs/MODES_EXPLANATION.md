# Differences Between LOCAL and CLOUD

> **Last Updated:** January 2026 - v6.0

---

## ✅ WHAT IS THE SAME IN BOTH MODES

**Both modes use OpenRouter for LLM**:
- Query understanding → OpenRouter (free models with fallback chain)
- Reranking → OpenRouter
- Generation → OpenRouter (user-selected model)
- Verification → OpenRouter

**Both modes use the same architecture**:
- RAG Pipeline v5 (`rag_service_v5.py`)
- Output Orchestrator with 9 Structures and 29+ Modules
- Query Understanding Service
- Suggestion Engine
- Session-based CV management

---

## 🔀 WHAT CHANGES BETWEEN MODES

### LOCAL Mode (`mode=local`)

| Component | Implementation | Details |
|-----------|----------------|---------|
| **Embeddings** | `LocalEmbeddingProvider` | sentence-transformers all-MiniLM-L6-v2 (384 dims) |
| **Vector Store** | `SimpleVectorStore` | JSON persistence (`./data/vectors.json`) |
| **PDF Storage** | File system | Directory `./storage/` |
| **Sessions** | `SessionManager` | JSON file (`backend/data/sessions.json`) |

### CLOUD Mode (`mode=cloud`)

| Component | Implementation | Details |
|-----------|----------------|---------|
| **Embeddings** | `OpenRouterEmbeddingProvider` | nomic-embed-text-v1.5 (768 dims) |
| **Vector Store** | `SupabaseVectorStore` | pgvector with RPC `match_cv_embeddings` |
| **PDF Storage** | Supabase Storage | Bucket `cv-pdfs` |
| **Sessions** | `SupabaseSessionManager` | Tables: sessions, session_cvs, session_messages |

---

## 📁 Code That Separates the Modes

### `backend/app/providers/factory.py`

```python
class ProviderFactory:
    @classmethod
    def get_embedding_provider(cls, mode: Mode) -> EmbeddingProvider:
        if mode == Mode.CLOUD:
            return OpenRouterEmbeddingProvider()  # 768 dims
        else:
            return LocalEmbeddingProvider()  # 384 dims

    @classmethod
    def get_vector_store(cls, mode: Mode) -> VectorStoreProvider:
        if mode == Mode.CLOUD:
            return SupabaseVectorStore()
        else:
            return SimpleVectorStore()  # JSON persistence

    @classmethod
    def get_llm_provider(cls, mode: Mode, model: str) -> LLMProvider:
        return OpenRouterLLMProvider(model=model)  # Same for both
```

### `backend/app/api/routes_sessions.py`

```python
def get_session_manager(mode: Mode):
    if mode == Mode.CLOUD:
        return supabase_session_manager
    return session_manager  # Local JSON-based
```

---

## 🗄️ Supabase Schema (Cloud Mode)

```sql
-- Tables
cvs (id, filename, upload_date, metadata)
cv_embeddings (id, cv_id, content, embedding vector(768), metadata)
sessions (id, name, description, created_at, updated_at)
session_cvs (session_id, cv_id, added_at)
session_messages (session_id, role, content, sources, pipeline_steps, structured_output)

-- RPC Function
match_cv_embeddings(query_embedding, match_count, match_threshold)

-- Storage
Bucket: cv-pdfs (public read, authenticated upload)
```

Setup script: `scripts/setup_supabase_complete.sql`

---

## ✅ Current Code Status (v6.0)

The modes are correctly separated:

| Component | LOCAL | CLOUD |
|-----------|-------|-------|
| Embeddings | ✅ LocalEmbeddingProvider | ✅ OpenRouterEmbeddingProvider |
| Vector Store | ✅ SimpleVectorStore (JSON) | ✅ SupabaseVectorStore |
| PDF Storage | ✅ Local filesystem | ✅ Supabase Storage |
| Sessions | ✅ JSON file | ✅ Supabase tables |
| LLM | ✅ OpenRouter | ✅ OpenRouter |

---

## 🔧 Configuration

### Environment Variables

```bash
# Mode selection
DEFAULT_MODE=local  # or "cloud"

# Required for CLOUD mode
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key

# Required for both modes (LLM)
OPENROUTER_API_KEY=your-openrouter-key
```

### Change Mode at Runtime

The mode can be changed via query parameter on any endpoint:
```
GET /api/sessions?mode=cloud
POST /api/sessions/{id}/chat?mode=local
```

---

## 📊 Dimension Comparison

| Mode | Embedding Model | Dimensions |
|------|-----------------|------------|
| LOCAL | all-MiniLM-L6-v2 | 384 |
| CLOUD | nomic-embed-text-v1.5 | 768 |

**Important**: LOCAL and CLOUD embeddings are not compatible with each other due to different dimensions.
