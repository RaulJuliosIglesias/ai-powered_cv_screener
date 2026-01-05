# 🧠 Thought Process

> **Criterion**: Your explanation of the architecture and technology choices.

---

## 🏗️ High-Level Architecture Decision: Dual-Mode Design

### The Problem

| Environment | Need | Challenge |
|-------------|------|-----------|
| **Development** | Fast iteration, zero costs | No cloud dependencies |
| **Production** | Scalable, persistent | Managed infrastructure |
| **Testing** | Deterministic, fast | Isolated from external APIs |

### The Solution: Factory Pattern with Mode Parameter

```
┌───────────────────────────────────────────────────────────────────┐
│                     DUAL-MODE ARCHITECTURE                        │
│                                                                   │
│   ┌────────────────┐               ┌────────────────┐            │
│   │   LOCAL MODE   │               │   CLOUD MODE   │            │
│   │                │               │                │            │
│   │ • JSON Storage │               │ • Supabase     │            │
│   │ • sentence-    │    SAME API   │ • pgvector     │            │
│   │   transformers │◀─────────────▶│ • OpenRouter   │            │
│   │ • File System  │               │ • Cloud Storage│            │
│   │ • Zero Cost    │               │ • Scalable     │            │
│   └────────────────┘               └────────────────┘            │
│                                                                   │
│           ?mode=local                    ?mode=cloud              │
└───────────────────────────────────────────────────────────────────┘
```

### Why This Approach?

| Alternative Considered | Problem | Our Solution |
|------------------------|---------|--------------|
| Cloud-only | Requires setup, costs money for dev | Local mode = free development |
| Local-only | Doesn't scale, no persistence | Cloud mode = production ready |
| Separate codebases | Maintenance nightmare, code drift | Single codebase, mode parameter |
| Environment variables only | Still requires restarts | Query param = runtime switching |

### Implementation: Factory Pattern

```python
class ProviderFactory:
    """Factory for creating providers based on mode."""
    
    _instances = {}  # Singleton cache
    
    @classmethod
    def get_embedding_provider(cls, mode: Mode) -> EmbeddingProvider:
        if mode == Mode.CLOUD:
            return OpenRouterEmbeddingProvider()  # 768 dims
        return LocalEmbeddingProvider()  # 384 dims
    
    @classmethod
    def get_vector_store(cls, mode: Mode) -> VectorStoreProvider:
        if mode == Mode.CLOUD:
            return SupabaseVectorStore()  # pgvector
        return SimpleVectorStore()  # JSON file
```

**Benefit**: Zero code changes to switch environments. Just change `?mode=local` to `?mode=cloud`.

---

## ⚡ Backend Technology: Why FastAPI?

### Comparison Matrix

| Criterion | FastAPI | Flask | Django | Express.js |
|-----------|---------|-------|--------|------------|
| **Async Native** | ✅ Built-in | ❌ Extensions | ❌ Sync default | ✅ Native |
| **Type Safety** | ✅ Pydantic | ❌ Manual | ⚠️ Partial | ❌ None |
| **Auto Docs** | ✅ OpenAPI | ❌ Manual | ⚠️ DRF only | ❌ Manual |
| **Performance** | ✅ Top-tier | ⚠️ Moderate | ⚠️ Heavy | ✅ Good |
| **Python ML** | ✅ Native | ✅ Native | ✅ Native | ❌ Different |

### Key Reasons for FastAPI

```
┌───────────────────────────────────────────────────────────────────┐
│                       WHY FASTAPI?                                │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. ASYNC/AWAIT NATIVE                                            │
│     └── LLM calls take 2-10 seconds                               │
│     └── Async prevents blocking other requests                    │
│     └── Better resource utilization                               │
│                                                                   │
│  2. PYDANTIC VALIDATION                                           │
│     └── Automatic request/response validation                     │
│     └── Type errors caught at request time                        │
│     └── Self-documenting schemas                                  │
│                                                                   │
│  3. AUTOMATIC OPENAPI DOCS                                        │
│     └── /docs endpoint auto-generated                             │
│     └── Interactive API testing                                   │
│     └── No manual documentation needed                            │
│                                                                   │
│  4. PYTHON ECOSYSTEM                                              │
│     └── Direct access to sentence-transformers                    │
│     └── Native pdfplumber integration                             │
│     └── LangChain compatibility                                   │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

---

## 🧮 Embedding Strategy: Hybrid Approach

### The Challenge

Different deployment scenarios have different constraints:

| Scenario | Constraint | Required Solution |
|----------|------------|-------------------|
| Local development | No API costs | Free, local embeddings |
| Offline deployment | No internet | Fully local model |
| Production | Quality matters | Best available model |
| CI/CD testing | Fast, deterministic | Lightweight fallback |

### The Solution: Cascading Fallback System

```
┌───────────────────────────────────────────────────────────────────┐
│                  EMBEDDING FALLBACK CASCADE                       │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  PRIORITY 1: sentence-transformers (all-MiniLM-L6-v2)             │
│  ├── Dimensions: 384                                              │
│  ├── Speed: ~14,000 sentences/sec on CPU                          │
│  ├── Size: 80MB                                                   │
│  └── Status: ✅ Preferred for local                               │
│       │                                                           │
│       ▼ (if unavailable)                                          │
│  PRIORITY 2: OpenRouter API (nomic-embed-text-v1.5)               │
│  ├── Dimensions: 768                                              │
│  ├── Quality: State-of-the-art                                    │
│  ├── Cost: ~$0.02/1M tokens                                       │
│  └── Status: ✅ Production quality                                │
│       │                                                           │
│       ▼ (if unavailable)                                          │
│  PRIORITY 3: Hash-based fallback                                  │
│  ├── Dimensions: 384 (MD5-based)                                  │
│  ├── Quality: Poor (testing only)                                 │
│  ├── Speed: Instant                                               │
│  └── Status: ⚠️ CI/CD fallback only                               │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

### Model Selection Rationale

| Model | Dims | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| `all-MiniLM-L6-v2` | 384 | 14K/sec | Good | Local dev |
| `nomic-embed-v1.5` | 768 | API | Excellent | Cloud prod |
| Hash fallback | 384 | Instant | Poor | CI/CD only |

---

## 💾 Vector Storage: JSON vs pgvector

### Why Two Different Stores?

```
┌───────────────────────────────────────────────────────────────────┐
│               VECTOR STORE COMPARISON                             │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌────────────────────────┐  ┌────────────────────────┐          │
│  │  SimpleVectorStore     │  │  SupabaseVectorStore   │          │
│  │  (Local Mode)          │  │  (Cloud Mode)          │          │
│  ├────────────────────────┤  ├────────────────────────┤          │
│  │ Storage: JSON file     │  │ Storage: PostgreSQL    │          │
│  │ Search: Linear scan    │  │ Search: IVFFlat index  │          │
│  │ Scale: <10K docs       │  │ Scale: Millions        │          │
│  │ Setup: Zero config     │  │ Setup: Supabase project│          │
│  │ Cost: Free             │  │ Cost: Supabase pricing │          │
│  │ Backup: Manual         │  │ Backup: Automatic      │          │
│  └────────────────────────┘  └────────────────────────┘          │
│                                                                   │
│  USE CASE:                   USE CASE:                            │
│  • Development               • Production                         │
│  • Small deployments         • Multi-user apps                    │
│  • Offline scenarios         • Persistent storage                 │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

### Local Mode: SimpleVectorStore Design

**Decision**: Pure Python, no external dependencies.

```python
class SimpleVectorStore:
    """
    Trade-offs:
    + Zero dependencies, works everywhere
    + Easy to debug (human-readable JSON)
    - O(n) search, not suitable for >10K docs
    - No concurrent write safety
    """
```

**Why not ChromaDB/FAISS locally?**
- ChromaDB: Heavy dependency, SQLite issues on Windows
- FAISS: Complex installation, C++ compilation required
- JSON: Works everywhere, easy to debug, sufficient for development

### Cloud Mode: pgvector Design

```sql
-- IVFFlat index for fast approximate nearest neighbor search
CREATE INDEX cv_embeddings_embedding_idx 
ON cv_embeddings 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- RPC function for similarity search
CREATE FUNCTION match_cv_embeddings(
    query_embedding vector(768),
    match_count INT,
    match_threshold FLOAT
) RETURNS TABLE (...);
```

**Why Supabase?**
- Managed PostgreSQL (no DevOps needed)
- pgvector built-in (vector extension pre-installed)
- Storage buckets for PDFs
- Row-level security for future multi-tenant support
- Generous free tier for development

---

## 🤖 LLM Integration: OpenRouter

### Why OpenRouter vs Direct APIs?

```
┌───────────────────────────────────────────────────────────────────┐
│                   LLM INTEGRATION OPTIONS                         │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ❌ Direct OpenAI API                                             │
│     └── Vendor lock-in                                            │
│     └── Single provider                                           │
│     └── Price changes affect everything                           │
│                                                                   │
│  ❌ Direct Anthropic API                                          │
│     └── Different API format                                      │
│     └── Separate key management                                   │
│     └── Can't easily compare models                               │
│                                                                   │
│  ❌ LangChain Abstraction                                         │
│     └── Heavy dependency                                          │
│     └── Abstraction complexity                                    │
│     └── Overkill for direct calls                                 │
│                                                                   │
│  ✅ OpenRouter                                                    │
│     └── 100+ models, single API                                   │
│     └── One API key for all providers                             │
│     └── Easy model comparison                                     │
│     └── Future-proof (new models available immediately)           │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

### 2-Step Model Strategy

```
┌───────────────────────────────────────────────────────────────────┐
│                   2-STEP MODEL STRATEGY                           │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  STEP 1: Query Understanding             Cost: ~$0.0001/query     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ Model: Fast/Cheap (GPT-3.5, Gemini Flash, Llama 8B)         │  │
│  │ Task: Parse intent, extract entities, reformulate           │  │
│  │ Latency: 100-300ms                                          │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                            │                                      │
│                            ▼                                      │
│  STEP 2: Response Generation             Cost: ~$0.01/query       │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ Model: Powerful (GPT-4o, Claude 3.5 Sonnet, Gemini Pro)     │  │
│  │ Task: Generate comprehensive, cited response                │  │
│  │ Latency: 1-5 seconds                                        │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  TOTAL COST SAVINGS: ~40% vs using powerful model for both        │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

---

## 🎨 Frontend: React + Shadcn UI

### Technology Selection

| Technology | Why Selected |
|------------|--------------|
| **React 18** | Industry standard, huge ecosystem, concurrent rendering |
| **Shadcn UI** | Copy-paste components, full customization, not a dependency |
| **Radix UI** | Accessible primitives (keyboard nav, screen readers) |
| **TailwindCSS** | Rapid styling, consistent design system, small bundle |
| **Lucide Icons** | Modern, consistent iconography |

### Why NOT Other Options?

| Alternative | Reason Not Chosen |
|-------------|-------------------|
| Vue/Svelte | Smaller ecosystem, less hiring pool |
| Material UI | Heavy, opinionated, hard to customize |
| Chakra UI | Good but Shadcn is more flexible |
| Plain CSS | Slower development, inconsistent |

---

## 🔄 RAG Pipeline: 11-Stage Architecture

### Evolution from Basic to Advanced

```
┌───────────────────────────────────────────────────────────────────┐
│                    PIPELINE EVOLUTION                             │
├───────────────────────────────────────────────────────────────────┤
│                                                                   │
│  BASIC RAG (Tutorial Level):                                      │
│  Query → Embed → Search → Generate                                │
│                                                                   │
│  Problems:                                                        │
│  ✗ Poor recall on ambiguous queries                               │
│  ✗ No protection against off-topic questions                      │
│  ✗ Hallucinations pass through unchecked                          │
│  ✗ No visibility into failures                                    │
│                                                                   │
│  ─────────────────────────────────────────────────────────────    │
│                                                                   │
│  OUR PIPELINE (Production Level):                                 │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ UNDERSTANDING LAYER                                         │  │
│  │ ├── Query Understanding (intent, entities)                  │  │
│  │ ├── Multi-Query Expansion (variations)                      │  │
│  │ └── Guardrail Check (off-topic filter)                      │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                            ↓                                      │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ RETRIEVAL LAYER                                             │  │
│  │ ├── Embedding (vectorize queries)                           │  │
│  │ ├── Vector Search (find chunks)                             │  │
│  │ └── Reranking (LLM-based relevance)                         │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                            ↓                                      │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ GENERATION LAYER                                            │  │
│  │ ├── Reasoning (Chain-of-Thought)                            │  │
│  │ └── Response Generation (with citations)                    │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                            ↓                                      │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ VERIFICATION LAYER                                          │  │
│  │ ├── Claim Verification (fact-check)                         │  │
│  │ ├── Hallucination Check (verify names/IDs)                  │  │
│  │ └── Eval Logging (metrics & debugging)                      │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

### Service-Oriented Design

Each stage is an isolated service:

```
backend/app/services/
├── query_understanding_service.py   # Stage 1
├── multi_query_service.py           # Stage 2
├── guardrail_service.py             # Stage 3
├── embedding_service.py             # Stage 4
├── vector_store.py                  # Stage 5
├── reranking_service.py             # Stage 6
├── reasoning_service.py             # Stage 7
├── rag_service_v5.py                # Stage 8 (orchestrator)
├── claim_verifier_service.py        # Stage 9
├── hallucination_service.py         # Stage 10
└── eval_service.py                  # Stage 11
```

**Benefits**:
- Each service can be tested independently
- Easy to disable stages via feature flags
- Clear debugging: which stage failed?
- Swap implementations without affecting others

---

## ⚙️ Configuration: Feature Flags

### Why Feature Flags?

| Use Case | Configuration |
|----------|---------------|
| Fast demo | Disable reranking, reasoning |
| High quality | Enable everything |
| Debugging | Enable verbose logging |
| Cost-sensitive | Disable multi-query |

### Implementation

```python
@dataclass
class RAGConfigV5:
    # Feature flags - toggle stages on/off
    multi_query_enabled: bool = True
    hyde_enabled: bool = True
    reasoning_enabled: bool = True
    reflection_enabled: bool = True
    claim_verification_enabled: bool = True
    reranking_enabled: bool = True
    verification_enabled: bool = True
```

**No code changes needed** — just configuration.

---

## 📐 Architectural Principles Summary

| Principle | Implementation |
|-----------|----------------|
| **Separation of Concerns** | Services, Providers, API layers isolated |
| **Dependency Injection** | Factory pattern for mode-specific providers |
| **Single Responsibility** | Each service does one thing well |
| **Open/Closed** | Feature flags extend behavior without modification |
| **Fail Gracefully** | Fallbacks at every layer |
| **Observable** | Logging, metrics, streaming at each stage |
| **Testable** | Services can be unit tested in isolation |

---

<div align="center">

**[← Previous: Execution & Functionality](./01_EXECUTION_AND_FUNCTIONALITY.md)** · **[Back to Index](./INDEX.md)** · **[Next: Code Quality →](./03_CODE_QUALITY.md)**

</div>
