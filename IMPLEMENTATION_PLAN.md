# CV Screener RAG Chatbot — Implementation Plan

## Overview

This document outlines the step-by-step implementation plan for building the AI-powered CV screening application. The project is divided into **4 phases** with clear milestones and deliverables.

**Estimated Total Time:** 3-4 weeks (full-time) or 6-8 weeks (part-time)

---

## Phase 1: Core Pipeline (Days 1-5)

**Goal:** Working RAG pipeline that can process PDFs and answer questions via terminal/notebook.

### 1.1 Project Setup (Day 1)
| Task | Description | Priority |
|------|-------------|----------|
| Create directory structure | Set up `backend/`, `frontend/`, `cvs/`, `docs/` folders | 🔴 High |
| Initialize Python environment | Create `venv`, install core dependencies | 🔴 High |
| Configure environment variables | Create `.env.example` and `.env` with API keys | 🔴 High |
| Set up config module | `app/config.py` with Pydantic Settings | 🔴 High |

**Deliverable:** Project skeleton with all directories and basic configuration.

### 1.2 PDF Processing Service (Day 1-2)
| Task | Description | Priority |
|------|-------------|----------|
| Create `pdf_service.py` | PDF text extraction with pdfplumber | 🔴 High |
| Implement text cleaning | Remove artifacts, normalize whitespace, fix encoding | 🔴 High |
| Implement section detection | Identify CV sections (experience, education, skills) | 🟡 Medium |
| Create chunking strategy | Section-based chunking with fallback | 🔴 High |
| Add metadata extraction | Extract candidate name, contact info | 🟡 Medium |
| Write unit tests | `test_pdf_service.py` | 🟡 Medium |

**Deliverable:** Service that extracts and chunks CV text with metadata.

### 1.3 Embedding Service (Day 2-3)
| Task | Description | Priority |
|------|-------------|----------|
| Create `embedding_service.py` | OpenAI embeddings integration | 🔴 High |
| Implement batch processing | Process multiple chunks efficiently | 🔴 High |
| Add retry logic | Handle API failures gracefully | 🟡 Medium |
| Optional: Local embeddings | Sentence-transformers fallback | 🟢 Low |

**Deliverable:** Service that generates embeddings for text chunks.

### 1.4 Vector Store Service (Day 3-4)
| Task | Description | Priority |
|------|-------------|----------|
| Create `vector_store.py` | ChromaDB setup and configuration | 🔴 High |
| Implement CRUD operations | Add, search, delete documents | 🔴 High |
| Configure persistence | Save to `./chroma_db` directory | 🔴 High |
| Implement metadata filtering | Filter by CV, section type | 🟡 Medium |
| Write unit tests | `test_vector_store.py` | 🟡 Medium |

**Deliverable:** Persistent vector store with full CRUD operations.

### 1.5 RAG Service (Day 4-5)
| Task | Description | Priority |
|------|-------------|----------|
| Create `rag_service.py` | Main RAG pipeline orchestration | 🔴 High |
| Configure Gemini LLM | Set up Google Generative AI client | 🔴 High |
| Create prompt templates | System prompt, query template in `prompts/templates.py` | 🔴 High |
| Implement retrieval | Similarity search with score threshold | 🔴 High |
| Implement generation | LLM response with context | 🔴 High |
| Add source tracking | Track which CVs contributed to response | 🔴 High |
| Write integration tests | `test_rag_service.py` | 🟡 Medium |

**Deliverable:** Complete RAG pipeline working in terminal/notebook.

### Phase 1 Milestone Checklist
- [ ] Can load a PDF and extract text
- [ ] Can chunk text into semantic sections
- [ ] Can generate embeddings
- [ ] Can store/retrieve from ChromaDB
- [ ] Can query and get grounded response
- [ ] Response includes source citations

---

## Phase 2: API Layer (Days 6-9)

**Goal:** RESTful API that exposes all functionality via HTTP endpoints.

### 2.1 FastAPI Setup (Day 6)
| Task | Description | Priority |
|------|-------------|----------|
| Create `main.py` | FastAPI app initialization | 🔴 High |
| Configure CORS | Allow frontend origins | 🔴 High |
| Set up error handlers | Global exception handling | 🔴 High |
| Create Pydantic schemas | `models/schemas.py` for all requests/responses | 🔴 High |
| Set up dependency injection | `api/dependencies.py` | 🟡 Medium |

**Deliverable:** Running FastAPI server with basic health check.

### 2.2 Upload Endpoint (Day 6-7)
| Task | Description | Priority |
|------|-------------|----------|
| Implement `POST /api/upload` | Accept multiple PDF files | 🔴 High |
| Add file validation | Check file type, size (max 10MB) | 🔴 High |
| Implement async processing | Background task for indexing | 🔴 High |
| Create job tracking | Store processing status | 🔴 High |
| Implement `GET /api/status/{job_id}` | Check processing progress | 🔴 High |

**Deliverable:** Working file upload with progress tracking.

### 2.3 CV Management Endpoints (Day 7-8)
| Task | Description | Priority |
|------|-------------|----------|
| Implement `GET /api/cvs` | List all indexed CVs | 🔴 High |
| Implement `DELETE /api/cvs/{cv_id}` | Remove CV from index | 🟡 Medium |
| Add pagination | Handle large CV lists | 🟢 Low |

**Deliverable:** Full CV management via API.

### 2.4 Chat Endpoint (Day 8-9)
| Task | Description | Priority |
|------|-------------|----------|
| Implement `POST /api/chat` | Query with RAG response | 🔴 High |
| Add conversation context | Optional conversation_id for follow-ups | 🟡 Medium |
| Return sources | Include matched chunks and scores | 🔴 High |
| Add usage tracking | Token counts and cost estimates | 🟡 Medium |
| Implement `GET /api/stats` | Usage statistics endpoint | 🟢 Low |

**Deliverable:** Complete chat API with sources and usage data.

### 2.5 API Testing (Day 9)
| Task | Description | Priority |
|------|-------------|----------|
| Write API tests | `test_api.py` with pytest | 🔴 High |
| Test error cases | Invalid files, empty queries | 🟡 Medium |
| Load testing | Basic performance validation | 🟢 Low |

**Deliverable:** Tested API with documented endpoints.

### Phase 2 Milestone Checklist
- [ ] All endpoints responding correctly
- [ ] File upload with validation working
- [ ] Processing status updates in real-time
- [ ] Chat returns grounded responses with sources
- [ ] Error handling for all edge cases

---

## Phase 3: Frontend (Days 10-15)

**Goal:** Modern React UI with all required components and states.

### 3.1 Project Setup (Day 10)
| Task | Description | Priority |
|------|-------------|----------|
| Initialize Vite + React | `npm create vite@latest` | 🔴 High |
| Configure Tailwind CSS | Install and configure | 🔴 High |
| Set up project structure | `components/`, `hooks/`, `services/` | 🔴 High |
| Create API client | `services/api.js` with Axios | 🔴 High |
| Configure proxy | Vite dev server proxy to backend | 🔴 High |

**Deliverable:** Running frontend dev environment.

### 3.2 Layout & Core Components (Day 10-11)
| Task | Description | Priority |
|------|-------------|----------|
| Create `Layout.jsx` | Main app layout with header | 🔴 High |
| Create `App.jsx` | Main component with state management | 🔴 High |
| Implement app states | EMPTY, UPLOADING, PROCESSING, READY, CHATTING | 🔴 High |

**Deliverable:** App skeleton with state transitions.

### 3.3 Upload Components (Day 11-12)
| Task | Description | Priority |
|------|-------------|----------|
| Create `UploadZone.jsx` | Drag & drop with react-dropzone | 🔴 High |
| Add file validation | PDF only, max 10MB | 🔴 High |
| Show staged files | List files before upload | 🟡 Medium |
| Create `useUpload.js` hook | Upload state management | 🔴 High |
| Implement upload progress | Individual file progress bars | 🟡 Medium |

**Deliverable:** Working file upload with visual feedback.

### 3.4 Processing Components (Day 12-13)
| Task | Description | Priority |
|------|-------------|----------|
| Create `ProcessingStatus.jsx` | Overall progress bar | 🔴 High |
| Show file status list | ✓ done, ⟳ processing, ○ pending | 🔴 High |
| Poll status endpoint | Update progress in real-time | 🔴 High |
| Handle completion | Transition to READY state | 🔴 High |

**Deliverable:** Real-time processing feedback.

### 3.5 CV List Component (Day 13)
| Task | Description | Priority |
|------|-------------|----------|
| Create `CVList.jsx` | Sidebar with indexed CVs | 🔴 High |
| Implement scrolling | Handle 30+ CVs | 🟡 Medium |
| Add "Show all" modal | View full list | 🟢 Low |
| Add count header | "INDEXED CVs (30)" | 🔴 High |

**Deliverable:** CV sidebar with all indexed files.

### 3.6 Chat Components (Day 13-15)
| Task | Description | Priority |
|------|-------------|----------|
| Create `ChatWindow.jsx` | Main chat container | 🔴 High |
| Create `MessageList.jsx` | Scrollable message history | 🔴 High |
| Create `Message.jsx` | User/assistant message bubbles | 🔴 High |
| Create `SourceBadge.jsx` | Source CV indicators | 🔴 High |
| Create `ChatInput.jsx` | Input with submit button | 🔴 High |
| Create `useChat.js` hook | Chat state management | 🔴 High |
| Add loading state | "Analyzing CVs..." indicator | 🔴 High |
| Add markdown rendering | Format assistant responses | 🟡 Medium |
| Add auto-scroll | Scroll to new messages | 🟡 Medium |

**Deliverable:** Complete chat interface.

### 3.7 Error Handling & Polish (Day 15)
| Task | Description | Priority |
|------|-------------|----------|
| Add error states | Display error messages | 🔴 High |
| Add retry functionality | Retry failed queries | 🟡 Medium |
| Responsive design | Mobile-friendly layout | 🟡 Medium |
| Add "+ Add" button | Upload more CVs | 🟡 Medium |

**Deliverable:** Polished UI with error handling.

### Phase 3 Milestone Checklist
- [ ] Can drag & drop PDFs
- [ ] Shows upload progress
- [ ] Shows processing progress
- [ ] CV list displays all indexed files
- [ ] Chat interface sends/receives messages
- [ ] Sources displayed on responses
- [ ] Error states handled gracefully

---

## Phase 4: Quality & Polish (Days 16-20)

**Goal:** Production-ready system with validation, monitoring, and testing.

### 4.1 Guardrails Integration (Day 16-17)
| Task | Description | Priority |
|------|-------------|----------|
| Create `guardrails_service.py` | Output validation service | 🔴 High |
| Implement `HallucinationGuard` | Check response grounding | 🔴 High |
| Add source citation check | Verify sources are cited | 🔴 High |
| Add out-of-scope detection | Detect declined questions | 🟡 Medium |
| Integrate with RAG pipeline | Validate before returning | 🔴 High |

**Deliverable:** Validated responses with hallucination detection.

### 4.2 Monitoring & Logging (Day 17-18)
| Task | Description | Priority |
|------|-------------|----------|
| Create `monitoring.py` | Usage tracking utilities | 🔴 High |
| Implement `UsageTracker` | Track tokens and costs | 🔴 High |
| Implement `QueryLogger` | Log all queries | 🟡 Medium |
| Implement `RateLimiter` | Prevent API abuse | 🟡 Medium |
| Optional: LangSmith integration | LLM observability | 🟢 Low |

**Deliverable:** Full usage tracking and cost monitoring.

### 4.3 Evaluation Framework (Day 18-19)
| Task | Description | Priority |
|------|-------------|----------|
| Create test cases | Factual, comparison, out-of-scope | 🔴 High |
| Implement `RAGEvaluator` | Run evaluation suite | 🔴 High |
| Generate metrics | Accuracy, latency, by category | 🔴 High |
| Document results | Evaluation report | 🟡 Medium |

**Deliverable:** Evaluation framework with passing test cases.

### 4.4 Generate Test CVs (Day 19)
| Task | Description | Priority |
|------|-------------|----------|
| Create CV generator script | Generate 30 diverse CVs | 🔴 High |
| Ensure variety | Different skills, locations, experience | 🔴 High |
| Export to PDF | Save in `cvs/` directory | 🔴 High |

**Deliverable:** 30 realistic test CVs.

### 4.5 Documentation & Final Testing (Day 20)
| Task | Description | Priority |
|------|-------------|----------|
| Write README.md | Setup instructions, usage guide | 🔴 High |
| Create architecture.md | System design documentation | 🟡 Medium |
| End-to-end testing | Full workflow validation | 🔴 High |
| Performance testing | Response time < 5 seconds | 🔴 High |
| Optional: Docker setup | `docker-compose.yml` | 🟢 Low |

**Deliverable:** Documented, tested, production-ready system.

### Phase 4 Milestone Checklist
- [ ] Guardrails preventing hallucinations
- [ ] Usage and costs being tracked
- [ ] Evaluation tests passing
- [ ] 30 test CVs generated
- [ ] README with full instructions
- [ ] Response time < 5 seconds
- [ ] All success criteria met

---

## Success Criteria Verification

| Criteria | Phase | Verification Method |
|----------|-------|---------------------|
| Can upload 30 PDF CVs | Phase 2 | API test with 30 files |
| Processing shows progress | Phase 3 | Manual UI testing |
| Accurate response to "Who has Python experience?" | Phase 1 | RAG evaluation test |
| Response cites source CVs | Phase 1 | Unit test on response format |
| Out-of-scope questions declined | Phase 4 | Guardrails test cases |
| No hallucinated information | Phase 4 | Hallucination guard tests |
| Response time < 5 seconds | Phase 4 | Performance test |
| Usage/cost tracked | Phase 4 | Stats endpoint validation |

---

## Dependencies & Prerequisites

### Before Starting
1. **API Keys Required:**
   - OpenAI API key (for embeddings)
   - Google API key (for Gemini LLM)

2. **Development Environment:**
   - Python 3.11+
   - Node.js 18+
   - Git

3. **Optional:**
   - Docker Desktop (for containerization)
   - LangSmith account (for monitoring)

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| API rate limits | High | Implement rate limiting, batch processing |
| PDF extraction failures | Medium | Fallback chunking, error handling |
| Hallucinations in responses | High | Guardrails, strict prompts, validation |
| High API costs | Medium | Token tracking, budget alerts |
| Slow response times | Medium | Caching, optimize retrieval k value |

---

## Next Steps

1. **Immediate:** Set up project structure and environment
2. **First:** Implement PDF service and test with sample CVs
3. **Focus:** Get Phase 1 working end-to-end before moving to API

Start with: `mkdir -p backend/app/{api,services,models,prompts,utils} backend/tests frontend/src/{components,hooks,services}`
