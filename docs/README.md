# 📚 Documentation

> Complete documentation for the **AI-Powered CV Screener** project.
>
> **Version 6.0** | January 2026

---

## 🆕 What's New in v6.0

### Complete Orchestration Architecture
**Orchestrator → Structures → Modules** system:

| Component | Count | Description |
|-----------|-------|-------------|
| **Structures** | 9 | Complete output assemblers (SingleCandidate, RiskAssessment, Comparison, etc.) |
| **Modules** | 29+ | Reusable components (Thinking, Analysis, RiskTable, MatchScore, Skills, etc.) |
| **Query Types** | 9 | Intelligent routing based on query classification |

### 9 Structures Implemented

| Structure | Query Type | Example |
|-----------|------------|---------|
| SingleCandidateStructure | `single_candidate` | "Give me the full profile of Juan" |
| RiskAssessmentStructure | `red_flags` | "What red flags does María have?" |
| ComparisonStructure | `comparison` | "Compare Juan and María" |
| SearchStructure | `search` | "Find Python developers" |
| RankingStructure | `ranking` | "Top 5 for backend" |
| JobMatchStructure | `job_match` | "Who fits for senior position?" |
| TeamBuildStructure | `team_build` | "Build a team of 3" |
| VerificationStructure | `verification` | "Verify AWS certification" |
| SummaryStructure | `summary` | "Overview of candidates" |

### Conversational Context
- `conversation_history` propagated through entire pipeline
- Structures receive context for follow-up queries
- Pronoun resolution: "compare those 3", "tell me more about her"

### Session-Based Architecture
- CVs organized in sessions (not global)
- Chat history per session with pipeline_steps and structured_output
- Duplicate CV detection via content hash
- AI-powered session naming

### Dual-Mode Support
- **LOCAL**: JSON vector store + sentence-transformers (384 dims) + JSON persistence
- **CLOUD**: Supabase pgvector + nomic-embed (768 dims) + Supabase Storage

---

## 📁 Structure

```
docs/
├── README.md                      ← You are here
├── RAG_WORKFLOW.md                ← RAG pipeline architecture (v6.0)
├── STRUCTURED_OUTPUT.md           ← Structured output processing (v6.0)
├── ARCHITECTURE_MODULES.md        ← Orchestrator/Structures/Modules architecture
├── CONVERSATIONAL_CONTEXT.md      ← Context system (implemented)
├── METADATA_FLOW.md               ← Metadata extraction pipeline
├── RED_FLAGS_ARCHITECTURE.md      ← Red flags detection system
├── CHANGELOG_ARCHITECTURE_V6.md   ← All v6.0 changes documented
├── architecture-visualization.html ← Interactive D3.js architecture diagram
├── testeo/                        ← Testing documentation
├── NextUpdate/                    ← Future architecture plans
├── evaluation/                    ← Project evaluation criteria
├── roadmap/                       ← Future development plans
└── archive/                       ← Historical documentation
```

---

## 📄 Main Documents

| Document | Description |
|----------|-------------|
| [RAG_WORKFLOW.md](./RAG_WORKFLOW.md) | RAG pipeline architecture with all stages |
| [STRUCTURED_OUTPUT.md](./STRUCTURED_OUTPUT.md) | 9 structures + 29 modules system |
| [ARCHITECTURE_MODULES.md](./ARCHITECTURE_MODULES.md) | Complete Orchestrator → Structures → Modules reference |
| [CONVERSATIONAL_CONTEXT.md](./CONVERSATIONAL_CONTEXT.md) | Context propagation and pronoun resolution |
| [CHANGELOG_ARCHITECTURE_V6.md](./CHANGELOG_ARCHITECTURE_V6.md) | All v6.0 changes and bug fixes |

---

## 📂 Folders

### [📋 evaluation/](./evaluation/)
Documentation demonstrating how the project meets professional evaluation criteria:
- **Execution & Functionality** - Working features demonstration
- **Thought Process** - Architecture decisions
- **Code Quality** - Code standards and patterns
- **Creativity & Ingenuity** - Innovative solutions
- **AI Literacy** - AI tools and industry knowledge
- **Learn & Adapt** - Learning and growth capability

### [🚀 roadmap/](./roadmap/)
Future development plans:
- **Advanced Evaluation** - Automated response quality metrics
- **Confidence Calibration** - Response confidence scoring
- **RAG v7 Enhancements** - Advanced ML models, NLI verification, Cross-Encoder reranking

### [📦 archive/](./archive/)
Historical documentation of already implemented plans. Useful for understanding project evolution.

---

## 🔧 Key Backend Components

| Component | Location | Description |
|-----------|----------|-------------|
| RAG Service v5 | `backend/app/services/rag_service_v5.py` | Main pipeline (2900+ lines) |
| Query Understanding | `backend/app/services/query_understanding_service.py` | Query classification |
| Output Orchestrator | `backend/app/services/output_processor/orchestrator.py` | Routes to structures |
| Structures (9) | `backend/app/services/output_processor/structures/` | Output assemblers |
| Modules (29+) | `backend/app/services/output_processor/modules/` | Reusable components |
| Suggestion Engine | `backend/app/services/suggestion_engine/` | Contextual suggestions |
| Prompt Templates | `backend/app/prompts/templates.py` | LLM prompts |

## 🎨 Key Frontend Components

| Component | Location | Description |
|-----------|----------|-------------|
| App | `frontend/src/App.jsx` | Main application |
| StructuredOutputRenderer | `frontend/src/components/output/` | Renders structured responses |
| PipelineContext | `frontend/src/contexts/PipelineContext.jsx` | Pipeline state |
| BackgroundTaskContext | `frontend/src/contexts/BackgroundTaskContext.jsx` | Upload tasks |
| API Client | `frontend/src/services/api.ts` | Backend communication |

---

## 🔗 Related Documentation

| Document | Location | Description |
|----------|----------|-------------|
| [Main README](../README.md) | Project root | Quick start and overview |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | docs/ | Complete technical architecture v6.0 |
| [MODES_EXPLANATION.md](./MODES_EXPLANATION.md) | docs/ | Local vs Cloud mode details |
| [SECURITY.md](../SECURITY.md) | Project root | Security considerations |

---

<div align="center">

**[← Back to Main README](../README.md)**

</div>
