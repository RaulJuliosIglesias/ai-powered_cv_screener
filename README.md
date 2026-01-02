# CV Screener - AI-Powered Resume Analysis

An AI-powered CV screening application with **switchable backend modes** (Local/Cloud). Upload PDF resumes and query them using natural language with RAG (Retrieval-Augmented Generation).

**Core Principle:** Zero hallucinations. Every response is traceable to source documents.

## Features

- **Dual Mode Architecture**: Switch between Local and Cloud backends
- **PDF Upload**: Drag & drop multiple CV files for processing
- **Smart Extraction**: Automatic text extraction and semantic chunking
- **Natural Language Queries**: Ask questions about candidates in plain English
- **Source Citations**: Every answer includes references to the source CVs
- **Performance Metrics**: Real-time display of embedding, search, and LLM latencies
- **Mode Comparison**: Compare performance between Local and Cloud modes

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React)                         │
│  ┌─────────────┐  ┌──────────────────────────────────────┐  │
│  │ MODE SWITCH │  │           METRICS BAR                │  │
│  │ ○ Local     │  │ Embed: 52ms | Search: 8ms | LLM: 823ms│  │
│  │ ● Cloud     │  │ Total: 883ms | Mode: cloud           │  │
│  └─────────────┘  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI)                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              PROVIDER FACTORY                        │    │
│  │   mode = "local" | "cloud"                           │    │
│  │         │                    │                       │    │
│  │   ┌─────┴─────┐        ┌─────┴─────┐                 │    │
│  │   │   LOCAL   │        │   CLOUD   │                 │    │
│  │   │ SentenceT │        │ OpenRouter│                 │    │
│  │   │ ChromaDB  │        │ Supabase  │                 │    │
│  │   │ Gemini    │        │ OpenRouter│                 │    │
│  │   └───────────┘        └───────────┘                 │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Tech Stack

### Local Mode
| Component | Technology | Purpose |
|-----------|------------|---------|
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) | Local embedding generation |
| Vector Store | ChromaDB | Local vector database |
| LLM | Google Gemini (gemini-1.5-flash) | Response generation |

### Cloud Mode
| Component | Technology | Purpose |
|-----------|------------|---------|
| Embeddings | OpenRouter (nomic-embed-text-v1.5) | API-based embeddings |
| Vector Store | Supabase pgvector | Cloud PostgreSQL with vectors |
| LLM | OpenRouter (gemini-2.0-flash-exp:free) | API-based LLM |

### Shared
- **Python 3.11+** with FastAPI
- **React 18** with Vite
- **TailwindCSS** for styling
- **pdfplumber** for PDF extraction

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- **Local Mode**: Google API key (for Gemini)
- **Cloud Mode**: OpenRouter API key + Supabase project

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/cv-screener.git
cd cv-screener
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env

# Edit .env with your API keys (see Environment Variables section)

# Start the server
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:5173`

### 4. Cloud Mode Setup (Optional)

If using Cloud mode with Supabase:

1. Create a Supabase project at https://supabase.com
2. Run the migration SQL in `supabase/migrations/001_create_cv_embeddings.sql`
3. Add your Supabase credentials to `.env`

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
