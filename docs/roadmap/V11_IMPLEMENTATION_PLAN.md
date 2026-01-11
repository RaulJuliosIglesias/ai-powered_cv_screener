# RAG v11 Implementation Plan

> **Status**: 📋 PLANNED
> 
> **Date**: January 2026
> 
> **Prerequisites**: RAG v10 (Auth, RLS, CI/CD) ✅
>
> **💰 Cost Philosophy**: $0 en servicios fijos. PostgreSQL FTS (gratis en Supabase). Sin Elasticsearch.

---

## 🗺️ Roadmap Vision: V11 Position

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ROADMAP OVERVIEW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  V8 ✅    V9 ✅         V10 ✅           V11 (Current)      V12             │
│  ───────  ───────       ───────          ───────            ───             │
│  UX       TypeScript    Multi-Tenant     Advanced           Simple          │
│  Features + CI/CD       + Auth           Features           Deploy          │
│           + Cloud                                                            │
│                                                                              │
│  ✅ Done  ✅ Done       ✅ Done          • PG FTS (FREE)    • Vercel        │
│                                          • LangGraph          (FREE)        │
│                                          • Analytics        • Render        │
│                                          • Mejorar Hybrid     (FREE)        │
│                                                                              │
│  🧪 LOCAL 📘 TS         🔐 AUTH          🚀 ADVANCED        🌐 PROD         │
│  Done     + ☁️ CLOUD    Supabase FREE    PG FTS + LangGraph Simple deploy   │
│           + 🔄 CI/CD    RLS included     $0 adicional       $0 hasta escalar│
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ❌ Por Qué NO Elasticsearch

| Factor | Elasticsearch | PostgreSQL FTS (Ya tienes) |
|--------|---------------|---------------------------|
| **Costo** | $95-200/mes | $0 (incluido en Supabase) |
| **Complejidad** | Alta (cluster, shards) | Baja (ya integrado) |
| **BM25** | ✅ | ✅ tsvector + GIN |
| **Vector** | ✅ dense_vector | ✅ pgvector |
| **Hybrid** | ✅ | ✅ Ya lo tienes en V8 |
| **Tu escala** | Millones docs | Miles docs (suficiente) |

**Conclusión**: Elasticsearch es overkill para <100K chunks. PostgreSQL FTS + pgvector es suficiente y GRATIS.

---

## Executive Summary

RAG v11 focuses on **mejorar lo que ya tienes** sin añadir servicios de pago:

### 🎯 Key Objectives

1. **PostgreSQL Full-Text Search** - Migrar BM25 local a PG FTS (cloud-ready, gratis)
2. **LangGraph Pipeline** - Flujos RAG stateful con memoria (librería open source)
3. **Analytics Básico** - Métricas en Supabase (tablas, no servicios externos)
4. **Mejorar Hybrid Search** - Fuzzy matching, sinónimos, stemming

### 📊 Impact

| Pillar | Benefit | Costo |
|--------|---------|-------|
| PostgreSQL FTS | BM25 en cloud, fuzzy, stemming | $0 (Supabase) |
| LangGraph | Queries complejas, memoria | $0 (open source) |
| Analytics | Métricas de calidad | $0 (tablas Supabase) |

---

## Timeline Overview

| Phase | Focus | Duration | Features |
|-------|-------|----------|----------|
| **Phase 1** | PostgreSQL FTS (Cloud) | 2 días | Migrar BM25 local → PG FTS |
| **Phase 2** | LangGraph Pipeline | 4 días | Stateful RAG, memoria |
| **Phase 3** | Analytics Básico | 2 días | Tablas de métricas en Supabase |
| **Phase 4** | Mejorar Hybrid Search | 2 días | Fuzzy, sinónimos, tuning |
| **Total** | | **10 días** | **4 phases** |

---

## 🔍 Phase 1: PostgreSQL Full-Text Search (2 días)

**Objetivo**: Migrar BM25 local (rank-bm25) a PostgreSQL FTS para que funcione en modo cloud.

### 1.1 Añadir tsvector a tabla cvs
**Time**: 0.5 días | **Priority**: 🔴 CRÍTICA

Ya tienes `hybrid_search_service.py` funcionando con `rank-bm25` local. Ahora lo migramos a PostgreSQL para el modo cloud.

**SQL Migration**:
```sql
-- Añadir columna tsvector para Full-Text Search
ALTER TABLE cv_embeddings ADD COLUMN IF NOT EXISTS 
  fts_content tsvector 
  GENERATED ALWAYS AS (to_tsvector('english', chunk_text)) STORED;

-- Índice GIN para búsqueda rápida
CREATE INDEX IF NOT EXISTS idx_cv_embeddings_fts 
  ON cv_embeddings USING GIN(fts_content);

-- Función de búsqueda híbrida (BM25 + Vector)
CREATE OR REPLACE FUNCTION hybrid_search_v11(
  query_text TEXT,
  query_embedding vector(768),
  p_session_id UUID,
  p_user_id UUID,
  match_count INT DEFAULT 20,
  bm25_weight FLOAT DEFAULT 0.3,
  vector_weight FLOAT DEFAULT 0.7
)
RETURNS TABLE (
  chunk_id UUID,
  cv_id UUID,
  chunk_text TEXT,
  filename TEXT,
  bm25_score FLOAT,
  vector_score FLOAT,
  combined_score FLOAT
) AS $$
BEGIN
  RETURN QUERY
  WITH bm25_results AS (
    SELECT 
      ce.id as chunk_id,
      ce.cv_id,
      ce.chunk_text,
      c.filename,
      ts_rank_cd(ce.fts_content, plainto_tsquery('english', query_text)) as bm25_score
    FROM cv_embeddings ce
    JOIN cvs c ON ce.cv_id = c.id
    JOIN sessions s ON c.session_id = s.id
    WHERE ce.fts_content @@ plainto_tsquery('english', query_text)
      AND c.session_id = p_session_id
      AND s.user_id = p_user_id
    ORDER BY bm25_score DESC
    LIMIT match_count * 2
  ),
  vector_results AS (
    SELECT 
      ce.id as chunk_id,
      ce.cv_id,
      ce.chunk_text,
      c.filename,
      1 - (ce.embedding <=> query_embedding) as vector_score
    FROM cv_embeddings ce
    JOIN cvs c ON ce.cv_id = c.id
    JOIN sessions s ON c.session_id = s.id
    WHERE c.session_id = p_session_id
      AND s.user_id = p_user_id
    ORDER BY ce.embedding <=> query_embedding
    LIMIT match_count * 2
  ),
  combined AS (
    SELECT 
      COALESCE(b.chunk_id, v.chunk_id) as chunk_id,
      COALESCE(b.cv_id, v.cv_id) as cv_id,
      COALESCE(b.chunk_text, v.chunk_text) as chunk_text,
      COALESCE(b.filename, v.filename) as filename,
      COALESCE(b.bm25_score, 0) as bm25_score,
      COALESCE(v.vector_score, 0) as vector_score,
      (bm25_weight * COALESCE(b.bm25_score, 0) + 
       vector_weight * COALESCE(v.vector_score, 0)) as combined_score
    FROM bm25_results b
    FULL OUTER JOIN vector_results v ON b.chunk_id = v.chunk_id
  )
  SELECT * FROM combined
  ORDER BY combined_score DESC
  LIMIT match_count;
END;
$$ LANGUAGE plpgsql;
```

---

### 1.2 Actualizar hybrid_search_service.py para Cloud
**Time**: 1 día | **Priority**: 🔴 CRÍTICA

**Modificar** `backend/app/services/hybrid_search_service.py`:

```python
# Añadir método para modo cloud
async def search_cloud(
    self,
    query: str,
    query_embedding: List[float],
    session_id: str,
    user_id: str,
    k: int = 20
) -> HybridSearchResponse:
    """Hybrid search using PostgreSQL FTS + pgvector (cloud mode)."""
    supabase = get_supabase_client()
    
    # Llamar función RPC
    result = await supabase.rpc('hybrid_search_v11', {
        'query_text': query,
        'query_embedding': query_embedding,
        'p_session_id': session_id,
        'p_user_id': user_id,
        'match_count': k
    }).execute()
    
    # Convertir a HybridSearchResult
    results = [
        HybridSearchResult(
            chunk_id=r['chunk_id'],
            content=r['chunk_text'],
            metadata={'filename': r['filename']},
            final_score=r['combined_score'],
            bm25_score=r['bm25_score'],
            vector_score=r['vector_score']
        )
        for r in result.data
    ]
    
    return HybridSearchResponse(
        results=results,
        bm25_count=len([r for r in results if r.bm25_score > 0]),
        vector_count=len([r for r in results if r.vector_score > 0]),
        fused_count=len(results),
        strategy="pg_fts_hybrid"
    )
```

---

### 1.3 Integrar con RAG Service
**Time**: 0.5 días | **Priority**: 🔴 ALTA

En `rag_service_v5.py`, detectar modo y usar el método correcto:

```python
if self.config.mode == Mode.CLOUD:
    hybrid_response = await hybrid_service.search_cloud(
        query=query,
        query_embedding=embedding,
        session_id=session_id,
        user_id=user_id,
        k=k
    )
else:
    # Modo local usa rank-bm25 (ya implementado)
    hybrid_response = hybrid_service.search(
        query=query,
        vector_results=vector_results,
        session_id=session_id,
        k=k
    )
```
    }
  },
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "analysis": {
      "analyzer": {
        "cv_analyzer": {
          "type": "custom",
          "tokenizer": "standard",
          "filter": ["lowercase", "english_stemmer", "english_stop"]
        }
      },
      "filter": {
        "english_stemmer": {
          "type": "stemmer",
          "language": "english"
        },
        "english_stop": {
          "type": "stop",
          "stopwords": "_english_"
        }
      }
    }
  }
}
```

---

### 1.3 Elasticsearch Client
**Time**: 0.5 días | **Priority**: 🔴 CRÍTICA

**client.py**:
```python
"""
Elasticsearch client wrapper with connection pooling and error handling.
"""
import logging
from typing import Optional, List, Dict, Any
from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import ConnectionError, NotFoundError

from app.config import settings

logger = logging.getLogger(__name__)


class ElasticsearchClient:
    """Async Elasticsearch client with retry and health checking."""
    
    def __init__(
        self,
        url: str = None,
        api_key: str = None,
        index_prefix: str = "cv_screener"
    ):
        self.url = url or settings.elasticsearch_url
        self.api_key = api_key or settings.elasticsearch_api_key
        self.index_prefix = index_prefix
        self._client: Optional[AsyncElasticsearch] = None
    
    async def get_client(self) -> AsyncElasticsearch:
        """Get or create ES client."""
        if self._client is None:
            self._client = AsyncElasticsearch(
                hosts=[self.url],
                api_key=self.api_key,
                retry_on_timeout=True,
                max_retries=3
            )
        return self._client
    
    async def health_check(self) -> bool:
        """Check ES cluster health."""
        try:
            client = await self.get_client()
            health = await client.cluster.health()
            return health["status"] in ["green", "yellow"]
        except Exception as e:
            logger.error(f"ES health check failed: {e}")
            return False
    
    def get_index_name(self, index_type: str) -> str:
        """Get full index name with prefix."""
        return f"{self.index_prefix}_{index_type}"
    
    async def close(self):
        """Close ES client."""
        if self._client:
            await self._client.close()
            self._client = None


# Singleton instance
_es_client: Optional[ElasticsearchClient] = None

def get_elasticsearch_client() -> ElasticsearchClient:
    global _es_client
    if _es_client is None:
        _es_client = ElasticsearchClient()
    return _es_client
```

---

### 1.4 Hybrid Search Implementation
**Time**: 1.5 días | **Priority**: 🔴 CRÍTICA

**search_service.py**:
```python
"""
Elasticsearch Hybrid Search Service.

Combines BM25 (lexical) with dense vector (semantic) search
using Reciprocal Rank Fusion (RRF) for optimal retrieval.
"""
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import asyncio

from app.providers.elasticsearch.client import get_elasticsearch_client

logger = logging.getLogger(__name__)


@dataclass
class HybridSearchResult:
    """Result from hybrid search."""
    chunk_id: str
    cv_id: str
    filename: str
    candidate_name: str
    chunk_text: str
    chunk_index: int
    
    # Scores
    bm25_score: float
    vector_score: float
    combined_score: float
    
    # Metadata
    metadata: Dict[str, Any]


class ElasticsearchHybridSearch:
    """
    Enterprise-grade hybrid search combining:
    - BM25 for exact keyword matching
    - Dense vector for semantic similarity
    - RRF for score fusion
    
    Performance targets:
    - p50 latency: <50ms
    - p99 latency: <200ms
    """
    
    # RRF constant (higher = more weight to lower ranks)
    RRF_K = 60
    
    def __init__(
        self,
        bm25_weight: float = 0.4,
        vector_weight: float = 0.6,
        min_score: float = 0.1
    ):
        self.es = get_elasticsearch_client()
        self.bm25_weight = bm25_weight
        self.vector_weight = vector_weight
        self.min_score = min_score
        self.index_name = self.es.get_index_name("cv_chunks")
    
    async def hybrid_search(
        self,
        query: str,
        query_embedding: List[float],
        session_id: str,
        user_id: str,
        k: int = 20,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[HybridSearchResult]:
        """
        Execute hybrid search with BM25 + vector + RRF fusion.
        
        Args:
            query: Text query for BM25
            query_embedding: Dense vector for semantic search
            session_id: Filter by session
            user_id: Filter by user (for RLS)
            k: Number of results to return
            filters: Additional filters (skills, experience, etc.)
            
        Returns:
            List of HybridSearchResult sorted by combined score
        """
        client = await self.es.get_client()
        
        # Build filter query
        filter_clauses = [
            {"term": {"session_id": session_id}},
            {"term": {"user_id": user_id}}
        ]
        
        if filters:
            if "skills" in filters:
                filter_clauses.append({
                    "terms": {"metadata.skills": filters["skills"]}
                })
            if "min_experience" in filters:
                filter_clauses.append({
                    "range": {"metadata.experience_years": {"gte": filters["min_experience"]}}
                })
        
        # Execute BM25 and vector search in parallel
        bm25_task = self._bm25_search(client, query, filter_clauses, k * 2)
        vector_task = self._vector_search(client, query_embedding, filter_clauses, k * 2)
        
        bm25_results, vector_results = await asyncio.gather(bm25_task, vector_task)
        
        # Fuse results using RRF
        fused_results = self._rrf_fusion(bm25_results, vector_results, k)
        
        logger.info(
            f"[ES_HYBRID] query='{query[:50]}...', "
            f"bm25_hits={len(bm25_results)}, vector_hits={len(vector_results)}, "
            f"fused={len(fused_results)}"
        )
        
        return fused_results
    
    async def _bm25_search(
        self,
        client,
        query: str,
        filters: List[Dict],
        k: int
    ) -> List[Dict[str, Any]]:
        """Execute BM25 search."""
        body = {
            "query": {
                "bool": {
                    "must": {
                        "multi_match": {
                            "query": query,
                            "fields": [
                                "chunk_text^2",
                                "candidate_name^3",
                                "metadata.skills^2",
                                "metadata.current_role"
                            ],
                            "type": "best_fields",
                            "fuzziness": "AUTO"
                        }
                    },
                    "filter": filters
                }
            },
            "size": k,
            "_source": True
        }
        
        response = await client.search(index=self.index_name, body=body)
        
        return [
            {
                "chunk_id": hit["_source"]["chunk_id"],
                "score": hit["_score"],
                "source": hit["_source"]
            }
            for hit in response["hits"]["hits"]
        ]
    
    async def _vector_search(
        self,
        client,
        embedding: List[float],
        filters: List[Dict],
        k: int
    ) -> List[Dict[str, Any]]:
        """Execute dense vector search."""
        body = {
            "query": {
                "bool": {
                    "must": {
                        "script_score": {
                            "query": {"bool": {"filter": filters}},
                            "script": {
                                "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                                "params": {"query_vector": embedding}
                            }
                        }
                    }
                }
            },
            "size": k,
            "_source": True
        }
        
        response = await client.search(index=self.index_name, body=body)
        
        return [
            {
                "chunk_id": hit["_source"]["chunk_id"],
                "score": hit["_score"] - 1.0,  # Normalize back to [0, 1]
                "source": hit["_source"]
            }
            for hit in response["hits"]["hits"]
        ]
    
    def _rrf_fusion(
        self,
        bm25_results: List[Dict],
        vector_results: List[Dict],
        k: int
    ) -> List[HybridSearchResult]:
        """
        Reciprocal Rank Fusion (RRF) to combine rankings.
        
        RRF score = sum(1 / (k + rank_i)) for each ranking
        """
        # Build rank maps
        bm25_ranks = {r["chunk_id"]: i + 1 for i, r in enumerate(bm25_results)}
        vector_ranks = {r["chunk_id"]: i + 1 for i, r in enumerate(vector_results)}
        
        # Build source map
        sources = {}
        for r in bm25_results + vector_results:
            if r["chunk_id"] not in sources:
                sources[r["chunk_id"]] = r["source"]
        
        # Calculate RRF scores
        all_chunk_ids = set(bm25_ranks.keys()) | set(vector_ranks.keys())
        rrf_scores = {}
        
        for chunk_id in all_chunk_ids:
            bm25_rank = bm25_ranks.get(chunk_id, len(bm25_results) + 100)
            vector_rank = vector_ranks.get(chunk_id, len(vector_results) + 100)
            
            bm25_rrf = self.bm25_weight / (self.RRF_K + bm25_rank)
            vector_rrf = self.vector_weight / (self.RRF_K + vector_rank)
            
            rrf_scores[chunk_id] = {
                "combined": bm25_rrf + vector_rrf,
                "bm25": bm25_rrf,
                "vector": vector_rrf
            }
        
        # Sort by combined score
        sorted_chunks = sorted(
            rrf_scores.items(),
            key=lambda x: x[1]["combined"],
            reverse=True
        )[:k]
        
        # Build results
        results = []
        for chunk_id, scores in sorted_chunks:
            source = sources[chunk_id]
            results.append(HybridSearchResult(
                chunk_id=chunk_id,
                cv_id=source["cv_id"],
                filename=source["filename"],
                candidate_name=source.get("candidate_name", "Unknown"),
                chunk_text=source["chunk_text"],
                chunk_index=source["chunk_index"],
                bm25_score=scores["bm25"],
                vector_score=scores["vector"],
                combined_score=scores["combined"],
                metadata=source.get("metadata", {})
            ))
        
        return results


# Factory function
_hybrid_search: Optional[ElasticsearchHybridSearch] = None

def get_elasticsearch_hybrid_search() -> ElasticsearchHybridSearch:
    global _hybrid_search
    if _hybrid_search is None:
        _hybrid_search = ElasticsearchHybridSearch()
    return _hybrid_search
```

---

### 1.5 Index Management
**Time**: 0.5 días | **Priority**: 🔴 ALTA

**index_manager.py**:
```python
"""
Elasticsearch index management for CV chunks.
"""
import logging
from typing import List, Dict, Any
from app.providers.elasticsearch.client import get_elasticsearch_client

logger = logging.getLogger(__name__)

INDEX_MAPPING = {
    # ... (mapping from 1.2)
}


class IndexManager:
    """Manage ES indices for CV screener."""
    
    def __init__(self):
        self.es = get_elasticsearch_client()
    
    async def create_index(self, index_type: str = "cv_chunks"):
        """Create index with mapping."""
        client = await self.es.get_client()
        index_name = self.es.get_index_name(index_type)
        
        if await client.indices.exists(index=index_name):
            logger.info(f"Index {index_name} already exists")
            return
        
        await client.indices.create(
            index=index_name,
            body=INDEX_MAPPING
        )
        logger.info(f"Created index {index_name}")
    
    async def index_cv_chunks(
        self,
        cv_id: str,
        session_id: str,
        user_id: str,
        filename: str,
        candidate_name: str,
        chunks: List[Dict[str, Any]],
        embeddings: List[List[float]]
    ):
        """Index CV chunks with embeddings."""
        client = await self.es.get_client()
        index_name = self.es.get_index_name("cv_chunks")
        
        # Bulk index
        actions = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            doc = {
                "chunk_id": f"{cv_id}_{i}",
                "cv_id": cv_id,
                "session_id": session_id,
                "user_id": user_id,
                "filename": filename,
                "candidate_name": candidate_name,
                "chunk_text": chunk["text"],
                "chunk_index": i,
                "embedding": embedding,
                "metadata": chunk.get("metadata", {})
            }
            actions.append({"index": {"_index": index_name, "_id": doc["chunk_id"]}})
            actions.append(doc)
        
        if actions:
            await client.bulk(body=actions, refresh=True)
            logger.info(f"Indexed {len(chunks)} chunks for CV {cv_id}")
    
    async def delete_cv_chunks(self, cv_id: str):
        """Delete all chunks for a CV."""
        client = await self.es.get_client()
        index_name = self.es.get_index_name("cv_chunks")
        
        await client.delete_by_query(
            index=index_name,
            body={"query": {"term": {"cv_id": cv_id}}}
        )
        logger.info(f"Deleted chunks for CV {cv_id}")
    
    async def delete_session_chunks(self, session_id: str):
        """Delete all chunks for a session."""
        client = await self.es.get_client()
        index_name = self.es.get_index_name("cv_chunks")
        
        await client.delete_by_query(
            index=index_name,
            body={"query": {"term": {"session_id": session_id}}}
        )
        logger.info(f"Deleted chunks for session {session_id}")
```

---

## 🔄 Phase 2: LangGraph Migration (5 días)

**Objetivo**: Migrar pipeline RAG a LangGraph para stateful workflows con memoria.

### 2.1 LangGraph Setup
**Time**: 0.5 días | **Priority**: 🔴 CRÍTICA

**Dependencies**:
```bash
pip install langgraph langchain-core langchain-openai
```

**Files to Create**:
```
backend/app/pipelines/
├── __init__.py
├── graph_state.py                   # State definitions
├── nodes/
│   ├── __init__.py
│   ├── query_understanding.py       # Understanding node
│   ├── retrieval.py                 # ES retrieval node
│   ├── reranking.py                 # Reranking node
│   ├── generation.py                # LLM generation node
│   └── verification.py              # Hallucination check node
├── edges.py                         # Conditional edges
└── rag_graph.py                     # Main graph definition
```

---

### 2.2 Graph State Definition
**Time**: 0.5 días | **Priority**: 🔴 CRÍTICA

**graph_state.py**:
```python
"""
LangGraph state definitions for RAG pipeline.
"""
from typing import TypedDict, List, Optional, Annotated
from operator import add
from dataclasses import dataclass, field
from enum import Enum


class QueryType(str, Enum):
    SINGLE_CANDIDATE = "single_candidate"
    COMPARISON = "comparison"
    RANKING = "ranking"
    SKILLS_SEARCH = "skills_search"
    EXPERIENCE_FILTER = "experience_filter"
    GENERAL = "general"


@dataclass
class RetrievedChunk:
    """A retrieved document chunk."""
    chunk_id: str
    cv_id: str
    filename: str
    candidate_name: str
    text: str
    score: float
    metadata: dict = field(default_factory=dict)


@dataclass
class VerificationResult:
    """Result of claim verification."""
    is_faithful: bool
    confidence: float
    issues: List[str] = field(default_factory=list)


class RAGState(TypedDict):
    """
    State that flows through the RAG graph.
    
    Using TypedDict for LangGraph compatibility.
    """
    # Input
    question: str
    session_id: str
    user_id: str
    cv_ids: Optional[List[str]]
    
    # Query Understanding
    query_type: Optional[str]
    query_intent: Optional[str]
    extracted_entities: Optional[dict]
    query_variations: Optional[List[str]]
    target_candidate: Optional[str]
    
    # Retrieval
    query_embedding: Optional[List[float]]
    retrieved_chunks: Annotated[List[dict], add]  # Accumulates across nodes
    reranked_chunks: Optional[List[dict]]
    
    # Generation
    context: Optional[str]
    response: Optional[str]
    structured_output: Optional[dict]
    
    # Verification
    verification_result: Optional[dict]
    needs_refinement: bool
    refinement_count: int
    
    # Conversation memory
    conversation_history: List[dict]
    
    # Metrics
    pipeline_steps: Annotated[List[dict], add]  # Accumulates timing info
    total_tokens: int
    
    # Error handling
    error: Optional[str]
    should_fallback: bool


def create_initial_state(
    question: str,
    session_id: str,
    user_id: str,
    cv_ids: List[str] = None,
    conversation_history: List[dict] = None
) -> RAGState:
    """Create initial state for RAG graph."""
    return RAGState(
        question=question,
        session_id=session_id,
        user_id=user_id,
        cv_ids=cv_ids or [],
        query_type=None,
        query_intent=None,
        extracted_entities=None,
        query_variations=None,
        target_candidate=None,
        query_embedding=None,
        retrieved_chunks=[],
        reranked_chunks=None,
        context=None,
        response=None,
        structured_output=None,
        verification_result=None,
        needs_refinement=False,
        refinement_count=0,
        conversation_history=conversation_history or [],
        pipeline_steps=[],
        total_tokens=0,
        error=None,
        should_fallback=False
    )
```

---

### 2.3 Graph Nodes
**Time**: 2 días | **Priority**: 🔴 CRÍTICA

**nodes/query_understanding.py**:
```python
"""
Query Understanding Node for LangGraph.
"""
import time
import logging
from typing import Dict, Any

from app.services.query_understanding_service import QueryUnderstandingService
from app.pipelines.graph_state import RAGState

logger = logging.getLogger(__name__)

query_service = QueryUnderstandingService()


async def query_understanding_node(state: RAGState) -> Dict[str, Any]:
    """
    Analyze and understand the user query.
    
    Updates:
    - query_type
    - query_intent
    - extracted_entities
    - query_variations
    - target_candidate
    - pipeline_steps
    """
    start = time.perf_counter()
    
    try:
        result = await query_service.understand(
            question=state["question"],
            conversation_history=state["conversation_history"],
            cv_ids=state["cv_ids"]
        )
        
        duration_ms = (time.perf_counter() - start) * 1000
        
        return {
            "query_type": result.query_type,
            "query_intent": result.intent,
            "extracted_entities": result.entities,
            "query_variations": result.variations,
            "target_candidate": result.target_candidate,
            "pipeline_steps": [{
                "step": "query_understanding",
                "duration_ms": duration_ms,
                "success": True,
                "metadata": {"query_type": result.query_type}
            }]
        }
    except Exception as e:
        logger.error(f"Query understanding failed: {e}")
        return {
            "query_type": "general",
            "error": str(e),
            "pipeline_steps": [{
                "step": "query_understanding",
                "duration_ms": (time.perf_counter() - start) * 1000,
                "success": False,
                "error": str(e)
            }]
        }
```

**nodes/retrieval.py**:
```python
"""
Retrieval Node using Elasticsearch.
"""
import time
import logging
from typing import Dict, Any

from app.providers.elasticsearch.search_service import get_elasticsearch_hybrid_search
from app.services.embedding_service import get_embedding_service
from app.pipelines.graph_state import RAGState

logger = logging.getLogger(__name__)


async def retrieval_node(state: RAGState) -> Dict[str, Any]:
    """
    Retrieve relevant chunks using Elasticsearch hybrid search.
    
    Updates:
    - query_embedding
    - retrieved_chunks
    - pipeline_steps
    """
    start = time.perf_counter()
    
    try:
        # Get embedding
        embedding_service = get_embedding_service()
        query_embedding = await embedding_service.embed_query(state["question"])
        
        # Execute hybrid search
        search_service = get_elasticsearch_hybrid_search()
        results = await search_service.hybrid_search(
            query=state["question"],
            query_embedding=query_embedding,
            session_id=state["session_id"],
            user_id=state["user_id"],
            k=20,
            filters=state.get("extracted_entities")
        )
        
        # Convert to dict for state
        chunks = [
            {
                "chunk_id": r.chunk_id,
                "cv_id": r.cv_id,
                "filename": r.filename,
                "candidate_name": r.candidate_name,
                "text": r.chunk_text,
                "score": r.combined_score,
                "metadata": r.metadata
            }
            for r in results
        ]
        
        duration_ms = (time.perf_counter() - start) * 1000
        
        return {
            "query_embedding": query_embedding,
            "retrieved_chunks": chunks,
            "pipeline_steps": [{
                "step": "retrieval",
                "duration_ms": duration_ms,
                "success": True,
                "metadata": {"chunks_retrieved": len(chunks)}
            }]
        }
    except Exception as e:
        logger.error(f"Retrieval failed: {e}")
        return {
            "error": str(e),
            "should_fallback": True,
            "pipeline_steps": [{
                "step": "retrieval",
                "duration_ms": (time.perf_counter() - start) * 1000,
                "success": False,
                "error": str(e)
            }]
        }
```

**nodes/generation.py**:
```python
"""
Generation Node using LLM.
"""
import time
import logging
from typing import Dict, Any

from app.services.llm_service import get_llm_service
from app.services.output_orchestrator import OutputOrchestrator
from app.pipelines.graph_state import RAGState

logger = logging.getLogger(__name__)


async def generation_node(state: RAGState) -> Dict[str, Any]:
    """
    Generate response using LLM with retrieved context.
    
    Updates:
    - context
    - response
    - structured_output
    - total_tokens
    - pipeline_steps
    """
    start = time.perf_counter()
    
    try:
        # Build context from reranked (or retrieved) chunks
        chunks = state.get("reranked_chunks") or state.get("retrieved_chunks", [])
        context = "\n\n---\n\n".join([
            f"[{c['filename']} - {c['candidate_name']}]\n{c['text']}"
            for c in chunks[:10]  # Limit context size
        ])
        
        # Get LLM service
        llm_service = get_llm_service()
        
        # Generate response
        llm_result = await llm_service.generate(
            question=state["question"],
            context=context,
            query_type=state.get("query_type", "general"),
            conversation_history=state.get("conversation_history", [])
        )
        
        # Generate structured output
        orchestrator = OutputOrchestrator()
        structured = orchestrator.process(
            query_type=state.get("query_type", "general"),
            response=llm_result.response,
            chunks=chunks
        )
        
        duration_ms = (time.perf_counter() - start) * 1000
        
        return {
            "context": context,
            "response": llm_result.response,
            "structured_output": structured,
            "total_tokens": state.get("total_tokens", 0) + llm_result.tokens_used,
            "pipeline_steps": [{
                "step": "generation",
                "duration_ms": duration_ms,
                "success": True,
                "metadata": {"tokens": llm_result.tokens_used}
            }]
        }
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        return {
            "error": str(e),
            "pipeline_steps": [{
                "step": "generation",
                "duration_ms": (time.perf_counter() - start) * 1000,
                "success": False,
                "error": str(e)
            }]
        }
```

---

### 2.4 Main Graph Definition
**Time**: 1.5 días | **Priority**: 🔴 CRÍTICA

**rag_graph.py**:
```python
"""
Main RAG Graph using LangGraph.

Stateful pipeline with:
- Query understanding
- Hybrid retrieval (ES)
- Reranking
- Generation
- Verification
- Conditional refinement
"""
import logging
from typing import Literal
from langgraph.graph import StateGraph, END

from app.pipelines.graph_state import RAGState, create_initial_state
from app.pipelines.nodes.query_understanding import query_understanding_node
from app.pipelines.nodes.retrieval import retrieval_node
from app.pipelines.nodes.reranking import reranking_node
from app.pipelines.nodes.generation import generation_node
from app.pipelines.nodes.verification import verification_node

logger = logging.getLogger(__name__)


def should_continue_after_verification(state: RAGState) -> Literal["refine", "end"]:
    """Decide whether to refine response or end."""
    if state.get("needs_refinement") and state.get("refinement_count", 0) < 2:
        return "refine"
    return "end"


def should_fallback(state: RAGState) -> Literal["fallback", "continue"]:
    """Check if we need to use fallback retrieval."""
    if state.get("should_fallback") or not state.get("retrieved_chunks"):
        return "fallback"
    return "continue"


def build_rag_graph() -> StateGraph:
    """
    Build the RAG pipeline graph.
    
    Flow:
    START → query_understanding → retrieval → [fallback?]
        → reranking → generation → verification → [refine?] → END
    """
    # Create graph with state schema
    graph = StateGraph(RAGState)
    
    # Add nodes
    graph.add_node("query_understanding", query_understanding_node)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("fallback_retrieval", fallback_retrieval_node)
    graph.add_node("reranking", reranking_node)
    graph.add_node("generation", generation_node)
    graph.add_node("verification", verification_node)
    graph.add_node("refinement", refinement_node)
    
    # Define edges
    graph.set_entry_point("query_understanding")
    
    graph.add_edge("query_understanding", "retrieval")
    
    graph.add_conditional_edges(
        "retrieval",
        should_fallback,
        {
            "fallback": "fallback_retrieval",
            "continue": "reranking"
        }
    )
    
    graph.add_edge("fallback_retrieval", "reranking")
    graph.add_edge("reranking", "generation")
    graph.add_edge("generation", "verification")
    
    graph.add_conditional_edges(
        "verification",
        should_continue_after_verification,
        {
            "refine": "refinement",
            "end": END
        }
    )
    
    graph.add_edge("refinement", "verification")
    
    return graph.compile()


# Compiled graph singleton
_rag_graph = None

def get_rag_graph():
    """Get compiled RAG graph."""
    global _rag_graph
    if _rag_graph is None:
        _rag_graph = build_rag_graph()
    return _rag_graph


async def run_rag_pipeline(
    question: str,
    session_id: str,
    user_id: str,
    cv_ids: list = None,
    conversation_history: list = None
) -> RAGState:
    """
    Run the full RAG pipeline.
    
    Args:
        question: User's question
        session_id: Session ID
        user_id: User ID for RLS
        cv_ids: Optional list of CV IDs to search
        conversation_history: Previous messages
        
    Returns:
        Final RAGState with response and metrics
    """
    graph = get_rag_graph()
    
    initial_state = create_initial_state(
        question=question,
        session_id=session_id,
        user_id=user_id,
        cv_ids=cv_ids,
        conversation_history=conversation_history
    )
    
    # Run graph
    final_state = await graph.ainvoke(initial_state)
    
    logger.info(
        f"[RAG_GRAPH] Pipeline complete: "
        f"steps={len(final_state['pipeline_steps'])}, "
        f"tokens={final_state['total_tokens']}"
    )
    
    return final_state
```

---

## 📊 Phase 3: Analytics Dashboard (3 días)

**Objetivo**: Dashboard para métricas de uso, calidad, y performance.

### 3.1 Analytics Schema
**Time**: 0.5 días | **Priority**: 🔴 ALTA

**SQL**:
```sql
-- Analytics events table
CREATE TABLE analytics_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type TEXT NOT NULL,  -- 'query', 'upload', 'export', etc.
  user_id UUID REFERENCES auth.users(id),
  session_id UUID,
  
  -- Event data
  data JSONB NOT NULL,
  
  -- Timing
  duration_ms FLOAT,
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for analytics queries
CREATE INDEX idx_analytics_user ON analytics_events(user_id);
CREATE INDEX idx_analytics_type ON analytics_events(event_type);
CREATE INDEX idx_analytics_created ON analytics_events(created_at);

-- Materialized view for daily stats
CREATE MATERIALIZED VIEW daily_stats AS
SELECT 
  DATE(created_at) as date,
  event_type,
  COUNT(*) as event_count,
  AVG(duration_ms) as avg_duration_ms,
  COUNT(DISTINCT user_id) as unique_users
FROM analytics_events
GROUP BY DATE(created_at), event_type;

-- Refresh function
CREATE OR REPLACE FUNCTION refresh_daily_stats()
RETURNS void AS $$
BEGIN
  REFRESH MATERIALIZED VIEW daily_stats;
END;
$$ LANGUAGE plpgsql;
```

---

### 3.2 Analytics Service
**Time**: 1 día | **Priority**: 🔴 ALTA

**Files to Create**:
```
backend/app/services/
└── analytics_service.py
```

**analytics_service.py**:
```python
"""
Analytics service for tracking usage and quality metrics.
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass

from app.providers.cloud.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


@dataclass
class QueryAnalytics:
    """Analytics for a single query."""
    query_type: str
    duration_ms: float
    tokens_used: int
    chunks_retrieved: int
    faithfulness_score: float
    user_tier: str


class AnalyticsService:
    """Service for tracking and querying analytics."""
    
    async def track_query(
        self,
        user_id: str,
        session_id: str,
        analytics: QueryAnalytics
    ):
        """Track a query event."""
        supabase = get_supabase_client(use_service_key=True)
        
        await supabase.table("analytics_events").insert({
            "event_type": "query",
            "user_id": user_id,
            "session_id": session_id,
            "duration_ms": analytics.duration_ms,
            "data": {
                "query_type": analytics.query_type,
                "tokens_used": analytics.tokens_used,
                "chunks_retrieved": analytics.chunks_retrieved,
                "faithfulness_score": analytics.faithfulness_score,
                "user_tier": analytics.user_tier
            }
        }).execute()
    
    async def get_usage_stats(
        self,
        user_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get usage statistics."""
        supabase = get_supabase_client(use_service_key=True)
        
        since = datetime.utcnow() - timedelta(days=days)
        
        query = supabase.table("analytics_events").select("*")
        
        if user_id:
            query = query.eq("user_id", user_id)
        
        query = query.gte("created_at", since.isoformat())
        
        result = await query.execute()
        events = result.data
        
        # Aggregate stats
        query_events = [e for e in events if e["event_type"] == "query"]
        
        return {
            "total_queries": len(query_events),
            "avg_duration_ms": sum(e["duration_ms"] for e in query_events) / len(query_events) if query_events else 0,
            "total_tokens": sum(e["data"].get("tokens_used", 0) for e in query_events),
            "avg_faithfulness": sum(e["data"].get("faithfulness_score", 0) for e in query_events) / len(query_events) if query_events else 0,
            "query_types": self._count_by_key(query_events, "query_type"),
            "daily_breakdown": self._daily_breakdown(query_events)
        }
    
    def _count_by_key(self, events: List[Dict], key: str) -> Dict[str, int]:
        """Count events by a data key."""
        counts = {}
        for e in events:
            value = e["data"].get(key, "unknown")
            counts[value] = counts.get(value, 0) + 1
        return counts
    
    def _daily_breakdown(self, events: List[Dict]) -> List[Dict]:
        """Break down events by day."""
        daily = {}
        for e in events:
            date = e["created_at"][:10]
            if date not in daily:
                daily[date] = {"count": 0, "tokens": 0}
            daily[date]["count"] += 1
            daily[date]["tokens"] += e["data"].get("tokens_used", 0)
        
        return [
            {"date": date, **stats}
            for date, stats in sorted(daily.items())
        ]
```

---

### 3.3 Dashboard UI
**Time**: 1.5 días | **Priority**: 🟡 MEDIA

**Files to Create**:
```
frontend/src/
├── pages/
│   └── Analytics.tsx                # Analytics dashboard
└── components/analytics/
    ├── UsageChart.tsx               # Usage over time
    ├── QueryTypeBreakdown.tsx       # Query types pie chart
    ├── PerformanceMetrics.tsx       # Latency, quality
    └── TopUsers.tsx                 # Top users (admin only)
```

---

## 🧪 Phase 4: A/B Testing Framework (2 días)

**Objetivo**: Framework para comparar modelos y estrategias.

### 4.1 A/B Test Configuration
**Time**: 1 día | **Priority**: 🟡 MEDIA

**SQL**:
```sql
-- A/B test experiments
CREATE TABLE ab_experiments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  description TEXT,
  
  -- Variants
  variants JSONB NOT NULL,  -- [{"name": "control", "weight": 50}, {"name": "treatment", "weight": 50}]
  
  -- Status
  status TEXT DEFAULT 'draft',  -- draft, running, completed
  
  -- Timestamps
  start_date TIMESTAMPTZ,
  end_date TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User assignments to variants
CREATE TABLE ab_assignments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  experiment_id UUID REFERENCES ab_experiments(id),
  user_id UUID REFERENCES auth.users(id),
  variant TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  
  UNIQUE(experiment_id, user_id)
);

-- Experiment results
CREATE TABLE ab_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  experiment_id UUID REFERENCES ab_experiments(id),
  user_id UUID REFERENCES auth.users(id),
  variant TEXT NOT NULL,
  
  -- Metrics
  metric_name TEXT NOT NULL,
  metric_value FLOAT NOT NULL,
  
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

### 4.2 A/B Testing Service
**Time**: 1 día | **Priority**: 🟡 MEDIA

**ab_testing_service.py**:
```python
"""
A/B Testing service for comparing models and strategies.
"""
import logging
import random
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from app.providers.cloud.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


@dataclass
class Experiment:
    id: str
    name: str
    variants: List[Dict[str, Any]]
    status: str


class ABTestingService:
    """Service for managing A/B tests."""
    
    async def get_variant(
        self,
        experiment_name: str,
        user_id: str
    ) -> Optional[str]:
        """
        Get user's variant for an experiment.
        Assigns randomly if not already assigned.
        """
        supabase = get_supabase_client(use_service_key=True)
        
        # Get experiment
        exp_result = await supabase.table("ab_experiments") \
            .select("*") \
            .eq("name", experiment_name) \
            .eq("status", "running") \
            .single() \
            .execute()
        
        if not exp_result.data:
            return None
        
        experiment = exp_result.data
        
        # Check existing assignment
        assign_result = await supabase.table("ab_assignments") \
            .select("variant") \
            .eq("experiment_id", experiment["id"]) \
            .eq("user_id", user_id) \
            .single() \
            .execute()
        
        if assign_result.data:
            return assign_result.data["variant"]
        
        # Assign new variant based on weights
        variant = self._weighted_choice(experiment["variants"])
        
        await supabase.table("ab_assignments").insert({
            "experiment_id": experiment["id"],
            "user_id": user_id,
            "variant": variant
        }).execute()
        
        return variant
    
    def _weighted_choice(self, variants: List[Dict]) -> str:
        """Choose variant based on weights."""
        total = sum(v["weight"] for v in variants)
        r = random.uniform(0, total)
        
        cumulative = 0
        for v in variants:
            cumulative += v["weight"]
            if r <= cumulative:
                return v["name"]
        
        return variants[-1]["name"]
    
    async def record_metric(
        self,
        experiment_name: str,
        user_id: str,
        metric_name: str,
        metric_value: float
    ):
        """Record a metric for A/B analysis."""
        supabase = get_supabase_client(use_service_key=True)
        
        # Get experiment and variant
        variant = await self.get_variant(experiment_name, user_id)
        if not variant:
            return
        
        exp_result = await supabase.table("ab_experiments") \
            .select("id") \
            .eq("name", experiment_name) \
            .single() \
            .execute()
        
        await supabase.table("ab_results").insert({
            "experiment_id": exp_result.data["id"],
            "user_id": user_id,
            "variant": variant,
            "metric_name": metric_name,
            "metric_value": metric_value
        }).execute()
```

---

## 📊 Priority Matrix (V11)

| Feature | Phase | Priority | Effort | Impact |
|---------|-------|----------|--------|--------|
| PG FTS Migration | 1 | 🔴 CRITICAL | 1d | High |
| Hybrid Search Cloud | 1 | 🔴 CRITICAL | 1d | High |
| LangGraph Setup | 2 | 🔴 HIGH | 0.5d | High |
| Graph State | 2 | 🔴 HIGH | 0.5d | High |
| Graph Nodes | 2 | 🔴 HIGH | 2d | Very High |
| Main Graph | 2 | 🔴 HIGH | 1d | Very High |
| Analytics Schema | 3 | 🟡 MEDIUM | 0.5d | Medium |
| Analytics Service | 3 | 🟡 MEDIUM | 1d | Medium |
| Fuzzy Search | 4 | 🟡 MEDIUM | 1d | Medium |
| Sinónimos | 4 | 🟡 MEDIUM | 1d | Medium |
| **TOTAL V11** | | | **~10 días** | |

---

## 💰 Cost Estimate (Optimizado para Prototipo)

| Feature | Monthly Cost | Notes |
|---------|-------------|-------|
| PostgreSQL FTS | $0 | Incluido en Supabase FREE |
| LangGraph | $0 | Open source |
| Analytics (tablas) | $0 | Tablas en Supabase FREE |
| **Total V11** | **$0/month** | Sin servicios adicionales |

### ❌ Eliminado (vs. plan original)
- ~~Elasticsearch~~ → PostgreSQL FTS (gratis)
- ~~Bonsai/Elastic Cloud~~ → No necesario
- ~~Servicios externos de analytics~~ → Tablas Supabase

---

## 📈 Success Metrics

| Metric | Current (V10) | Target (V11) | Improvement |
|--------|---------------|--------------|-------------|
| Search Latency (p50) | ~300ms | <200ms | **33% faster** |
| Search Quality | 85% | 90% | **+6%** |
| Complex Queries | Limited | Full support | LangGraph |
| Cloud Hybrid Search | ❌ | ✅ | PG FTS |

---

## 🔧 Dependencies (V11)

```bash
# LangGraph (open source, gratis)
pip install langgraph>=0.0.20
pip install langchain-core>=0.1.0

# NO se necesita:
# - elasticsearch (usamos PostgreSQL FTS)
# - servicios externos de pago
```

---

## 📝 V11 Completion Checklist

### Phase 1: PostgreSQL FTS (Cloud)
- [ ] Añadir tsvector a cv_embeddings
- [ ] Crear índice GIN
- [ ] Función hybrid_search_v11 en Supabase
- [ ] Actualizar hybrid_search_service.py para cloud
- [ ] Tests de paridad local vs cloud

### Phase 2: LangGraph
- [ ] LangGraph dependencies
- [ ] Graph state definition
- [ ] Query understanding node
- [ ] Retrieval node (usa hybrid_search existente)
- [ ] Reranking node
- [ ] Generation node
- [ ] Verification node
- [ ] Main graph compilation
- [ ] Integration con API routes

### Phase 3: Analytics Básico
- [ ] Tabla analytics_events en Supabase
- [ ] Analytics service (simple)
- [ ] Tracking de queries
- [ ] Vista de métricas (opcional)

### Phase 4: Mejorar Hybrid Search
- [ ] Fuzzy matching en PG FTS
- [ ] Sinónimos para skills técnicos
- [ ] Tuning de pesos BM25/vector

### Validation
- [ ] Hybrid search funciona en modo cloud
- [ ] LangGraph pipeline working
- [ ] Analytics tracking queries
- [ ] Sin costos adicionales de infraestructura
