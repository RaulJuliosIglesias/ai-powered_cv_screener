# CV Screener - Architecture v9.0

> **Last Updated:** January 2026 - Complete v9.0 implementation with TypeScript, CI/CD, Cloud Parity, Streaming, Hybrid Search, 10 Structures (9 rigid + 1 Adaptive), 29+ Modules, 6 Adaptive Modules, and Conversational Context

## 🌐 Production Instance

| Environment | URL |
|-------------|-----|
| **Live Demo** | [https://ai-poweredcvscreener-production.up.railway.app/](https://ai-poweredcvscreener-production.up.railway.app/) |
| **API Docs** | [https://ai-poweredcvscreener-production.up.railway.app/docs](https://ai-poweredcvscreener-production.up.railway.app/docs) |

**Deployment Stack**: Railway (Monolith Container) + Supabase (PostgreSQL + pgvector + Storage)

---

## 🏗️ SYSTEM OVERVIEW

### Operating Modes
The system supports **2 modes**: `local` and `cloud` (Supabase)

| Component | LOCAL Mode | CLOUD Mode |
|-----------|------------|------------|
| **Embeddings** | sentence-transformers (384 dims) | OpenRouter nomic-embed-v1.5 (768 dims) |
| **Vector Store** | JSON + cosine similarity | Supabase pgvector |
| **PDF Storage** | Local filesystem | Supabase Storage |
| **Sessions** | JSON file persistence | Supabase tables |
| **LLM** | OpenRouter API | OpenRouter API |

---

## 📍 MODE: LOCAL (`mode=local`)

### Components:

| Component | File | Status | Description |
|-----------|------|--------|-------------|
| **Embeddings** | `providers/local/embeddings.py` | ✅ OK | sentence-transformers all-MiniLM-L6-v2 (384 dims) |
| **Vector Store** | `providers/local/vector_store.py` | ✅ OK | JSON persistence with cosine similarity |
| **LLM** | `providers/cloud/llm.py` | ✅ OK | OpenRouter API (shared) |
| **Sessions** | `models/sessions.py` | ✅ OK | JSON file persistence |

---

## ☁️ MODE: CLOUD - SUPABASE (`mode=cloud`)

### Components:

| Component | File | Status | Description |
|-----------|------|--------|-------------|
| **Embeddings** | `providers/cloud/embeddings.py` | ✅ OK | OpenRouter nomic-embed-text-v1.5 (768 dims) |
| **Vector Store** | `providers/cloud/vector_store.py` | ✅ OK | Supabase pgvector with RPC search |
| **PDF Storage** | `providers/cloud/pdf_storage.py` | ✅ OK | Supabase Storage bucket `cv-pdfs` |
| **Sessions** | `providers/cloud/sessions.py` | ✅ OK | Supabase tables (sessions, session_cvs, session_messages) |
| **LLM** | `providers/cloud/llm.py` | ✅ OK | OpenRouter API |

### Supabase Schema:
```sql
-- Tables: cvs, cv_embeddings (768 dims), sessions, session_cvs, session_messages
-- RPC Function: match_cv_embeddings(query_embedding, match_count, match_threshold)
-- Storage Bucket: cv-pdfs
-- Setup: scripts/setup_supabase_complete.sql
```

---

## 🔄 RAG PIPELINE v9.0

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              RAG PIPELINE v9.0                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  USER QUERY                                                                     │
│      │                                                                          │
│      ▼                                                                          │
│  ┌─────────────────────┐                                                       │
│  │ QUERY UNDERSTANDING │ → Classify query_type, extract requirements           │
│  │ (QueryUnderstandingService) │   Resolve pronouns using conversation history │
│  └─────────────────────┘                                                       │
│      │                                                                          │
│      ▼                                                                          │
│  ┌─────────────────────┐                                                       │
│  │    GUARDRAILS       │ → Validate CV-related, reject off-topic               │
│  └─────────────────────┘                                                       │
│      │                                                                          │
│      ▼                                                                          │
│  ┌─────────────────────┐                                                       │
│  │    EMBEDDING        │ → Generate query embedding (384 or 768 dims)          │
│  └─────────────────────┘                                                       │
│      │                                                                          │
│      ▼                                                                          │
│  ┌─────────────────────┐                                                       │
│  │   HYBRID SEARCH     │ → BM25 + Vector search for relevant CV chunks         │
│  └─────────────────────┘                                                       │
│      │                                                                          │
│      ▼                                                                          │
│  ┌─────────────────────┐                                                       │
│  │    RERANKING        │ → LLM-based reranking for relevance                   │
│  └─────────────────────┘                                                       │
│      │                                                                          │
│      ▼                                                                          │
│  ┌─────────────────────┐                                                       │
│  │   LLM GENERATION    │ → Generate response with context + prompt template    │
│  └─────────────────────┘                                                       │
│      │                                                                          │
│      ▼                                                                          │
│  ┌─────────────────────┐                                                       │
│  │   VERIFICATION      │ → Claim verification, hallucination detection         │
│  └─────────────────────┘                                                       │
│      │                                                                          │
│      ▼                                                                          │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                      OUTPUT ORCHESTRATOR                                  │  │
│  │  Routes query_type → STRUCTURE → MODULES → StructuredOutput              │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│      │                                                                          │
│      ▼                                                                          │
│  STRUCTURED RESPONSE (with sources, metrics, pipeline_steps)                   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 OUTPUT ORCHESTRATOR ARCHITECTURE

### Query Type → Structure Routing

| Query Type | Structure | Example Query |
|------------|-----------|---------------|
| `single_candidate` | SingleCandidateStructure | "Give me the full profile of Juan" |
| `red_flags` | RiskAssessmentStructure | "What are the red flags for María?" |
| `comparison` | ComparisonStructure | "Compare Juan and María" |
| `search` | SearchStructure | "Find developers with Python" |
| `ranking` | RankingStructure | "Top 5 candidates for backend" |
| `job_match` | JobMatchStructure | "Who fits best for senior position?" |
| `team_build` | TeamBuildStructure | "Build a team of 3 developers" |
| `verification` | VerificationStructure | "Verify if Juan has AWS certification" |
| `summary` | SummaryStructure | "Overview of all candidates" |
| `adaptive` | **AdaptiveStructureBuilder** | "What technologies do they have?" |

### Modules (29+) + Adaptive Modules (6)

| Category | Modules |
|----------|---------|
| **Core (4)** | ThinkingModule, DirectAnswerModule, AnalysisModule, ConclusionModule |
| **Profile (4)** | HighlightsModule, CareerModule, SkillsModule, CredentialsModule |
| **Tables (6)** | RiskTableModule, TableModule, ResultsTableModule, RankingTableModule, RankingCriteriaModule, TopPickModule |
| **Risk (2)** | RedFlagsModule, TimelineModule |
| **Match (3)** | RequirementsModule, MatchScoreModule, GapAnalysisModule |
| **Team (4)** | TeamRequirementsModule, TeamCompositionModule, SkillCoverageModule, TeamRiskModule |
| **Verify (3)** | ClaimModule, EvidenceModule, VerdictModule |
| **Summary (3)** | TalentPoolModule, SkillDistributionModule, ExperienceDistributionModule |
| **Adaptive (6)** | QueryAnalyzer, SchemaInferenceEngine, SmartDataExtractor, DynamicTableGenerator, AdaptiveAnalysisGenerator, AdaptiveStructureBuilder |

---

## 💬 CONVERSATIONAL CONTEXT

Conversation history is propagated through the entire pipeline:

1. **QueryUnderstandingService** - Receives last 6 messages for pronoun resolution
2. **LLM Generation** - Includes conversation context in prompt
3. **OutputOrchestrator** - Structures receive context for follow-up queries
4. **SuggestionEngine** - Generates contextual suggestions based on history

### Context Resolution Examples:
- "compare those 3" → Resolves to candidates mentioned in previous response
- "tell me more about her" → Resolves to last mentioned female candidate
- "what about the top one?" → Resolves to #1 ranked candidate

---

## 📊 ENRICHED METADATA

During CV indexing, the following is automatically extracted:

| Field | Description |
|-------|-------------|
| `total_experience_years` | Total years of experience |
| `seniority_level` | junior/mid/senior/lead/executive |
| `current_role` | Current position |
| `current_company` | Current company |
| `has_faang_experience` | Experience at Big Tech |
| `job_hopping_score` | Rotation index (0-1) |
| `avg_tenure_years` | Average tenure |
| `employment_gaps` | Detected employment gaps |

---

## 🔧 KEY FILES

### Backend Core
| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI application entry point |
| `app/config.py` | Settings with Mode enum (LOCAL/CLOUD) |
| `app/services/rag_service_v5.py` | Main RAG pipeline (2900+ lines) |
| `app/services/query_understanding_service.py` | Query classification & reformulation |
| `app/services/output_processor/orchestrator.py` | Routes to structures |

### Providers
| File | Purpose |
|------|---------|
| `providers/factory.py` | Provider factory with mode switching |
| `providers/local/embeddings.py` | sentence-transformers |
| `providers/local/vector_store.py` | ChromaDB |
| `providers/cloud/embeddings.py` | OpenRouter nomic-embed |
| `providers/cloud/vector_store.py` | Supabase pgvector |
| `providers/cloud/sessions.py` | Supabase session management |

### Output Processing
| File | Purpose |
|------|---------|
| `services/output_processor/orchestrator.py` | Main orchestrator |
| `services/output_processor/structures/` | 9 rigid structure classes |
| `services/output_processor/adaptive/` | 6 adaptive modules (dynamic schema-less) |
| `services/output_processor/modules/` | 29+ module classes |

### Frontend Core
| File | Purpose |
|------|---------|
| `src/App.jsx` | Main application component |
| `src/components/output/StructuredOutputRenderer.jsx` | Renders structured responses |
| `src/contexts/PipelineContext.jsx` | Pipeline state management |
| `src/services/api.ts` | API client |

---

## ✅ IMPLEMENTED FEATURES (v9.0)

- [x] Dual-mode architecture (Local/Cloud)
- [x] 10 Output Structures (9 rigid + 1 Adaptive) with intelligent routing
- [x] 29+ Reusable Modules + 6 Adaptive Modules
- [x] Conversational Context propagation
- [x] Query Understanding with pronoun resolution
- [x] Real-time pipeline progress tracking
- [x] Structured output rendering in frontend
- [x] Dynamic suggestion engine
- [x] Session-based CV management
- [x] PDF viewing and storage
- [x] Duplicate CV detection (content hash)
- [x] Background upload processing
- [x] AI-powered session naming
- [x] **v8:** Streaming token generation
- [x] **v8:** Export PDF/CSV
- [x] **v8:** Hybrid Search (BM25 + Vector)
- [x] **v8:** Semantic Cache
- [x] **v8:** LLM Fallback Chain
- [x] **v9:** TypeScript migration (90%+ coverage)
- [x] **v9:** GitHub Actions CI/CD
- [x] **v9:** Full Cloud Parity (Supabase)
- [x] **v9:** Adaptive Structure System (dynamic schema-less output)
- [x] **v9:** Production deployment on Railway

---

## 🚀 DEPLOYMENT ARCHITECTURE

```
┌──────────────────────────────────────────────────────────────────────┐
│                         PRODUCTION ARCHITECTURE                            │
├──────────────────────────────────────────────────────────────────────┤
│                                                                            │
│   ┌────────────────────────────────────────────────────────────────┐     │
│   │                   RAILWAY (Monolith Container)                    │     │
│   │   ┌─────────────────────────────────────────────────────────┐  │     │
│   │   │                    FastAPI Backend                          │  │     │
│   │   │   • /api/* routes                                          │  │     │
│   │   │   • RAG Pipeline v9.0                                      │  │     │
│   │   │   • Output Orchestrator (9 structures + 29 modules)        │  │     │
│   │   │   • SSE Streaming                                          │  │     │
│   │   └─────────────────────────────────────────────────────────┘  │     │
│   │   ┌─────────────────────────────────────────────────────────┐  │     │
│   │   │               Static Frontend (React 18)                   │  │     │
│   │   │   • Served from /app/static                                │  │     │
│   │   │   • Vite-built SPA                                         │  │     │
│   │   └─────────────────────────────────────────────────────────┘  │     │
│   └────────────────────────────────────────────────────────────────┘     │
│                                     │                                      │
│                                     ▼                                      │
│   ┌────────────────────────────────────────────────────────────────┐     │
│   │                     SUPABASE (Free Tier)                        │     │
│   │   • PostgreSQL + pgvector extension                             │     │
│   │   • cv_embeddings table (768-dim vectors)                       │     │
│   │   • match_cv_embeddings RPC function                            │     │
│   │   • Storage bucket: cv-pdfs                                     │     │
│   └────────────────────────────────────────────────────────────────┘     │
│                                     │                                      │
│                                     ▼                                      │
│   ┌────────────────────────────────────────────────────────────────┐     │
│   │                 OPENROUTER (User-Provided Keys)                  │     │
│   │   • LLM generation (GPT-4o, Claude 3.5, etc.)                   │     │
│   │   • Embeddings (nomic-embed-text-v1.5)                          │     │
│   │   • No server-side API key required                             │     │
│   └────────────────────────────────────────────────────────────────┘     │
│                                                                            │
└──────────────────────────────────────────────────────────────────────┘
```

### Why This Architecture?

| Decision | Rationale |
|----------|----------|
| **Railway Monolith** | Single container deployment reduces complexity, no inter-service networking |
| **Supabase Free Tier** | Production-grade PostgreSQL with pgvector at $0/month |
| **User-Provided API Keys** | Zero LLM costs for the server, users control their usage |
| **FastAPI Static Files** | No need for separate Nginx, simplifies deployment |

---

## 📋 NEXT STEPS (Roadmap)

| Version | Features | Status |
|---------|----------|--------|
| **V10** | Supabase Auth, Row Level Security, User Quotas | 📋 Planned |
| **V11** | PostgreSQL FTS, LangGraph Pipeline | 📋 Planned |
| **V12** | Multi-provider deploy (Vercel + Render) | 📋 Planned |

See [Roadmap Documentation](./roadmap/README.md) for full details.
