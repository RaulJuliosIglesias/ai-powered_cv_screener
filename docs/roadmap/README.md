# 🚀 Roadmap - Future Plans

> Planning documents for future improvements to the **AI-Powered CV Screener** project.
>
> **Current Version:** 9.0 | January 2026
>
> **💰 Cost Philosophy:** $0 en servicios fijos hasta tener usuarios. Solo pagar por uso (OpenRouter LLM).

---

## 🗺️ Version Roadmap Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ROADMAP OVERVIEW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  V6 ✅       V7 ✅         V8 ✅           V9 ✅           V10        V11   │
│  ─────────   ─────────     ─────────       ─────────       ───        ───   │
│  Output      ML Models     UX Features     TypeScript      Auth       PG FTS│
│  Orchestr.   NLI/RAGAS     Streaming       + CI/CD         + RLS      + Lang│
│                                            (FREE)          (FREE)     Graph │
│                                                                              │
│  ✅ Done     ✅ Done       ✅ Done         ✅ Done         📋 Next    📋 Plan│
│                                                                              │
│  9 Struct.   Cross-Enc.    • Streaming     • TypeScript    • Login    • PG  │
│  29 Modules  Zero-Shot     • Export PDF    • GitHub Act.   • OAuth      FTS │
│  Suggestions RAGAS Eval    • Hybrid BM25   • Cloud Parity  • RLS      • Lang│
│                            • Sem. Cache    • $0/month      • $0/month   Graph│
│                            • Screening                                       │
│                                                                              │
│  V12: Simple Deploy (Vercel FREE + Render FREE + Supabase FREE) = $0/month  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## ✅ Completed Versions

### V9.0 (Current) - TypeScript + CI/CD + Cloud Parity
| Feature | Status | Description |
|---------|--------|--------------|
| TypeScript Migration | ✅ Done | 90%+ type coverage frontend |
| GitHub Actions CI/CD | ✅ Done | Backend + Frontend pipelines |
| Cloud Parity | ✅ Done | Supabase = Local functionality |
| Pre-commit Hooks | ✅ Done | 8 quality gate hooks |
| Dependabot | ✅ Done | Automated dependency updates |

### V8.0 - UX Features
| Feature | Status | Description |
|---------|--------|-------------|
| Streaming Tokens | ✅ Done | Token-by-token SSE streaming |
| Export PDF/CSV | ✅ Done | Download candidate reports |
| Fallback Chain | ✅ Done | Auto-failover between models |
| Hybrid Search | ✅ Done | BM25 + Vector fusion |
| Semantic Cache | ✅ Done | Query similarity caching |
| Auto-Screening | ✅ Done | Rule-based candidate filtering |
| Candidate Scoring | ✅ Done | Configurable scoring model |

### V7.0 - ML Enhancements
| Feature | Status | Description |
|---------|--------|-------------|
| Cross-Encoder Reranking | ✅ Done | HuggingFace BGE reranker |
| NLI Verification | ✅ Done | Hallucination detection |
| Zero-Shot Guardrails | ✅ Done | ML-based query filtering |
| RAGAS Evaluation | ✅ Done | Quality metrics logging |

### V6.0 - Core Architecture
| Feature | Status | Description |
|---------|--------|-------------|
| Output Orchestrator | ✅ Done | 9 Structures + 29 Modules |
| Conversational Context | ✅ Done | Full pipeline context |
| Dynamic Suggestions | ✅ Done | SuggestionEngine |
| Query Understanding | ✅ Done | Pronoun resolution |

---

## 📋 Upcoming Versions

### 🔴 V10 - Authentication & Multi-Tenant (Next)
**Duration**: ~13 days | **Status**: 📋 PLANNED

| Feature | Priority | Description |
|---------|----------|-------------|
| **Supabase Auth** | 🔴 Critical | Login, Signup, OAuth |
| **Row Level Security** | 🔴 Critical | Data isolation per user |
| **User Quotas** | 🔴 High | Tier-based limits |
| **CI/CD Professional** | 🔴 High | Staging + auto-deploy |
| E2E Tests (Playwright) | 🟡 Medium | End-to-end testing |

📄 **[V10 Implementation Plan](./V10_IMPLEMENTATION_PLAN.md)**

---

### 🟢 V11 - PostgreSQL FTS + LangGraph
**Duration**: ~10 days | **Status**: 📋 PLANNED | **Cost**: $0/month

| Feature | Priority | Description |
|---------|----------|-------------|
| **PostgreSQL FTS** | 🔴 Critical | BM25 en cloud (gratis en Supabase) |
| **LangGraph Pipeline** | 🔴 High | Stateful RAG con memoria |
| Analytics Básico | 🟡 Medium | Tablas en Supabase (gratis) |
| Mejorar Hybrid Search | � Medium | Fuzzy, sinónimos |

📄 **[V11 Implementation Plan](./V11_IMPLEMENTATION_PLAN.md)**

---

### 🌐 V12 - Simple Deploy (FREE)
**Duration**: ~3 days | **Status**: 📋 PLANNED | **Cost**: $0/month

| Feature | Priority | Description |
|---------|----------|-------------|
| **Vercel (Frontend)** | 🔴 Critical | FREE tier, CDN global |
| **Render (Backend)** | 🔴 Critical | FREE tier, 750h/mes |
| **Supabase** | 🔴 Critical | Ya configurado, FREE |
| Monitoring Básico | 🟡 Medium | UptimeRobot (gratis) |

📄 **[V12 Implementation Plan](./V12_IMPLEMENTATION_PLAN.md)**

---

## 🎯 Quick Navigation

```
docs/roadmap/
├── README.md                       ← You are here
├── V8_IMPLEMENTATION_PLAN.md       ← ✅ UX Features (COMPLETED)
├── V9_IMPLEMENTATION_PLAN.md       ← ✅ TypeScript + CI/CD (COMPLETED)
├── V10_IMPLEMENTATION_PLAN.md      ← 📋 Auth + Multi-Tenant (NEXT)
├── V11_IMPLEMENTATION_PLAN.md      ← 📋 PG FTS + LangGraph
├── V12_IMPLEMENTATION_PLAN.md      ← 📋 Simple Deploy (FREE)
├── RAG_V7.md                       ← ✅ ML models (COMPLETED)
├── CONFIDENCE.md                   ← LLM-as-Judge & calibration
├── ADVANCED_EVAL.md                ← Token analysis & citations
└── SECURITY_IMPROVEMENTS.md        ← Covered in V10 (Auth)
```

---

## 🛠️ New Technologies by Version

| Version | Technologies Added | Monthly Cost |
|---------|-------------------|--------------|
| **V9** | TypeScript, GitHub Actions | $0 |
| **V10** | Supabase Auth, Playwright E2E | $0 |
| **V11** | PostgreSQL FTS, LangGraph | $0 |
| **V12** | Vercel, Render (FREE tiers) | $0 |

### ❌ Tecnologías Descartadas (innecesarias para prototipo)
- ~~Elasticsearch~~ → PostgreSQL FTS (gratis en Supabase)
- ~~Kubernetes~~ → Vercel + Render (gratis)
- ~~AWS/GCP managed~~ → Free tiers suficientes

---

## 📊 Estimated Timeline & Costs

| Version | Duration | Key Deliverables | Monthly Cost |
|---------|----------|------------------|--------------|
| V9 | ~15 días | TypeScript, CI/CD | $0 |
| V10 | ~13 días | Auth, RLS | $0 |
| V11 | ~10 días | PG FTS, LangGraph | $0 |
| V12 | ~3 días | Production deploy | $0 |
| **Total** | **~41 días** | **Production-ready** | **$0/month** |

*Solo pagas por uso de LLM (OpenRouter): ~$1-5/mes con uso moderado*

---

## 📑 Legacy Planning Documents

| Priority | Document | Description |
|----------|----------|-------------|
| 🟡 Medium | [Confidence Improvements](./CONFIDENCE.md) | Answer confidence calibration |
| 🟢 Low | [Advanced Evaluation](./ADVANCED_EVAL.md) | Production metrics dashboard |

---

## 🔗 Related Documentation

| Document | Description |
|----------|-------------|
| [RAG Workflow](../RAG_WORKFLOW.md) | Current RAG pipeline architecture |
| [Architecture](../ARCHITECTURE.md) | System architecture overview |
| [Structured Output](../STRUCTURED_OUTPUT.md) | 9 Structures + 29 Modules |
| [Evaluation Criteria](../evaluation/) | Project evaluation documentation |

---

<div align="center">

**[← Back to Docs](../README.md)** · **[← Back to Main README](../../README.md)**

</div>
