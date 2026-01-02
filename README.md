# CV Screener - AI-Powered Resume Analysis

An AI-powered CV screening application that allows users to upload PDF resumes and query them using natural language. The system uses Retrieval-Augmented Generation (RAG) to provide accurate, grounded answers based exclusively on the uploaded CV content.

**Core Principle:** Zero hallucinations. Every response is traceable to source documents.

![CV Screener Demo](docs/demo.png)

## Features

- **PDF Upload**: Drag & drop multiple CV files for processing
- **Smart Extraction**: Automatic text extraction and semantic chunking
- **Natural Language Queries**: Ask questions about candidates in plain English
- **Source Citations**: Every answer includes references to the source CVs
- **Real-time Processing**: Progress tracking for file uploads and indexing
- **Anti-Hallucination**: Guardrails ensure responses are grounded in actual CV content
- **Cost Tracking**: Monitor API usage and estimated costs

## Tech Stack

### Backend
- **Python 3.11+** with FastAPI
- **ChromaDB** for vector storage
- **OpenAI** for embeddings (text-embedding-3-small)
- **Google Gemini** for response generation (gemini-1.5-flash)
- **pdfplumber** for PDF extraction

### Frontend
- **React 18** with Vite
- **TailwindCSS** for styling
- **Lucide React** for icons
- **Axios** for API communication

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- OpenAI API key
- Google API key (for Gemini)

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
cp ../.env.example .env

# Edit .env with your API keys
# OPENAI_API_KEY=your_openai_key
# GOOGLE_API_KEY=your_google_key

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

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/upload` | Upload PDF files |
| GET | `/api/status/{job_id}` | Check processing status |
| GET | `/api/cvs` | List indexed CVs |
| DELETE | `/api/cvs/{cv_id}` | Remove a CV |
| POST | `/api/chat` | Send a query |
| GET | `/api/stats` | Get usage statistics |
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
