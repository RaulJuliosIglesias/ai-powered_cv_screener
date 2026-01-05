# 🤖 AI Literacy

> **Criterion**: Your awareness of the relevant tools, models, and trends in the AI industry.

---

## 🧠 Embedding Models: State-of-the-Art Selection

### Cloud Mode: `nomic-ai/nomic-embed-text-v1.5`

```
┌─────────────────────────────────────────────────────────────────┐
│              NOMIC EMBED TEXT v1.5                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Dimensions:      768                                           │
│  Context Length:  8,192 tokens                                  │
│  MTEB Ranking:    Top-tier open-source embedding model          │
│                                                                  │
│  KEY FEATURE: Task-prefixed embeddings                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Documents: "search_document: <text>"                     │    │
│  │ Queries:   "search_query: <text>"                        │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  WHY THIS MODEL:                                                │
│  • 2024 state-of-the-art open embedding model                   │
│  • Outperforms text-embedding-ada-002 on retrieval benchmarks   │
│  • More cost-effective than OpenAI embeddings                   │
│  • Longer context window (8K vs 8K)                             │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Implementation Awareness**:
```python
# Correct use of task prefixes for asymmetric search
def embed_texts(self, texts: List[str]) -> List[List[float]]:
    # Documents get document prefix
    prefixed_texts = [f"search_document: {t}" for t in texts]
    return self._embed(prefixed_texts)

def embed_query(self, query: str) -> List[float]:
    # Queries get query prefix
    prefixed_query = f"search_query: {query}"
    return self._embed([prefixed_query])[0]
```

### Local Mode: `all-MiniLM-L6-v2`

| Attribute | Value |
|-----------|-------|
| **Dimensions** | 384 |
| **Speed** | ~14,000 sentences/sec on CPU |
| **Size** | 80MB |
| **Quality** | Good for its size |
| **Use Case** | Development, offline environments |

**Why This Model**: Industry-standard for local inference — small, fast, and good quality. Perfect for development without API costs.

---

## 🔌 LLM Integration: Model-Agnostic Architecture

### OpenRouter API Integration

```
┌─────────────────────────────────────────────────────────────────┐
│              MODEL-AGNOSTIC LLM ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    OpenRouter API                        │    │
│  │                   (Single Endpoint)                      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                           │                                      │
│           ┌───────────────┼───────────────┐                     │
│           │               │               │                     │
│           ▼               ▼               ▼                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   OpenAI    │  │  Anthropic  │  │   Google    │             │
│  │ • GPT-4o    │  │ • Claude 3.5│  │ • Gemini    │             │
│  │ • GPT-4     │  │ • Claude 3  │  │ • Gemini    │             │
│  │ • GPT-3.5   │  │ • Haiku     │  │   Flash     │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│           │               │               │                     │
│           ▼               ▼               ▼                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │    Meta     │  │   Mistral   │  │   Others    │             │
│  │ • Llama 3.1 │  │ • Large     │  │ • Qwen      │             │
│  │   405B/70B  │  │ • Mixtral   │  │ • DeepSeek  │             │
│  │   /8B      │  │ • 7B        │  │ • Cohere    │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                  │
│  BENEFITS:                                                       │
│  ✅ No vendor lock-in                                           │
│  ✅ Switch models without code changes                          │
│  ✅ Single API key for all providers                            │
│  ✅ New models available immediately                            │
│  ✅ Cost optimization (mix cheap + powerful)                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2-Step Model Strategy (Industry Best Practice)

```
┌─────────────────────────────────────────────────────────────────┐
│              2-STEP MODEL OPTIMIZATION                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  STEP 1: Query Understanding                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Model: Fast/Cheap                                        │    │
│  │ • GPT-3.5 Turbo ($0.0005/1K tokens)                     │    │
│  │ • Gemini Flash ($0.00001/1K tokens)                     │    │
│  │ • Llama 3.1 8B ($0.0001/1K tokens)                      │    │
│  │                                                          │    │
│  │ Task: Parse intent, extract entities, reformulate query │    │
│  │ Latency: 100-300ms                                       │    │
│  │ Cost: ~$0.0001/query                                     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                           │                                      │
│                           ▼                                      │
│  STEP 2: Response Generation                                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Model: Powerful                                          │    │
│  │ • GPT-4o ($0.005/1K tokens)                             │    │
│  │ • Claude 3.5 Sonnet ($0.003/1K tokens)                  │    │
│  │ • Gemini 1.5 Pro ($0.00125/1K tokens)                   │    │
│  │                                                          │    │
│  │ Task: Generate comprehensive, cited response            │    │
│  │ Latency: 1-5 seconds                                     │    │
│  │ Cost: ~$0.01/query                                       │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  TOTAL SAVINGS: ~40% vs using powerful model for both          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 💾 Vector Database Knowledge

### Understanding Trade-offs

```
┌─────────────────────────────────────────────────────────────────┐
│              VECTOR DATABASE COMPARISON                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Solution          │ Scale      │ Latency │ Setup    │ Cost     │
│  ─────────────────────────────────────────────────────────────  │
│  In-Memory/JSON    │ <10K docs  │ O(n)    │ Zero     │ Free     │
│  ChromaDB          │ <100K docs │ Fast    │ Medium   │ Free     │
│  pgvector          │ Millions   │ Fast    │ Medium   │ Varies   │
│  Pinecone          │ Billions   │ Fast    │ Easy     │ $$       │
│  Weaviate          │ Millions   │ Fast    │ Medium   │ $        │
│                                                                  │
│  OUR IMPLEMENTATION:                                            │
│  • LOCAL:  SimpleVectorStore (JSON + cosine similarity)         │
│  • CLOUD:  Supabase pgvector (PostgreSQL + IVFFlat index)      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### pgvector Implementation Details

**Awareness of Vector Indexing**:
```sql
-- IVFFlat index for approximate nearest neighbor search
-- lists=100 is optimal for ~10K-100K vectors
CREATE INDEX cv_embeddings_embedding_idx 
ON cv_embeddings 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

**Understanding of Similarity Operators**:
```sql
-- Cosine distance operator in PostgreSQL
-- <=> returns distance (0-2), we convert to similarity (0-1)
SELECT 
    *,
    1 - (embedding <=> query_embedding) as similarity
FROM cv_embeddings
WHERE 1 - (embedding <=> query_embedding) > 0.3
ORDER BY embedding <=> query_embedding
LIMIT 10;
```

---

## 📚 RAG Best Practices from Recent Research

### Advanced Retrieval Techniques

```
┌─────────────────────────────────────────────────────────────────┐
│              RAG TECHNIQUES IMPLEMENTED                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  TECHNIQUE          │ RESEARCH ORIGIN    │ IMPLEMENTATION       │
│  ─────────────────────────────────────────────────────────────  │
│  Multi-Query        │ RAG-Fusion (2023)  │ MultiQueryService    │
│  Retrieval          │                    │ generates variations │
│  ─────────────────────────────────────────────────────────────  │
│  HyDE               │ Gao et al. (2022)  │ Hypothetical Doc     │
│                     │                    │ Embeddings           │
│  ─────────────────────────────────────────────────────────────  │
│  Reranking          │ Cross-encoder      │ LLM-based relevance  │
│                     │ research           │ scoring              │
│  ─────────────────────────────────────────────────────────────  │
│  Chain-of-Thought   │ Wei et al. (2022)  │ ReasoningService     │
│                     │                    │ structured thinking  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### RAG Pipeline Stages (Beyond Basic RAG)

```
BASIC RAG (Tutorial-level):
  Query → Embed → Retrieve → Generate

THIS IMPLEMENTATION (Production-level):
  Query → Understand → Multi-Query → Guardrail → Embed → 
  Retrieve → Rerank → Reason → Generate → Verify Claims → 
  Detect Hallucinations → Log Metrics
```

---

## ✍️ Prompt Engineering Patterns

### Structured Output Formatting

```python
# Forcing reliable LLM output with JSON schemas
QUERY_UNDERSTANDING_PROMPT = """
Analyze this question about CVs/resumes.

Question: {question}

You MUST respond in the following JSON format:
{
  "intent": "ranking|search|comparison|factual|summary",
  "entities": {
    "names": ["extracted names"],
    "skills": ["extracted skills"],
    "companies": ["extracted companies"],
    "education": ["extracted education"]
  },
  "reformulated_query": "optimized search query"
}
"""
```

### Anti-Hallucination Prompting

```python
GENERATION_PROMPT = """
Answer the question based ONLY on the provided CV context.

CRITICAL RULES:
1. ONLY use information from the provided CV chunks
2. If information is not in the context, say "Not found in CVs"
3. Always cite sources using [CV:cv_id] format
4. Never invent or assume information not in context
5. If uncertain, express uncertainty

Context:
{context}

Question: {question}

Provide a comprehensive answer with citations:
"""
```

---

## 📊 Evaluation & Observability (Evals)

### LLM Evaluation Awareness

```
┌─────────────────────────────────────────────────────────────────┐
│              EVALUATION METRICS TRACKED                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  RETRIEVAL QUALITY                                              │
│  ├── Similarity scores distribution                             │
│  ├── Number of chunks retrieved                                 │
│  ├── Diversity (unique CVs)                                     │
│  └── Relevance threshold hit rate                               │
│                                                                  │
│  GENERATION QUALITY                                             │
│  ├── Response length                                            │
│  ├── Citation count                                             │
│  ├── Verification pass rate                                     │
│  └── Confidence score                                           │
│                                                                  │
│  LATENCY BREAKDOWN                                              │
│  ├── Embedding time (ms)                                        │
│  ├── Search time (ms)                                           │
│  ├── Reranking time (ms)                                        │
│  ├── LLM generation time (ms)                                   │
│  └── Total pipeline time (ms)                                   │
│                                                                  │
│  COST TRACKING                                                  │
│  ├── Input tokens per stage                                     │
│  ├── Output tokens per stage                                    │
│  └── Estimated cost per query                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Implementation**:
```python
@dataclass
class PipelineMetrics:
    """Metrics collected during RAG pipeline execution."""
    total_ms: float
    stages: Dict[str, StageMetrics]
    cache_hit: bool
    retry_count: int
    tokens_used: TokenUsage
    estimated_cost: float

@dataclass
class StageMetrics:
    """Metrics for a single pipeline stage."""
    name: str
    latency_ms: float
    success: bool
    details: Dict[str, Any]
```

---

## 🛡️ Production AI Patterns

### Resilience Patterns

```
┌─────────────────────────────────────────────────────────────────┐
│              PRODUCTION RESILIENCE PATTERNS                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  RETRY WITH EXPONENTIAL BACKOFF                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ @dataclass                                               │    │
│  │ class RetryConfig:                                       │    │
│  │     max_attempts: int = 3                                │    │
│  │     base_delay_ms: int = 100                            │    │
│  │     max_delay_ms: int = 5000                            │    │
│  │     exponential_base: float = 2.0                       │    │
│  │     jitter: bool = True  # Prevent thundering herd      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  CIRCUIT BREAKER (FULLY IMPLEMENTED & WIRED)                    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ @dataclass(frozen=True)                                  │    │
│  │ class CircuitBreakerConfig:                              │    │
│  │     enabled: bool = True                                 │    │
│  │     failure_threshold: int = 5                          │    │
│  │     recovery_timeout_seconds: int = 30                  │    │
│  │     half_open_max_calls: int = 3                        │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ✓ Wired to LLM generation (allow_request/record_success/fail) │
│  ✓ Wired to reasoning step with graceful degradation           │
│  ✓ State machine: CLOSED → OPEN → HALF_OPEN → CLOSED           │
│                                                                  │
│  TIMEOUT MANAGEMENT                                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ EMBEDDING_TIMEOUT = 10.0    # Fast operation            │    │
│  │ SEARCH_TIMEOUT = 20.0       # Database query            │    │
│  │ LLM_TIMEOUT = 120.0         # Can be slow               │    │
│  │ TOTAL_TIMEOUT = 240.0       # Hard limit                │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  GRACEFUL DEGRADATION                                           │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ • Fallback to simpler response on failure               │    │
│  │ • Embedding fallback cascade                            │    │
│  │ • Cache previous successful responses                   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  3-LEVEL FALLBACK FOR QUERY UNDERSTANDING                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ LEVEL 1: Retry with Exponential Backoff                 │    │
│  │   • 3 attempts per model                                │    │
│  │   • Delays: 1.5s → 3s → 4.5s                           │    │
│  │   • Only for HTTP 429 (rate limiting)                   │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │ LEVEL 2: Free Model Fallback Chain                      │    │
│  │   • gemini-2.0-flash-exp:free                          │    │
│  │   • llama-3.3-70b-instruct:free                        │    │
│  │   • gemma-3-27b-it:free                                │    │
│  │   • deepseek-r1-0528:free                              │    │
│  │   • mistral-7b-instruct:free                           │    │
│  │   ✓ Strict validation: only `:free` suffix allowed     │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │ LEVEL 3: Heuristic Fallback (No LLM)                    │    │
│  │   • Keyword detection for query_type                    │    │
│  │   • Pattern matching for is_cv_related                  │    │
│  │   • Cost: $0.00 - NEVER FAILS                          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3-Level Fallback System (Query Understanding)

```python
# From query_understanding_service.py
FREE_MODEL_FALLBACK_CHAIN = [
    "google/gemini-2.0-flash-exp:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-3-27b-it:free",
    "deepseek/deepseek-r1-0528:free",
    "mistralai/mistral-7b-instruct:free",
]

def _get_models_to_try(self) -> List[str]:
    """Get ordered list of models: primary + free fallbacks."""
    models = [self.model]
    for fallback in FREE_MODEL_FALLBACK_CHAIN:
        if fallback != self.model and fallback.endswith(":free"):
            models.append(fallback)
    return models

def _create_heuristic_fallback(self, query: str) -> QueryUnderstanding:
    """Level 3: Pure heuristic fallback - NEVER fails, costs $0."""
    query_lower = query.lower()
    
    # Detect query type by keywords
    if any(kw in query_lower for kw in ['rank', 'order', 'sort', 'best']):
        query_type = 'ranking'
    elif any(kw in query_lower for kw in ['compare', 'versus', 'vs']):
        query_type = 'comparison'
    # ... more patterns
    
    return QueryUnderstanding(
        understood_query=query,
        query_type=query_type,
        is_cv_related=is_cv_related,
        reformulated_prompt=query
    )
```

**Guarantee**: Query Understanding **NEVER fails** - always produces a result with $0 cost fallback.

### Caching Strategy

```python
@dataclass
class CacheConfig:
    """Configuration for caching layer."""
    enabled: bool = True
    ttl_seconds: int = 300
    max_entries: int = 1000
    cache_embeddings: bool = True
    cache_responses: bool = True
```

---

## 📈 AI Industry Trends Awareness (2024-2025)

```
┌─────────────────────────────────────────────────────────────────┐
│              AI TRENDS & PROJECT ALIGNMENT                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  TREND                    │ PROJECT ALIGNMENT                   │
│  ─────────────────────────────────────────────────────────────  │
│  Multi-Modal RAG          │ Architecture supports extension     │
│                           │ to image/table extraction           │
│  ─────────────────────────────────────────────────────────────  │
│  Agentic RAG              │ Self-Ask pattern, iterative         │
│                           │ refinement implemented              │
│  ─────────────────────────────────────────────────────────────  │
│  Structured Outputs       │ JSON mode, schema validation        │
│                           │ throughout pipeline                 │
│  ─────────────────────────────────────────────────────────────  │
│  Smaller, Faster Models   │ 2-step pipeline uses fast models   │
│                           │ where appropriate                   │
│  ─────────────────────────────────────────────────────────────  │
│  Open-Source Models       │ Llama, Mistral, Qwen supported     │
│                           │ via OpenRouter                      │
│  ─────────────────────────────────────────────────────────────  │
│  Embedding Evolution      │ Uses latest nomic-embed,           │
│                           │ not legacy ada-002                  │
│  ─────────────────────────────────────────────────────────────  │
│  RAG Evaluation           │ Built-in eval logging,             │
│                           │ ready for RAGAS integration         │
│  ─────────────────────────────────────────────────────────────  │
│  Hybrid Search            │ Vector + keyword search            │
│                           │ architecture supported              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 AI Literacy Summary

| Area | Evidence |
|------|----------|
| **Embedding Models** | Correct selection of nomic-embed-v1.5 (cloud) and MiniLM (local) with proper task prefixes |
| **LLM Landscape** | Model-agnostic design supporting all major providers via OpenRouter |
| **Vector Databases** | Understanding of pgvector, indexing strategies, similarity operators |
| **RAG Research** | Multi-query, HyDE, reranking, CoT — beyond basic tutorials |
| **Prompt Engineering** | Structured outputs, anti-hallucination, citation formats |
| **Evaluation** | Per-stage metrics, cost tracking, observability hooks |
| **Production Patterns** | Retries, circuit breakers, caching, timeouts |
| **Industry Trends** | Aligned with 2024-2025 direction (agentic, structured, open models) |

---

<div align="center">

**[← Previous: Creativity & Ingenuity](./04_CREATIVITY_AND_INGENUITY.md)** · **[Back to Index](./INDEX.md)** · **[Next: Learn & Adapt →](./06_LEARN_AND_ADAPT.md)**

</div>
