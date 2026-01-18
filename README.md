<div align="center">

# 🎯 AI-Powered CV Screener

### Intelligent Resume Analysis with RAG Technology

[![Live Demo](https://img.shields.io/badge/🚀_Live_Demo-Railway-blueviolet.svg)](https://ai-poweredcvscreener-production.up.railway.app/)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://reactjs.org)
[![License](https://img.shields.io/badge/License-All%20Rights%20Reserved-red.svg)](LICENSE)

**Version 9.0** - Production-ready RAG pipeline deployed on Railway with TypeScript frontend, GitHub Actions CI/CD, full Cloud Parity (Supabase), HuggingFace NLI verification, RAGAS evaluation, Streaming, Export (PDF/CSV), Hybrid Search, 65+ query detection patterns, 9 output structures, 29+ modules, and intelligent query routing.

### 🌐 **[Try it Live →](https://ai-poweredcvscreener-production.up.railway.app/)**

[Features](#-features) · [Quick Start](#-quick-start) · [Architecture](#-architecture) · [Demo](#-demo) · [Deployment](#-deployment) · [Documentation](#-documentation)

</div>

---

## 🌟 Highlights

```
┌────────────────────────────────────────────────────────────────────────────┐
│                                                                            │
│  📄 Upload CVs    →    🔍 Ask Questions    →    ✅ Get Structured Answers  │
│                                                                            │
│  "Rank all candidates by experience and show red flags"                    │
│                                                                            │
│  ✨ Response:                                                               │
│     🏆 Top Pick: Juan García [cv:cv_a1b2c3] - 8 years, no red flags        │
│     📊 Risk Assessment Table with 5-factor analysis                        │
│     📎 Sources: Juan_Garcia.pdf (95%), Maria_Lopez.pdf (89%)               │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

**Core Principle**: Zero hallucinations. Every response is traceable to source documents with structured visual output.

---

## ✨ Features

### 🔄 Dual-Mode Architecture
Switch seamlessly between **Local** (ChromaDB + sentence-transformers) and **Cloud** (Supabase pgvector) backends.

### 🧠 Advanced RAG Pipeline (v9.0)
Multi-stage pipeline: Query Understanding → Multi-Query Expansion → Guardrails → Embedding → Hybrid Search (BM25 + Vector) → Cross-Encoder Reranking → Reasoning → Generation (Streaming) → NLI Verification → RAGAS Evaluation → Output Orchestration.

### 🔬 HuggingFace Integration (FREE)
- **NLI Verification**: Natural Language Inference for claim verification using `facebook/bart-large-mnli`
- **Cross-Encoder Reranking**: Semantic reranking with `BAAI/bge-reranker-base`
- **Zero-Shot Guardrails**: Topic classification without training
- **RAGAS Evaluation**: Automatic quality metrics (faithfulness, relevance, context)

### 🎯 9 Output Structures
Intelligent routing to specialized output formats: SingleCandidate, RiskAssessment, Comparison, Search, Ranking, JobMatch, TeamBuild, Verification, Summary.

### 🧩 29+ Reusable Modules
Modular components: Thinking, DirectAnswer, Analysis, Tables, RiskTable, MatchScore, Timeline, GapAnalysis, RedFlags, and more.

### 💬 Conversational Context
Full conversation history propagation for follow-up queries with pronoun resolution ("compare those 3", "tell me more about her").

### 🛡️ Anti-Hallucination System
Three-layer verification: Pre-LLM guardrails, claim verification, and entity validation.

### 📎 Source Citations
Every answer includes clickable references to source CVs with relevance scores.

### ⚡ Real-Time Pipeline Progress
Visual pipeline steps panel showing current stage, duration, and details for each processing step.

### 🎨 Modern UI
React 18 + Shadcn UI + TailwindCSS with dark mode, structured output rendering, and interactive components.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- [OpenRouter API Key](https://openrouter.ai) (free tier available)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ai-powered-cv-screener.git
cd ai-powered-cv-screener

# Backend setup
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your OPENROUTER_API_KEY

# Frontend setup
cd ../frontend
npm install
```

### Run

```bash
# Start both backend and frontend
npm run dev

# Or separately:
python scripts/start_api.py   # Backend → http://localhost:8000
python scripts/start_web.py   # Frontend → http://localhost:6001
```

### Usage

1. **Upload CVs**: Drag & drop PDF files
2. **Ask Questions**: "Who has Python experience?"
3. **Get Answers**: Receive cited responses with source documents

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React 18 + Shadcn UI)                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │ Sessions │ │   Chat   │ │ Pipeline │ │ Sources  │ │ Metrics  │          │
│  │  Panel   │ │ Window   │ │ Progress │ │ Badges   │ │  Panel   │          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
│  ┌──────────────────────────────────────────────────────────────┐          │
│  │              STRUCTURED OUTPUT RENDERER                       │          │
│  │  SingleCandidateProfile | RankingTable | RiskAssessment | ... │          │
│  └──────────────────────────────────────────────────────────────┘          │
└────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                        BACKEND (FastAPI + Python)                          │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      RAG PIPELINE v9.0                                │  │
│  Query → Understand → MultiQuery → Guardrail → Embed → HybridSearch → │  │
│  CrossEncoder → Generate(Stream) → NLI Verify → RAGAS → ORCHESTRATOR  │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                     │                                      │
│  ┌──────────────────────────────────┴───────────────────────────────────┐  │
│  │                      OUTPUT ORCHESTRATOR                              │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │  STRUCTURES (9): SingleCandidate | RiskAssessment | Comparison  │ │  │
│  │  │  Search | Ranking | JobMatch | TeamBuild | Verify | Summary     │ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  │  ┌─────────────────────────────────────────────────────────────────┐ │  │
│  │  │  MODULES (29+): Thinking | DirectAnswer | Analysis | RiskTable  │ │  │
│  │  │  MatchScore | Timeline | GapAnalysis | RedFlags | Skills | ...  │ │  │
│  │  └─────────────────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ┌─────────────────────────┐       ┌─────────────────────────┐             │
│  │      LOCAL MODE         │       │      CLOUD MODE         │             │
│  │  • ChromaDB             │  OR   │  • Supabase pgvector    │             │
│  │  • sentence-transformers│       │  • nomic-embed-v1.5     │             │
│  │  • 384-dim vectors      │       │  • 768-dim vectors      │             │
│  └─────────────────────────┘       └─────────────────────────┘             │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎬 Demo

### 🌐 Live Production

**[https://ai-poweredcvscreener-production.up.railway.app/](https://ai-poweredcvscreener-production.up.railway.app/)**

> **Note**: You'll need an [OpenRouter API Key](https://openrouter.ai/keys) (free tier available) to use the app. Enter it in Settings (⚙️) after loading.

### 📹 Video Demo

https://cap.so/s/9jnex9fx01ddcxp

### Sample Questions by Query Type

| Query Type | Example Question | Output Structure |
|------------|------------------|------------------|
| **Search** | "Who has experience with Python?" | Results table with match scores |
| **Single Candidate** | "Give me the full profile of Juan García" | Complete profile with highlights, career, skills, risks |
| **Ranking** | "Rank top 5 candidates for senior backend" | Ranking table + Top Pick card |
| **Comparison** | "Compare María vs Juan for leadership" | Side-by-side comparison table |
| **Red Flags** | "What are the red flags for this candidate?" | 5-factor risk assessment table |
| **Job Match** | "Who best fits a senior React developer role?" | Match scores + requirements coverage |
| **Team Build** | "Build a team of 3 developers" | Team composition + skill coverage |
| **Summary** | "Give me an overview of all candidates" | Talent pool summary + distributions |
| **Off-topic** | "What's a good recipe for pasta?" | Polite rejection ✓ |

### Response Format (v9.0)

```json
{
  "response": "Based on the CVs, the following candidates have Python experience...",
  "sources": [
    {"cv_id": "cv_a1b2c3", "filename": "John_Doe.pdf", "relevance": 0.92}
  ],
  "metrics": {
    "total_ms": 2340,
    "stages": {
      "query_understanding": {"duration_ms": 150, "success": true},
      "embedding": {"duration_ms": 45, "success": true},
      "search": {"duration_ms": 120, "success": true},
      "generation": {"duration_ms": 2000, "success": true}
    }
  },
  "confidence_score": 0.95,
  "pipeline_steps": [
    {"name": "Query Understanding", "status": "completed", "duration_ms": 150},
    {"name": "Vector Search", "status": "completed", "duration_ms": 120}
  ],
  "structured_output": {
    "structure_type": "search",
    "direct_answer": "3 candidates match Python experience",
    "results_table": { "headers": ["Candidate", "Experience", "Match"], "rows": [...] }
  }
}
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | React 18 + TypeScript (v9) | UI Framework |
| **UI Components** | Shadcn UI + Radix | Accessible components |
| **Styling** | TailwindCSS | Utility-first CSS |
| **Backend** | FastAPI + Python 3.11+ | REST API |
| **Embeddings (Local)** | sentence-transformers | 384-dim vectors |
| **Embeddings (Cloud)** | nomic-embed-text-v1.5 | 768-dim vectors |
| **Vector Store (Local)** | JSON + cosine similarity | Development |
| **Vector Store (Cloud)** | Supabase pgvector | Production |
| **LLM** | OpenRouter API | 100+ models supported |
| **PDF Processing** | pdfplumber | Text extraction |

---

## 📚 Documentation

### 🔗 Quick Access - Evaluation Documents

<table>
<tr>
<td align="center" width="140">

**📋 [INDEX](./docs/evaluation/README.md)**

*Start Here*

</td>
<td align="center" width="140">

**🚀 [01](./docs/evaluation/01_EXECUTION_AND_FUNCTIONALITY.md)**

*Execution*

</td>
<td align="center" width="140">

**🧠 [02](./docs/evaluation/02_THOUGHT_PROCESS.md)**

*Thought Process*

</td>
<td align="center" width="140">

**💎 [03](./docs/evaluation/03_CODE_QUALITY.md)**

*Code Quality*

</td>
<td align="center" width="140">

**💡 [04](./docs/evaluation/04_CREATIVITY_AND_INGENUITY.md)**

*Creativity*

</td>
<td align="center" width="140">

**🤖 [05](./docs/evaluation/05_AI_LITERACY.md)**

*AI Literacy*

</td>
<td align="center" width="140">

**📈 [06](./docs/evaluation/06_LEARN_AND_ADAPT.md)**

*Learn & Adapt*

</td>
</tr>
</table>

### Evaluation Criteria Documentation

Comprehensive documentation explaining how this project meets professional evaluation standards:

| # | Document | Description | Key Topics |
|---|----------|-------------|------------|
| 📋 | [**INDEX**](./docs/evaluation/INDEX.md) | Overview & Navigation | Summary matrix, quick links |
| 01 | [**Execution & Functionality**](./docs/evaluation/01_EXECUTION_AND_FUNCTIONALITY.md) | Working features & demo | RAG pipeline, API endpoints, demo scenarios |
| 02 | [**Thought Process**](./docs/evaluation/02_THOUGHT_PROCESS.md) | Architecture decisions | Why FastAPI, dual-mode design, embedding choices |
| 03 | [**Code Quality**](./docs/evaluation/03_CODE_QUALITY.md) | Code standards & patterns | Type safety, async patterns, error handling |
| 04 | [**Creativity & Ingenuity**](./docs/evaluation/04_CREATIVITY_AND_INGENUITY.md) | Innovative solutions | 3-layer verification, HyDE, RRF fusion, streaming |
| 05 | [**AI Literacy**](./docs/evaluation/05_AI_LITERACY.md) | AI industry knowledge | Embeddings, LLMs, vector DBs, circuit breakers |
| 06 | [**Learn & Adapt**](./docs/evaluation/06_LEARN_AND_ADAPT.md) | Learning demonstration | Evolution from v1→v5, problem-solving approach |

### Technical Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](./docs/ARCHITECTURE.md) | Detailed architecture |
| [MODES_EXPLANATION.md](./docs/MODES_EXPLANATION.md) | Local vs Cloud modes |
| [API Docs](http://localhost:8000/docs) | Interactive API (when running) |

### 🔒 Security & Roadmap

| Document | Description |
|----------|-------------|
| [SECURITY.md](./SECURITY.md) | Security best practices |
| [**🚨 SECURITY_IMPROVEMENTS.md**](./docs/roadmap/SECURITY_IMPROVEMENTS.md) | **Critical security improvements pending** |

---

## 📁 Project Structure

```
ai-powered-cv-screener/
├── backend/
│   ├── app/
│   │   ├── api/                    # FastAPI routes
│   │   │   ├── routes.py           # Legacy routes
│   │   │   ├── routes_v2.py        # Main API routes
│   │   │   ├── routes_sessions.py  # Session management
│   │   │   └── routes_sessions_stream.py  # SSE streaming
│   │   ├── providers/              # Embedding & storage providers
│   │   │   ├── local/              # ChromaDB + sentence-transformers
│   │   │   └── cloud/              # Supabase + OpenRouter
│   │   ├── services/               # Business logic
│   │   │   ├── rag_service_v5.py   # Main RAG pipeline (2958 lines)
│   │   │   ├── query_understanding_service.py
│   │   │   ├── output_processor/   # Output orchestration
│   │   │   │   ├── orchestrator.py # Routes to structures
│   │   │   │   ├── structures/     # 9 output structures
│   │   │   │   └── modules/        # 29+ reusable modules
│   │   │   └── suggestion_engine/  # Dynamic suggestions
│   │   ├── models/                 # Pydantic schemas
│   │   │   ├── schemas.py          # API schemas
│   │   │   ├── sessions.py         # Session models
│   │   │   └── structured_output.py # Output structures
│   │   └── prompts/                # LLM prompt templates
│   ├── tests/                      # Backend tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/             # React components
│   │   │   ├── output/             # Structured output renderers
│   │   │   ├── modals/             # Settings, About modals
│   │   │   └── ui/                 # Shadcn UI components
│   │   ├── contexts/               # React contexts
│   │   │   ├── PipelineContext.jsx # Pipeline state
│   │   │   ├── BackgroundTaskContext.jsx
│   │   │   └── LanguageContext.jsx
│   │   ├── hooks/                  # Custom hooks
│   │   └── services/               # API client
│   └── package.json
├── docs/                           # Complete documentation
│   ├── ARCHITECTURE_MODULES.md     # Orchestrator/Structures/Modules
│   ├── RAG_WORKFLOW.md             # Pipeline architecture
│   ├── STRUCTURED_OUTPUT.md        # Output processing
│   └── evaluation/                 # Evaluation criteria docs
├── scripts/                        # Setup & utility scripts
│   ├── setup_supabase_complete.sql # Supabase schema
│   └── reindex_cvs.py              # Re-indexing utility
├── supabase/migrations/            # Database migrations
├── .env.example                    # Environment template
└── README.md                       # You are here
```

---

## ⚙️ Configuration

### Environment Variables

```bash
# Required
OPENROUTER_API_KEY=your_openrouter_api_key

# Mode Selection
DEFAULT_MODE=local            # "local" | "cloud"

# Cloud Mode (optional)
SUPABASE_URL=your_supabase_project_url
SUPABASE_SERVICE_KEY=your_key_here

# Server
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:5173
```

### API Endpoints

#### Session Management
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/sessions?mode=cloud` | List all sessions |
| `POST` | `/api/sessions?mode=cloud` | Create new session |
| `GET` | `/api/sessions/{id}?mode=cloud` | Get session details |
| `DELETE` | `/api/sessions/{id}?mode=cloud` | Delete session |

#### CV Management (within sessions)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/sessions/{id}/cvs?mode=cloud` | Upload CVs to session |
| `GET` | `/api/sessions/{id}/cvs/status/{job_id}` | Check upload status |
| `DELETE` | `/api/sessions/{id}/cvs/{cv_id}?mode=cloud` | Remove CV from session |

#### Chat & Suggestions
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/sessions/{id}/chat?mode=cloud` | Send chat message |
| `GET` | `/api/sessions/{id}/suggestions?mode=cloud` | Get contextual suggestions |
| `DELETE` | `/api/sessions/{id}/chat?mode=cloud` | Clear chat history |
| `POST` | `/api/sessions/{id}/generate-name?mode=cloud` | AI-generate session name |

#### Global
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/models` | List available LLM models |
| `GET` | `/api/cvs/{cv_id}/pdf?mode=cloud` | Get CV PDF file |

---

## 🚀 Deployment

### Production Environment

The application is deployed on **Railway** with the following architecture:

| Component | Service | Details |
|-----------|---------|---------|
| **Frontend + Backend** | Railway (Monolith) | Single container with Nginx + FastAPI |
| **Database** | Supabase | PostgreSQL with pgvector for embeddings |
| **File Storage** | Supabase Storage | CV PDFs stored in `cv-pdfs` bucket |
| **LLM API** | OpenRouter | User-provided API keys (client-side) |

### Live URLs

| Environment | URL |
|-------------|-----|
| **Production** | [https://ai-poweredcvscreener-production.up.railway.app/](https://ai-poweredcvscreener-production.up.railway.app/) |
| **API Docs** | [https://ai-poweredcvscreener-production.up.railway.app/docs](https://ai-poweredcvscreener-production.up.railway.app/docs) |

### Why This Architecture?

1. **Zero Fixed Costs**: Supabase free tier + Railway pay-per-use = $0/month base cost
2. **User-Provided API Keys**: Each user brings their own OpenRouter key, no server-side LLM costs
3. **Monolith for Simplicity**: Single container deployment reduces complexity and cold start times
4. **Supabase pgvector**: Production-grade vector search without managing infrastructure

### Deploy Your Own

```bash
# Fork this repo, then:
railway login
railway init
railway up

# Set environment variables in Railway dashboard:
# - SUPABASE_URL
# - SUPABASE_SERVICE_KEY
# - DEFAULT_MODE=cloud
```

📄 **[Full Deployment Guide →](./DEPLOYMENT.md)**

---

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

---

## 💰 Cost Estimation

| Operation | Model | Cost |
|-----------|-------|------|
| Embeddings (Cloud) | nomic-embed-v1.5 | ~$0.02 / 1M tokens |
| Query Understanding | GPT-3.5 / Gemini Flash | ~$0.0001 / query |
| Generation | GPT-4o / Claude 3.5 | ~$0.01 / query |

**Typical usage** (30 CVs, 50 queries): **~$0.10-0.20**

**Local mode**: **$0** (uses local embeddings)

---

## 📄 License

**All Rights Reserved** - This source code is provided for viewing purposes only as part of a professional portfolio demonstration. See [LICENSE](LICENSE) for full terms.

---

<div align="center">

**Built with ❤️ for intelligent CV screening**

[⬆ Back to Top](#-ai-powered-cv-screener)

</div>
