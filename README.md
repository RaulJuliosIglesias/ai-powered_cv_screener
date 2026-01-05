<div align="center">

# 🎯 AI-Powered CV Screener

### Intelligent Resume Analysis with RAG Technology

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://reactjs.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**A production-ready RAG pipeline for CV/Resume screening with dual-mode architecture, hallucination detection, and source-cited responses.**

[Features](#-features) · [Quick Start](#-quick-start) · [Architecture](#-architecture) · [Demo](#-demo) · [Documentation](#-documentation)

</div>

---

## 🌟 Highlights

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                              │
│   📄 Upload CVs    →    🔍 Ask Questions    →    ✅ Get Cited Answers       │
│                                                                              │
│   "Who has Python experience?"                                               │
│                                                                              │
│   ✨ Response: Based on the CVs, John Doe [CV:cv_a1b2c3] has 5 years...     │
│      📎 Sources: John_Doe.pdf (92%), Jane_Smith.pdf (87%)                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Core Principle**: Zero hallucinations. Every response is traceable to source documents.

---

## ✨ Features

### 🔄 Dual-Mode Architecture
Switch seamlessly between **Local** (free development) and **Cloud** (production-ready) backends with a single parameter.

### 🧠 11-Stage RAG Pipeline
Advanced pipeline with query understanding, multi-query expansion, guardrails, reranking, and verification.

### 🛡️ Anti-Hallucination System
Three-layer verification: Pre-LLM guardrails, claim verification, and entity validation.

### 📎 Source Citations
Every answer includes clickable references to source CVs with relevance scores.

### ⚡ Real-Time Streaming
SSE-based streaming shows pipeline progress and token-by-token generation.

### 🎨 Modern UI
React 18 + Shadcn UI + TailwindCSS for a clean, accessible interface.

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
python start_api.py   # Backend → http://localhost:8000
python start_web.py   # Frontend → http://localhost:6001
```

### Usage

1. **Upload CVs**: Drag & drop PDF files
2. **Ask Questions**: "Who has Python experience?"
3. **Get Answers**: Receive cited responses with source documents

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React + Shadcn UI)                         │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│   │   Upload    │  │    Chat     │  │   Sources   │  │   Metrics   │       │
│   └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BACKEND (FastAPI + Python)                           │
│                                                                              │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                      11-STAGE RAG PIPELINE                           │   │
│   │                                                                      │   │
│   │  Query → Understand → MultiQuery → Guardrail → Embed → Search →     │   │
│   │  Rerank → Reason → Generate → Verify Claims → Check Hallucinations  │   │
│   │                                                                      │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│   ┌───────────────────────┐          ┌───────────────────────┐             │
│   │     LOCAL MODE        │          │     CLOUD MODE        │             │
│   │  • JSON Vector Store  │   OR     │  • Supabase pgvector  │             │
│   │  • sentence-transform │          │  • nomic-embed-v1.5   │             │
│   │  • Zero cost          │          │  • Production-ready   │             │
│   └───────────────────────┘          └───────────────────────┘             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🎬 Demo

### Sample Questions

| Question | What It Tests |
|----------|---------------|
| "Who has experience with Python?" | Skill search |
| "Which candidate graduated from UPC?" | Education lookup |
| "Summarize the profile of Jane Doe" | Single CV summary |
| "Compare top 3 candidates for a senior role" | Ranking & comparison |
| "What's a good recipe for pasta?" | Off-topic rejection ✓ |

### Response Format

```json
{
  "response": "Based on the CVs, the following candidates have Python experience...",
  "sources": [
    {"cv_id": "cv_a1b2c3", "filename": "John_Doe.pdf", "relevance": 0.92},
    {"cv_id": "cv_d4e5f6", "filename": "Jane_Smith.pdf", "relevance": 0.87}
  ],
  "metrics": {
    "total_ms": 2340,
    "embedding_ms": 45,
    "search_ms": 120,
    "generation_ms": 2100
  },
  "confidence": 0.95
}
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | React 18 + TypeScript | UI Framework |
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

**📋 [INDEX](./docs/evaluation/INDEX.md)**

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
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Detailed architecture |
| [MODES_EXPLANATION.md](./MODES_EXPLANATION.md) | Local vs Cloud modes |
| [API Docs](http://localhost:8000/docs) | Interactive API (when running) |

---

## 📁 Project Structure

```
ai-powered-cv-screener/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI routes
│   │   ├── providers/        # Embedding & storage providers
│   │   │   ├── local/        # Local implementations
│   │   │   └── cloud/        # Cloud implementations
│   │   ├── services/         # Business logic & RAG pipeline
│   │   ├── models/           # Pydantic schemas
│   │   └── prompts/          # LLM prompt templates
│   ├── tests/                # Backend tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── hooks/            # Custom hooks
│   │   └── services/         # API client
│   └── package.json
├── docs/
│   └── evaluation/           # Evaluation criteria docs
├── .env.example              # Environment template
└── README.md                 # You are here
```

---

## ⚙️ Configuration

### Environment Variables

```bash
# Required
OPENROUTER_API_KEY=sk-or-v1-your_key_here

# Mode Selection
DEFAULT_MODE=local            # "local" | "cloud"

# Cloud Mode (optional)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=your_key_here

# Server
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:5173
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload?mode=local` | Upload PDF files |
| `GET` | `/api/status/{job_id}` | Check processing status |
| `GET` | `/api/cvs?mode=local` | List indexed CVs |
| `DELETE` | `/api/cvs/{cv_id}?mode=local` | Remove a CV |
| `POST` | `/api/chat?mode=local` | Send a query |
| `GET` | `/api/health` | Health check |

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

MIT License - see [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with ❤️ for intelligent CV screening**

[⬆ Back to Top](#-ai-powered-cv-screener)

</div>
