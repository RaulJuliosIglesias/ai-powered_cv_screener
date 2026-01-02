# CV Screener - Architecture Documentation

## System Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│   React UI      │────▶│   FastAPI       │────▶│   ChromaDB      │
│   (Frontend)    │     │   (Backend)     │     │   (Vectors)     │
│                 │     │                 │     │                 │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
                    ▼            ▼            ▼
             ┌──────────┐ ┌──────────┐ ┌──────────┐
             │  OpenAI  │ │  Gemini  │ │ pdfplumber│
             │Embeddings│ │   LLM    │ │   PDF    │
             └──────────┘ └──────────┘ └──────────┘
```

## Component Details

### Frontend (React + Vite)

**Purpose:** User interface for uploading CVs and querying the system.

**Key Components:**
- `App.jsx` - Main application state management
- `UploadZone.jsx` - Drag & drop file upload
- `ProcessingStatus.jsx` - Real-time processing feedback
- `CVList.jsx` - Sidebar with indexed CVs
- `ChatWindow.jsx` - Chat interface container
- `Message.jsx` - Individual message bubbles with sources

**State Management:** React hooks (useState, useEffect, useCallback)

### Backend (FastAPI)

**Purpose:** REST API, business logic, and service orchestration.

**Layers:**
1. **API Layer** (`api/routes.py`) - HTTP endpoints
2. **Service Layer** (`services/`) - Business logic
3. **Data Layer** (`models/schemas.py`) - Pydantic models

### Services

#### PDF Service
- Extracts text from PDF using pdfplumber
- Cleans and normalizes text
- Chunks by semantic sections (experience, education, skills)
- Extracts metadata (candidate name, skills)

#### Embedding Service
- Generates embeddings using OpenAI text-embedding-3-small
- Batch processing for efficiency
- Retry logic for API failures

#### Vector Store Service
- ChromaDB for persistent vector storage
- CRUD operations for CV chunks
- Similarity search with score threshold

#### RAG Service
- Orchestrates retrieval and generation
- Manages conversation history
- Formats prompts with context

#### Guardrails Service
- Validates LLM outputs
- Detects potential hallucinations
- Sanitizes user input

## Data Flow

### Upload Flow
```
PDF File → PDFService → ExtractedCV → EmbeddingService → VectorStoreService
              │              │
              ▼              ▼
         Raw Text      CVChunks with metadata
```

### Query Flow
```
User Question → Sanitize → Embed Query → Vector Search → Top-K Chunks
                                                              │
                                                              ▼
Response ← Validate ← Generate ← Build Prompt ← Format Context
```

## Security Considerations

1. **API Keys:** Stored in `.env`, never committed
2. **Input Sanitization:** Prompt injection prevention
3. **Rate Limiting:** Prevents API abuse
4. **CORS:** Restricted to frontend origin

## Monitoring

- **UsageTracker:** Token and cost tracking
- **QueryLogger:** Query logging for analysis
- **RateLimiter:** Request throttling

## Scaling Considerations

For production:
- Replace in-memory job storage with Redis
- Add authentication/authorization
- Use managed vector database (Pinecone, Weaviate)
- Add request queuing for uploads
- Implement caching for common queries
