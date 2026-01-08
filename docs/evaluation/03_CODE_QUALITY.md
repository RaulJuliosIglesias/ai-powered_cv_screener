# 💎 Code Quality

> **Criterion**: The clarity, structure, and readability of your code.
> 
> **Version**: 6.0 (January 2026) - 22+ Services, Output Orchestrator, 9 Structures, 29 Modules

---

## 📁 Project Structure: Clean Organization (v6.0)

```
ai-powered_cv_screener/
│
├── backend/
│   ├── app/
│   │   ├── api/                    # HTTP layer (routes only)
│   │   │   ├── routes_v2.py        # Core endpoints
│   │   │   ├── routes_sessions.py  # Session management
│   │   │   └── dependencies.py     # FastAPI dependencies
│   │   │
│   │   ├── config.py               # Centralized configuration
│   │   │
│   │   ├── models/                 # Data models (Pydantic)
│   │   │   └── sessions.py
│   │   │
│   │   ├── providers/              # External integrations
│   │   │   ├── base.py             # Abstract interfaces
│   │   │   ├── factory.py          # Dependency injection
│   │   │   ├── local/              # Local implementations (JSON store)
│   │   │   └── cloud/              # Cloud implementations (Supabase)
│   │   │
│   │   ├── services/               # Business logic (22+ services)
│   │   │   ├── rag_service_v5.py           # 128KB - Main orchestrator
│   │   │   ├── query_understanding_service.py  # 40KB - 9 query_types
│   │   │   ├── context_resolver.py         # 18KB - Pronoun resolution ◄── NEW
│   │   │   ├── smart_chunking_service.py   # 41KB - Semantic chunking ◄── NEW
│   │   │   ├── confidence_calculator.py    # 28KB - 5-factor scoring ◄── NEW
│   │   │   ├── cost_tracker.py             # 7KB - Cost estimation ◄── NEW
│   │   │   ├── reasoning_service.py        # 21KB - Chain-of-thought
│   │   │   ├── claim_verifier_service.py   # 13KB - Fact verification
│   │   │   ├── hallucination_service.py    # 12KB - Hallucination detection
│   │   │   ├── reranking_service.py        # 12KB - LLM reranking
│   │   │   ├── multi_query_service.py      # 11KB - Query expansion + HyDE
│   │   │   ├── guardrail_service.py        # 11KB - Bilingual filtering
│   │   │   ├── eval_service.py             # 12KB - Metrics & logging
│   │   │   │
│   │   │   ├── output_processor/           # 44 items ◄── NEW v6.0
│   │   │   │   ├── orchestrator.py         # Routes query_type → structure
│   │   │   │   ├── structures/             # 9 structure classes
│   │   │   │   │   ├── single_candidate_structure.py
│   │   │   │   │   ├── ranking_structure.py
│   │   │   │   │   ├── comparison_structure.py
│   │   │   │   │   ├── search_structure.py
│   │   │   │   │   ├── risk_assessment_structure.py
│   │   │   │   │   ├── job_match_structure.py
│   │   │   │   │   ├── team_build_structure.py
│   │   │   │   │   ├── verification_structure.py
│   │   │   │   │   └── summary_structure.py
│   │   │   │   └── modules/                # 29 reusable modules
│   │   │   │       ├── thinking_module.py
│   │   │   │       ├── conclusion_module.py
│   │   │   │       ├── analysis_module.py
│   │   │   │       ├── ranking_table_module.py
│   │   │   │       ├── top_pick_module.py
│   │   │   │       └── ... (24 more)
│   │   │   │
│   │   │   └── suggestion_engine/          # 17 items ◄── NEW v6.0
│   │   │       └── Dynamic suggestion generation
│   │   │
│   │   ├── prompts/                # LLM prompt templates
│   │   │   └── templates.py
│   │   │
│   │   └── utils/                  # Shared utilities
│   │       ├── error_handling.py
│   │       └── exceptions.py
│   │
│   └── tests/                      # Test suite
│
└── frontend/
    └── src/
        ├── components/             # UI components
        │   └── output/             # StructuredOutputRenderer ◄── NEW
        │       ├── StructuredOutputRenderer.jsx
        │       ├── RankingTable.jsx
        │       ├── TopPickCard.jsx
        │       └── ... (per-structure components)
        ├── contexts/               # React contexts
        │   └── PipelineContext.jsx # Pipeline state ◄── NEW
        ├── hooks/                  # Custom React hooks
        ├── services/               # API client
        └── utils/                  # Helpers
```

### Layer Separation Principle

| Layer | Responsibility | Does NOT Handle |
|-------|---------------|-----------------|
| `api/` | HTTP request/response | Business logic |
| `services/` | Business logic | HTTP, storage details |
| `providers/` | External integrations | Business rules |
| `models/` | Data validation | Logic |
| `output_processor/` | Structured output assembly | RAG retrieval |
| `suggestion_engine/` | Context-aware suggestions | Query processing |

---

## 🔒 Type Safety: Full Type Annotations

### Python Type Hints Throughout

```python
# backend/app/providers/base.py
from typing import List, Dict, Any, Optional, Protocol
from dataclasses import dataclass

@dataclass
class EmbeddingResult:
    """Result of an embedding operation."""
    embeddings: List[List[float]]
    tokens_used: int
    latency_ms: float

@dataclass
class SearchResult:
    """Result of a vector search."""
    id: str
    cv_id: str
    filename: str
    content: str
    similarity: float
    metadata: Dict[str, Any]

class EmbeddingProvider(Protocol):
    """Protocol defining embedding provider interface."""
    
    @property
    def dimensions(self) -> int: ...
    
    async def embed_texts(self, texts: List[str]) -> EmbeddingResult: ...
    
    async def embed_query(self, query: str) -> EmbeddingResult: ...
```

### Benefits of Type Hints

```
┌─────────────────────────────────────────────────────────────────┐
│                   TYPE HINTS BENEFITS                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ✅ IDE AUTOCOMPLETE                                            │
│     result.embeddings  → IDE knows it's List[List[float]]       │
│                                                                  │
│  ✅ EARLY ERROR DETECTION                                       │
│     embed_texts(123)   → Type checker catches before runtime    │
│                                                                  │
│  ✅ SELF-DOCUMENTATION                                          │
│     Function signature tells you what it expects/returns        │
│                                                                  │
│  ✅ REFACTORING SAFETY                                          │
│     Changing types shows all affected locations                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📦 Dataclasses: Structured Data

### Configuration Objects

```python
# backend/app/services/rag_service_v5.py
@dataclass(frozen=True)
class RetryConfig:
    """Configuration for retry behavior with exponential backoff."""
    max_attempts: int = 3
    base_delay_ms: int = 100
    max_delay_ms: int = 5000
    exponential_base: float = 2.0
    jitter: bool = True
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter."""
        import random
        delay = min(
            self.base_delay_ms * (self.exponential_base ** attempt),
            self.max_delay_ms
        )
        if self.jitter:
            delay *= (0.5 + random.random())
        return delay / 1000

@dataclass
class RAGConfigV5:
    """Complete RAG v5 service configuration."""
    mode: Mode = Mode.LOCAL
    
    # Model configuration
    understanding_model: str | None = None
    generation_model: str | None = None
    
    # Feature flags
    multi_query_enabled: bool = True
    hyde_enabled: bool = True
    reranking_enabled: bool = True
    
    # Retrieval settings
    default_k: int = 15
    default_threshold: float = 0.25
```

### Result Objects

```python
@dataclass
class GuardrailResult:
    """Result of guardrail check."""
    is_allowed: bool
    rejection_message: Optional[str] = None
    confidence: float = 1.0
    reason: Optional[str] = None

@dataclass
class HallucinationCheckResult:
    """Result of hallucination verification."""
    is_valid: bool
    confidence_score: float
    verified_cv_ids: List[str] = field(default_factory=list)
    unverified_cv_ids: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
```

### Why Dataclasses?

| vs Alternative | Advantage |
|----------------|-----------|
| vs `dict` | IDE support, type checking, immutability option |
| vs `namedtuple` | Mutable by default, default values, methods |
| vs `class` | Less boilerplate, auto `__init__`, `__repr__`, `__eq__` |

---

## ⚡ Async/Await: Non-Blocking I/O

### Proper Async Pattern

```python
# backend/app/providers/cloud/embeddings.py
async def embed_texts(self, texts: List[str]) -> EmbeddingResult:
    """Generate embeddings asynchronously."""
    start = time.perf_counter()
    
    # Non-blocking HTTP call
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{self.base_url}/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "input": texts}
        )
        response.raise_for_status()
        data = response.json()
    
    latency = (time.perf_counter() - start) * 1000
    
    return EmbeddingResult(
        embeddings=[item["embedding"] for item in data["data"]],
        tokens_used=data.get("usage", {}).get("total_tokens", 0),
        latency_ms=latency
    )
```

### CPU-Bound Work in Thread Pool

```python
# backend/app/providers/local/embeddings.py
async def embed_texts(self, texts: List[str]) -> EmbeddingResult:
    """Generate embeddings - runs CPU work in thread pool."""
    start = time.perf_counter()
    self._ensure_model()
    
    # Run CPU-intensive encoding in thread pool
    # This prevents blocking the event loop
    embeddings = await asyncio.to_thread(self._encode_sync, texts)
    
    latency = (time.perf_counter() - start) * 1000
    return EmbeddingResult(embeddings=embeddings, latency_ms=latency)
```

---

## 🚨 Error Handling: Custom Exceptions

### Exception Hierarchy

```python
# backend/app/utils/exceptions.py

class CVScreenerException(Exception):
    """Base exception for CV Screener application."""
    
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)

class RAGError(CVScreenerException):
    """Error during RAG pipeline execution."""
    
    def __init__(self, message: str, stage: str = None):
        super().__init__(message, {"stage": stage})
        self.stage = stage

class GuardrailError(CVScreenerException):
    """Query rejected by guardrail."""
    
    def __init__(self, rejection_reason: str):
        super().__init__(f"Query rejected: {rejection_reason}")
        self.rejection_reason = rejection_reason

class EmbeddingError(CVScreenerException):
    """Error during embedding generation."""
    pass

class VectorStoreError(CVScreenerException):
    """Error during vector store operations."""
    pass
```

### Centralized Exception Handler

```python
# backend/app/main.py

@app.exception_handler(CVScreenerException)
async def cv_screener_exception_handler(
    request: Request, 
    exc: CVScreenerException
):
    """Handle custom CV Screener exceptions."""
    logger.error(f"CVScreenerException: {exc.message}", extra=exc.details)
    return JSONResponse(
        status_code=500,
        content={
            "detail": exc.message, 
            "error_code": type(exc).__name__
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.exception(f"Unexpected error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred."}
    )
```

---

## 📝 Logging: Structured & Informative

### Consistent Logging Pattern

```python
import logging
logger = logging.getLogger(__name__)

class RAGServiceV5:
    async def query(self, question: str, ...) -> RAGResponseV5:
        logger.info(f"[QUERY] Starting pipeline for: {question[:50]}...")
        
        # Stage logging with consistent prefixes
        logger.info(f"[STAGE:GUARDRAIL] Checking question relevance")
        logger.info(f"[STAGE:EMBEDDING] Vectorizing query")
        logger.info(f"[STAGE:SEARCH] Found {len(results)} chunks")
        logger.debug(f"[STAGE:SEARCH] Top result: {results[0].content[:100]}")
        
        # Error logging with context
        logger.error(f"[STAGE:LLM] Failed after {attempts} attempts: {error}")
        
        logger.info(f"[QUERY] Complete in {total_ms:.0f}ms")
```

### Log Output Example

```
2026-01-05 10:30:45 INFO  [QUERY] Starting pipeline: "Who has Python experience?"
2026-01-05 10:30:45 INFO  [STAGE:GUARDRAIL] Query passed - CV-related keywords found
2026-01-05 10:30:45 INFO  [STAGE:EMBEDDING] Embedded query in 45ms
2026-01-05 10:30:46 INFO  [STAGE:SEARCH] Found 12 chunks above threshold 0.25
2026-01-05 10:30:48 INFO  [STAGE:GENERATION] Response generated in 2100ms
2026-01-05 10:30:48 INFO  [QUERY] Complete in 2340ms
```

---

## ✅ Pydantic Models: Request/Response Validation

### API Models

```python
# backend/app/api/routes_v2.py
from pydantic import BaseModel, Field
from typing import List, Optional

class ChatRequest(BaseModel):
    """Chat request payload."""
    message: str = Field(..., min_length=1, max_length=5000)
    conversation_id: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Who has Python experience?",
                "conversation_id": "conv_abc123"
            }
        }

class SourceInfo(BaseModel):
    """Source citation information."""
    cv_id: str
    filename: str
    relevance: float = Field(..., ge=0, le=1)

class ChatResponse(BaseModel):
    """Chat response payload."""
    response: str
    sources: List[SourceInfo]
    conversation_id: str
    metrics: dict
    mode: str
```

### Automatic Validation

```python
# Invalid request automatically rejected with clear error
POST /api/chat
{"message": ""}  # Empty string

# Response: 422 Unprocessable Entity
{
    "detail": [
        {
            "loc": ["body", "message"],
            "msg": "ensure this value has at least 1 character",
            "type": "value_error"
        }
    ]
}
```

---

## 🎯 Clean Function Design

### Single Responsibility

```python
# Each function does ONE thing well

def extract_text_from_pdf(content: bytes, filename: str) -> str:
    """Extract text from PDF bytes. Nothing else."""
    
def chunk_cv(text: str, cv_id: str, filename: str) -> List[Dict]:
    """Split text into semantic chunks. Nothing else."""
    
async def embed_texts(texts: List[str]) -> EmbeddingResult:
    """Generate embeddings. Nothing else."""
    
async def search(embedding: List[float], k: int) -> List[SearchResult]:
    """Find similar documents. Nothing else."""
```

### Clear Function Signatures

```python
async def search(
    self,
    embedding: List[float],           # What to search for
    k: int = 10,                       # How many results
    threshold: float = 0.3,            # Minimum similarity
    cv_ids: Optional[List[str]] = None, # Filter by CVs
    diversify_by_cv: bool = True       # One result per CV?
) -> List[SearchResult]:
    """
    Search for similar documents.
    
    Args:
        embedding: Query embedding vector
        k: Maximum results to return
        threshold: Minimum similarity score (0-1)
        cv_ids: Optional filter to specific CVs
        diversify_by_cv: If True, return top chunk from each CV
    
    Returns:
        List of SearchResult ordered by similarity descending
    """
```

---

## 🏷️ Enums: Type-Safe Constants

### Mode Selection

```python
# backend/app/config.py
from enum import Enum, auto

class Mode(str, Enum):
    """Backend mode selection."""
    LOCAL = "local"
    CLOUD = "cloud"

# Usage - type-safe, IDE autocomplete
def get_vector_store(mode: Mode):
    if mode == Mode.CLOUD:  # Not string comparison
        return SupabaseVectorStore()
    return SimpleVectorStore()
```

### Pipeline Stages

```python
class PipelineStage(Enum):
    """Stages in the RAG pipeline for tracking and metrics."""
    QUERY_UNDERSTANDING = auto()
    MULTI_QUERY = auto()
    GUARDRAIL = auto()
    EMBEDDING = auto()
    SEARCH = auto()
    RERANKING = auto()
    REASONING = auto()
    GENERATION = auto()
    VERIFICATION = auto()
    CLAIM_VERIFICATION = auto()
    REFINEMENT = auto()
```

---

## 🏭 Factory Pattern: Clean Dependency Injection

```python
# backend/app/providers/factory.py

class ProviderFactory:
    """Factory for creating providers based on mode."""
    
    _instances = {}  # Singleton cache
    
    @classmethod
    def get_embedding_provider(cls, mode: Mode) -> EmbeddingProvider:
        """Get embedding provider for specified mode."""
        key = f"embedding_{mode}"
        if key not in cls._instances:
            if mode == Mode.CLOUD:
                from app.providers.cloud.embeddings import OpenRouterEmbeddingProvider
                cls._instances[key] = OpenRouterEmbeddingProvider()
            else:
                from app.providers.local.embeddings import LocalEmbeddingProvider
                cls._instances[key] = LocalEmbeddingProvider()
        return cls._instances[key]
    
    @classmethod
    def clear_instances(cls):
        """Clear instance cache - useful for testing."""
        cls._instances.clear()
```

### Benefits

| Benefit | How |
|---------|-----|
| **Lazy Loading** | Imports happen only when needed |
| **Singleton** | Same instance reused, no duplicate connections |
| **Testable** | `clear_instances()` for test isolation |
| **Decoupled** | Services don't know about specific implementations |

---

## ⚛️ Frontend: Component Organization

### Component Structure

```jsx
// frontend/src/components/MessageList.jsx
import React from 'react';
import { Message } from './Message';
import { SkeletonLoader } from './SkeletonLoader';

export function MessageList({ messages, isLoading, onSourceClick }) {
  if (messages.length === 0 && !isLoading) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500">
        Start by uploading CVs and asking a question
      </div>
    );
  }

  return (
    <div className="flex flex-col space-y-4 p-4">
      {messages.map((msg, idx) => (
        <Message 
          key={idx} 
          message={msg} 
          onSourceClick={onSourceClick}
        />
      ))}
      {isLoading && <SkeletonLoader />}
    </div>
  );
}
```

### Clear Props Interface

```jsx
// Props destructuring makes interface explicit
function CVList({ cvs, onDelete, onSelect, selectedIds, isLoading }) {
  // Component knows exactly what it receives
  // IDE provides autocomplete
  // Easy to understand at a glance
}
```

---

## 🎯 Output Orchestrator Pattern (NEW in v6.0)

### Structure-Module Architecture

```python
# backend/app/services/output_processor/orchestrator.py
class OutputOrchestrator:
    """Routes query_type to appropriate structure for output assembly."""
    
    STRUCTURE_MAP = {
        "single_candidate": SingleCandidateStructure,
        "ranking": RankingStructure,
        "comparison": ComparisonStructure,
        "search": SearchStructure,
        "red_flags": RiskAssessmentStructure,
        "job_match": JobMatchStructure,
        "team_build": TeamBuildStructure,
        "verification": VerificationStructure,
        "summary": SummaryStructure,
    }
    
    def process(self, raw_output: str, query_type: str, context: dict) -> StructuredOutput:
        structure_class = self.STRUCTURE_MAP.get(query_type, FallbackStructure)
        structure = structure_class()
        return structure.assemble(raw_output, context)
```

### Module Reusability Example

```python
# backend/app/services/output_processor/structures/ranking_structure.py
class RankingStructure(BaseStructure):
    """Assembles ranking output using 6 modules."""
    
    def __init__(self):
        self.modules = [
            ThinkingModule(),      # Shared across ALL 9 structures
            AnalysisModule(),      # Shared across 6 structures
            RankingCriteriaModule(),  # Ranking-specific
            RankingTableModule(),     # Ranking-specific
            TopPickModule(),          # Ranking-specific
            ConclusionModule(),    # Shared across ALL 9 structures
        ]
    
    def assemble(self, raw_output: str, context: dict) -> StructuredOutput:
        result = {}
        for module in self.modules:
            result[module.name] = module.extract(raw_output, context)
        return StructuredOutput(structure_type="ranking", modules=result)
```

### Benefits of This Pattern

| Benefit | How Achieved |
|---------|--------------|
| **DRY** | ThinkingModule used by ALL 9 structures |
| **Single Responsibility** | Each module extracts ONE thing |
| **Easy Testing** | Test modules independently |
| **Extensibility** | Add new structure = combine existing modules |
| **Consistency** | Same module = same output format everywhere |

---

## 📊 Code Quality Summary (v6.0)

| Quality Aspect | Implementation |
|----------------|----------------|
| **Type Safety** | Full Python type hints + TypeScript frontend |
| **Structure** | Clear separation: api / services / providers / models / output_processor |
| **Readability** | Descriptive names, docstrings, consistent formatting |
| **Error Handling** | Custom exception hierarchy, centralized handlers |
| **Logging** | Structured logs with stage prefixes |
| **Validation** | Pydantic models for all API contracts |
| **Constants** | Enums instead of magic strings |
| **Dependencies** | Factory pattern with lazy loading |
| **Async** | Proper async/await, thread pools for CPU work |
| **Documentation** | Docstrings with Args/Returns sections |
| **Modularity** | 29 reusable modules across 9 structures |
| **Scalability** | Output Orchestrator pattern for easy extension |

### Code Metrics (v6.0)

| Metric | Value |
|--------|-------|
| **Total Services** | 22+ files |
| **Largest Service** | `rag_service_v5.py` (128KB) |
| **Output Processor** | 44 items (orchestrator + 9 structures + 29 modules) |
| **Suggestion Engine** | 17 items |
| **Total Backend Code** | ~500KB Python |

---

<div align="center">

**[← Previous: Thought Process](./02_THOUGHT_PROCESS.md)** · **[Back to Index](./README.md)** · **[Next: Creativity & Ingenuity →](./04_CREATIVITY_AND_INGENUITY.md)**

</div>
