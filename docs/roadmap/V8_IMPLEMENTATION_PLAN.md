# RAG v8 Implementation Plan

> **Status**: 📋 PLANNED
> 
> **Date**: January 2026
> 
> **Prerequisites**: RAG v7 (Cross-Encoder, NLI, Zero-Shot Guardrails, RAGAS, 65+ Query Patterns) ✅ Completed

---

## Executive Summary

RAG v8 focuses on **user-visible improvements**, **RAG quality enhancements**, and **premium features**:

### 🎯 Key Objectives
1. **Quick Wins** - Streaming, Export, Fallback (Usuario ve mejoras inmediatas)
2. **RAG Quality** - Hybrid Search, Source Highlighting, Caching (Mejores respuestas)
3. **Premium Features** - Auto-Screening, Scoring, Interview Questions (Diferenciadores)
4. **Architecture** - LangGraph Pipeline (Escalabilidad)

### ❌ Removed from Plan (Postponed to V9)
- ~~LangSmith~~ - Nice-to-have, not critical for MVP
- ~~A/B Testing Dashboard~~ - Only basic metrics first

---

## Timeline Overview

| Phase | Focus | Duration | Features |
|-------|-------|----------|----------|
| **Phase 1** | Quick Wins | 3 días | Streaming, Export, Fallback |
| **Phase 2** | RAG Quality | 4 días | Hybrid Search, Source Highlighting, Caching |
| **Phase 3** | Premium Features | 5 días | Auto-Screening, Scoring, Interview Questions |
| **Phase 4** | Architecture | 3 días | LangGraph Pipeline |
| **Total** | | **15 días** | **12 features** |

---

## 📦 Phase 1: Quick Wins (3 días)

**Objetivo**: Usuario ve mejoras inmediatas

### 1.1 Streaming Responses
**Time**: 1.5 días | **Priority**: 🔴 CRÍTICA

Mostrar respuesta token-a-token en tiempo real.

**Flow**:
```
Backend (FastAPI)              Frontend (React)
─────────────────              ─────────────────
[LLM Generation]  ──stream──►  [StreamingResponse]
      │                              │
      ▼                              ▼
yield token ──────────────────► append to UI
yield token ──────────────────► append to UI
      │                              │
      ▼                              ▼
[DONE signal] ────────────────► [Final render]
```

**Files to Create/Modify**:
```
backend/
├── app/api/routes.py                   # Add /api/query/stream endpoint
├── app/services/streaming_service.py   # NEW: SSE streaming logic
└── app/services/rag_service_v5.py      # Add stream=True option

frontend/
├── src/services/api.js                 # Add streamQuery function
├── src/components/ChatMessage.jsx      # Handle streaming state
└── src/hooks/useStreamingQuery.js      # NEW: Custom hook
```

**Benefits**:
- Percepción de velocidad 3x mejor
- Usuario ve progreso en tiempo real
- Mejor UX para queries largas

---

### 1.2 Export to PDF/DOCX
**Time**: 1 día | **Priority**: 🔴 ALTA

Permitir descargar análisis de candidato.

**Export Formats**:
| Format | Use Case |
|--------|----------|
| **PDF** | Professional reports, printing |
| **DOCX** | Editable, Word-compatible |
| **CSV** | Rankings, Excel import |

**Files to Create**:
```
backend/
├── app/services/export_service.py      # PDF/DOCX generation
├── app/api/export_routes.py            # /api/export endpoints
└── app/templates/
    ├── candidate_report.html           # PDF template
    └── candidate_report.docx           # DOCX template

frontend/
├── src/components/ExportButton.jsx     # Export dropdown
└── src/services/exportApi.js           # Export API calls
```

**Dependencies**:
```
weasyprint>=60.0    # PDF generation
python-docx>=1.0    # DOCX generation
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
        "anthropic/claude-3-haiku",         # Fallback 3 (paid, reliable)
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
└── app/services/fallback_chain.py      # Fallback logic
```

**Benefits**:
- 99.9% uptime
- Transparente para usuario
- Resiliente a rate limits

---

## 🔍 Phase 2: RAG Quality (4 días)

**Objetivo**: Mejores respuestas, más precisión

### 2.1 Hybrid Search (BM25 + Vector)
**Time**: 1 día | **Priority**: 🔴 ALTA

Combinar búsqueda léxica con semántica.

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
├── app/services/hybrid_search_service.py   # Hybrid search
├── app/services/bm25_service.py            # BM25 implementation
└── app/services/rag_service_v5.py          # Integrate hybrid
```

**Dependencies**:
```
rank-bm25>=0.2.2    # BM25 implementation
```

**Benefits**:
- +15-20% retrieval quality
- Better for exact terms (names, technologies)
- Better for concepts (semantic)

---

### 2.2 Source Highlighting
**Time**: 1.5 días | **Priority**: 🔴 ALTA

Mostrar exactamente qué parte del CV se usó.

**UI Example**:
```
Response:
"Juan has 5 years of Python experience [1] and led a 
team of 8 developers at TechCorp [2]"

Sources:
┌─────────────────────────────────────────────┐
│ [1] Juan_Garcia.pdf - Page 1, Lines 12-15   │
│ "Senior Python Developer (2019-2024)        │
│  • 5 years developing backend services..."  │
└─────────────────────────────────────────────┘
┌─────────────────────────────────────────────┐
│ [2] Juan_Garcia.pdf - Page 2, Lines 3-7     │
│ "Team Lead at TechCorp (2022-2024)          │
│  • Managed team of 8 developers..."         │
└─────────────────────────────────────────────┘
```

**Files to Create**:
```
backend/
├── app/services/source_highlighter.py      # Extract & highlight
├── app/services/claim_extractor.py         # Extract claims

frontend/
├── src/components/SourceHighlight.jsx      # Expandable sources
├── src/components/ClaimWithSource.jsx      # Inline citations
```

**Benefits**:
- Verificabilidad
- Transparencia
- Debugging retrieval

---

### 2.3 Contextual Compression
**Time**: 0.5 días | **Priority**: 🟡 MEDIA

Comprimir chunks para enviar solo info relevante.

**Process**:
```
Original Chunk (500 tokens)
         │
         ▼
[Score sentences for relevance]
         │
         ▼
Keep only relevant (score > 0.5)
         │
         ▼
Compressed Chunk (200 tokens)
```

**Files to Create**:
```
backend/
└── app/services/contextual_compression.py
```

**Benefits**:
- -30% tokens al LLM
- Respuestas más focalizadas
- Menor costo

---

### 2.4 Semantic Caching
**Time**: 1 día | **Priority**: 🔴 ALTA

Cache por similaridad semántica.

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
    'ttl_seconds': 86400,  # 24 hours
    'max_entries': 10000
}
```

**Files to Create**:
```
backend/
├── app/services/semantic_cache.py
└── app/providers/cache_provider.py
```

**Benefits**:
- 90%+ más rápido para queries similares
- Reduce costos API
- Mejor UX

---

## ⭐ Phase 3: Premium Features (5 días)

**Objetivo**: Diferenciadores competitivos

### 3.1 Auto-Screening Rules
**Time**: 2 días | **Priority**: 🔴 MUY ALTA

Definir reglas automáticas de screening.

**Rule Builder**:
```
IF [Experience Years] [<] [3]     THEN [REJECT]
IF [Skills] [contains] [Python]   THEN [+20 points]
IF [Education] [equals] [Master]  THEN [+10 points]
IF [Employment Gaps] [>] [6 mo]   THEN [FLAG]
IF [Job Hopping] [>] [3 jobs/2yr] THEN [WARN]
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
├── src/components/ScreeningRuleBuilder.jsx
├── src/components/ScreeningResults.jsx
└── src/pages/ScreeningRulesPage.jsx
```

**Benefits**:
- Ahorra horas de screening manual
- Consistencia en evaluación
- Cumplimiento de requisitos

---

### 3.2 Candidate Scoring Model
**Time**: 1.5 días | **Priority**: 🔴 ALTA

Score 0-100 configurable por criterios.

**Weight Configuration**:
```
Experience        ████████████████░░░░  40%
Skills Match      ████████████░░░░░░░░  30%
Education         ████████░░░░░░░░░░░░  20%
Stability         ████░░░░░░░░░░░░░░░░  10%
```

**Score Card**:
```
Juan García
─────────────────────────────────────
Overall: 87/100  ████████████████████░░  🏆

Experience:  35/40   Skills: 28/30
Education:   16/20   Stability: 8/10
```

**Files to Create**:
```
backend/
├── app/services/scoring_service.py
├── app/models/scoring_config.py
├── app/api/scoring_routes.py

frontend/
├── src/components/ScoringConfig.jsx
├── src/components/CandidateScoreCard.jsx
└── src/components/ScoreBreakdown.jsx
```

**Benefits**:
- Comparación objetiva
- Personalizable por puesto
- Transparencia

---

### 3.3 Interview Questions Generator
**Time**: 1 día | **Priority**: 🟡 MEDIA

Generar preguntas específicas para cada candidato.

**Output Example**:
```
Interview Questions for Juan García
────────────────────────────────────

📋 Technical (based on CV gaps):
1. "You mention Python experience but no specific frameworks. 
    Which Python web frameworks have you used?"
2. "Your CV shows AWS but limited details. Can you describe 
    a complex AWS architecture you've designed?"

🔍 Behavioral (based on experience):
3. "You led a team of 8 at TechCorp. Describe a conflict 
    you resolved within the team."
4. "You transitioned from Backend to Full Stack. What 
    motivated this change?"

⚠️ Clarification (red flags):
5. "There's a 6-month gap between TechCorp and StartupXYZ. 
    What were you doing during this period?"
```

**Files to Create**:
```
backend/
├── app/services/interview_generator.py
├── app/prompts/interview_prompts.py
├── app/api/interview_routes.py

frontend/
├── src/components/InterviewQuestions.jsx
└── src/components/QuestionCategory.jsx
```

---

### 3.4 Skill Gap Analysis
**Time**: 0.5 días | **Priority**: 🟡 MEDIA

Comparar candidato vs job description.

**Output**:
```
Skill Gap Analysis: Juan García vs Senior Developer Role
────────────────────────────────────────────────────────

✅ MATCHES (8/10 required):
  • Python (Advanced) ✓
  • AWS (Intermediate) ✓
  • PostgreSQL ✓
  • Docker ✓
  • Git ✓
  • Agile ✓
  • REST APIs ✓
  • Team Leadership ✓

❌ GAPS (2/10 required):
  • Kubernetes - NOT FOUND
  • Terraform - NOT FOUND

📊 Match Score: 80%

💡 RECOMMENDATIONS:
  • Ask about container orchestration experience
  • Kubernetes can be learned quickly with Docker background
```

**Files to Create**:
```
backend/
├── app/services/skill_gap_service.py
└── app/api/skill_gap_routes.py

frontend/
├── src/components/SkillGapAnalysis.jsx
└── src/components/SkillMatchChart.jsx
```

---

## 🏗️ Phase 4: Architecture (3 días)

**Objetivo**: Escalabilidad y mantenibilidad

### 4.1 LangGraph Pipeline
**Time**: 3 días | **Priority**: 🟡 MEDIA

Reemplazar pipeline secuencial con grafo stateful.

**Architecture**:
```
┌─────────────────────────────────────────────────────────┐
│                 LangGraph Pipeline v8                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  [Query] ──► [Understanding] ──► [Router]                │
│                                     │                    │
│                          ┌──────────┴──────────┐         │
│                          ▼                     ▼         │
│                    [Simple Path]         [Complex Path]  │
│                          │                     │         │
│                          │          ┌──────────┴───┐     │
│                          │          ▼              ▼     │
│                          │    [Retrieval]    [Analysis]  │
│                          │          │              │     │
│                          │          └──────┬───────┘     │
│                          │                 ▼             │
│                          │          [Reranking]          │
│                          │                 │             │
│                          └────────┬────────┘             │
│                                   ▼                      │
│                            [Generation]                  │
│                                   │                      │
│                                   ▼                      │
│                         [Verify + Refine]                │
│                                   │                      │
│                                   ▼                      │
│                             [Response]                   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Files to Create**:
```
backend/
├── app/services/langgraph/
│   ├── __init__.py
│   ├── pipeline.py          # Main graph definition
│   ├── nodes.py             # Individual node functions
│   ├── state.py             # State definitions
│   └── router.py            # Query routing logic
```

**Dependencies**:
```
langgraph>=0.0.40
```

**Benefits**:
- 30-40% más rápido (parallel execution)
- Mejor error recovery
- Visual debugging
- Conditional branching

---

## 📊 Priority Matrix

| Feature | Phase | Priority | Effort | Impact | User Visible |
|---------|-------|----------|--------|--------|--------------|
| Streaming | 1 | 🔴 CRITICAL | 1.5d | Very High | ✅ Yes |
| Export PDF/DOCX | 1 | 🔴 HIGH | 1d | High | ✅ Yes |
| Fallback Chain | 1 | 🟡 MEDIUM | 0.5d | Medium | ❌ No |
| Hybrid Search | 2 | 🔴 HIGH | 1d | High | ❌ Indirect |
| Source Highlighting | 2 | 🔴 HIGH | 1.5d | High | ✅ Yes |
| Contextual Compression | 2 | 🟡 MEDIUM | 0.5d | Medium | ❌ No |
| Semantic Caching | 2 | 🔴 HIGH | 1d | Very High | ✅ Yes |
| Auto-Screening Rules | 3 | 🔴 VERY HIGH | 2d | Very High | ✅ Yes |
| Candidate Scoring | 3 | 🔴 HIGH | 1.5d | High | ✅ Yes |
| Interview Questions | 3 | 🟡 MEDIUM | 1d | Medium | ✅ Yes |
| Skill Gap Analysis | 3 | 🟡 MEDIUM | 0.5d | Medium | ✅ Yes |
| LangGraph Pipeline | 4 | 🟡 MEDIUM | 3d | High | ❌ No |

---

## 📅 Recommended Schedule

### Week 1: Quick Wins + RAG Quality Start
| Day | Task | Output |
|-----|------|--------|
| 1 | Streaming Backend | SSE endpoint working |
| 2 | Streaming Frontend | Real-time token display |
| 3 | Export PDF/DOCX | Download button functional |
| 4 | Fallback Chain | Auto-failover working |
| 5 | Hybrid Search | BM25 + Vector integrated |

### Week 2: RAG Quality + Premium Start
| Day | Task | Output |
|-----|------|--------|
| 6-7 | Source Highlighting | Citations in responses |
| 8 | Contextual Compression | Token reduction |
| 9 | Semantic Caching | Cache hits working |
| 10 | Auto-Screening Rules | Rule builder UI |

### Week 3: Premium Features + Architecture
| Day | Task | Output |
|-----|------|--------|
| 11 | Auto-Screening Rules (cont.) | Full rule engine |
| 12 | Candidate Scoring | Score cards |
| 13 | Interview Questions | Question generator |
| 14 | Skill Gap Analysis | Gap visualization |
| 15 | LangGraph Pipeline | Graph-based pipeline |

---

## 💰 Cost Estimate

| Feature | Monthly Cost |
|---------|-------------|
| Streaming | $0 (no extra API) |
| Export | $0 (local processing) |
| Fallback | $0-5 (backup models) |
| Hybrid Search | $0 (local BM25) |
| Source Highlighting | $0 (post-processing) |
| Compression | $0 (local NLP) |
| Semantic Cache | $0 (local/Redis) |
| Screening Rules | $0 (local logic) |
| Scoring | $0 (local calculation) |
| Interview Questions | ~$1 (LLM calls) |
| Skill Gap | $0 (local matching) |
| LangGraph | $0 (local) |
| **Total** | **~$1-6/month** |

---

## 📈 Success Metrics

| Metric | Current (V7) | Target (V8) | Improvement |
|--------|--------------|-------------|-------------|
| Perceived Response Time | ~8-12s | ~2-3s (streaming) | **-75%** |
| Cache Hit Rate | 0% | 30-50% | **+50%** |
| Retrieval Quality | ~85% | ~95% | **+12%** |
| User Engagement | Baseline | +40% | (Export, Features) |
| Error Rate | ~5% | <1% | **-80%** |
| Unique Features | 3 | 10+ | **+233%** |

---

## 🔧 Dependencies to Install

```bash
# Phase 1
pip install sse-starlette     # Streaming
pip install weasyprint         # PDF export
pip install python-docx        # DOCX export

# Phase 2
pip install rank-bm25          # BM25 search

# Phase 4
pip install langgraph          # Graph pipeline
```

---

## ❓ Decision Points

Before starting, decide:

1. **Streaming approach**: SSE vs WebSocket?
   - Recommended: SSE (simpler, sufficient)

2. **Cache storage**: Local dict vs Redis?
   - Recommended: Local first, Redis if scaling

3. **PDF library**: WeasyPrint vs ReportLab?
   - Recommended: WeasyPrint (HTML templates)

4. **LangGraph timing**: Now vs after premium features?
   - Recommended: After (features first)

---

## 🚀 Quick Start

To begin implementation:

```bash
# 1. Create feature branch
git checkout -b feature/v8-implementation

# 2. Start with Phase 1.1 (Streaming)
# See detailed implementation in docs/implementation/streaming.md

# 3. Run tests
pytest tests/test_streaming.py

# 4. PR and merge
```

---

## 📝 Notes

- Each feature should have its own PR
- Write tests before implementation (TDD)
- Update CHANGELOG after each feature
- Demo to stakeholders after each phase
