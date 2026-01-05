# 📚 Documentation

> Complete documentation for the **AI-Powered CV Screener** project.
>
> **Version 5.1.1** | January 2026

---

## 🆕 What's New in v5.1.1

### Enhanced Analysis Modules
Three new powerful modules that analyze CV metadata:

| Module | Purpose |
|--------|---------|
| **GapAnalysisModule** | Skills gap detection vs job requirements |
| **RedFlagsModule** | Risk detection (job-hopping, gaps, short tenures) |
| **TimelineModule** | Career trajectory visualization with progression scoring |

### Enriched Metadata Indexing
Each CV now extracts:
- `total_experience_years`, `seniority_level`, `current_role`
- `job_hopping_score`, `avg_tenure_years`, `has_faang_experience`
- `employment_gaps`, `companies_worked`

### New Question Types
```
"¿Hay candidatos con job hopping?"
"¿Quién tiene la mejor progresión de carrera?"
"¿Qué gaps tienen los candidatos para el puesto de Lead?"
"Dame los candidatos más estables sin red flags"
```

---

## 📁 Structure

```
docs/
├── README.md                 ← You are here
├── INSTRUCTIONS.md           ← Complete setup and usage guide
├── RAG_WORKFLOW.md           ← RAG pipeline architecture (v5.1.1)
├── STRUCTURED_OUTPUT.md      ← Structured output & 8 modules (v5.1.1)
├── evaluation/               ← Project evaluation criteria
├── roadmap/                  ← Future plans and improvements
└── archive/                  ← Historical documentation
```

---

## 📄 Main Documents

| Document | Description |
|----------|-------------|
| [INSTRUCTIONS.md](./INSTRUCTIONS.md) | Complete installation, configuration, and usage guide |
| [RAG_WORKFLOW.md](./RAG_WORKFLOW.md) | Technical documentation of RAG pipeline, embeddings, and data flow |
| [STRUCTURED_OUTPUT.md](./STRUCTURED_OUTPUT.md) | Structured output processing, **8 modules** (5 core + 3 enhanced), and data models |

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
Future development plans and planned improvements:
- **RAG V6** - Pipeline improvements with HuggingFace NLI
- **Confidence** - Confidence calibration system
- **Advanced Evaluation** - Advanced metrics
- **Security Improvements** - Security hardening

### [📦 archive/](./archive/)
Historical documentation of already implemented plans. Useful for understanding project evolution.

---

## 🔗 Related Documentation

| Document | Location | Description |
|----------|----------|-------------|
| [Main README](../README.md) | Project root | Quick start and overview |
| [ARCHITECTURE.md](../ARCHITECTURE.md) | Project root | Detailed technical architecture |
| [MODES_EXPLANATION.md](../MODES_EXPLANATION.md) | Project root | Local vs Cloud mode explanation |
| [SECURITY.md](../SECURITY.md) | Project root | Security considerations |

---

<div align="center">

**[← Back to Main README](../README.md)**

</div>
