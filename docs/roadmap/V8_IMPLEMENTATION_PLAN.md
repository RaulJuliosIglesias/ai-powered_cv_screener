# RAG v8 Implementation Plan

> **Status**: ✅ COMPLETED
> 
> **Date**: January 2026
> 
> **Prerequisites**: RAG v7 (Cross-Encoder, NLI, Zero-Shot Guardrails, RAGAS, 65+ Query Patterns) ✅ Completed

---

## 🗺️ Roadmap Vision: V8 → V9 → V10 → V11 → V12

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ROADMAP OVERVIEW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  V8 (Current)       V9 (Next)           V10               V11        V12    │
│  ─────────────      ─────────           ───               ───        ───    │
│  UX Features        Cloud Parity        Multi-Tenant      Advanced   Deploy │
│  (Local Mode)       (Supabase=Local)    (Auth)            Features   (K8s)  │
│                                                                              │
│  • Streaming        • PDF Storage       • User login      • LangGraph • Docker│
│  • Export PDF       • Sessions table    • User signup     • Complex   • K8s  │
│  • Fallback         • Chats history     • RLS policies      queries   • CI/CD│
│  • Hybrid search    • Full migration    • Usage quotas    • Analytics • Scale│
│  • Premium feat.    • Mode parity       • Workspaces      • A/B tests        │
│                                                                              │
│  🧪 LOCAL MODE      ☁️ CLOUD PARITY     🔐 AUTH           🚀 ADVANCED 🐳 PROD │
│  Test & develop     Supabase complete   Multi-user        Power feat. Deploy │
│                                                                              │
│  Modo local =       Cloud funciona      Usuarios pueden   Features    Docker │
│  siempre existe     IGUAL que local     registrarse       avanzados   + K8s  │
│  para testing                                                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### ⚠️ Estrategia de Desarrollo

```
LOCAL MODE (siempre activo para testing)
    │
    ├── V8: Desarrollar features en LOCAL primero
    │        (funciona, se puede testear)
    │
    ├── V9: Replicar TODO en CLOUD (Supabase)
    │        (paridad completa Local = Cloud)
    │
    ├── V10: Añadir Auth sobre Cloud
    │         (login, multi-tenant)
    │
    └── V12: Desactivar Local en PRODUCCIÓN
             (Local solo para dev/testing)
```

---

## Executive Summary

RAG v8 focuses on **user-visible improvements** developed in **LOCAL MODE** (which is stable and testable):

### 🎯 Key Objectives
1. **UX Improvements** - Streaming tokens, Export, Fallback (Usuario ve mejoras)
2. **RAG Quality** - Hybrid Search, Semantic Caching (Mejores respuestas)
3. **Premium Features** - Auto-Screening, Scoring (Diferenciadores)

### 📍 Modo de Desarrollo
- **Desarrollar en LOCAL** (estable, testeable)
- Cloud mode (Supabase) se actualiza en V9
- Local mode **siempre existe** para testing

### ❌ Moved to V9 (Cloud Parity)
- Subir PDFs a Supabase Storage
- Tablas de sesiones en Supabase
- Historial de chats persistido
- Paridad completa Local = Cloud

### ❌ Moved to V10 (Auth)
- Login/Signup usuarios
- Row Level Security
- Workspaces por usuario

### ❌ Moved to V11+ (Advanced)
- LangGraph Pipeline
- Analytics avanzados

### ❌ Moved to V12 (Deploy)
- Docker/Kubernetes
- CI/CD Pipeline

---

## Timeline Overview

| Phase | Focus | Duration | Features |
|-------|-------|----------|----------|
| **Phase 1** | Quick Wins (Local) | 3 días | Streaming tokens, Export PDF, Fallback |
| **Phase 2** | RAG Quality (Local) | 3 días | Hybrid Search (BM25), Semantic Cache (local) |
| **Phase 3** | Premium Features | 4 días | Auto-Screening, Scoring, Interview Questions |
| **Total** | | **10 días** | **9 features** |

---

## 📦 Phase 1: Quick Wins - UX (3 días)

**Objetivo**: Mejoras visibles para el usuario (desarrollar en LOCAL, testear, luego migrar a V9)

### 1.1 Streaming Token-by-Token
**Time**: 1 día | **Priority**: 🔴 CRÍTICA

**Nota**: Ya existe SSE para pipeline steps. Mejorar para streaming de tokens.

**Current State** (routes_sessions_stream.py):
- ✅ SSE endpoint existe
- ❌ Solo emite pipeline steps, no tokens

**Target State**:
- ✅ Streaming de tokens del LLM
- ✅ Pipeline steps + tokens combinados

**Files to Modify**:
```
backend/
├── app/api/routes_sessions_stream.py   # Add token streaming
├── app/services/rag_service_v5.py      # Yield tokens from LLM
└── app/providers/cloud/llm.py          # Stream from OpenRouter

frontend/
├── src/components/ChatMessage.jsx      # Render streaming tokens
└── src/hooks/useStreamingQuery.js      # Handle token events
```

**SSE Events**:
```
event: step
data: {"step": "generating", "status": "running"}

event: token
data: {"token": "The"}

event: token  
data: {"token": " candidate"}

event: complete
data: {"answer": "...", "structured_output": {...}}
```

---

### 1.2 Export to PDF/CSV
**Time**: 1 día | **Priority**: 🔴 ALTA

Permitir descargar análisis de candidato en PDF o CSV.

**Export Formats**:
| Format | Library | Use Case |
|--------|---------|----------|
| **PDF** | `fpdf2` | Professional reports |
| **CSV** | Built-in | Rankings, Excel import |

**Files to Create**:
```
backend/
├── app/services/export_service.py      # PDF/CSV generation
├── app/api/export_routes.py            # /api/export endpoints

frontend/
├── src/components/ExportButton.jsx     # Export dropdown
```

**Dependencies**:
```
fpdf2>=2.7.0        # Pure Python PDF
```

---

### 1.3 Smart Fallback Chain
**Time**: 0.5 días | **Priority**: 🟡 MEDIA

Auto-cambio de modelo si falla o rate-limited.

**Fallback Configuration**:
```python
FALLBACK_CHAINS = {
    'generation': [
        "google/gemini-2.0-flash-001",      # Primary (fast, free)
        "google/gemini-2.0-flash-lite-001", # Fallback 1 (faster, free)
        "openai/gpt-4o-mini",               # Fallback 2 (paid, reliable)
    ],
    'understanding': [
        "google/gemini-2.0-flash-001",
        "openai/gpt-4o-mini",
    ],
}
```

**Files to Create**:
```
backend/
└── app/services/fallback_chain_service.py
```

---

## 🔍 Phase 2: RAG Quality - Local (3 días)

**Objetivo**: Mejores respuestas (desarrollar en LOCAL primero)

### 2.1 Hybrid Search (BM25 + Vector)
**Time**: 1 día | **Priority**: 🔴 ALTA

Combinar búsqueda léxica (BM25) con semántica (vector) para mejor retrieval.

**How it works**:
```
Query: "Python developer with AWS"
         │
    ┌────┴────┐
    ▼         ▼
 [BM25]    [Vector]
    │         │
    ▼         ▼
 Exact:    Semantic:
 "Python"  "programming"
 "AWS"     "cloud"
    │         │
    └────┬────┘
         ▼
 [RRF Fusion]
         │
         ▼
  Final Ranking
```

**Files to Create**:
```
backend/
├── app/services/bm25_service.py            # BM25 implementation
├── app/services/hybrid_search_service.py   # Combine BM25 + Vector
└── app/services/rag_service_v5.py          # Integrate hybrid search
```

**Dependencies**:
```
rank-bm25>=0.2.2    # BM25 implementation
```

**Benefits**:
- +15-20% retrieval quality
- Better for exact terms (names, technologies)
- Better for concepts (semantic)

**V9 Migration**: En V9 se replicará usando PostgreSQL Full-Text Search + pgvector

---

### 2.2 Semantic Cache (Local)
**Time**: 1 día | **Priority**: 🔴 ALTA

Cache por similaridad semántica para queries repetidas.

**How it works**:
```
Query: "Who knows Python?"
         │
         ▼
   [Embed Query]
         │
         ▼
   [Search Cache]
   cosine > 0.95?
         │
    ┌────┴────┐
   YES        NO
    │          │
    ▼          ▼
 Return     Run Pipeline
 Cached     Cache Result
```

**Configuration**:
```python
CACHE_CONFIG = {
    'similarity_threshold': 0.95,
    'ttl_seconds': 3600,  # 1 hour (session-based)
    'max_entries': 1000
}
```

**Files to Create**:
```
backend/
├── app/services/semantic_cache_service.py  # Cache logic
└── app/providers/local/cache_provider.py   # Local cache (dict + embeddings)
```

**Benefits**:
- 90%+ más rápido para queries similares
- Reduce costos API
- Mejor UX

**V9 Migration**: En V9 se migrará a tabla Supabase con TTL

---

### 2.3 Source Attribution UI
**Time**: 1 día | **Priority**: 🟡 MEDIA

Mostrar qué chunks se usaron para cada respuesta (mejorar UI existente).

**Files to Modify**:
```
frontend/
├── src/components/output/SourcesPanel.jsx    # Expandable sources
└── src/components/output/ChunkPreview.jsx    # Show chunk text with highlight
```

**Note**: Backend ya devuelve sources. Solo mejora de frontend.

---

## ⭐ Phase 3: Premium Features (4 días)

**Objetivo**: Diferenciadores competitivos (desarrollar en LOCAL, persistencia JSON)

### 3.1 Auto-Screening Rules
**Time**: 2 días | **Priority**: 🔴 MUY ALTA

Reglas automáticas de screening guardadas localmente (JSON por sesión).

**Rule Builder UI**:
```
IF [Experience Years] [<] [3]     THEN [REJECT]
IF [Skills] [contains] [Python]   THEN [+20 points]
IF [Education] [equals] [Master]  THEN [+10 points]
IF [Employment Gaps] [>] [6 mo]   THEN [FLAG]
```

**Results**:
```
✅ Juan García      - Score: 85 - PASSED
⚠️  María López     - Score: 65 - FLAGGED (gap)
❌ Pedro Martínez   - Score: 40 - REJECTED (<3 yrs)
```

**Files to Create**:
```
backend/
├── app/services/screening_rules_service.py
├── app/models/screening_rules.py
├── app/api/screening_routes.py

frontend/
├── src/components/screening/RuleBuilder.jsx
├── src/components/screening/ScreeningResults.jsx
```

**V9 Migration**: En V9 se migrará a tabla Supabase `screening_rules`

---

### 3.2 Candidate Scoring Model
**Time**: 1.5 días | **Priority**: 🔴 ALTA

Score 0-100 configurable por criterios.

**Weight Configuration** (stored in session metadata):
```
Experience        ████████████████░░░░  40%
Skills Match      ████████████░░░░░░░░  30%
Education         ████████░░░░░░░░░░░░  20%
Stability         ████░░░░░░░░░░░░░░░░  10%
```

**Files to Create**:
```
backend/
├── app/services/scoring_service.py
├── app/models/scoring_config.py

frontend/
├── src/components/scoring/ScoringConfig.jsx
├── src/components/scoring/CandidateScoreCard.jsx
```

---

### 3.3 Interview Questions Generator
**Time**: 0.5 días | **Priority**: 🟡 MEDIA

Generar preguntas específicas usando el LLM (ya tenemos la infraestructura).

**Files to Create**:
```
backend/
├── app/services/interview_generator_service.py
├── app/prompts/interview_prompts.py

frontend/
└── src/components/InterviewQuestions.jsx
```

**Note**: Puede ser un nuevo query_type en el sistema existente.

---

---

## 🔮 V9 Preview: Cloud Parity (Supabase = Local)

> **Status**: 📋 PLANNED (after V8)
> 
> **Focus**: Replicar TODA la funcionalidad local en Supabase

### V9 Objetivo Principal
Que el modo CLOUD funcione **exactamente igual** que el modo LOCAL.

### V9 Key Features

| Feature | Local (V8) | Cloud (V9) |
|---------|------------|------------|
| **PDF Storage** | Filesystem local | Supabase Storage bucket |
| **Sessions** | JSON files | Supabase `sessions` table |
| **Chat History** | JSON files | Supabase `session_messages` table |
| **CV Metadata** | JSON files | Supabase `cvs` table |
| **Screening Rules** | JSON files | Supabase `screening_rules` table |
| **Semantic Cache** | In-memory dict | Supabase `query_cache` table |
| **Hybrid Search** | BM25 (rank-bm25) | PostgreSQL Full-Text Search |

### V9 Supabase Schema (Complete)

```sql
-- 1. Sessions table
CREATE TABLE sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. CVs table (with PDF reference)
CREATE TABLE cvs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
  filename TEXT NOT NULL,
  pdf_storage_path TEXT,  -- Reference to Supabase Storage
  content TEXT,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. CV Embeddings (already exists from V7)
CREATE TABLE cv_embeddings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  cv_id UUID REFERENCES cvs(id) ON DELETE CASCADE,
  chunk_index INT,
  chunk_text TEXT,
  embedding vector(768),
  metadata JSONB
);

-- 4. Session Messages (chat history)
CREATE TABLE session_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
  role TEXT NOT NULL,  -- 'user' or 'assistant'
  content TEXT NOT NULL,
  sources JSONB,
  structured_output JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Screening Rules
CREATE TABLE screening_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  rules JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. Query Cache
CREATE TABLE query_cache (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
  query_embedding vector(768),
  query_text TEXT,
  response JSONB,
  expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '1 hour'
);

-- 7. Full-Text Search for Hybrid Search
ALTER TABLE cvs ADD COLUMN fts_content tsvector 
  GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;
CREATE INDEX cvs_fts_idx ON cvs USING GIN(fts_content);
```

### V9 PDF Storage (Supabase Storage)

```
Supabase Storage Bucket: cv-pdfs
├── {session_id}/
│   ├── {cv_id}_original.pdf    # Original uploaded PDF
│   └── {cv_id}_filename.pdf    # With original filename
```

---

## 🔐 V10 Preview: Authentication & Multi-Tenant

> **Status**: 📋 PLANNED (after V9)
> 
> **Focus**: User login, data isolation, workspaces

### V10 Key Features

| Feature | Description | Supabase Component |
|---------|-------------|-------------------|
| **User Auth** | Login/Signup/OAuth | Supabase Auth |
| **User Workspaces** | Isolated sessions per user | RLS Policies |
| **Usage Quotas** | Query limits per tier | Edge Functions |
| **Subscription Tiers** | Free/Pro/Enterprise | Stripe + Supabase |

### V10 Schema Changes

```sql
-- All tables get user_id column
ALTER TABLE sessions ADD COLUMN user_id UUID REFERENCES auth.users(id);
ALTER TABLE cvs ADD COLUMN user_id UUID REFERENCES auth.users(id);

-- Row Level Security
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users see own sessions" ON sessions
  FOR ALL USING (auth.uid() = user_id);

-- User profiles
CREATE TABLE user_profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id),
  tier TEXT DEFAULT 'free',
  queries_used INT DEFAULT 0,
  queries_limit INT DEFAULT 100
);
```

---

## 🚀 V11 Preview: Advanced Features

> **Status**: 📋 PLANNED (after V10)
> 
> **Focus**: LangGraph, Analytics, Complex queries

### V11 Key Features

| Feature | Description |
|---------|-------------|
| **LangGraph Pipeline** | Stateful graph with user context |
| **Advanced Analytics** | Usage patterns, query insights |
| **A/B Testing** | Compare model performance |
| **Complex Queries** | Multi-step reasoning |

---

## 🐳 V12 Preview: Containerization & Orchestration

> **Status**: 📋 PLANNED (after V11)
> 
> **Focus**: Docker, Kubernetes, CI/CD, Production-Ready

### V12 Key Features

| Feature | Description | Technology |
|---------|-------------|------------|
| **Docker Images** | Backend + Frontend containers | Docker |
| **Kubernetes** | Orchestration, auto-scaling | K8s / GKE / EKS |
| **CI/CD Pipeline** | Automated testing & deploy | GitHub Actions |
| **Multi-Region** | Global deployment | Cloudflare / Vercel |
| **Monitoring** | Logs, metrics, alerts | Prometheus + Grafana |

### V12 Notes
- Local mode se desactiva en producción
- Solo Cloud mode disponible para usuarios finales
- Local mode sigue existiendo para desarrollo/testing

---

## 📊 Priority Matrix (V8)

| Feature | Phase | Priority | Effort | Impact | Mode |
|---------|-------|----------|--------|--------|------|
| Streaming Tokens | 1 | 🔴 CRITICAL | 1d | Very High | LOCAL |
| Export PDF/CSV | 1 | 🔴 HIGH | 1d | High | LOCAL |
| Fallback Chain | 1 | 🟡 MEDIUM | 0.5d | Medium | LOCAL |
| Hybrid Search (BM25) | 2 | 🔴 HIGH | 1d | High | LOCAL |
| Semantic Cache | 2 | 🔴 HIGH | 1d | Very High | LOCAL |
| Source Attribution UI | 2 | 🟡 MEDIUM | 1d | Medium | Frontend |
| Auto-Screening Rules | 3 | 🔴 VERY HIGH | 2d | Very High | LOCAL |
| Candidate Scoring | 3 | 🔴 HIGH | 1.5d | High | LOCAL |
| Interview Questions | 3 | 🟡 MEDIUM | 0.5d | Medium | LOCAL |
| **TOTAL V8** | | | **~10 días** | | |

### Future Versions Summary

| Version | Focus | Duration | Key Features |
|---------|-------|----------|--------------|
| **V9** | Cloud Parity | ~10 días | Supabase = Local (PDFs, sessions, chat history) |
| **V10** | Auth | ~8 días | Login, RLS, user workspaces |
| **V11** | Advanced | ~5 días | LangGraph, analytics |
| **V12** | Deploy | ~5 días | Docker, Kubernetes, CI/CD |

---

## 📅 Recommended Schedule (10 días)

### Week 1: Quick Wins + RAG Quality (Local Mode)
| Day | Task | Output |
|-----|------|--------|
| 1 | Streaming Tokens | Token-by-token SSE working |
| 2 | Export PDF/CSV | Download button functional |
| 3 | Fallback Chain | Auto-failover working |
| 4 | Hybrid Search (BM25) | BM25 + Vector fusion working |
| 5 | Semantic Cache | Local cache with embeddings |

### Week 2: Premium Features (Local Mode)
| Day | Task | Output |
|-----|------|--------|
| 6 | Source Attribution UI | Expandable sources panel |
| 7-8 | Auto-Screening Rules | Rule builder + JSON storage |
| 9 | Candidate Scoring | Score cards working |
| 10 | Interview Questions | Question generator |

---

## 💰 Cost Estimate

| Feature | Monthly Cost | Notes |
|---------|-------------|-------|
| Streaming | $0 | No extra API calls |
| Export PDF/CSV | $0 | fpdf2 pure Python |
| Fallback | $0-5 | Backup models rarely used |
| Hybrid Search | $0 | rank-bm25 local |
| Semantic Cache | $0 | In-memory local |
| Screening Rules | $0 | JSON local storage |
| Scoring | $0 | Local calculation |
| Interview Questions | ~$1 | LLM calls |
| **Total V8** | **~$1-6/month** | Same as V7 |

---

## 📈 Success Metrics

| Metric | Current (V7) | Target (V8) | Improvement |
|--------|--------------|-------------|-------------|
| Perceived Response Time | ~8-12s | ~2-3s (streaming) | **-75%** |
| Cache Hit Rate | 0% | 30-50% | **+50%** |
| Retrieval Quality | ~85% | ~95% | **+12%** (hybrid BM25) |
| Premium Features | 0 | 3 | Screening, Scoring, Interview |

---

## 🔧 Dependencies (V8)

```bash
# V8 New Dependencies
pip install fpdf2>=2.7.0       # PDF export
pip install rank-bm25>=0.2.2   # BM25 hybrid search

# Already installed (no changes):
# - sentence-transformers (local embeddings)
# - chromadb (local vector store)
# - httpx (API calls)
# - huggingface-hub (v7 features)
```

### Requirements.txt Changes (V8)

```diff
# New in V8
+ fpdf2>=2.7.0
+ rank-bm25>=0.2.2
```

---

## ❓ Decision Points (V8)

| Decision | Choice | Reason |
|----------|--------|--------|
| Streaming | SSE (existing) | Already implemented, just add tokens |
| Cache storage | Local (in-memory) | Migrate to Supabase in V9 |
| PDF library | fpdf2 | Pure Python, no system deps |
| Hybrid search | BM25 (rank-bm25) | Migrate to pg FTS in V9 |
| Rules storage | JSON local | Migrate to Supabase in V9 |
| Local mode | Keep for testing | Always available for dev |

---

## 🚀 Quick Start

To begin V8 implementation:

```bash
# 1. Create feature branch
git checkout -b feature/v8-ux-improvements

# 2. Start with Phase 1.1 (Streaming Tokens)
# Improve existing SSE to stream tokens

# 3. Run tests in LOCAL mode
pytest tests/ -v

# 4. Test manually in browser (localhost)
```

---

## 📝 V8 Completion Checklist

- [x] **Phase 1.1**: Streaming tokens (token-by-token) ✅
- [x] **Phase 1.2**: Export PDF/CSV ✅
- [x] **Phase 1.3**: Fallback chain ✅
- [x] **Phase 2.1**: Hybrid search (BM25 + Vector) ✅
- [x] **Phase 2.2**: Semantic cache (local) ✅
- [x] **Phase 2.3**: Source attribution UI ✅
- [x] **Phase 3.1**: Auto-screening rules ✅
- [x] **Phase 3.2**: Candidate scoring ✅
- [x] **Phase 3.3**: Interview questions ✅

### Post-V8 Validation
- [x] All tests pass in LOCAL mode
- [x] All features work in browser
- [x] No breaking changes to existing functionality
- [x] Ready for V9 cloud migration
