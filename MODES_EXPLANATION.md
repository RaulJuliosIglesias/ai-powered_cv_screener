# Diferencias entre LOCAL y CLOUD

## ✅ LO QUE ES IGUAL EN AMBOS MODOS

**Ambos modos usan OpenRouter para LLM**:
- Chat queries → OpenRouterLLMProvider
- Query understanding → OpenRouter
- Reranking → OpenRouter
- Generation → OpenRouter
- Verification → OpenRouter

## 🔀 LO QUE CAMBIA ENTRE MODOS

### Modo LOCAL
- **Embeddings**: `LocalEmbeddingProvider`
  - Prioridad 1: sentence-transformers (all-MiniLM-L6-v2) - 384 dims
  - Prioridad 2: OpenRouter API (nomic-embed) - 768 dims
  - Prioridad 3: Hash fallback - 384 dims
- **Storage**: ChromaDB (`SimpleVectorStore`)
  - Archivo local: `./chroma_db`
- **PDF Storage**: Sistema de archivos local

### Modo CLOUD
- **Embeddings**: `OpenRouterEmbeddingProvider`
  - OpenRouter API (nomic-embed-text-v1.5) - 768 dims
- **Storage**: Supabase pgvector (`SupabaseVectorStore`)
  - Tabla: `cv_embeddings`
  - Vector dimension: 768
- **PDF Storage**: Supabase Storage bucket `cv-pdfs`

---

## 📁 Código que separa los modos

### `backend/app/providers/factory.py`

```python
# Embeddings - SEPARADOS
def get_embedding_provider(mode):
    if mode == Mode.CLOUD:
        return OpenRouterEmbeddingProvider()  # nomic-embed vía API
    else:
        return LocalEmbeddingProvider()  # sentence-transformers o fallback

# Vector Store - SEPARADOS
def get_vector_store(mode):
    if mode == Mode.CLOUD:
        return SupabaseVectorStore()  # Supabase pgvector
    else:
        return SimpleVectorStore()  # ChromaDB local

# LLM - MISMO PARA AMBOS
def get_llm_provider(mode, model):
    return OpenRouterLLMProvider(model=model)  # Siempre OpenRouter
```

---

## ✅ Estado actual del código

Los modos NO están mezclados:

1. **LOCAL mode** usa:
   - ✅ LocalEmbeddingProvider (línea 20-21 factory.py)
   - ✅ SimpleVectorStore/ChromaDB (línea 34-35 factory.py)
   - ✅ OpenRouterLLMProvider (línea 58-59 factory.py)

2. **CLOUD mode** usa:
   - ✅ OpenRouterEmbeddingProvider (línea 17-18 factory.py)
   - ✅ SupabaseVectorStore (línea 31-32 factory.py)
   - ✅ OpenRouterLLMProvider (línea 58-59 factory.py)

---

## 🔧 Lo que se arregló

**Problema**: `index_documents()` fallaba con "Providers not initialized" en CLOUD mode

**Solución**: `from_factory()` ahora inicializa embedder y vector_store inmediatamente:
- Permite subir CVs y crear embeddings en AMBOS modos
- LLM providers se inicializan lazy cuando se hace una query (necesitan el modelo del frontend)

**Archivos modificados**: 
- `backend/app/services/rag_service_v5.py` líneas 737-750

**NO se tocó**:
- ✅ factory.py - separación de modos intacta
- ✅ local/embeddings.py - embeddings locales intactos
- ✅ local/vector_store.py - ChromaDB intacto
- ✅ cloud/embeddings.py - OpenRouter embeddings intacto
- ✅ cloud/vector_store.py - Supabase intacto
