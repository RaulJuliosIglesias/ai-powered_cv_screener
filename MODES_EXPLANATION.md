# Diferencias entre LOCAL y CLOUD

> **Última actualización:** Enero 2026 - v6.0

---

## ✅ LO QUE ES IGUAL EN AMBOS MODOS

**Ambos modos usan OpenRouter para LLM**:
- Query understanding → OpenRouter (free models with fallback chain)
- Reranking → OpenRouter
- Generation → OpenRouter (user-selected model)
- Verification → OpenRouter

**Ambos modos usan la misma arquitectura**:
- RAG Pipeline v5 (`rag_service_v5.py`)
- Output Orchestrator con 9 Structures y 29+ Modules
- Query Understanding Service
- Suggestion Engine
- Session-based CV management

---

## 🔀 LO QUE CAMBIA ENTRE MODOS

### Modo LOCAL (`mode=local`)

| Componente | Implementación | Detalles |
|------------|----------------|----------|
| **Embeddings** | `LocalEmbeddingProvider` | sentence-transformers all-MiniLM-L6-v2 (384 dims) |
| **Vector Store** | `SimpleVectorStore` | ChromaDB local (`./chroma_db`) |
| **PDF Storage** | Sistema de archivos | Directorio `./storage/` |
| **Sessions** | `SessionManager` | JSON file (`backend/data/sessions.json`) |

### Modo CLOUD (`mode=cloud`)

| Componente | Implementación | Detalles |
|------------|----------------|----------|
| **Embeddings** | `OpenRouterEmbeddingProvider` | nomic-embed-text-v1.5 (768 dims) |
| **Vector Store** | `SupabaseVectorStore` | pgvector con RPC `match_cv_embeddings` |
| **PDF Storage** | Supabase Storage | Bucket `cv-pdfs` |
| **Sessions** | `SupabaseSessionManager` | Tablas: sessions, session_cvs, session_messages |

---

## 📁 Código que separa los modos

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
            return SimpleVectorStore()  # ChromaDB

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

## ✅ Estado actual del código (v6.0)

Los modos están correctamente separados:

| Componente | LOCAL | CLOUD |
|------------|-------|-------|
| Embeddings | ✅ LocalEmbeddingProvider | ✅ OpenRouterEmbeddingProvider |
| Vector Store | ✅ SimpleVectorStore (ChromaDB) | ✅ SupabaseVectorStore |
| PDF Storage | ✅ Local filesystem | ✅ Supabase Storage |
| Sessions | ✅ JSON file | ✅ Supabase tables |
| LLM | ✅ OpenRouter | ✅ OpenRouter |

---

## 🔧 Configuración

### Variables de entorno

```bash
# Mode selection
DEFAULT_MODE=local  # or "cloud"

# Required for CLOUD mode
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key

# Required for both modes (LLM)
OPENROUTER_API_KEY=your-openrouter-key
```

### Cambiar modo en runtime

El modo se puede cambiar via query parameter en cualquier endpoint:
```
GET /api/sessions?mode=cloud
POST /api/sessions/{id}/chat?mode=local
```

---

## 📊 Comparación de dimensiones

| Modo | Modelo de Embedding | Dimensiones |
|------|---------------------|-------------|
| LOCAL | all-MiniLM-L6-v2 | 384 |
| CLOUD | nomic-embed-text-v1.5 | 768 |

**Importante**: Los embeddings de LOCAL y CLOUD no son compatibles entre sí debido a las diferentes dimensiones.
