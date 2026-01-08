# 🧠 Thought Process

> **Criterion**: Your explanation of the architecture and technology choices.
> 
> **Version**: 6.0 (January 2026) - Output Orchestrator, 9 Structures, 29 Modules, Conversational Context

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

## 🎯 Output Orchestrator: Structured Response Architecture (NEW in v6.0)

### The Problem

Basic RAG returns unstructured text that's hard to:
- Display consistently in UI
- Parse for specific data points
- Maintain quality across query types

### The Solution: Query Type → Structure → Modules

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        OUTPUT ORCHESTRATOR ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  USER QUERY: "Top 5 candidates for backend"                                     │
│       │                                                                          │
│       ▼                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────┐│
│  │ QUERY UNDERSTANDING → query_type: "ranking"                                 ││
│  └─────────────────────────────────────────────────────────────────────────────┘│
│       │                                                                          │
│       ▼                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────┐│
│  │ ORCHESTRATOR ROUTING                                                        ││
│  │                                                                             ││
│  │ query_type → STRUCTURE mapping:                                             ││
│  │ ├── "single_candidate" → SingleCandidateStructure                           ││
│  │ ├── "red_flags"        → RiskAssessmentStructure                            ││
│  │ ├── "comparison"       → ComparisonStructure                                ││
│  │ ├── "search"           → SearchStructure                                    ││
│  │ ├── "ranking"          → RankingStructure          ◄── SELECTED             ││
│  │ ├── "job_match"        → JobMatchStructure                                  ││
│  │ ├── "team_build"       → TeamBuildStructure                                 ││
│  │ ├── "verification"     → VerificationStructure                              ││
│  │ └── "summary"          → SummaryStructure                                   ││
│  └─────────────────────────────────────────────────────────────────────────────┘│
│       │                                                                          │
│       ▼                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────┐│
│  │ RANKINGSTRUCTURE assembles MODULES:                                         ││
│  │                                                                             ││
│  │ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         ││
│  │ │  Thinking   │  │  Analysis   │  │  Ranking    │  │  Ranking    │         ││
│  │ │   Module    │  │   Module    │  │  Criteria   │  │   Table     │         ││
│  │ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘         ││
│  │ ┌─────────────┐  ┌─────────────┐                                           ││
│  │ │   TopPick   │  │ Conclusion  │                                           ││
│  │ │   Module    │  │   Module    │                                           ││
│  │ └─────────────┘  └─────────────┘                                           ││
│  └─────────────────────────────────────────────────────────────────────────────┘│
│       │                                                                          │
│       ▼                                                                          │
│  STRUCTURED OUTPUT (JSON) → Frontend renders visual components                  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Why This Approach?

| Alternative | Problem | Our Solution |
|-------------|---------|--------------|
| Unstructured text | Hard to display, parse | Typed structures with modules |
| Single response format | Doesn't fit all query types | 9 specialized structures |
| Monolithic output | No reusability | 29 reusable modules |
| Frontend parsing | Fragile, regex-based | Backend provides structured JSON |

### Module Reusability Matrix

| Module | Used By Structures | Purpose |
|--------|-------------------|---------|
| ThinkingModule | ALL 9 | Extract reasoning process |
| ConclusionModule | ALL 9 | Final assessment |
| AnalysisModule | 6 structures | Detailed analysis |
| RiskTableModule | SingleCandidate, RiskAssessment | 5-factor risk table |

---

## 💬 Conversational Context: Pronoun Resolution (NEW in v6.0)

### The Problem

Users naturally use pronouns and references:
- "Tell me more about **her**"
- "Compare **those 3**"
- "What about **the top one**?"

Basic RAG has no memory of previous responses.

### The Solution: Context Resolver Service

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        CONTEXT RESOLVER ARCHITECTURE                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  CONVERSATION HISTORY (last 6 messages)                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────┐│
│  │ User: "Top 3 candidates for frontend"                                       ││
│  │ AI: [RankingStructure] 1. Alex Chen, 2. Sarah Kim, 3. Mike Johnson         ││
│  │ User: "Tell me more about the second one"  ◄── CURRENT QUERY               ││
│  └─────────────────────────────────────────────────────────────────────────────┘│
│       │                                                                          │
│       ▼                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────┐│
│  │ CONTEXT RESOLVER                                                            ││
│  │                                                                             ││
│  │ Resolution Types:                                                           ││
│  │ ├── Pronoun: "her", "him", "them" → Last mentioned candidate(s)            ││
│  │ ├── Ordinal: "first one", "second one" → From last ranking                 ││
│  │ ├── Demonstrative: "those 3", "these candidates" → Last result set         ││
│  │ └── Follow-up: "what about X?" → Continue previous context                 ││
│  │                                                                             ││
│  │ Result: "the second one" → Sarah Kim                                       ││
│  └─────────────────────────────────────────────────────────────────────────────┘│
│       │                                                                          │
│       ▼                                                                          │
│  RESOLVED QUERY: "Tell me more about Sarah Kim"                                 │
│  → Routes to SingleCandidateStructure                                           │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Implementation Insight

```python
# context_resolver.py (18KB)
class ContextResolver:
    def resolve(self, query: str, conversation_history: List[Message]) -> ResolvedQuery:
        # Extract candidates mentioned in last AI response
        last_candidates = self._extract_candidates_from_response(history[-1])
        
        # Resolve ordinal references
        if "second one" in query.lower():
            return last_candidates[1] if len(last_candidates) > 1 else None
        
        # Resolve pronouns
        if "her" in query.lower() or "she" in query.lower():
            return self._find_female_candidate(last_candidates)
```

---

## 🔄 RAG Pipeline: v6.0 Architecture (22+ Services)

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
│  ✗ No conversational context                                      │
│  ✗ Unstructured output hard to display                            │
│                                                                   │
│  ─────────────────────────────────────────────────────────────    │
│                                                                   │
│  v6.0 PIPELINE (Production Level):                                │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ UNDERSTANDING LAYER                                         │  │
│  │ ├── Query Understanding (9 query_types, entities)           │  │
│  │ ├── Context Resolver (pronouns, follow-ups) ◄── NEW         │  │
│  │ ├── Multi-Query Expansion + HyDE                            │  │
│  │ └── Guardrail Check (bilingual EN/ES)                       │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                            ↓                                      │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ RETRIEVAL LAYER                                             │  │
│  │ ├── Embedding (384d local / 768d cloud)                     │  │
│  │ ├── Vector Search (JSON / pgvector)                        │  │
│  │ └── Reranking (LLM-based relevance)                         │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                            ↓                                      │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ GENERATION LAYER                                            │  │
│  │ ├── Reasoning (Chain-of-Thought)                            │  │
│  │ └── Response Generation (structured prompts)                │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                            ↓                                      │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ VERIFICATION LAYER                                          │  │
│  │ ├── Claim Verification (fact-check)                         │  │
│  │ ├── Hallucination Check (verify names/IDs)                  │  │
│  │ ├── Confidence Calculator (5-factor) ◄── NEW                │  │
│  │ └── Cost Tracker + Eval Logging ◄── NEW                     │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                            ↓                                      │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │ OUTPUT LAYER (NEW in v6.0)                                  │  │
│  │ ├── Output Orchestrator (routes to structures)              │  │
│  │ ├── 9 Structures (assemble modules)                         │  │
│  │ ├── 29 Modules (extract/format data)                        │  │
│  │ └── Suggestion Engine (context-aware suggestions)           │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
```

### Service-Oriented Design

Each stage is an isolated service:

```python
backend/app/services/
├── rag_service_v5.py                # 128KB - Main orchestrator
├── query_understanding_service.py   # 40KB - Query classification
├── context_resolver.py              # 18KB - Conversational context ◄── NEW
├── multi_query_service.py           # 11KB - Query expansion + HyDE
├── guardrail_service.py             # 11KB - Off-topic filtering
├── embedding_service.py             # 4KB - Embedding wrapper
├── vector_store.py                  # 11KB - Vector operations
├── reranking_service.py             # 12KB - LLM-based reranking
├── reasoning_service.py             # 21KB - Chain-of-thought
├── claim_verifier_service.py        # 13KB - Fact verification
├── hallucination_service.py         # 12KB - Hallucination detection
├── confidence_calculator.py         # 28KB - 5-factor scoring ◄── NEW
├── cost_tracker.py                  # 7KB - Cost estimation ◄── NEW
├── eval_service.py                  # 12KB - Metrics & logging
├── smart_chunking_service.py        # 41KB - Semantic chunking ◄── NEW
├── verification_service.py          # 11KB - Response verification
│
├── output_processor/                # 44 items ◄── NEW
│   ├── orchestrator.py              # Routes query_type → structure
│   ├── structures/                  # 9 structure classes
│   │   ├── single_candidate_structure.py
│   │   ├── ranking_structure.py
│   │   ├── comparison_structure.py
│   │   └── ... (6 more)
│   └── modules/                     # 29 module classes
│       ├── thinking_module.py
│       ├── conclusion_module.py
│       └── ... (27 more)
│
└── suggestion_engine/               # 17 items ◄── NEW
    └── Dynamic suggestion generation
```

**Benefits**:
- Each service can be tested independently
- Easy to disable stages via feature flags
- Clear debugging: which stage failed?
- Swap implementations without affecting others
- **Modular output**: Add new structures without touching RAG core
- **Reusable modules**: DRY principle across structures

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

**[← Previous: Execution & Functionality](./01_EXECUTION_AND_FUNCTIONALITY.md)** · **[Back to Index](./README.md)** · **[Next: Code Quality →](./03_CODE_QUALITY.md)**

</div>
