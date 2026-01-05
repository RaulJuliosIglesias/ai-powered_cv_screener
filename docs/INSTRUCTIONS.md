# CV Screener RAG Chatbot — Technical Specification

## Project Overview

Build an AI-powered CV screening application that allows users to upload PDF resumes and query them using natural language. The system uses Retrieval-Augmented Generation (RAG) to provide accurate, grounded answers based exclusively on the uploaded CV content.

**Core Principle:** Zero hallucinations. Every response must be traceable to source documents.

---

## Technology Stack

### Backend
| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Runtime | Python | 3.11+ | Main backend language |
| Framework | FastAPI | 0.109+ | Async REST API |
| PDF Extraction | pdfplumber | 0.10+ | Text extraction from PDFs |
| Embeddings | OpenAI | text-embedding-3-small | Vector representations |
| Vector Store | ChromaDB | 0.4+ | Local vector database |
| LLM | Google Gemini | gemini-1.5-flash | Response generation |
| RAG Framework | LangChain | 0.1+ | RAG pipeline orchestration |
| Validation | Pydantic | 2.0+ | Data validation |
| Guardrails | Guardrails-AI | 0.4+ | Output validation |
| Monitoring | LangSmith | latest | LLM observability |

### Frontend
| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Framework | React | 18+ | UI framework |
| Build Tool | Vite | 5+ | Fast development |
| Styling | TailwindCSS | 3+ | Utility-first CSS |
| HTTP Client | Axios | 1.6+ | API communication |
| File Upload | react-dropzone | 14+ | Drag & drop uploads |
| State | React useState/useReducer | - | Local state management |

### Development
| Tool | Purpose |
|------|---------|
| Docker | Containerization (optional) |
| pytest | Backend testing |
| Vitest | Frontend testing |

---

## Project Structure

```
cv-screener/
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI application entry point
│   │   ├── config.py                  # Environment variables & settings
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── routes.py              # All API endpoints
│   │   │   └── dependencies.py        # Dependency injection
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── pdf_service.py         # PDF text extraction
│   │   │   ├── embedding_service.py   # Embedding generation
│   │   │   ├── vector_store.py        # ChromaDB operations
│   │   │   ├── rag_service.py         # RAG pipeline & query
│   │   │   └── guardrails_service.py  # Output validation
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── schemas.py             # Pydantic request/response models
│   │   │
│   │   ├── prompts/
│   │   │   ├── __init__.py
│   │   │   └── templates.py           # All LLM prompt templates
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── monitoring.py          # Cost tracking & logging
│   │       └── exceptions.py          # Custom exceptions
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_pdf_service.py
│   │   ├── test_rag_service.py
│   │   └── test_api.py
│   │
│   ├── uploads/                       # Temporary PDF storage
│   ├── chroma_db/                     # ChromaDB persistence
│   ├── requirements.txt
│   ├── .env.example
│   └── .env
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Layout.jsx             # Main layout wrapper
│   │   │   ├── UploadZone.jsx         # Drag & drop PDF upload
│   │   │   ├── ProcessingStatus.jsx   # Upload/indexing progress
│   │   │   ├── CVList.jsx             # List of indexed CVs
│   │   │   ├── ChatWindow.jsx         # Main chat container
│   │   │   ├── MessageList.jsx        # Chat message history
│   │   │   ├── Message.jsx            # Individual message bubble
│   │   │   ├── SourceBadge.jsx        # Source document indicator
│   │   │   └── ChatInput.jsx          # Message input field
│   │   │
│   │   ├── hooks/
│   │   │   ├── useChat.js             # Chat state management
│   │   │   └── useUpload.js           # Upload state management
│   │   │
│   │   ├── services/
│   │   │   └── api.js                 # API client functions
│   │   │
│   │   ├── App.jsx                    # Main application component
│   │   ├── main.jsx                   # React entry point
│   │   └── index.css                  # Tailwind imports
│   │
│   ├── public/
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── index.html
│
├── cvs/                               # Generated CV PDFs (30 files)
│   └── *.pdf
│
├── docs/
│   └── architecture.md
│
├── docker-compose.yml                 # Optional containerization
└── README.md
```

---

## User Experience Specification

### Application States

```
STATE 1: EMPTY (No CVs uploaded)
┌─────────────────────────────────────────────────────────────────┐
│  CV Screener                                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                                                           │  │
│  │      ┌─────────┐                                          │  │
│  │      │  📄 +   │                                          │  │
│  │      └─────────┘                                          │  │
│  │                                                           │  │
│  │      Drop PDF files here or click to browse               │  │
│  │                                                           │  │
│  │      Supports: .pdf (max 10MB per file)                   │  │
│  │                                                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  No CVs indexed yet. Upload CVs to start asking questions.      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘


STATE 2: UPLOADING (Files being uploaded)
┌─────────────────────────────────────────────────────────────────┐
│  CV Screener                                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Uploading files...                                             │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  maria_garcia.pdf                    ████████████░░ 80%   │  │
│  │  juan_lopez.pdf                      ██████░░░░░░░░ 45%   │  │
│  │  ana_martinez.pdf                    ░░░░░░░░░░░░░░ 0%    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  [Cancel]                                                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘


STATE 3: PROCESSING (Extracting & indexing)
┌─────────────────────────────────────────────────────────────────┐
│  CV Screener                                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Processing CVs...                                              │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  ████████████████░░░░░░░░░░░░░░  15/30 CVs indexed        │  │
│  │                                                           │  │
│  │  ✓ maria_garcia.pdf         ✓ juan_lopez.pdf              │  │
│  │  ✓ ana_martinez.pdf         ✓ carlos_ruiz.pdf             │  │
│  │  ✓ laura_sanchez.pdf        ⟳ pedro_gonzalez.pdf          │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Extracting text and creating embeddings...                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘


STATE 4: READY (Chat interface active)
┌─────────────────────────────────────────────────────────────────┐
│  CV Screener                                           [+ Add]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌───────────────────────────────────────┐ │
│  │ INDEXED CVs (30)│  │                                       │ │
│  ├─────────────────┤  │  Welcome! I can help you search       │ │
│  │ 📄 maria_garcia │  │  through 30 CVs. Try asking:          │ │
│  │ 📄 juan_lopez   │  │                                       │ │
│  │ 📄 ana_martinez │  │  • "Who has Python experience?"       │ │
│  │ 📄 carlos_ruiz  │  │  • "List candidates from Madrid"      │ │
│  │ 📄 laura_sanch..│  │  • "Who worked at Google?"            │ │
│  │ 📄 pedro_gonz.. │  │                                       │ │
│  │ 📄 sofia_martin │  │                                       │ │
│  │ 📄 diego_fernan │  │                                       │ │
│  │ ...             │  │                                       │ │
│  │                 │  │                                       │ │
│  │ [Show all]      │  │                                       │ │
│  └─────────────────┘  ├───────────────────────────────────────┤ │
│                       │ [Ask a question about the CVs...]  ➤  │ │
│                       └───────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘


STATE 5: CHATTING (Active conversation)
┌─────────────────────────────────────────────────────────────────┐
│  CV Screener                                           [+ Add]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌───────────────────────────────────────┐ │
│  │ INDEXED CVs (30)│  │                                       │ │
│  ├─────────────────┤  │  YOU                                  │ │
│  │ 📄 maria_garcia │  │  Who has experience with Python       │ │
│  │ 📄 juan_lopez   │  │  and machine learning?                │ │
│  │ 📄 ana_martinez │  │                                       │ │
│  │ 📄 carlos_ruiz  │  │  ─────────────────────────────────    │ │
│  │ 📄 laura_sanch..│  │                                       │ │
│  │ 📄 pedro_gonz.. │  │  ASSISTANT                            │ │
│  │ 📄 sofia_martin │  │  Based on the CVs, I found 4          │ │
│  │ 📄 diego_fernan │  │  candidates with Python and ML:       │ │
│  │ ...             │  │                                       │ │
│  │                 │  │  1. María García - 5 years Python,    │ │
│  │ [Show all]      │  │     TensorFlow, PyTorch experience    │ │
│  │                 │  │     at DataCorp (Senior ML Engineer)  │ │
│  │                 │  │                                       │ │
│  │                 │  │  2. Juan López - 3 years Python,      │ │
│  │                 │  │     scikit-learn at TechStartup       │ │
│  │                 │  │     (Data Scientist)                  │ │
│  │                 │  │                                       │ │
│  │                 │  │  3. Ana Martínez - 4 years Python,    │ │
│  │                 │  │     Keras at AILabs (ML Developer)    │ │
│  │                 │  │                                       │ │
│  │                 │  │  4. Carlos Ruiz - 2 years Python,     │ │
│  │                 │  │     basic ML at University project    │ │
│  │                 │  │                                       │ │
│  │                 │  │  📎 Sources:                          │ │
│  │                 │  │  maria_garcia.pdf • juan_lopez.pdf    │ │
│  │                 │  │  ana_martinez.pdf • carlos_ruiz.pdf   │ │
│  │                 │  │                                       │ │
│  └─────────────────┘  ├───────────────────────────────────────┤ │
│                       │ [Ask a follow-up question...]      ➤  │ │
│                       └───────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘


STATE 6: LOADING (Waiting for response)
┌─────────────────────────────────────────────────────────────────┐
│  ...                                                            │
│  ├───────────────────────────────────────────────────────────┤  │
│  │                                                           │  │
│  │  YOU                                                      │  │
│  │  Compare the top 3 candidates for a senior role           │  │
│  │                                                           │  │
│  │  ─────────────────────────────────────────────────────    │  │
│  │                                                           │  │
│  │  ASSISTANT                                                │  │
│  │  ●●● Analyzing CVs...                                     │  │
│  │                                                           │  │
│  ├───────────────────────────────────────────────────────────┤  │
│  │ [Ask a question about the CVs...]                      ➤  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘


STATE 7: ERROR (Something went wrong)
┌─────────────────────────────────────────────────────────────────┐
│  ...                                                            │
│  │                                                           │  │
│  │  ASSISTANT                                                │  │
│  │  ⚠️ I couldn't process your request. This might be       │  │
│  │  because:                                                 │  │
│  │  • The question is outside the scope of the CVs           │  │
│  │  • There was a temporary connection issue                 │  │
│  │                                                           │  │
│  │  Please try rephrasing your question or ask something     │  │
│  │  specific about the candidates.                           │  │
│  │                                                           │  │
│  │  [Retry]                                                  │  │
│  │                                                           │  │
└─────────────────────────────────────────────────────────────────┘
```

### UI Components Specification

#### UploadZone Component
- Drag & drop area with dashed border
- Click to open file browser
- Accept only .pdf files
- Max file size: 10MB per file
- Show file count and names when files are staged
- "Upload & Process" button to start indexing
- Visual feedback on drag over (border color change)

#### ProcessingStatus Component
- Progress bar showing X/total CVs processed
- List of files with status icons: ✓ done, ⟳ processing, ○ pending
- Estimated time remaining (optional)
- Cancel button

#### CVList Component (Sidebar)
- Scrollable list of indexed CV names
- Truncate long names with ellipsis
- Show total count in header
- "Show all" expands to modal with full list
- Click on CV name shows preview (optional enhancement)

#### ChatWindow Component
- Scrollable message history
- Auto-scroll to bottom on new messages
- Clear visual distinction between user and assistant messages
- Timestamp on messages (optional)

#### Message Component
- User messages: right-aligned, colored background
- Assistant messages: left-aligned, white/light background
- Source badges at bottom of assistant messages
- Markdown rendering support for formatted responses
- Copy button on assistant messages (optional)

#### SourceBadge Component
- Small pill-shaped badges
- Show PDF filename
- Clickable to highlight in sidebar (optional)

#### ChatInput Component
- Text input field with placeholder
- Submit button (arrow icon)
- Disable while waiting for response
- Enter key to submit, Shift+Enter for newline

---

## Backend API Specification

### Endpoints

#### POST /api/upload
Upload PDF files for processing.

**Request:**
```
Content-Type: multipart/form-data

files: File[] (multiple PDF files)
```

**Response:**
```json
{
  "job_id": "uuid-string",
  "files_received": 30,
  "status": "processing"
}
```

**Errors:**
- 400: No files provided
- 400: Invalid file type (not PDF)
- 400: File too large (>10MB)
- 500: Processing error

---

#### GET /api/status/{job_id}
Check processing status.

**Response:**
```json
{
  "job_id": "uuid-string",
  "status": "processing | completed | failed",
  "total_files": 30,
  "processed_files": 15,
  "failed_files": [],
  "progress_percent": 50,
  "error_message": null
}
```

---

#### GET /api/cvs
List all indexed CVs.

**Response:**
```json
{
  "total": 30,
  "cvs": [
    {
      "id": "cv_001",
      "filename": "maria_garcia.pdf",
      "indexed_at": "2025-01-02T10:30:00Z",
      "chunk_count": 3,
      "metadata": {
        "name": "María García",
        "extracted_skills": ["Python", "TensorFlow"]
      }
    }
  ]
}
```

---

#### DELETE /api/cvs/{cv_id}
Remove a CV from the index.

**Response:**
```json
{
  "success": true,
  "message": "CV removed from index"
}
```

---

#### POST /api/chat
Send a question and get RAG-powered response.

**Request:**
```json
{
  "message": "Who has experience with Python?",
  "conversation_id": "optional-uuid-for-context"
}
```

**Response:**
```json
{
  "response": "Based on the CVs, I found 5 candidates with Python experience:\n\n1. María García - 5 years...",
  "sources": [
    {
      "cv_id": "cv_001",
      "filename": "maria_garcia.pdf",
      "relevance_score": 0.92,
      "matched_chunk": "Skills: Python (5 years), TensorFlow..."
    },
    {
      "cv_id": "cv_002",
      "filename": "juan_lopez.pdf",
      "relevance_score": 0.87,
      "matched_chunk": "Experience: Python developer at..."
    }
  ],
  "conversation_id": "uuid-string",
  "usage": {
    "prompt_tokens": 1250,
    "completion_tokens": 350,
    "total_tokens": 1600,
    "estimated_cost_usd": 0.0008
  }
}
```

**Errors:**
- 400: Empty message
- 404: No CVs indexed
- 500: LLM/RAG error

---

#### GET /api/stats
Get usage statistics and monitoring data.

**Response:**
```json
{
  "total_queries": 150,
  "total_tokens_used": 45000,
  "estimated_total_cost_usd": 0.15,
  "average_response_time_ms": 1200,
  "cvs_indexed": 30,
  "vector_store_size_mb": 12.5
}
```

---

## RAG Pipeline Specification

### 1. PDF Processing Pipeline

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   PDF File   │────▶│  pdfplumber  │────▶│  Raw Text    │
└──────────────┘     │  extract()   │     └──────┬───────┘
                     └──────────────┘            │
                                                 ▼
                                    ┌──────────────────────┐
                                    │   Text Cleaning      │
                                    │   - Remove artifacts │
                                    │   - Normalize spaces │
                                    │   - Fix encoding     │
                                    └──────────┬───────────┘
                                               │
                                               ▼
                                    ┌──────────────────────┐
                                    │   Metadata Extract   │
                                    │   - Candidate name   │
                                    │   - Contact info     │
                                    │   - Section headers  │
                                    └──────────┬───────────┘
                                               │
                                               ▼
                                    ┌──────────────────────┐
                                    │   Chunking Strategy  │
                                    └──────────────────────┘
```

### 2. Chunking Strategy

**Approach: Semantic Section-Based Chunking**

For CVs, do NOT use fixed-size chunking. Instead, chunk by logical sections:

```python
CHUNK_STRATEGY = {
    "method": "section_based",
    "sections": [
        "contact_info",      # Name, email, phone, location
        "summary",           # Professional summary/objective
        "experience",        # Each job as separate chunk
        "education",         # Each degree as separate chunk  
        "skills",            # All skills together
        "certifications",    # Certifications/courses
        "languages",         # Language proficiencies
    ],
    "fallback": {
        "method": "recursive_character",
        "chunk_size": 500,
        "chunk_overlap": 50
    }
}
```

**Chunk Metadata:**
```python
{
    "cv_id": "cv_001",
    "filename": "maria_garcia.pdf",
    "candidate_name": "María García",
    "section_type": "experience",
    "chunk_index": 2,
    "total_chunks": 5
}
```

### 3. Embedding Generation

```python
EMBEDDING_CONFIG = {
    "model": "text-embedding-3-small",  # OpenAI
    "dimensions": 1536,
    "batch_size": 100,  # Process 100 chunks at once
    "retry_attempts": 3,
    "retry_delay_seconds": 1
}
```

**Alternative (Free/Local):**
```python
EMBEDDING_CONFIG_LOCAL = {
    "model": "sentence-transformers/all-MiniLM-L6-v2",
    "dimensions": 384,
    "device": "cpu"  # or "cuda" if available
}
```

### 4. Vector Store Configuration

```python
CHROMA_CONFIG = {
    "collection_name": "cv_collection",
    "persist_directory": "./chroma_db",
    "distance_metric": "cosine",  # or "l2", "ip"
    "hnsw_config": {
        "space": "cosine",
        "ef_construction": 100,
        "M": 16
    }
}
```

### 5. Retrieval Configuration

```python
RETRIEVAL_CONFIG = {
    "search_type": "similarity",  # or "mmr" for diversity
    "k": 8,                       # Number of chunks to retrieve
    "score_threshold": 0.5,       # Minimum similarity score
    "filter": None,               # Optional metadata filters
    
    # For MMR (Maximal Marginal Relevance)
    "mmr_config": {
        "fetch_k": 20,           # Fetch more, then diversify
        "lambda_mult": 0.7       # 0=max diversity, 1=max relevance
    }
}
```

### 6. LLM Configuration

```python
LLM_CONFIG = {
    "provider": "google",
    "model": "gemini-1.5-flash",
    "temperature": 0.1,          # Low for factual responses
    "max_output_tokens": 2048,
    "top_p": 0.95,
    "top_k": 40,
    
    # Safety settings
    "safety_settings": {
        "harassment": "block_none",
        "hate_speech": "block_none",
        "sexually_explicit": "block_medium_and_above",
        "dangerous_content": "block_medium_and_above"
    }
}
```

---

## Prompt Engineering

### System Prompt

```python
SYSTEM_PROMPT = """You are a CV screening assistant. Your ONLY job is to answer questions about candidate CVs that have been provided to you.

CRITICAL RULES:
1. ONLY use information from the provided CV excerpts. Never invent or assume information.
2. If the information is not in the provided CVs, say "I don't have information about that in the uploaded CVs."
3. Always cite which CV(s) your information comes from.
4. Be specific: include names, years of experience, company names, and specific skills.
5. If asked to compare candidates, create structured comparisons with clear criteria.
6. Never provide information about candidates that isn't in their CV.

RESPONSE FORMAT:
- Start with a direct answer to the question
- List relevant candidates with specific details
- End by citing the source CVs used

Remember: You can ONLY know what's in the CVs. No external knowledge about companies, technologies, or general career advice."""
```

### Query Prompt Template

```python
QUERY_TEMPLATE = """Based on the following CV excerpts, answer the user's question.

=== CV EXCERPTS ===
{context}
=== END CV EXCERPTS ===

User Question: {question}

Instructions:
1. Only use information from the CV excerpts above
2. If the answer isn't in the excerpts, say so clearly
3. Cite the candidate names and CV filenames
4. Be specific with details (years, companies, skills)

Answer:"""
```

### Grounding Prompt (Anti-Hallucination)

```python
GROUNDING_PROMPT = """Before answering, verify:
1. Is this information explicitly stated in the provided CVs?
2. Am I making any assumptions not supported by the text?
3. Have I correctly attributed information to the right candidate?

If you cannot verify any claim from the CV text, do not include it.

Verified Answer:"""
```

---

## Guardrails Implementation

### Output Validation Schema

```python
from guardrails import Guard
from guardrails.validators import (
    ValidLength,
    OneLine,
    LowerCase
)

# Define expected output structure
OUTPUT_SCHEMA = {
    "response": {
        "type": "string",
        "validators": [
            ValidLength(min=10, max=5000)
        ]
    },
    "sources_cited": {
        "type": "array",
        "items": {"type": "string"},
        "validators": [
            lambda x: len(x) >= 1  # At least one source
        ]
    },
    "confidence": {
        "type": "string",
        "enum": ["high", "medium", "low"]
    }
}
```

### Hallucination Detection

```python
class HallucinationGuard:
    """
    Validates that LLM responses only contain information
    from the retrieved context.
    """
    
    def __init__(self, retrieved_chunks: list[str]):
        self.context = " ".join(retrieved_chunks).lower()
        self.known_entities = self._extract_entities(retrieved_chunks)
    
    def validate(self, response: str) -> tuple[bool, list[str]]:
        """
        Returns (is_valid, list_of_issues)
        """
        issues = []
        
        # Check for names not in context
        response_names = self._extract_names(response)
        for name in response_names:
            if name.lower() not in self.context:
                issues.append(f"Unknown candidate mentioned: {name}")
        
        # Check for companies not in context
        response_companies = self._extract_companies(response)
        for company in response_companies:
            if company.lower() not in self.context:
                issues.append(f"Unknown company mentioned: {company}")
        
        # Check for specific numbers/years not in context
        response_numbers = self._extract_numbers(response)
        for number in response_numbers:
            if str(number) not in self.context:
                issues.append(f"Unverified number: {number}")
        
        return len(issues) == 0, issues
    
    def _extract_entities(self, chunks):
        # Implementation using NER or regex
        pass
    
    def _extract_names(self, text):
        # Implementation
        pass
    
    def _extract_companies(self, text):
        # Implementation
        pass
    
    def _extract_numbers(self, text):
        # Implementation
        pass
```

### Response Validation Pipeline

```python
async def validate_response(
    response: str,
    retrieved_chunks: list[str],
    question: str
) -> dict:
    """
    Multi-stage validation of LLM response.
    """
    validation_result = {
        "is_valid": True,
        "original_response": response,
        "corrected_response": None,
        "issues": [],
        "confidence_score": 1.0
    }
    
    # Stage 1: Hallucination check
    hallucination_guard = HallucinationGuard(retrieved_chunks)
    is_grounded, hallucination_issues = hallucination_guard.validate(response)
    
    if not is_grounded:
        validation_result["issues"].extend(hallucination_issues)
        validation_result["confidence_score"] -= 0.3
    
    # Stage 2: Source citation check
    if not any(chunk_source in response for chunk_source in get_source_names(retrieved_chunks)):
        validation_result["issues"].append("No sources cited")
        validation_result["confidence_score"] -= 0.2
    
    # Stage 3: "I don't know" detection for out-of-scope questions
    out_of_scope_phrases = [
        "I don't have information",
        "not mentioned in the CVs",
        "cannot find"
    ]
    if any(phrase in response.lower() for phrase in out_of_scope_phrases):
        # This is actually good - model is being honest
        validation_result["confidence_score"] = 0.9
    
    # Stage 4: Length and coherence check
    if len(response) < 20:
        validation_result["issues"].append("Response too short")
        validation_result["confidence_score"] -= 0.2
    
    validation_result["is_valid"] = validation_result["confidence_score"] >= 0.5
    
    return validation_result
```

---

## Monitoring & Cost Control

### Token Usage Tracking

```python
from dataclasses import dataclass
from datetime import datetime
import json

@dataclass
class UsageRecord:
    timestamp: datetime
    operation: str  # "embedding" | "completion" | "query"
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    
class UsageTracker:
    """Track all API usage and costs."""
    
    PRICING = {
        "text-embedding-3-small": {
            "input": 0.00002 / 1000,  # $0.00002 per 1K tokens
        },
        "gemini-1.5-flash": {
            "input": 0.000075 / 1000,   # Free tier, then $0.075/1M
            "output": 0.0003 / 1000,    # $0.30/1M output
        }
    }
    
    def __init__(self, log_file: str = "usage_log.jsonl"):
        self.log_file = log_file
        self.session_usage = []
    
    def record(
        self,
        operation: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int = 0
    ):
        pricing = self.PRICING.get(model, {"input": 0, "output": 0})
        
        cost = (
            prompt_tokens * pricing.get("input", 0) +
            completion_tokens * pricing.get("output", 0)
        )
        
        record = UsageRecord(
            timestamp=datetime.now(),
            operation=operation,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            estimated_cost_usd=cost
        )
        
        self.session_usage.append(record)
        self._persist(record)
        
        return record
    
    def get_session_stats(self) -> dict:
        return {
            "total_requests": len(self.session_usage),
            "total_tokens": sum(r.total_tokens for r in self.session_usage),
            "total_cost_usd": sum(r.estimated_cost_usd for r in self.session_usage),
            "by_operation": self._group_by_operation()
        }
    
    def _persist(self, record: UsageRecord):
        with open(self.log_file, "a") as f:
            f.write(json.dumps({
                "timestamp": record.timestamp.isoformat(),
                "operation": record.operation,
                "model": record.model,
                "tokens": record.total_tokens,
                "cost_usd": record.estimated_cost_usd
            }) + "\n")
    
    def _group_by_operation(self) -> dict:
        groups = {}
        for record in self.session_usage:
            if record.operation not in groups:
                groups[record.operation] = {"count": 0, "tokens": 0, "cost": 0}
            groups[record.operation]["count"] += 1
            groups[record.operation]["tokens"] += record.total_tokens
            groups[record.operation]["cost"] += record.estimated_cost_usd
        return groups
```

### Query Logging

```python
import logging
from datetime import datetime
import json

class QueryLogger:
    """Log all queries for analysis and debugging."""
    
    def __init__(self, log_file: str = "queries.jsonl"):
        self.log_file = log_file
        self.logger = logging.getLogger("cv_screener.queries")
    
    def log_query(
        self,
        query: str,
        retrieved_chunks: list[dict],
        response: str,
        sources: list[str],
        latency_ms: float,
        validation_result: dict,
        usage: dict
    ):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "num_chunks_retrieved": len(retrieved_chunks),
            "chunk_scores": [c.get("score", 0) for c in retrieved_chunks],
            "response_length": len(response),
            "sources_cited": sources,
            "latency_ms": latency_ms,
            "validation": {
                "is_valid": validation_result["is_valid"],
                "confidence": validation_result["confidence_score"],
                "issues": validation_result["issues"]
            },
            "usage": usage
        }
        
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
        
        self.logger.info(
            f"Query processed: {query[:50]}... | "
            f"Latency: {latency_ms:.0f}ms | "
            f"Sources: {len(sources)} | "
            f"Valid: {validation_result['is_valid']}"
        )
```

### Rate Limiting

```python
from datetime import datetime, timedelta
from collections import deque

class RateLimiter:
    """Prevent excessive API calls."""
    
    def __init__(
        self,
        max_requests_per_minute: int = 60,
        max_tokens_per_minute: int = 100000
    ):
        self.max_rpm = max_requests_per_minute
        self.max_tpm = max_tokens_per_minute
        self.request_times = deque()
        self.token_usage = deque()  # (timestamp, tokens)
    
    def check_limit(self, estimated_tokens: int = 1000) -> tuple[bool, float]:
        """
        Returns (allowed, wait_seconds)
        """
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        
        # Clean old entries
        while self.request_times and self.request_times[0] < minute_ago:
            self.request_times.popleft()
        while self.token_usage and self.token_usage[0][0] < minute_ago:
            self.token_usage.popleft()
        
        # Check request limit
        if len(self.request_times) >= self.max_rpm:
            wait = (self.request_times[0] - minute_ago).total_seconds()
            return False, wait
        
        # Check token limit
        current_tokens = sum(t[1] for t in self.token_usage)
        if current_tokens + estimated_tokens > self.max_tpm:
            wait = (self.token_usage[0][0] - minute_ago).total_seconds()
            return False, wait
        
        return True, 0
    
    def record_request(self, tokens_used: int):
        now = datetime.now()
        self.request_times.append(now)
        self.token_usage.append((now, tokens_used))
```

---

## Evaluation Framework

### Test Cases

```python
EVAL_TEST_CASES = [
    # Factual retrieval
    {
        "id": "fact_01",
        "question": "Who has more than 5 years of Python experience?",
        "expected_behavior": "List candidates with 5+ years Python",
        "requires_sources": True,
        "category": "factual_retrieval"
    },
    {
        "id": "fact_02", 
        "question": "Which candidate worked at Google?",
        "expected_behavior": "Name specific candidate(s) or say none found",
        "requires_sources": True,
        "category": "factual_retrieval"
    },
    
    # Comparison
    {
        "id": "compare_01",
        "question": "Compare the top 3 candidates for a senior backend role",
        "expected_behavior": "Structured comparison with criteria",
        "requires_sources": True,
        "category": "comparison"
    },
    
    # Aggregation
    {
        "id": "agg_01",
        "question": "How many candidates have a Master's degree?",
        "expected_behavior": "Specific count with names",
        "requires_sources": True,
        "category": "aggregation"
    },
    
    # Out of scope (should decline)
    {
        "id": "oos_01",
        "question": "What is the capital of France?",
        "expected_behavior": "Decline - not in CVs",
        "requires_sources": False,
        "category": "out_of_scope"
    },
    {
        "id": "oos_02",
        "question": "What salary should I offer María García?",
        "expected_behavior": "Decline - salary not in CVs",
        "requires_sources": False,
        "category": "out_of_scope"
    },
    
    # Edge cases
    {
        "id": "edge_01",
        "question": "Tell me about John Smith",
        "expected_behavior": "Find if exists, or say not found",
        "requires_sources": True,
        "category": "edge_case"
    },
    {
        "id": "edge_02",
        "question": "",
        "expected_behavior": "Handle gracefully",
        "requires_sources": False,
        "category": "edge_case"
    }
]
```

### Evaluation Metrics

```python
@dataclass
class EvalResult:
    test_id: str
    passed: bool
    response: str
    sources_cited: list[str]
    latency_ms: float
    issues: list[str]
    category: str

class RAGEvaluator:
    """Evaluate RAG system quality."""
    
    def __init__(self, rag_service):
        self.rag = rag_service
        self.results = []
    
    async def run_eval(self, test_cases: list[dict]) -> dict:
        for test in test_cases:
            result = await self._evaluate_single(test)
            self.results.append(result)
        
        return self._compute_metrics()
    
    async def _evaluate_single(self, test: dict) -> EvalResult:
        start = datetime.now()
        
        try:
            response = await self.rag.query(test["question"])
            latency = (datetime.now() - start).total_seconds() * 1000
            
            issues = []
            passed = True
            
            # Check source citation
            if test["requires_sources"] and not response.get("sources"):
                issues.append("Missing source citations")
                passed = False
            
            # Check for out-of-scope handling
            if test["category"] == "out_of_scope":
                if not self._detects_out_of_scope(response["response"]):
                    issues.append("Failed to recognize out-of-scope query")
                    passed = False
            
            return EvalResult(
                test_id=test["id"],
                passed=passed,
                response=response["response"],
                sources_cited=response.get("sources", []),
                latency_ms=latency,
                issues=issues,
                category=test["category"]
            )
            
        except Exception as e:
            return EvalResult(
                test_id=test["id"],
                passed=False,
                response="",
                sources_cited=[],
                latency_ms=0,
                issues=[str(e)],
                category=test["category"]
            )
    
    def _detects_out_of_scope(self, response: str) -> bool:
        indicators = [
            "not in the cvs",
            "don't have information",
            "cannot find",
            "no information about",
            "outside the scope"
        ]
        return any(ind in response.lower() for ind in indicators)
    
    def _compute_metrics(self) -> dict:
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        
        by_category = {}
        for result in self.results:
            cat = result.category
            if cat not in by_category:
                by_category[cat] = {"total": 0, "passed": 0}
            by_category[cat]["total"] += 1
            if result.passed:
                by_category[cat]["passed"] += 1
        
        return {
            "overall_accuracy": passed / total if total > 0 else 0,
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "by_category": {
                cat: {
                    "accuracy": stats["passed"] / stats["total"],
                    **stats
                }
                for cat, stats in by_category.items()
            },
            "average_latency_ms": sum(r.latency_ms for r in self.results) / total,
            "failed_tests": [
                {"id": r.test_id, "issues": r.issues}
                for r in self.results if not r.passed
            ]
        }
```

---

## Environment Variables

```bash
# .env file

# API Keys
OPENAI_API_KEY=sk-...                    # For embeddings
GOOGLE_API_KEY=AIza...                   # For Gemini LLM

# Alternative: Use local embeddings (no API key needed)
USE_LOCAL_EMBEDDINGS=false

# Vector Store
CHROMA_PERSIST_DIR=./chroma_db
CHROMA_COLLECTION_NAME=cv_collection

# Server
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:5173

# Limits
MAX_FILE_SIZE_MB=10
MAX_FILES_PER_UPLOAD=50
RATE_LIMIT_RPM=60
RATE_LIMIT_TPM=100000

# Monitoring
ENABLE_LANGSMITH=false
LANGSMITH_API_KEY=ls__...
LANGSMITH_PROJECT=cv-screener

# Logging
LOG_LEVEL=INFO
LOG_FILE=app.log
```

---

## Dependencies

### requirements.txt

```
# Core
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6
pydantic==2.5.3
pydantic-settings==2.1.0

# PDF Processing
pdfplumber==0.10.3

# AI/ML
langchain==0.1.4
langchain-openai==0.0.5
langchain-google-genai==0.0.6
langchain-chroma==0.0.1
chromadb==0.4.22
openai==1.10.0
google-generativeai==0.3.2

# Optional: Local embeddings
sentence-transformers==2.2.2

# Guardrails
guardrails-ai==0.4.0

# Monitoring
langsmith==0.0.83

# Utilities
python-dotenv==1.0.0
httpx==0.26.0
tenacity==8.2.3

# Testing
pytest==7.4.4
pytest-asyncio==0.23.3
httpx==0.26.0
```

### package.json (Frontend)

```json
{
  "name": "cv-screener-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview",
    "test": "vitest"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "axios": "^1.6.5",
    "react-dropzone": "^14.2.3",
    "react-markdown": "^9.0.1",
    "lucide-react": "^0.312.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.1",
    "autoprefixer": "^10.4.17",
    "postcss": "^8.4.33",
    "tailwindcss": "^3.4.1",
    "vite": "^5.0.12",
    "vitest": "^1.2.1"
  }
}
```

---

## Quick Start Commands

```bash
# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
uvicorn app.main:app --reload

# Frontend setup (separate terminal)
cd frontend
npm install
npm run dev

# Run tests
cd backend
pytest

# Run evaluation
python -m app.utils.evaluator
```

---

## Implementation Priority

Build in this order:

1. **Phase 1: Core Pipeline** (Working RAG)
   - PDF extraction service
   - Embedding generation
   - ChromaDB setup
   - Basic query function
   - Test in terminal/notebook

2. **Phase 2: API Layer**
   - FastAPI endpoints
   - File upload handling
   - Chat endpoint
   - Error handling

3. **Phase 3: Frontend**
   - Upload zone
   - Processing status
   - Chat interface
   - Source display

4. **Phase 4: Quality & Polish**
   - Guardrails integration
   - Usage tracking
   - Evaluation tests
   - Error states in UI

---

## Maintenance Scripts (v5.1)

### Re-index CVs with Smart Chunking

When upgrading from v5.0 to v5.1, or if CV metadata seems outdated, use the re-indexing script:

```bash
cd backend
python ../scripts/reindex_cvs.py
```

**What it does**:
1. Finds all PDF files in `/storage/`
2. Clears existing vector store embeddings
3. Re-processes each PDF with `SmartChunkingService`
4. Creates enriched chunks with metadata:
   - `current_role`, `current_company`
   - `total_experience_years` (calculated)
   - `start_year`, `end_year`, `is_current` per position

**When to use**:
- After upgrading to v5.1
- If "current role" or "years of experience" queries return wrong data
- After modifying `SmartChunkingService` patterns

### Utility Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `scripts/reindex_cvs.py` | Re-index all CVs with smart chunking | `python ../scripts/reindex_cvs.py` |
| `scripts/demo_queries.py` | Test sample queries | `python scripts/demo_queries.py` |
| `scripts/setup_supabase_complete.sql` | Supabase schema setup | Run in Supabase SQL editor |

---

## Success Criteria

The system is complete when:

- [ ] Can upload 30 PDF CVs
- [ ] Processing shows progress
- [ ] Can ask "Who has Python experience?" and get accurate response
- [ ] Response cites source CVs
- [ ] Out-of-scope questions are declined gracefully
- [ ] No hallucinated information in responses
- [ ] Response time < 5 seconds
- [ ] Usage/cost is tracked
- [ ] **v5.1**: Single-candidate queries return current role and total experience correctly