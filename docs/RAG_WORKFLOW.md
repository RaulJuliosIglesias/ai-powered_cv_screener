# RAG Workflow Documentation

> **CV Screener AI - Complete RAG Pipeline Reference**
> 
> Version: 5.1.0 | Last Updated: January 2026

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Smart CV Chunking](#smart-cv-chunking) ← **NEW in v5.1**
3. [Architecture Diagram](#architecture-diagram)
4. [Pipeline Stages](#pipeline-stages)
5. [Targeted Retrieval](#targeted-retrieval) ← **NEW in v5.1**
6. [V5 Advanced Features](#v5-advanced-features)
7. [Structured Output Processing](#structured-output-processing)
8. [Core Scripts Reference](#core-scripts-reference)
9. [Data Flow](#data-flow)
10. [Configuration](#configuration)
11. [Providers](#providers)
12. [Error Handling](#error-handling)
13. [Caching & Performance](#caching--performance)
14. [Evaluation & Logging](#evaluation--logging)

---

## System Overview

The CV Screener uses a **multi-step RAG (Retrieval-Augmented Generation) pipeline** designed for intelligent CV analysis and candidate screening. The system supports two operation modes:

| Mode | Description |
|------|-------------|
| **LOCAL** | In-memory vector store, local embeddings |
| **CLOUD** | Supabase pgvector, OpenAI embeddings, OpenRouter LLMs |

### Key Features (V5)

- ✅ **Multi-Query Retrieval**: Generate query variations for better recall
- ✅ **HyDE (Hypothetical Document Embeddings)**: Improved semantic matching
- ✅ **Reciprocal Rank Fusion (RRF)**: Combine results from multiple queries
- ✅ **Chain-of-Thought Reasoning**: Structured Self-Ask pattern for complex queries
- ✅ **Claim-Level Verification**: Verify individual claims against source context
- ✅ **Iterative Refinement**: Regenerate response if verification fails
- ✅ **Guardrails**: Pre-LLM filtering to reject off-topic queries
- ✅ **Adaptive Retrieval**: Strategy varies based on query type and session size
- ✅ **LLM-based Reranking**: Re-orders chunks by semantic relevance
- ✅ **Circuit Breaker**: Prevents cascading failures
- ✅ **Response Caching**: LRU cache with TTL for embeddings and responses
- ✅ **Graceful Degradation**: Auto-disable failing features to maintain service

### Key Features (V5.1 - NEW)

- ✅ **Smart CV Chunking**: Intelligent extraction of dates, roles, and experience years
- ✅ **Enriched Metadata**: Pre-calculated `current_role`, `total_experience_years`, `is_current`
- ✅ **Targeted Retrieval**: Fetch ALL chunks for a specific candidate (bypasses semantic search)
- ✅ **Summary Chunks**: Pre-built profile summaries for instant candidate lookups

### Key Features (V5.1.1 - Enhanced Modules)

- ✅ **Gap Analysis Module**: Skills gap detection between job requirements and candidate profiles
- ✅ **Red Flags Module**: Risk detection (job-hopping, employment gaps, short tenures)
- ✅ **Timeline Module**: Career trajectory visualization with progression scoring
- ✅ **Deep Enriched Metadata**: `seniority_level`, `job_hopping_score`, `avg_tenure_years`, `has_faang_experience`
- ✅ **Summary Chunk with Career Path**: Pre-built career trajectory summary per CV

---

## Smart CV Chunking

> **NEW in v5.1** - Intelligent document processing that extracts structured data from CVs

### The Problem (v5.0 and before)

The original `ChunkingService` divided CVs by generic sections (experience, education, skills) but:

- ❌ **No date extraction** - Couldn't identify "current role" vs past roles
- ❌ **No experience calculation** - Couldn't sum years across positions
- ❌ **Basic metadata** - Only stored `section_type` and `candidate_name`
- ❌ **Semantic search limitations** - Questions like "what's their current job?" failed

### The Solution: SmartChunkingService

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CV PDF UPLOAD                                      │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 0: SMART CHUNKING (SmartChunkingService)                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ 1. EXTRACT STRUCTURED DATA:                                              ││
│  │    • Parse dates: "2020-Present", "2018-2023", "Jan 2019 - Dec 2021"    ││
│  │    • Identify current position (Present/Actual/Current indicators)       ││
│  │    • Extract job titles and companies                                    ││
│  │    • Calculate duration per position                                     ││
│  │                                                                          ││
│  │ 2. CALCULATE TOTALS:                                                     ││
│  │    • Total years of experience (earliest start → latest end)             ││
│  │    • Number of positions held                                            ││
│  │    • Current role and company                                            ││
│  │                                                                          ││
│  │ 3. CREATE ENRICHED CHUNKS:                                               ││
│  │    • Summary Chunk (pre-calculated profile)                              ││
│  │    • Position Chunks (one per job, with dates)                           ││
│  │    • Skills Chunk                                                        ││
│  │    • Full CV Chunk (for comprehensive queries)                           ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│  Script: smart_chunking_service.py                                           │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
                         [Embedding & Indexing]
```

### Chunk Types Created

| Chunk Type | Purpose | Key Metadata |
|------------|---------|--------------|
| **Summary** | Quick profile lookup | `current_role`, `current_company`, `total_experience_years`, `position_count` |
| **Position** | Individual job details | `job_title`, `company`, `start_year`, `end_year`, `is_current`, `duration_years` |
| **Skills** | Technical competencies | `skill_count` |
| **Full CV** | Comprehensive queries | All metadata + first 4000 chars |

### Enriched Metadata Schema

```python
# Summary Chunk Metadata
{
    "section_type": "summary",
    "candidate_name": "Matteo Rossi",
    "current_role": "Lead Merchandising Strategist",      # ← NEW
    "current_company": "Global Fashion Retail Corp",      # ← NEW
    "total_experience_years": 6.0,                        # ← NEW (calculated)
    "is_summary": True,                                   # ← NEW
    "position_count": 3                                   # ← NEW
}

# Position Chunk Metadata
{
    "section_type": "experience",
    "candidate_name": "Matteo Rossi",
    "job_title": "Lead Merchandising Strategist",         # ← NEW
    "company": "Global Fashion Retail Corp",              # ← NEW
    "start_year": 2023,                                   # ← NEW
    "end_year": None,                                     # ← NEW (None = Present)
    "is_current": True,                                   # ← NEW
    "duration_years": 2.0,                                # ← NEW
    "position_order": 1                                   # ← NEW (1 = most recent)
}
```

### Date Extraction Patterns

The service recognizes multiple date formats:

```python
YEAR_PATTERNS = [
    r'(\d{4})\s*[-–—]\s*(Present|Presente|Actual|Current|Now)',  # 2020 - Present
    r'(\d{4})\s*[-–—]\s*(\d{4})',                                 # 2018 - 2023
    r'(?:Jan|Feb|...)\s*(\d{4})\s*[-–—]\s*(?:Jan|...)\s*(\d{4})', # Jan 2020 - Dec 2023
    r'(?:\d{1,2}/)?(\d{4})\s*[-–—]\s*(?:\d{1,2}/)?(\d{4})',       # 01/2020 - 12/2023
]

CURRENT_INDICATORS = ['present', 'presente', 'actual', 'current', 'now', 'hoy', 'actualidad']
```

### Experience Calculation

```python
def _calculate_total_experience(positions: List[JobPosition]) -> float:
    """
    Calculate total years from career span.
    
    Method: max(end_years) - min(start_years)
    
    Example:
        Position 1: 2023-Present (2 years)
        Position 2: 2021-2023    (2 years)
        Position 3: 2019-2021    (2 years)
        
        Total = 2025 - 2019 = 6 years
    """
```

### Summary Chunk Content Example

```
===== CANDIDATE PROFILE: Matteo Rossi =====

CURRENT POSITION: Lead Merchandising Strategist
CURRENT COMPANY: Global Fashion Retail Corp
TOTAL YEARS OF EXPERIENCE: 6 years
NUMBER OF POSITIONS HELD: 3

CAREER HISTORY (chronological, most recent first):
  1. Lead Merchandising Strategist at Global Fashion Retail Corp (2023-Present, 2y) [CURRENT]
  2. Inventory Planner at Fashion Dynamics Inc (2021-2023, 2y)
  3. Junior Buyer at Style Co (2019-2021, 2y)

KEY SKILLS: Python, Excel, SAP, Demand Forecasting, Inventory Management
```

---

## Targeted Retrieval

> **NEW in v5.1** - Retrieve ALL chunks for a specific candidate

### The Problem

When a user asks "tell me everything about Matteo Rossi":

- ❌ **Semantic search** only returns chunks semantically similar to the query
- ❌ May miss the most recent job if query doesn't mention specific terms
- ❌ Cannot reliably answer "what's their current role?" or "how many years of experience?"

### The Solution

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  QUERY: "damelo todo sobre Matteo Rossi"                                     │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 1: CANDIDATE NAME EXTRACTION                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ extract_candidate_name_from_query("damelo todo sobre Matteo Rossi")     ││
│  │                                                                          ││
│  │ Patterns recognized:                                                     ││
│  │ • "damelo todo sobre X" / "tell me about X"                             ││
│  │ • "información sobre X" / "profile of X"                                ││
│  │ • Direct name queries                                                    ││
│  │                                                                          ││
│  │ Result: ctx.target_candidate_name = "Matteo Rossi"                      ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 5: TARGETED RETRIEVAL (instead of semantic search)                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ IF ctx.target_candidate_name is set:                                     ││
│  │                                                                          ││
│  │   vector_store.get_all_chunks_by_candidate("Matteo Rossi")              ││
│  │                                                                          ││
│  │   Returns ALL chunks where metadata.candidate_name matches:              ││
│  │   • Summary chunk (with pre-calculated totals)                           ││
│  │   • All position chunks (with dates and durations)                       ││
│  │   • Skills chunk                                                         ││
│  │   • Full CV chunk                                                        ││
│  │                                                                          ││
│  │   Sorted by priority: summary → experience → skills → full_cv            ││
│  │                                                                          ││
│  │ ELSE:                                                                    ││
│  │   Standard RRF fusion retrieval (semantic search)                        ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 6: SKIP RERANKING (for targeted retrieval)                             │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ IF retrieval_strategy == "targeted_candidate":                           ││
│  │   Skip reranking - we want ALL chunks, not filtered by relevance         ││
│  │   Reason: "Skills" chunk may not be semantically similar to query        ││
│  │           but we still want to include it for complete profile           ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

### Vector Store Method

```python
# SimpleVectorStore.get_all_chunks_by_candidate()

def get_all_chunks_by_candidate(
    self, 
    candidate_name: str, 
    cv_ids: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Get ALL chunks for a specific candidate.
    
    - Case-insensitive partial match
    - Returns chunks sorted by section priority
    - Used for single-candidate queries
    """
```

### Benefits

| Query Type | Before (v5.0) | After (v5.1) |
|------------|---------------|--------------|
| "What's Matteo's current role?" | ❌ May miss if "current" not in chunk | ✅ Summary chunk has `current_role` |
| "How many years of experience?" | ❌ Cannot calculate | ✅ `total_experience_years` pre-calculated |
| "Tell me everything about X" | ⚠️ Only semantically similar chunks | ✅ ALL chunks for that candidate |

---

## Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              USER QUERY                                    │
└────────────────────────────────────┬───────────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  STEP 1: QUERY UNDERSTANDING                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ • Model: google/gemini-2.0-flash-001 (fast, cheap)                   │  │
│  │ • Extracts: query_type, requirements, is_cv_related                  │  │
│  │ • Reformulates query for better retrieval                            │  │
│  │ • Output: QueryUnderstandingV5 dataclass                             │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│  Script: query_understanding_service.py                                    │
└────────────────────────────────────┬───────────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  STEP 2: MULTI-QUERY GENERATION (V5 NEW)                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ • Generates 3-5 query variations for broader recall                  │  │
│  │ • Extracts entities (skills, names, companies)                       │  │
│  │ • HyDE: Generates hypothetical ideal CV excerpt                      │  │
│  │ • Output: MultiQueryResult (variations, entities, hyde_document)     │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│  Script: multi_query_service.py                                            │
└────────────────────────────────────┬───────────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  STEP 3: GUARDRAIL CHECK                                                   │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ • Keyword matching: CV_KEYWORDS set (100+ terms)                     │  │
│  │ • Pattern matching: OFF_TOPIC_PATTERNS (recipes, weather, etc.)      │  │
│  │ • Fast, no LLM call required                                         │  │
│  │ • Output: GuardrailResult (is_allowed, rejection_message)            │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│  Script: guardrail_service.py                                              │
│                                                                            │
│  ❌ REJECTED → Return early with rejection message                         │
│  ✅ PASSED → Continue to next step                                         │
└────────────────────────────────────┬───────────────────────────────────────┘
                                     │
                                     ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  STEP 4: MULTI-EMBEDDING (V5 NEW)                                          │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ • Model: text-embedding-3-small (1536 dimensions)                    │  │
│  │ • Embeds: original query + variations + HyDE document                │  │
│  │ • Cache: LRU with TTL (5 min default)                                │  │
│  │ • Parallel embedding generation                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│  Script: embedding_service.py                                              │
│  Provider: OpenAI / LocalEmbeddingProvider                                 │
└────────────────────────────────────┬───────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 5: FUSION RETRIEVAL (V5 NEW)                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ MULTI-QUERY SEARCH:                                                     ││
│  │ • Search with each embedding (original + variations + HyDE)             ││
│  │ • k=10 per query variation                                              ││
│  │                                                                         ││
│  │ RECIPROCAL RANK FUSION (RRF):                                           ││
│  │ • Combines ranked lists from all queries                                ││
│  │ • Formula: RRF(d) = Σ 1/(k + rank(d)) where k=60                        ││
│  │ • Documents found by multiple queries ranked higher                     ││
│  │                                                                         ││
│  │ • Threshold: 0.25 default (lower for broader recall)                    ││
│  │ • Timeout: 20 seconds                                                   ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│  Script: vector_store.py + multi_query_service.py (RRF)                      │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 6: RERANKING                                                           │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ • Model: google/gemini-2.0-flash-001                                    ││
│  │ • Scores each chunk 1-10 for relevance to query                         ││
│  │ • Combined score: LLM_score * 0.7 + similarity * 0.3                    ││
│  │ • Returns ALL chunks reordered (not truncated)                          ││
│  │ • Can be disabled via config                                            ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│  Script: reranking_service.py                                                │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 7: CHAIN-OF-THOUGHT REASONING (V5 NEW)                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ SELF-ASK PATTERN:                                                       ││
│  │ • Deep query understanding with explicit reasoning                      ││
│  │ • Comprehensive candidate inventory                                     ││
│  │ • Systematic evidence gathering per candidate                           ││
│  │ • Structured comparison and scoring                                     ││
│  │                                                                         ││
│  │ OUTPUT FORMAT:                                                          ││
│  │ • :::thinking block with detailed analysis                              ││
│  │ • :::answer block with final response                                   ││
│  │                                                                         ││
│  │ • Reflection: Can request more context if needed                        ││
│  │ • Timeout: 120 seconds                                                  ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│  Script: reasoning_service.py                                                │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 8: RESPONSE GENERATION                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ PROMPT CONSTRUCTION (templates.py):                                     ││
│  │ ┌─────────────────────────────────────────────────────────────────────┐ ││
│  │ │ SYSTEM_PROMPT (Expert HR analyst persona)                           │ ││
│  │ │    +                                                                │ ││
│  │ │ QUERY_TEMPLATE / COMPARISON_TEMPLATE / RANKING_TEMPLATE             │ ││
│  │ │    +                                                                │ ││
│  │ │ Formatted context (chunks with CV IDs and metadata)                 │ ││
│  │ │    +                                                                │ ││
│  │ │ Reasoning trace (from Step 7)                                       │ ││
│  │ └─────────────────────────────────────────────────────────────────────┘ ││
│  │                                                                         ││
│  │ • Models: gemini-2.0-flash, gemini-1.5-pro, gpt-4o, claude-3           ││
│  │ • Temperature: 0.1 (for accuracy)                                       ││
│  │ • Max tokens: 4096-8192                                                 ││
│  │ • Timeout: 120 seconds                                                  ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│  Script: llm.py (OpenRouterLLMProvider)                                      │
│  Templates: templates.py (PromptBuilder class)                               │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 9: CLAIM-LEVEL VERIFICATION (V5 NEW)                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ CLAIM EXTRACTION:                                                       ││
│  │ • Extract individual factual claims from response                       ││
│  │ • Each claim is a verifiable statement                                  ││
│  │                                                                         ││
│  │ CLAIM VERIFICATION:                                                     ││
│  │ • Check each claim against source context chunks                        ││
│  │ • Classify as: VERIFIED, UNVERIFIED, or CONTRADICTED                    ││
│  │                                                                         ││
│  │ OUTPUT:                                                                 ││
│  │ • overall_score: ratio of verified claims                               ││
│  │ • needs_regeneration: true if too many unverified claims                ││
│  │ • Min verified ratio: 0.7 (configurable)                                ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│  Script: claim_verifier_service.py                                           │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 10: ITERATIVE REFINEMENT (V5 NEW)                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ IF needs_regeneration == true:                                          ││
│  │   • Regenerate response with feedback about unverified claims           ││
│  │   • Include list of contradicted claims to avoid                        ││
│  │   • Max 1 refinement iteration to prevent loops                         ││
│  │                                                                         ││
│  │ ELSE:                                                                   ││
│  │   • Pass through to final response                                      ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│  Script: rag_service_v5.py (_step_refinement)                                │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 11: EVALUATION LOGGING                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ • Logs to: eval_logs/queries_YYYYMMDD.jsonl                             ││
│  │ • Fields: query, response, sources, metrics, claim_verification         ││
│  │ • Tracks: verified/unverified/contradicted claims                       ││
│  │ • Daily stats aggregation                                               ││
│  │ • Low confidence tracking (threshold: 0.5)                              ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│  Script: eval_service.py                                                     │
└─────────────────────────────────┬───────────────────────────────────────────┘
                                  │
                                  ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                              RAG RESPONSE V5                               │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ {                                                                    │  │
│  │   "answer": "Generated response text...",                            │  │
│  │   "sources": [{"cv_id": "cv_xxx", "filename": "John_Doe.pdf"}],      │  │
│  │   "metrics": {"total_ms": 1234, "stages": {...}},                    │  │
│  │   "confidence_score": 0.85,                                          │  │
│  │   "guardrail_passed": true,                                          │  │
│  │   "verification": {                                                  │  │
│  │     "verified_claims": [...],                                        │  │
│  │     "unverified_claims": [...],                                      │  │
│  │     "claim_verification_score": 0.92                                 │  │
│  │   },                                                                 │  │
│  │   "reasoning_trace": "...",                                          │  │
│  │   "mode": "cloud",                                                   │  │
│  │   "request_id": "abc123"                                             │  │
│  │ }                                                                    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Pipeline Stages

### Stage Enum Definition (V5)

```python
class PipelineStage(Enum):
    QUERY_UNDERSTANDING = auto()  # Step 1
    MULTI_QUERY = auto()          # Step 2 (V5 NEW)
    GUARDRAIL = auto()            # Step 3
    EMBEDDING = auto()            # Step 4
    SEARCH = auto()               # Step 5 (Fusion Retrieval)
    RERANKING = auto()            # Step 6
    REASONING = auto()            # Step 7 (V5 NEW)
    GENERATION = auto()           # Step 8
    VERIFICATION = auto()         # Step 9 (Legacy)
    CLAIM_VERIFICATION = auto()   # Step 9 (V5 NEW)
    REFINEMENT = auto()           # Step 10 (V5 NEW)
```

### Stage Metrics

Each stage tracks:
- `duration_ms`: Execution time
- `success`: Boolean status
- `error`: Error message if failed
- `metadata`: Stage-specific data (tokens, costs, etc.)

---

## V5 Advanced Features

### Multi-Query Retrieval

Generates multiple query variations to improve recall:

```python
@dataclass
class MultiQueryResult:
    original_query: str
    variations: List[str]      # 3-5 query variations
    hyde_document: str | None  # Hypothetical ideal CV excerpt
    entities: Dict[str, List[str]]  # Extracted entities
```

**Benefits:**
- Catches documents that match different phrasings
- Entities enable hybrid keyword search
- HyDE improves semantic matching for abstract queries

### HyDE (Hypothetical Document Embeddings)

Instead of just embedding the query, generates a hypothetical ideal answer:

```
Query: "Who has Python experience?"

HyDE Document: "Senior Software Engineer with 5+ years of Python 
development experience. Expert in Django, FastAPI, and data science 
libraries including pandas, numpy, and scikit-learn..."
```

The HyDE embedding often matches relevant documents better than the raw query.

### Reciprocal Rank Fusion (RRF)

Combines results from multiple query embeddings:

```python
def reciprocal_rank_fusion(ranked_lists: List[List[str]], k: int = 60):
    """
    RRF Score = Σ 1/(k + rank(d))
    
    Documents found by multiple queries get higher scores.
    k=60 is the standard smoothing constant.
    """
```

### Chain-of-Thought Reasoning

Structured Self-Ask pattern for complex queries:

```
:::thinking

### STEP 1: DEEP QUERY UNDERSTANDING
- What is the user's main objective?
- What are explicit vs implicit requirements?

### STEP 2: COMPREHENSIVE CANDIDATE INVENTORY
- List all candidates with initial relevance assessment

### STEP 3: DETAILED EVIDENCE GATHERING
- For each relevant candidate, extract specific evidence

### STEP 4: COMPARATIVE ANALYSIS
- Score candidates against criteria
- Identify gaps and strengths

:::

:::answer
[Final structured response based on reasoning]
:::
```

### Claim-Level Verification

Verifies individual claims rather than the whole response:

```python
@dataclass
class ClaimVerificationResult:
    total_claims: int
    verified_claims: List[VerifiedClaim]    # Found in context
    unverified_claims: List[Claim]          # Not found
    contradicted_claims: List[Claim]        # Conflicts with context
    overall_score: float                    # verified / total
    needs_regeneration: bool                # If score < 0.7
```

### Iterative Refinement

If too many claims are unverified:
1. Identifies problematic claims
2. Regenerates response with explicit instructions to avoid those claims
3. Maximum 1 refinement iteration to prevent loops

### Graceful Degradation

Features auto-disable on repeated failures:

```python
from app.utils.error_handling import degradation

# If multi-query times out, disable for this request
if timeout_error:
    degradation.disable_feature('multi_query', 'Timeout')
    # Pipeline continues without multi-query
```

---

## Structured Output Processing

> **📚 Full documentation**: [STRUCTURED_OUTPUT.md](./STRUCTURED_OUTPUT.md)

The Structured Output system transforms raw LLM responses into consistent, type-safe data structures.

### Pipeline Step: Output Processing

After LLM generation, the response passes through the **OutputOrchestrator**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  STEP 11: STRUCTURED OUTPUT PROCESSING (V5 NEW)                              │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ ORCHESTRATOR FLOW:                                                       ││
│  │ 1. Pre-clean LLM output (remove code blocks, artifacts)                  ││
│  │ 2. Extract components via 5 specialized modules:                         ││
│  │    • ThinkingModule     → :::thinking::: blocks                          ││
│  │    • DirectAnswerModule → First 1-3 sentences                            ││
│  │    • AnalysisModule     → Detailed analysis section                      ││
│  │    • TableModule        → Candidate table → TableData                    ││
│  │    • ConclusionModule   → :::conclusion::: blocks                        ││
│  │ 3. Generate fallback analysis if none extracted                          ││
│  │ 4. Format candidate references: [📄](cv:cv_xxx) **Name**                 ││
│  │ 5. Assemble components sequentially                                      ││
│  │ 6. Post-clean (deduplicate, fix formatting)                              ││
│  │                                                                          ││
│  │ OUTPUT:                                                                  ││
│  │ • StructuredOutput (data model with all components)                      ││
│  │ • formatted_answer (markdown string for rendering)                       ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│  Script: output_processor/orchestrator.py                                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Models

```python
@dataclass
class StructuredOutput:
    direct_answer: str              # Concise 1-3 sentence answer
    raw_content: str                # Original LLM output
    thinking: Optional[str]         # Reasoning (collapsible)
    analysis: Optional[str]         # Detailed analysis
    table_data: Optional[TableData] # Candidate comparison table
    conclusion: Optional[str]       # Final recommendations
    cv_references: List[CVReference]
    parsing_warnings: List[str]
    fallback_used: bool

@dataclass
class TableData:
    title: str                      # "Candidate Comparison Table"
    headers: List[str]              # ["Candidate", "Skills", "Match Score"]
    rows: List[TableRow]            # One row per candidate

@dataclass
class TableRow:
    candidate_name: str             # "Sofia Grijalva"
    cv_id: str                      # "cv_sofia_grijalva_abc123"
    columns: Dict[str, str]         # {"Skills": "Python", "Experience": "5 years"}
    match_score: int                # 0-100 (for color coding)
```

### Table Modes: Comparison vs Individual

| Mode | Use Case | Table Structure |
|------|----------|-----------------|
| **Comparison** | "Who has Python?" | Multiple candidates, one row per candidate |
| **Individual** | "Tell me about Sofia" | Single candidate, one row per attribute |

**Comparison Mode Example**:
```
| Candidate | Skills | Match Score |
|-----------|--------|-------------|
| Sofia G.  | Python | 95% 🟢      |
| Carlos L. | Flask  | 75% 🟡      |
```

**Individual Mode Example**:
```
| Attribute  | Value                      |
|------------|----------------------------|
| Experience | 5 years backend dev        |
| Skills     | Python, Django, AWS        |
| Education  | B.S. Computer Science, MIT |
```

### Match Score Colors

| Score | Color | Meaning |
|-------|-------|---------|
| ≥ 90% | 🟢 Green | Strong match |
| 70-89% | 🟡 Yellow | Partial match |
| < 70% | ⚪ Gray | Weak match |

### Candidate Reference Format

All candidate mentions are formatted uniformly:

```
[📄](cv:cv_xxx) **Candidate Name**
 │      │            │
 │      │            └── Bold name (NOT clickable)
 │      └── cv: prefix (required for frontend)
 └── 📄 icon (clickable → opens PDF)
```

---

## Core Scripts Reference

### 📁 Orchestration Layer

| Script | Class | Description |
|--------|-------|-------------|
| `rag_service_v5.py` | `RAGServiceV5` | **Main orchestrator (V5)**. Multi-query, reasoning, claim verification, iterative refinement. |
| `factory.py` | `ProviderFactory` | Factory pattern for provider instantiation based on mode. |

### 📁 Pipeline Steps (in order)

| # | Script | Class | Input → Output |
|---|--------|-------|----------------|
| 1 | `query_understanding_service.py` | `QueryUnderstandingService` | `str` → `QueryUnderstandingV5` |
| 2 | `multi_query_service.py` | `MultiQueryService` | `str` → `MultiQueryResult` **(V5 NEW)** |
| 3 | `guardrail_service.py` | `GuardrailService` | `str` → `GuardrailResult` |
| 4 | `embedding_service.py` | `EmbeddingService` | `List[str]` → `Dict[str, List[float]]` |
| 5 | `vector_store.py` | `SupabaseVectorStore` / `SimpleVectorStore` | `List[float]` → `List[SearchResult]` |
| 6 | `reranking_service.py` | `RerankingService` | `List[SearchResult]` → `RerankResult` |
| 7 | `reasoning_service.py` | `ReasoningService` | `query + context` → `ReasoningResult` **(V5 NEW)** |
| 8 | `llm.py` | `OpenRouterLLMProvider` | `prompt: str` → `str` |
| 9 | `claim_verifier_service.py` | `ClaimVerifierService` | `response + context` → `ClaimVerificationResult` **(V5 NEW)** |
| 10 | `hallucination_service.py` | `HallucinationService` | `response + context` → `HallucinationCheckResult` |
| 11 | `eval_service.py` | `EvalService` | Logs query/response to JSONL |

### 📁 Support Layer

| Script | Class | Description |
|--------|-------|-------------|
| `templates.py` | `PromptBuilder` | All prompt templates and builder methods |
| `chunking_service.py` | `ChunkingService` | CV text → semantic sections |
| `pdf_service.py` | `PDFService` | PDF → text extraction |
| `confidence_calculator.py` | `ConfidenceCalculator` | Calculate confidence scores |
| `cost_tracker.py` | `CostTracker` | Track OpenRouter API costs |
| `base.py` | `EmbeddingProvider`, `VectorStoreProvider`, `LLMProvider` | Abstract interfaces |

### 📁 Output Processing (V5)

> **📚 Complete documentation**: See [STRUCTURED_OUTPUT.md](./STRUCTURED_OUTPUT.md) for detailed structured output documentation including orchestration flow, data models, and module descriptions.

| Script | Class | Description |
|--------|-------|-------------|
| `output_processor/orchestrator.py` | `OutputOrchestrator` | **Main entry point** - Coordinates extraction and assembly |
| `output_processor/processor.py` | `OutputProcessor` | Invokes 5 modules to extract components |
| `output_processor/modules/thinking_module.py` | `ThinkingModule` | Extracts :::thinking::: blocks |
| `output_processor/modules/direct_answer_module.py` | `DirectAnswerModule` | Extracts concise 1-3 sentence answer |
| `output_processor/modules/analysis_module.py` | `AnalysisModule` | Processes analysis + generates fallbacks |
| `output_processor/modules/table_module.py` | `TableModule` | Parses tables → TableData (comparison/individual) |
| `output_processor/modules/conclusion_module.py` | `ConclusionModule` | Extracts :::conclusion::: blocks |
| `models/structured_output.py` | `StructuredOutput`, `TableData`, `TableRow` | Data models for structured output |

---

## Data Flow

### CV Ingestion Flow

```
PDF Upload
    │
    ▼
┌─────────────────┐
│   PDF Service   │ → Extract text from PDF
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Chunking Service│ → Split into sections (experience, education, skills...)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│Embedding Service│ → Generate vector for each chunk
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Vector Store   │ → Store in Supabase with metadata
└─────────────────┘
```

### Query Flow

```
User Question: "Who has Python experience?"
         │
         ▼
┌────────────────────────────────────────────────────────────────┐
│ QueryUnderstanding:                                            │
│   query_type: "search"                                         │
│   requirements: ["Search for Python skill"]                    │
│   reformulated_prompt: "Find candidates with Python..."        │
└────────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────┐
│ Guardrail: PASSED (contains CV keywords)                       │
└────────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────┐
│ Vector Search:                                                 │
│   Strategy: top-k (search query, large session)                │
│   Results: 10 chunks from 5 different CVs                      │
└────────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────┐
│ Reranking:                                                     │
│   Scores: [9.5, 8.2, 7.8, 6.5, ...]                            │
│   Reordered by relevance                                       │
└────────────────────────────────────────────────────────────────┘
         │
         ▼
┌────────────────────────────────────────────────────────────────┐
│ LLM Generation:                                                │
│   SYSTEM_PROMPT + QUERY_TEMPLATE + formatted chunks            │
│   → "Based on the CVs, the following candidates have Python    │
│      experience: [CV:cv_abc123] John Doe (5 years)..."         │
└────────────────────────────────────────────────────────────────┘
```

---

## Configuration

### RAGConfigV5 Dataclass

```python
@dataclass
class RAGConfigV5:
    mode: Mode = Mode.LOCAL
    
    # Model configuration
    understanding_model: str | None = None      # Default: gemini-2.0-flash-001
    reranking_model: str | None = None          # Default: gemini-2.0-flash-001
    generation_model: str | None = None         # Default: gemini-2.0-flash
    reasoning_model: str | None = None          # Default: same as generation
    verification_model: str | None = None       # Default: gemini-2.0-flash-001
    
    # V5 Feature flags (NEW)
    multi_query_enabled: bool = True            # Generate query variations
    hyde_enabled: bool = True                   # Hypothetical document embeddings
    reasoning_enabled: bool = True              # Chain-of-Thought reasoning
    reflection_enabled: bool = True             # Self-reflection in reasoning
    claim_verification_enabled: bool = True     # Claim-level verification
    iterative_refinement_enabled: bool = True   # Regenerate if verification fails
    
    # Legacy feature flags
    reranking_enabled: bool = True
    verification_enabled: bool = True
    streaming_enabled: bool = False
    parallel_steps_enabled: bool = True
    
    # Retrieval settings
    default_k: int = 15                         # Increased for multi-query fusion
    default_threshold: float = 0.25             # Lower for broader recall
    max_context_tokens: int = 60000
    multi_query_k: int = 10                     # k per query variation
    
    # Timeouts (seconds)
    embedding_timeout: float = 10.0
    search_timeout: float = 20.0                # Increased for multi-query
    llm_timeout: float = 120.0
    reasoning_timeout: float = 120.0            # For Chain-of-Thought
    total_timeout: float = 240.0                # Increased for multi-step
```

### Environment Variables

```bash
# Required
OPENAI_API_KEY=your_openai_key           # For embeddings
OPENROUTER_API_KEY=your_openrouter_key    # For LLM generation

# Optional (Cloud mode)
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_service_key
GOOGLE_API_KEY=...              # For LangChain Gemini

# Feature flags
USE_LANGCHAIN=false             # Use LangChain wrapper
```

---

## Providers

### Provider Interface

```python
class EmbeddingProvider(ABC):
    async def embed_query(self, text: str) -> EmbeddingResult
    async def embed_documents(self, texts: List[str]) -> EmbeddingResult

class VectorStoreProvider(ABC):
    async def search(self, embedding, k, threshold, cv_ids, diversify_by_cv) -> List[SearchResult]
    async def add_embeddings(self, embeddings, metadatas, ids)

class LLMProvider(ABC):
    async def generate(self, prompt: str, system_prompt: str, **kwargs) -> LLMResult
```

### Provider Implementations

| Provider | Mode | Implementation |
|----------|------|----------------|
| `OpenRouterEmbeddingProvider` | Cloud | OpenAI text-embedding-3-small via OpenRouter |
| `LocalEmbeddingProvider` | Local | sentence-transformers (fallback) |
| `SupabaseVectorStore` | Cloud | pgvector in Supabase |
| `SimpleVectorStore` | Local | NumPy cosine similarity |
| `OpenRouterLLMProvider` | Both | OpenRouter API (Gemini, GPT-4, Claude) |

---

## Error Handling

### Error Types

```python
class RAGError(Exception):
    stage: PipelineStage | None
    severity: ErrorSeverity  # WARNING, RECOVERABLE, FATAL
    cause: Exception | None
    recoverable: bool

class GuardrailError(RAGError):      # Query rejected
class RetrievalError(RAGError):      # Search failed
class GenerationError(RAGError):     # LLM failed
```

### Retry Configuration

```python
@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay_ms: int = 100
    max_delay_ms: int = 5000
    exponential_base: float = 2.0
    jitter: bool = True
```

### Circuit Breaker

```python
@dataclass
class CircuitBreakerConfig:
    enabled: bool = True
    failure_threshold: int = 5        # Open after 5 failures
    recovery_timeout_seconds: int = 30 # Try recovery after 30s
    half_open_max_calls: int = 3      # Test calls before closing
```

**States:**
- `CLOSED` → Normal operation
- `OPEN` → Failing, rejecting all calls
- `HALF_OPEN` → Testing recovery

---

## Caching & Performance

### LRU Cache

```python
@dataclass
class CacheConfig:
    enabled: bool = True
    ttl_seconds: int = 300      # 5 minutes
    max_entries: int = 1000
    cache_embeddings: bool = True
    cache_responses: bool = True
```

### What Gets Cached

| Item | Cache Key | TTL |
|------|-----------|-----|
| Query embeddings | `emb:{query_text}` | 5 min |
| Full responses | `resp:{query_hash}` | 5 min |

### Performance Metrics

```python
@dataclass
class PipelineMetrics:
    total_ms: float
    stages: list[StageMetrics]
    cache_hit: bool
    retry_count: int
```

---

## Evaluation & Logging

### Query Log Entry

```python
@dataclass
class QueryLogEntry:
    timestamp: str
    session_id: Optional[str]
    query: str
    response: str
    sources: List[Dict[str, Any]]
    metrics: Dict[str, float]
    hallucination_check: Dict[str, Any]
    guardrail_passed: bool
    confidence_score: float
    mode: str
```

### Log Location

```
eval_logs/
├── queries_20260103.jsonl    # Today's queries
├── queries_20260102.jsonl    # Yesterday's queries
└── ...
```

### Daily Statistics

```python
@dataclass
class DailyStats:
    date: str
    total_queries: int
    avg_confidence: float
    guardrail_rejections: int
    avg_latency_ms: float
    low_confidence_count: int
    unique_sessions: int
```

---

## Prompt Templates

### System Prompt (Persona)

```python
SYSTEM_PROMPT = """You are an expert HR analyst and CV reviewer assistant.
Your job is to analyze CVs and help with candidate screening.

CRITICAL RULES:
1. ONLY use information from the provided CV context
2. NEVER fabricate information not in the CVs
3. Include [CV:cv_id] references for every claim
4. Use Markdown tables when comparing candidates
..."""
```

### Query Templates

| Template | Use Case |
|----------|----------|
| `QUERY_TEMPLATE` | General questions |
| `QUERY_TEMPLATE_CONCISE` | Short answers |
| `QUERY_TEMPLATE_JSON` | Structured JSON output |
| `COMPARISON_TEMPLATE` | Compare multiple candidates |
| `RANKING_TEMPLATE` | Rank candidates by criteria |

### PromptBuilder Class

```python
class PromptBuilder:
    def build_query_prompt(question, chunks, total_cvs, response_format)
    def build_comparison_prompt(criteria, chunks)
    def build_ranking_prompt(role, criteria, chunks, top_n)
```

---

## API Endpoints

### Query Endpoint

```
POST /api/v2/query
{
    "question": "Who has Python experience?",
    "session_id": "session_xxx",
    "k": 10,
    "threshold": 0.3
}

Response:
{
    "answer": "...",
    "sources": [...],
    "metrics": {...},
    "confidence_score": 0.85,
    "guardrail_passed": true
}
```

### Health Check

```
GET /api/health
{
    "status": "ok",
    "mode": "cloud",
    "reranking_enabled": true,
    "verification_enabled": true
}
```

---

## File Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── routes.py              # Main API routes
│   │   ├── routes_v2.py           # V2 API with sessions
│   │   ├── routes_sessions.py     # Session management
│   │   └── dependencies.py        # FastAPI dependencies
│   │
│   ├── services/
│   │   ├── rag_service_v5.py      # Main RAG orchestrator (V5) ⭐
│   │   ├── query_understanding_service.py
│   │   ├── multi_query_service.py # Query variations + HyDE (V5) ⭐
│   │   ├── reasoning_service.py   # Chain-of-Thought (V5) ⭐
│   │   ├── claim_verifier_service.py # Claim verification (V5) ⭐
│   │   ├── guardrail_service.py
│   │   ├── embedding_service.py
│   │   ├── reranking_service.py
│   │   ├── verification_service.py
│   │   ├── hallucination_service.py
│   │   ├── chunking_service.py
│   │   ├── pdf_service.py
│   │   ├── confidence_calculator.py
│   │   ├── cost_tracker.py
│   │   ├── eval_service.py
│   │   └── output_processor/      # Output processing (V5) ⭐
│   │       ├── orchestrator.py
│   │       ├── processor.py
│   │       ├── validators.py
│   │       └── modules/
│   │           ├── thinking_module.py
│   │           ├── analysis_module.py
│   │           ├── table_module.py
│   │           ├── conclusion_module.py
│   │           ├── direct_answer_module.py
│   │           ├── gap_analysis_module.py   # NEW v5.1.1
│   │           ├── red_flags_module.py      # NEW v5.1.1
│   │           └── timeline_module.py       # NEW v5.1.1
│   │
│   ├── providers/
│   │   ├── base.py                # Abstract interfaces
│   │   ├── factory.py             # Provider factory
│   │   ├── cloud/
│   │   │   ├── embeddings.py
│   │   │   ├── llm.py
│   │   │   ├── vector_store.py
│   │   │   └── sessions.py
│   │   └── local/
│   │       ├── embeddings.py
│   │       ├── llm.py
│   │       └── vector_store.py
│   │
│   ├── prompts/
│   │   └── templates.py           # All prompt templates
│   │
│   ├── models/
│   │   ├── schemas.py             # Pydantic models
│   │   └── sessions.py            # Session management
│   │
│   ├── utils/
│   │   ├── error_handling.py      # Graceful degradation (V5) ⭐
│   │   └── text_utils.py          # Text processing utilities
│   │
│   ├── config.py                  # Settings and configuration
│   └── main.py                    # FastAPI app entry point
│
├── eval_logs/                     # Query logs (JSONL)
├── migrations/                    # SQL migrations
└── tests/                         # Test suite
```

---

## Version History

| Version | Date | Commit | Changes |
|---------|------|--------|---------|
| **6.0.0** | **Upcoming** | - | HuggingFace NLI verification, Zero-shot classification, RAGAS evaluation framework ([Roadmap](./roadmap/RAG_V6.md)) |
| **5.1.1** | **2026-01-05** | - | **Current**: GapAnalysisModule, RedFlagsModule, TimelineModule, Deep Enriched Metadata (seniority, job-hopping, FAANG detection) |
| 5.1.0 | 2026-01-04 | - | Smart CV Chunking, Enriched Metadata, Targeted Retrieval, Summary Chunks |
| 5.0.0 | 2026-01-03 21:38 | `b63a069` | Multi-Query, HyDE, RRF, Chain-of-Thought Reasoning, Claim Verification, Iterative Refinement, Graceful Degradation |
| 4.0.0 | 2026-01-03 18:33 | `e785e61` | 4-step pipeline with Re-ranking and LLM Verification, circuit breaker, combined confidence scoring |
| 3.0.0 | 2026-01-03 15:02 | `2870a05` | RAGServiceV3 with confidence scoring, guardrails, 2-step LLM with QueryUnderstanding |
| 2.0.0 | 2026-01-02 17:15 | `dea6b07` | OpenRouter unified LLM provider, session-based chat architecture |
| 1.0.0 | 2026-01-02 13:42 | `27ec7d7` | Initial RAG pipeline with dual-mode architecture (local/cloud) |

---

> **Note**: This project was started on **January 2, 2026**. This document reflects the current state of the RAG system (V5). For future improvements, see the [roadmap documentation](./roadmap/).
