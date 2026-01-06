# 📚 Documentation

> Complete documentation for the **AI-Powered CV Screener** project.
>
> **Version 6.0** | January 2026

---

## 🆕 What's New in v6.0

### Complete Orchestration Architecture
New **Orchestrator → Structures → Modules** system with:

| Component | Count | Description |
|-----------|-------|-------------|
| **Structures** | 9 | Complete output assemblers (SingleCandidate, Comparison, JobMatch, etc.) |
| **Modules** | 25+ | Reusable components (Thinking, Analysis, RiskTable, MatchScore, etc.) |
| **Query Types** | 9 | Intelligent routing based on query classification |

### 9 Structures Implemented

| Structure | Query Type | Example |
|-----------|------------|---------|
| SingleCandidateStructure | `single_candidate` | "Dame el perfil de Juan" |
| RiskAssessmentStructure | `red_flags` | "Qué red flags tiene María?" |
| ComparisonStructure | `comparison` | "Compara Juan y María" |
| SearchStructure | `search` | "Busca developers Python" |
| RankingStructure | `ranking` | "Top 5 para backend" |
| JobMatchStructure | `job_match` | "Quién encaja para senior?" |
| TeamBuildStructure | `team_build` | "Build a team of 3" |
| VerificationStructure | `verification` | "Verify AWS certification" |
| SummaryStructure | `summary` | "Overview of candidates" |

### Conversational Context
- `conversation_history` propagated through entire pipeline
- Structures receive context for follow-up queries
- Pronoun resolution for "he/she/this candidate"

---

## 📁 Structure

```
docs/
├── README.md                      ← You are here
├── INSTRUCTIONS.md                ← Complete setup and usage guide
├── RAG_WORKFLOW.md                ← RAG pipeline architecture (v6.0)
├── STRUCTURED_OUTPUT.md           ← Structured output processing (v6.0)
├── ARCHITECTURE_MODULES.md        ← Orchestrator/Structures/Modules architecture
├── CONVERSATIONAL_CONTEXT.md      ← Context system (implemented)
├── METADATA_FLOW.md               ← Metadata extraction pipeline
├── RED_FLAGS_ARCHITECTURE.md      ← Red flags detection system
├── CHANGELOG_ARCHITECTURE_V6.md   ← All v6.0 changes documented
├── testeo/                        ← Testing documentation
│   └── TEST_ORCHESTRATION_...md   ← Query tests per structure
├── NextUpdate/                    ← Reference architecture docs
├── evaluation/                    ← Project evaluation criteria
├── roadmap/                       ← Future plans
└── archive/                       ← Historical documentation
```

---

## 📄 Main Documents

| Document | Description |
|----------|-------------|
| [INSTRUCTIONS.md](./INSTRUCTIONS.md) | Complete installation, configuration, and usage guide |
| [RAG_WORKFLOW.md](./RAG_WORKFLOW.md) | RAG pipeline architecture with orchestration |
| [STRUCTURED_OUTPUT.md](./STRUCTURED_OUTPUT.md) | 9 structures + 25 modules system |
| [ARCHITECTURE_MODULES.md](./ARCHITECTURE_MODULES.md) | Complete Orchestrator → Structures → Modules reference |
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
- **Context Resolution** - Smart pronoun resolution using context
- **Context-Aware Structures** - Structures adapt based on conversation
- **Smart Context Management** - Intelligent message selection
- **Confidence Calibration** - Response confidence scoring

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
