# CV Screener - AI-Powered Resume Analysis

An AI-powered CV screening application with **switchable backend modes** (Local/Cloud). Upload PDF resumes and query them using natural language with RAG (Retrieval-Augmented Generation).

**Core Principle:** Zero hallucinations. Every response is traceable to source documents.

## ✨ Features

- **Dual Mode Architecture**: Switch between Local and Cloud backends
- **2-Step RAG Pipeline**: Query understanding + Response generation with configurable models
- **LangChain Integration**: Optional LangChain-based RAG service
- **PDF Upload**: Drag & drop multiple CV files for processing
- **Smart Extraction**: Automatic text extraction and semantic chunking
- **Natural Language Queries**: Ask questions about candidates in plain English
- **Source Citations**: Every answer includes clickable references to source CVs
- **Guardrails**: Pre-LLM filtering for off-topic questions
- **Anti-Hallucination**: Post-LLM verification of CV references
- **Performance Metrics**: Real-time display of embedding, search, and LLM latencies
- **TypeScript Frontend**: Type-safe React components
- **Shadcn UI Components**: Modern, accessible UI components

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                 FRONTEND (React + TypeScript + Shadcn)            │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Sessions | CVs | Chat | RAG Pipeline Settings             │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI + LangChain)                  │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ STEP 1: Query Understanding (fast model)                   │  │
│  │ → Analyze question → Extract requirements → Reformulate    │  │
│  └────────────────────────────────────────────────────────────┘  │
│                               │                                   │
│                               ▼                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Guardrails → Embedding → Vector Search → LLM Generation    │  │
│  └────────────────────────────────────────────────────────────┘  │
│                               │                                   │
│                               ▼                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ STEP 2: Hallucination Check → Eval Logging                 │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌─────────────────┐              ┌─────────────────┐            │
│  │  LOCAL MODE     │              │  CLOUD MODE     │            │
│  │  SimpleVectorDB │              │  Supabase       │            │
│  │  (JSON+cosine)  │              │  pgvector       │            │
│  └─────────────────┘              └─────────────────┘            │
└──────────────────────────────────────────────────────────────────┘
```

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | React 18 + TypeScript | UI Framework |
| **UI Components** | Shadcn UI + Radix | Accessible components |
| **Styling** | TailwindCSS | Utility-first CSS |
| **Backend** | FastAPI + Python 3.11+ | REST API |
| **RAG Framework** | LangChain (optional) | RAG orchestration |
| **Embeddings** | OpenRouter (nomic-embed-text-v1.5) | 768-dim vectors |
| **Vector Store (Local)** | SimpleVectorStore | JSON + cosine similarity |
| **Vector Store (Cloud)** | Supabase pgvector | PostgreSQL vectors |
| **LLM** | OpenRouter API | Multi-model support |
| **PDF Processing** | pdfplumber | Text extraction |

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- OpenRouter API key (get free at https://openrouter.ai)
- **(Cloud Mode)**: Supabase project

### 1. Clone and Setup

```bash
git clone https://github.com/yourusername/cv-screener.git
cd cv-screener

# Backend setup
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your OPENROUTER_API_KEY

# Frontend setup
cd ../frontend
npm install
```

### 2. Run the Application

```bash
# From project root - starts both backend and frontend
npm run dev

# Or separately:
python start_api.py   # Backend (auto-finds available port from 8000)
python start_web.py   # Frontend (auto-finds available port from 6001)
```

### 3. Cloud Mode Setup (Optional)

For Supabase pgvector:

1. Create project at https://supabase.com
2. Run migration: `supabase/migrations/001_cv_embeddings.sql`
3. Add credentials to `.env`:
   ```
   SUPABASE_URL=https://xxxxx.supabase.co
   SUPABASE_SERVICE_KEY=eyJ...
   ```

### 4. Enable LangChain (Optional)

```bash
# In .env
USE_LANGCHAIN=true
```

## API Endpoints

All endpoints accept a `mode` query parameter: `?mode=local` or `?mode=cloud`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/upload?mode=local` | Upload PDF files |
| GET | `/api/status/{job_id}` | Check processing status |
| GET | `/api/cvs?mode=local` | List indexed CVs |
| DELETE | `/api/cvs/{cv_id}?mode=local` | Remove a CV |
| POST | `/api/chat?mode=local` | Send a query |
| GET | `/api/stats?mode=local` | Get system statistics |
| GET | `/api/health` | Health check |

## Example Queries

Once you've uploaded CVs, try asking:

- "Who has experience with Python?"
- "List candidates from New York"
- "Who worked at Google?"
- "Compare the top 3 candidates for a senior developer role"
- "Which candidates have a Master's degree?"
- "Who has more than 5 years of experience?"

## Project Structure

```
cv-screener/
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI routes
│   │   ├── services/      # Business logic
│   │   ├── models/        # Pydantic schemas
│   │   ├── prompts/       # LLM prompt templates
│   │   └── utils/         # Utilities
│   ├── tests/             # Backend tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── hooks/         # Custom hooks
│   │   └── services/      # API client
│   └── package.json
├── .env.example           # Environment template
├── .gitignore
└── README.md
```

## Environment Variables

Copy `.env.example` to `.env` in the backend directory:

```bash
# Required
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza...

# Optional
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:5173
LOG_LEVEL=INFO
```

## Security

- API keys are stored in `.env` files (never committed to git)
- `.env` is included in `.gitignore`
- See `SECURITY.md` for best practices

## Testing

### Backend Tests

```bash
cd backend
pytest
```

### Frontend Tests

```bash
cd frontend
npm test
```

## Cost Estimation

| Operation | Model | Cost |
|-----------|-------|------|
| Embeddings | text-embedding-3-small | $0.02 / 1M tokens |
| Generation | gemini-1.5-flash | $0.075 / 1M input, $0.30 / 1M output |

Typical usage (30 CVs, 50 queries): ~$0.05-0.15

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- OpenAI for embeddings API
- Google for Gemini LLM
- LangChain community for RAG patterns
