# RAG Workflow Documentation

> **CV Screener AI - Complete RAG Pipeline Reference**
> 
> Version: 4.0.0 | Last Updated: January 2026

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Pipeline Stages](#pipeline-stages)
4. [Core Scripts Reference](#core-scripts-reference)
5. [Data Flow](#data-flow)
6. [Configuration](#configuration)
7. [Providers](#providers)
8. [Error Handling](#error-handling)
9. [Caching & Performance](#caching--performance)
10. [Evaluation & Logging](#evaluation--logging)

---

## System Overview

The CV Screener uses a **multi-step RAG (Retrieval-Augmented Generation) pipeline** designed for intelligent CV analysis and candidate screening. The system supports two operation modes:

| Mode | Description |
|------|-------------|
| **LOCAL** | In-memory vector store, local embeddings |
| **CLOUD** | Supabase pgvector, OpenAI embeddings, OpenRouter LLMs |

### Key Features

- ✅ **2-Step LLM Architecture**: Fast model for query understanding + powerful model for generation
- ✅ **Guardrails**: Pre-LLM filtering to reject off-topic queries
- ✅ **Hallucination Detection**: Post-LLM verification against context
- ✅ **Adaptive Retrieval**: Strategy varies based on query type and session size
- ✅ **LLM-based Reranking**: Re-orders chunks by semantic relevance
- ✅ **Circuit Breaker**: Prevents cascading failures
- ✅ **Response Caching**: LRU cache with TTL for embeddings and responses
- ✅ **Evaluation Logging**: JSONL logs for continuous improvement

---

## Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              USER QUERY                                    │
└────────────────────────────────────┬───────────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  STEP 1: QUERY UNDERSTANDING                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ • Model: google/gemini-2.0-flash-001 (fast, cheap)                   │  │
│  │ • Extracts: query_type, requirements, is_cv_related                  │  │
│  │ • Reformulates query for better retrieval                            │  │
│  │ • Output: QueryUnderstanding dataclass                               │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│  Script: query_understanding_service.py                                    │
└────────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  STEP 2: GUARDRAIL CHECK                                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ • Keyword matching: CV_KEYWORDS set (100+ terms)                     │  │
│  │ • Pattern matching: OFF_TOPIC_PATTERNS (recipes, weather, etc.)      │  │
│  │ • Fast, no LLM call required                                         │  │
│  │ • Output: GuardrailResult (is_allowed, rejection_message)            │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│  Script: guardrail_service.py                                              │
│                                                                            │
│  ❌ REJECTED → Return early with rejection message                         │
│  ✅ PASSED → Continue to next step                                         │
└────────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  STEP 3: EMBEDDING GENERATION                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ • Model: text-embedding-3-small (1536 dimensions)                    │  │
│  │ • Cache: LRU with TTL (5 min default)                                │  │
│  │ • Retry: 3 attempts with exponential backoff                         │  │
│  │ • Timeout: 10 seconds                                                │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│  Script: embedding_service.py                                              │
│  Provider: OpenAI / LocalEmbeddingProvider                                 │
└────────────────────────────────────┬───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 4: VECTOR SEARCH (Retrieval)                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ ADAPTIVE STRATEGY based on query_type and session size:                 ││
│  │                                                                         ││
│  │ ┌─────────────────────────────────────────────────────────────────────┐ ││
│  │ │ Query Type      │ Strategy           │ K Value                      │ ││
│  │ ├─────────────────┼────────────────────┼──────────────────────────────┤ ││
│  │ │ ranking         │ diversify_by_cv    │ min(num_cvs, 30-100)         │ ││
│  │ │ comparison      │ diversify_by_cv    │ min(num_cvs, 30-100)         │ ││
│  │ │ search (small)  │ diversify_by_cv    │ num_cvs                      │ ││
│  │ │ search (large)  │ top-k precision    │ k (10 default)               │ ││
│  │ └─────────────────────────────────────────────────────────────────────┘ ││
│  │                                                                         ││
│  │ • Threshold: 0.3 default (lowered for large sessions)                   ││
│  │ • Filters by session_id and optional cv_ids                             ││
│  │ • Timeout: 15 seconds                                                   ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│  Script: vector_store.py (Cloud: Supabase pgvector, Local: in-memory)        │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 5: RERANKING                                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ • Model: google/gemini-2.0-flash-001                                    ││
│  │ • Scores each chunk 1-10 for relevance to query                         ││
│  │ • Combined score: LLM_score * 0.7 + similarity * 0.3                    ││
│  │ • Returns ALL chunks reordered (not truncated)                          ││
│  │ • Can be disabled via config                                            ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│  Script: reranking_service.py                                                │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 6: RESPONSE GENERATION                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ PROMPT CONSTRUCTION (templates.py):                                     ││
│  │ ┌─────────────────────────────────────────────────────────────────────┐ ││
│  │ │ SYSTEM_PROMPT (Expert HR analyst persona)                           │ ││
│  │ │    +                                                                │ ││
│  │ │ QUERY_TEMPLATE / COMPARISON_TEMPLATE / RANKING_TEMPLATE             │ ││
│  │ │    +                                                                │ ││
│  │ │ Formatted context (chunks with CV IDs and metadata)                 │ ││
│  │ └─────────────────────────────────────────────────────────────────────┘ ││
│  │                                                                         ││
│  │ • Models: gemini-1.5-flash, gemini-1.5-pro, gpt-4o, claude-3           ││
│  │ • Temperature: 0.1 (for accuracy)                                       ││
│  │ • Max tokens: 2048-4096                                                 ││
│  │ • Timeout: 120 seconds                                                  ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│  Script: llm.py (OpenRouterLLMProvider)                                      │
│  Templates: templates.py (PromptBuilder class)                               │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 7: VERIFICATION & HALLUCINATION CHECK                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ 7a. LLM VERIFICATION (verification_service.py)                          ││
│  │     • Uses LLM to check if response is grounded in context              ││
│  │     • Returns: groundedness_score, verified_claims, ungrounded_claims   ││
│  │                                                                         ││
│  │ 7b. HEURISTIC HALLUCINATION CHECK (hallucination_service.py)            ││
│  │     • Regex-based verification (no LLM call)                            ││
│  │     • Checks: CV IDs match context, names exist in CVs                  ││
│  │     • Returns: confidence_score, verified_cv_ids, warnings              ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│  If not grounded: Adds warning "⚠️ Some information could not be verified" │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 8: EVALUATION LOGGING                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ • Logs to: eval_logs/queries_YYYYMMDD.jsonl                             ││
│  │ • Fields: query, response, sources, metrics, hallucination_check        ││
│  │ • Daily stats aggregation                                               ││
│  │ • Low confidence tracking (threshold: 0.5)                              ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│  Script: eval_service.py                                                     │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                              RAG RESPONSE                                  │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ {                                                                    │  │
│  │   "answer": "Generated response text...",                            │  │
│  │   "sources": [{"cv_id": "cv_xxx", "filename": "John_Doe.pdf"}],      │  │
│  │   "metrics": {"total_ms": 1234, "stages": {...}},                    │  │
│  │   "confidence_score": 0.85,                                          │  │
│  │   "guardrail_passed": true,                                          │  │
│  │   "mode": "cloud",                                                   │  │
│  │   "request_id": "abc123"                                             │  │
│  │ }                                                                    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Pipeline Stages

### Stage Enum Definition

```python
class PipelineStage(Enum):
    QUERY_UNDERSTANDING = auto()  # Step 1
    GUARDRAIL = auto()            # Step 2
    EMBEDDING = auto()            # Step 3
    SEARCH = auto()               # Step 4
    RERANKING = auto()            # Step 5
    GENERATION = auto()           # Step 6
    VERIFICATION = auto()         # Step 7a
    HALLUCINATION_CHECK = auto()  # Step 7b
```

### Stage Metrics

Each stage tracks:
- `duration_ms`: Execution time
- `success`: Boolean status
- `error`: Error message if failed
- `metadata`: Stage-specific data

---

## Core Scripts Reference

### 📁 Orchestration Layer

| Script | Class | Description |
|--------|-------|-------------|
| `rag_service_v3.py` | `RAGServiceV4` | Main orchestrator. Executes pipeline, manages caching, circuit breakers, retry logic. |
| `rag_service_langchain.py` | `LangChainRAGService` | Alternative orchestrator using LangChain LCEL components. |
| `factory.py` | `ProviderFactory` | Factory pattern for provider instantiation based on mode. |

### 📁 Pipeline Steps (in order)

| # | Script | Class | Input → Output |
|---|--------|-------|----------------|
| 1 | `query_understanding_service.py` | `QueryUnderstandingService` | `str` → `QueryUnderstanding` |
| 2 | `guardrail_service.py` | `GuardrailService` | `str` → `GuardrailResult` |
| 3 | `embedding_service.py` | `EmbeddingService` | `str` → `List[float]` |
| 4 | `vector_store.py` | `SupabaseVectorStore` / `SimpleVectorStore` | `List[float]` → `List[SearchResult]` |
| 5 | `reranking_service.py` | `RerankingService` | `List[SearchResult]` → `RerankResult` |
| 6 | `llm.py` | `OpenRouterLLMProvider` | `prompt: str` → `str` |
| 7a | `verification_service.py` | `LLMVerificationService` | `response + context` → `VerificationResult` |
| 7b | `hallucination_service.py` | `HallucinationService` | `response + context` → `HallucinationCheckResult` |
| 8 | `eval_service.py` | `EvalService` | Logs query/response to JSONL |

### 📁 Support Layer

| Script | Class | Description |
|--------|-------|-------------|
| `templates.py` | `PromptBuilder` | All prompt templates and builder methods |
| `chunking_service.py` | `ChunkingService` | CV text → semantic sections |
| `pdf_service.py` | `PDFService` | PDF → text extraction |
| `base.py` | `EmbeddingProvider`, `VectorStoreProvider`, `LLMProvider` | Abstract interfaces |

---

## Data Flow

### CV Ingestion Flow

```
PDF Upload
    │
    ▼
┌─────────────────┐
│   PDF Service   │ → Extract text from PDF
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Chunking Service│ → Split into sections (experience, education, skills...)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│Embedding Service│ → Generate vector for each chunk
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Vector Store   │ → Store in Supabase with metadata
└─────────────────┘
```

### Query Flow

```
User Question: "Who has Python experience?"
         │
         ▼
┌────────────────────────────────────────────────────────────────┐
│ QueryUnderstanding:                                            │
│   query_type: "search"                                         │
│   requirements: ["Search for Python skill"]                    │
│   reformulated_prompt: "Find candidates with Python..."        │
└────────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────┐
│ Guardrail: PASSED (contains CV keywords)                       │
└────────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────┐
│ Vector Search:                                                 │
│   Strategy: top-k (search query, large session)                │
│   Results: 10 chunks from 5 different CVs                      │
└────────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────┐
│ Reranking:                                                     │
│   Scores: [9.5, 8.2, 7.8, 6.5, ...]                            │
│   Reordered by relevance                                       │
└────────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────┐
│ LLM Generation:                                                │
│   SYSTEM_PROMPT + QUERY_TEMPLATE + formatted chunks            │
│   → "Based on the CVs, the following candidates have Python    │
│      experience: [CV:cv_abc123] John Doe (5 years)..."         │
└────────────────────────────────────────────────────────────────┘
```

---

## Configuration

### RAGConfig Dataclass

```python
@dataclass
class RAGConfig:
    mode: Mode = Mode.LOCAL
    
    # Model configuration
    understanding_model: str | None = None      # Default: gemini-2.0-flash-001
    reranking_model: str | None = None          # Default: gemini-2.0-flash-001
    generation_model: str | None = None         # Default: gemini-1.5-flash
    verification_model: str | None = None       # Default: gemini-2.0-flash-001
    
    # Feature flags
    reranking_enabled: bool = True
    verification_enabled: bool = True
    streaming_enabled: bool = False
    parallel_steps_enabled: bool = True
    
    # Retrieval settings
    default_k: int = 10
    default_threshold: float = 0.3
    max_context_tokens: int = 60000
    
    # Timeouts (seconds)
    embedding_timeout: float = 10.0
    search_timeout: float = 15.0
    llm_timeout: float = 120.0
    total_timeout: float = 180.0
```

### Environment Variables

```bash
# Required
OPENAI_API_KEY=your_openai_key           # For embeddings
OPENROUTER_API_KEY=your_openrouter_key    # For LLM generation

# Optional (Cloud mode)
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_service_key
GOOGLE_API_KEY=...              # For LangChain Gemini

# Feature flags
USE_LANGCHAIN=false             # Use LangChain wrapper
```

---

## Providers

### Provider Interface

```python
class EmbeddingProvider(ABC):
    async def embed_query(self, text: str) -> EmbeddingResult
    async def embed_documents(self, texts: List[str]) -> EmbeddingResult

class VectorStoreProvider(ABC):
    async def search(self, embedding, k, threshold, cv_ids, diversify_by_cv) -> List[SearchResult]
    async def add_embeddings(self, embeddings, metadatas, ids)

class LLMProvider(ABC):
    async def generate(self, prompt: str, system_prompt: str, **kwargs) -> LLMResult
```

### Provider Implementations

| Provider | Mode | Implementation |
|----------|------|----------------|
| `OpenRouterEmbeddingProvider` | Cloud | OpenAI text-embedding-3-small via OpenRouter |
| `LocalEmbeddingProvider` | Local | sentence-transformers (fallback) |
| `SupabaseVectorStore` | Cloud | pgvector in Supabase |
| `SimpleVectorStore` | Local | NumPy cosine similarity |
| `OpenRouterLLMProvider` | Both | OpenRouter API (Gemini, GPT-4, Claude) |

---

## Error Handling

### Error Types

```python
class RAGError(Exception):
    stage: PipelineStage | None
    severity: ErrorSeverity  # WARNING, RECOVERABLE, FATAL
    cause: Exception | None
    recoverable: bool

class GuardrailError(RAGError):      # Query rejected
class RetrievalError(RAGError):      # Search failed
class GenerationError(RAGError):     # LLM failed
```

### Retry Configuration

```python
@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay_ms: int = 100
    max_delay_ms: int = 5000
    exponential_base: float = 2.0
    jitter: bool = True
```

### Circuit Breaker

```python
@dataclass
class CircuitBreakerConfig:
    enabled: bool = True
    failure_threshold: int = 5        # Open after 5 failures
    recovery_timeout_seconds: int = 30 # Try recovery after 30s
    half_open_max_calls: int = 3      # Test calls before closing
```

**States:**
- `CLOSED` → Normal operation
- `OPEN` → Failing, rejecting all calls
- `HALF_OPEN` → Testing recovery

---

## Caching & Performance

### LRU Cache

```python
@dataclass
class CacheConfig:
    enabled: bool = True
    ttl_seconds: int = 300      # 5 minutes
    max_entries: int = 1000
    cache_embeddings: bool = True
    cache_responses: bool = True
```

### What Gets Cached

| Item | Cache Key | TTL |
|------|-----------|-----|
| Query embeddings | `emb:{query_text}` | 5 min |
| Full responses | `resp:{query_hash}` | 5 min |

### Performance Metrics

```python
@dataclass
class PipelineMetrics:
    total_ms: float
    stages: list[StageMetrics]
    cache_hit: bool
    retry_count: int
```

---

## Evaluation & Logging

### Query Log Entry

```python
@dataclass
class QueryLogEntry:
    timestamp: str
    session_id: Optional[str]
    query: str
    response: str
    sources: List[Dict[str, Any]]
    metrics: Dict[str, float]
    hallucination_check: Dict[str, Any]
    guardrail_passed: bool
    confidence_score: float
    mode: str
```

### Log Location

```
eval_logs/
├── queries_20260103.jsonl    # Today's queries
├── queries_20260102.jsonl    # Yesterday's queries
└── ...
```

### Daily Statistics

```python
@dataclass
class DailyStats:
    date: str
    total_queries: int
    avg_confidence: float
    guardrail_rejections: int
    avg_latency_ms: float
    low_confidence_count: int
    unique_sessions: int
```

---

## Prompt Templates

### System Prompt (Persona)

```python
SYSTEM_PROMPT = """You are an expert HR analyst and CV reviewer assistant.
Your job is to analyze CVs and help with candidate screening.

CRITICAL RULES:
1. ONLY use information from the provided CV context
2. NEVER fabricate information not in the CVs
3. Include [CV:cv_id] references for every claim
4. Use Markdown tables when comparing candidates
..."""
```

### Query Templates

| Template | Use Case |
|----------|----------|
| `QUERY_TEMPLATE` | General questions |
| `QUERY_TEMPLATE_CONCISE` | Short answers |
| `QUERY_TEMPLATE_JSON` | Structured JSON output |
| `COMPARISON_TEMPLATE` | Compare multiple candidates |
| `RANKING_TEMPLATE` | Rank candidates by criteria |

### PromptBuilder Class

```python
class PromptBuilder:
    def build_query_prompt(question, chunks, total_cvs, response_format)
    def build_comparison_prompt(criteria, chunks)
    def build_ranking_prompt(role, criteria, chunks, top_n)
```

---

## API Endpoints

### Query Endpoint

```
POST /api/v2/query
{
    "question": "Who has Python experience?",
    "session_id": "session_xxx",
    "k": 10,
    "threshold": 0.3
}

Response:
{
    "answer": "...",
    "sources": [...],
    "metrics": {...},
    "confidence_score": 0.85,
    "guardrail_passed": true
}
```

### Health Check

```
GET /api/health
{
    "status": "ok",
    "mode": "cloud",
    "reranking_enabled": true,
    "verification_enabled": true
}
```

---

## File Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── routes.py              # Main API routes
│   │   ├── routes_v2.py           # V2 API with sessions
│   │   ├── routes_sessions.py     # Session management
│   │   └── dependencies.py        # FastAPI dependencies
│   │
│   ├── services/
│   │   ├── rag_service_v3.py      # Main RAG orchestrator (RAGServiceV4)
│   │   ├── rag_service_langchain.py # LangChain alternative
│   │   ├── query_understanding_service.py
│   │   ├── guardrail_service.py
│   │   ├── embedding_service.py
│   │   ├── reranking_service.py
│   │   ├── verification_service.py
│   │   ├── hallucination_service.py
│   │   ├── chunking_service.py
│   │   ├── pdf_service.py
│   │   └── eval_service.py
│   │
│   ├── providers/
│   │   ├── base.py                # Abstract interfaces
│   │   ├── factory.py             # Provider factory
│   │   ├── cloud/
│   │   │   ├── embeddings.py
│   │   │   ├── llm.py
│   │   │   ├── vector_store.py
│   │   │   └── sessions.py
│   │   └── local/
│   │       ├── embeddings.py
│   │       ├── llm.py
│   │       └── vector_store.py
│   │
│   ├── prompts/
│   │   └── templates.py           # All prompt templates
│   │
│   ├── models/
│   │   ├── schemas.py             # Pydantic models
│   │   └── sessions.py            # Session management
│   │
│   ├── config.py                  # Settings and configuration
│   └── main.py                    # FastAPI app entry point
│
├── eval_logs/                     # Query logs (JSONL)
├── migrations/                    # SQL migrations
└── tests/                         # Test suite
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 4.0.0 | Jan 2026 | RAGServiceV4 with circuit breaker, LRU cache, pipeline metrics |
| 3.0.0 | Dec 2025 | 2-step LLM, QueryUnderstanding, Reranking |
| 2.0.0 | Nov 2025 | Guardrails, Hallucination detection |
| 1.0.0 | Oct 2025 | Initial RAG pipeline |

---

## Backward Compatibility

```python
# In rag_service_v3.py
RAGServiceV3 = RAGServiceV4  # Alias for backward compatibility
```

Routes and other modules importing `RAGServiceV3` will automatically use the latest `RAGServiceV4` implementation.

---

> **Note**: This document reflects the current state of the RAG system as of January 2026. For updates, refer to the source code and CHANGELOG.
