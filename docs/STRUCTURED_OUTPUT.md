# Structured Output & Orchestration

> **CV Screener AI - Complete Structured Output Documentation**
> 
> Version: 6.0 | Last Updated: January 2026

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture (v6.0)](#architecture-v60)
3. [Query Type → Structure Routing](#query-type--structure-routing)
4. [9 Structures Reference](#9-structures-reference)
5. [29 Modules Reference](#29-modules-reference)
6. [Data Models](#data-models)
7. [Orchestration Flow](#orchestration-flow)
8. [Conversational Context](#conversational-context)
9. [Legacy: Table Module Details](#legacy-table-module-details)
10. [API Response Format](#api-response-format)

---

## Overview

The Structured Output system in **v6.0** implements a complete **Orchestrator → Structures → Modules** architecture that:

- **Routes queries** to the appropriate Structure based on `query_type`
- **Assembles outputs** using reusable Modules
- **Supports context** via `conversation_history` parameter
- **Ensures consistency** through type-safe dataclasses

### Key Components (v6.0)

| Component | Count | Purpose |
|-----------|-------|---------|
| **Orchestrator** | 1 | Routes queries and coordinates Structures |
| **Structures** | 9 | Complete output assemblers for each query type |
| **Modules** | 29 | Reusable extraction/formatting components |
| **StructuredOutput** | 1 | Main data model for all response types |

### Query Types Supported

| Query Type | Structure | Example |
|------------|-----------|---------|
| `single_candidate` | SingleCandidateStructure | "Dame el perfil de Juan" |
| `red_flags` | RiskAssessmentStructure | "Qué red flags tiene María?" |
| `comparison` | ComparisonStructure | "Compara Juan y María" |
| `search` | SearchStructure | "Busca developers Python" |
| `ranking` | RankingStructure | "Top 5 para backend" |
| `job_match` | JobMatchStructure | "Quién encaja para senior?" |
| `team_build` | TeamBuildStructure | "Build a team of 3" |
| `verification` | VerificationStructure | "Verify AWS certification" |
| `summary` | SummaryStructure | "Overview of candidates" |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RAW LLM OUTPUT                                     │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ :::thinking                                                              ││
│  │ [Detailed reasoning about candidates...]                                 ││
│  │ :::                                                                      ││
│  │                                                                          ││
│  │ **Sofia Grijalva** is the best candidate with 5 years Python...         ││
│  │                                                                          ││
│  │ | Candidate | Skills | Match Score |                                    ││
│  │ |-----------|--------|-------------|                                    ││
│  │ | Sofia G.  | Python | 95%         |                                    ││
│  │                                                                          ││
│  │ :::conclusion                                                            ││
│  │ Sofia is highly recommended for the role.                               ││
│  │ :::                                                                      ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         OUTPUT ORCHESTRATOR                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ 1. Pre-clean LLM output (remove code blocks, artifacts)                 ││
│  │ 2. Invoke OutputProcessor to extract components                         ││
│  │ 3. Generate fallbacks for missing components                            ││
│  │ 4. Format candidate references uniformly                                ││
│  │ 5. Assemble final output sequentially                                   ││
│  │ 6. Post-clean (remove duplicates, fix formatting)                       ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          OUTPUT PROCESSOR                                    │
│  ┌───────────────┬───────────────┬───────────────┬───────────────┬────────┐│
│  │ ThinkingModule│DirectAnswer   │AnalysisModule │ TableModule   │Conclus.││
│  │               │Module         │               │               │Module  ││
│  │ :::thinking   │ First 1-3     │ Content       │ Markdown      │:::conc ││
│  │ extraction    │ sentences     │ between       │ table →       │extract ││
│  │               │               │ answer/table  │ TableData     │        ││
│  └───────────────┴───────────────┴───────────────┴───────────────┴────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          STRUCTURED OUTPUT                                   │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ {                                                                        ││
│  │   "direct_answer": "Sofia Grijalva is the best candidate...",           ││
│  │   "raw_content": "[Original LLM output]",                               ││
│  │   "thinking": "Detailed reasoning...",                                  ││
│  │   "analysis": "Se analizaron 3 candidatos...",                          ││
│  │   "table_data": {                                                       ││
│  │     "title": "Candidate Comparison Table",                              ││
│  │     "headers": ["Candidate", "Skills", "Match Score"],                  ││
│  │     "rows": [{ "candidate_name": "Sofia", "cv_id": "cv_xxx", ... }]     ││
│  │   },                                                                    ││
│  │   "conclusion": "Sofia is highly recommended...",                       ││
│  │   "cv_references": [...],                                               ││
│  │   "parsing_warnings": [],                                               ││
│  │   "fallback_used": false                                                ││
│  │ }                                                                        ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Models

### StructuredOutput (Main Model)

```python
@dataclass
class StructuredOutput:
    """
    Complete structured output from LLM processing.
    
    This structure guarantees that the frontend always receives
    consistent data, regardless of LLM output quality.
    """
    # Core components (always present)
    direct_answer: str          # Concise 1-3 sentence answer
    raw_content: str            # Original LLM output (preserved)
    
    # Optional components (null if not found/parsed)
    thinking: Optional[str]     # Reasoning process (collapsible)
    analysis: Optional[str]     # Detailed analysis section
    table_data: Optional[TableData]  # Candidate comparison table
    conclusion: Optional[str]   # Final recommendations
    
    # Metadata
    cv_references: List[CVReference]  # All candidate mentions
    parsing_warnings: List[str]       # Any parsing issues
    fallback_used: bool               # True if fallback table generated
```

### TableData (Comparison Table)

```python
@dataclass
class TableData:
    """Parsed table structure with match scores."""
    title: str = "Candidate Comparison Table"
    headers: List[str]          # ["Candidate", "Skills", "Match Score"]
    rows: List[TableRow]        # One row per candidate
```

### TableRow (Individual Candidate Row)

```python
@dataclass
class TableRow:
    """A single row in the candidate comparison table."""
    candidate_name: str         # "Sofia Grijalva"
    cv_id: str                  # "cv_sofia_grijalva_abc123"
    columns: Dict[str, str]     # {"Skills": "Python, Django", "Experience": "5 years"}
    match_score: int            # 0-100 for coloring (green ≥90, yellow 70-89, gray <70)
```

### CVReference (Candidate Mention)

```python
@dataclass
class CVReference:
    """A candidate reference in the output."""
    cv_id: str                  # "cv_sofia_grijalva_abc123"
    name: str                   # "Sofia Grijalva"
    context: str                # Surrounding text where mentioned
```

---

## Output Modules

The system uses **5 dedicated modules** to extract and format each component:

### 1. ThinkingModule

**Purpose**: Extract `:::thinking:::` blocks containing LLM reasoning.

**Location**: `backend/app/services/output_processor/modules/thinking_module.py`

```python
class ThinkingModule:
    def extract(self, llm_output: str) -> Optional[str]:
        """
        Extract thinking block from LLM output.
        
        Patterns recognized:
        - :::thinking ... :::
        - :::thinking ... (no closing)
        
        Returns: Thinking content WITHOUT markers, stripped of markdown
        """
    
    def format(self, content: str) -> str:
        """Format: ':::thinking\n{content}\n:::'"""
```

**Special Processing**:
- Strips markdown (bold, links, headers) since thinking dropdown doesn't render it
- Converts `**[Name](cv:cv_xxx)**` → `Name (cv_xxx)` for plain text display

---

### 2. DirectAnswerModule

**Purpose**: Extract the concise 1-3 sentence direct answer.

**Location**: `backend/app/services/output_processor/modules/direct_answer_module.py`

```python
class DirectAnswerModule:
    def extract(self, llm_output: str) -> str:
        """
        Extract direct answer from LLM output.
        
        Strategy:
        1. Remove thinking/conclusion blocks
        2. Remove tables and code blocks
        3. Remove prompt contamination (CRITICAL RULES, etc.)
        4. Take first 1-3 sentences from first paragraph
        5. Clean transition phrases ("Here is the analysis...")
        6. Deduplicate candidate mentions
        
        Returns: Always returns something (never None)
        """
    
    def format(self, content: str) -> str:
        """Ensure proper capitalization"""
```

**Contamination Patterns Removed**:
- `ABSOLUTELY FORBIDDEN` sections
- `CRITICAL RULES` headers
- `Match Score Legend` instructions
- `code Copy code` artifacts
- Hallucinated `References` sections

---

### 3. AnalysisModule

**Purpose**: Extract detailed analysis between direct answer and table/conclusion.

**Location**: `backend/app/services/output_processor/modules/analysis_module.py`

```python
class AnalysisModule:
    def extract(self, llm_output: str, direct_answer: str, conclusion: str) -> Optional[str]:
        """
        Extract analysis section.
        
        Strategy:
        1. Try explicit ### Analysis section
        2. Fallback: Extract content between answer and table/conclusion
        3. Remove ALL prompt contamination
        
        Returns: Analysis content or None
        """
    
    def generate_fallback(self, direct_answer: str, table_data: TableData, conclusion: str) -> Optional[str]:
        """
        Generate fallback analysis with REAL reasoning.
        
        Includes:
        - Number of candidates analyzed
        - Distribution of match scores (high/medium/low)
        - Best candidate identification
        """
    
    def format(self, content: str) -> str:
        """Add '### Analysis' header if not present"""
```

**Fallback Analysis Example**:
```
Se analizaron 3 candidato(s) en base a los requisitos especificados.
2 candidato(s) tienen match score alto (≥70%): Sofia Grijalva, Carlos López.
1 candidato(s) no cumplen los requisitos principales (<40%).
El candidato con mejor puntuación es Sofia Grijalva con 95% de match.
```

---

### 4. TableModule

**Purpose**: Extract and structure candidate comparison tables.

**Location**: `backend/app/services/output_processor/modules/table_module.py`

```python
class TableModule:
    def extract(self, llm_output: str, chunks: List[dict]) -> Optional[TableData]:
        """
        Extract table from LLM output with match scores.
        
        Process:
        1. Pre-process: extract tables from code blocks
        2. Parse markdown table
        3. Extract candidate info (name, cv_id) from first column
        4. Extract match score from last column (percentage, stars, text)
        5. Deduplicate rows by candidate name
        6. Fallback: generate from chunks if no table found
        
        Returns: TableData with TableRow objects
        """
    
    def _extract_candidate_info(self, cell: str) -> tuple[str, str]:
        """
        Extract candidate name and cv_id from cell.
        
        Patterns recognized:
        - **[Name](cv:cv_xxx)**
        - **Name** cv_xxx
        - Name cv_xxx
        """
    
    def _extract_match_score(self, cell: str, all_cells: List[str]) -> int:
        """
        Extract numeric match score (0-100).
        
        Search strategy:
        1. Explicit percentage: "95%"
        2. Stars: ⭐⭐⭐⭐⭐ = 100%
        3. Text indicators: "excellent" = 95, "good" = 75, "weak" = 25
        4. Default: 50
        """
    
    def _generate_fallback_table(self, chunks: List[dict]) -> Optional[TableData]:
        """
        Generate fallback table from CV chunks.
        
        Features:
        - Groups chunks by candidate name
        - Deduplicates by name (not cv_id)
        - Priority: Most recent upload > Higher similarity score
        - Extracts skills from content
        """
```

---

### 5. ConclusionModule

**Purpose**: Extract `:::conclusion:::` blocks with final recommendations.

**Location**: `backend/app/services/output_processor/modules/conclusion_module.py`

```python
class ConclusionModule:
    def extract(self, llm_output: str) -> Optional[str]:
        """
        Extract conclusion block.
        
        Patterns recognized:
        - :::conclusion ... :::
        - :::conclusion ... (no closing)
        
        Includes cleaning of:
        - Prompt contamination
        - Web search artifacts
        - Malformed bold formatting
        - Duplicate candidate mentions
        """
    
    def format(self, content: str) -> str:
        """Format: ':::conclusion\n{content}\n:::'"""
```

---

## Orchestration Flow

The `OutputOrchestrator` is the **main entry point** called by the RAG service.

### Entry Point

```python
# In rag_service_v5.py
from app.services.output_processor.orchestrator import get_orchestrator

orchestrator = get_orchestrator()
structured_output, formatted_answer = orchestrator.process(
    raw_llm_output=ctx.generated_response,
    chunks=ctx.effective_chunks
)
```

### Processing Steps

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR.PROCESS()                            │
└─────────────────────────────────────────────────────────────────────┘
                              │
    ┌─────────────────────────┼─────────────────────────┐
    │                         │                         │
    ▼                         │                         │
┌───────────────────┐         │                         │
│ STEP 0: PRE-CLEAN │         │                         │
│ ───────────────── │         │                         │
│ • Unwrap code     │         │                         │
│   block wrappers  │         │                         │
│ • Remove "code    │         │                         │
│   Copy code"      │         │                         │
└─────────┬─────────┘         │                         │
          │                   │                         │
          ▼                   │                         │
┌───────────────────┐         │                         │
│ STEP 1: EXTRACT   │◄────────┘                         │
│ ───────────────── │                                   │
│ OutputProcessor   │                                   │
│ invokes 5 modules:│                                   │
│ • thinking        │                                   │
│ • direct_answer   │                                   │
│ • analysis        │                                   │
│ • table           │                                   │
│ • conclusion      │                                   │
└─────────┬─────────┘                                   │
          │                                             │
          ▼                                             │
┌───────────────────┐                                   │
│ STEP 1.5: FALLBACK│                                   │
│ ───────────────── │                                   │
│ If no analysis:   │                                   │
│ generate_fallback │                                   │
│ from table_data   │                                   │
└─────────┬─────────┘                                   │
          │                                             │
          ▼                                             │
┌───────────────────┐                                   │
│ STEP 1.6: FORMAT  │◄──────────────────────────────────┘
│ CANDIDATE REFS    │
│ ───────────────── │
│ Build candidate   │
│ map from table    │
│ Convert all refs: │
│ [Name](cv_xxx) →  │
│ [📄](cv:cv_xxx)   │
│ **Name**          │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ STEP 2: ASSEMBLE  │
│ ───────────────── │
│ Sequential order: │
│ 1. thinking       │
│ 2. direct_answer  │
│ 3. analysis       │
│ 4. table          │
│ 5. conclusion     │
│                   │
│ Join with "\n\n"  │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ STEP 3: DEDUP     │
│ ───────────────── │
│ Remove duplicate  │
│ paragraphs that   │
│ slipped through   │
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ STEP 4: POST-CLEAN│
│ ───────────────── │
│ • Fix bold format │
│ • Ensure cv:      │
│   prefix on links │
│ • Remove "code"   │
│   artifacts       │
│ • Clean whitespace│
└─────────┬─────────┘
          │
          ▼
┌───────────────────┐
│ RETURN            │
│ ───────────────── │
│ (StructuredOutput,│
│  formatted_answer)│
└───────────────────┘
```

### Code Flow

```python
def process(self, raw_llm_output: str, chunks: List[Dict]) -> tuple[StructuredOutput, str]:
    # STEP 0: PRE-PROCESS
    cleaned_llm_output = self._pre_clean_llm_output(raw_llm_output)
    
    # STEP 1: Extract all components
    structured = self.processor.process(cleaned_llm_output, chunks)
    
    # STEP 1.5: Generate fallback analysis if none extracted
    if not structured.analysis:
        fallback = self.analysis_module.generate_fallback(
            structured.direct_answer,
            structured.table_data,
            structured.conclusion
        )
        if fallback:
            structured.analysis = fallback
    
    # STEP 1.6: Format candidate references uniformly
    candidate_map = {}  # {name: cv_id}
    if structured.table_data:
        for row in structured.table_data.rows:
            candidate_map[row.candidate_name] = row.cv_id
    
    structured.direct_answer = self._format_candidate_references(structured.direct_answer, candidate_map)
    structured.analysis = self._format_candidate_references(structured.analysis, candidate_map)
    structured.conclusion = self._format_candidate_references(structured.conclusion, candidate_map)
    
    # STEP 2: Assemble output SEQUENTIALLY
    parts = []
    if structured.thinking:
        parts.append(self.thinking_module.format(structured.thinking))
    parts.append(self.direct_answer_module.format(structured.direct_answer))
    if structured.analysis:
        parts.append(self.analysis_module.format(structured.analysis))
    if structured.table_data:
        parts.append(self.table_module.format(structured.table_data))
    if structured.conclusion:
        parts.append(self.conclusion_module.format(structured.conclusion))
    
    final_answer = "\n\n".join(parts)
    
    # STEP 3: Remove duplicate paragraphs
    final_answer = self._remove_duplicate_paragraphs(final_answer)
    
    # STEP 4: POST-PROCESS
    final_answer = self._post_clean_output(final_answer)
    
    return structured, final_answer
```

---

## Table Module: Comparison vs Individual

The TableModule handles **two distinct use cases**:

### Use Case 1: Multiple Candidates (Comparison Table)

**Query**: "Who has Python experience?" or "Compare candidates for Senior Developer"

**Output Structure**:

```
┌─────────────────────────────────────────────────────────────────────┐
│                   CANDIDATE COMPARISON TABLE                         │
├────────────────┬─────────────────────┬─────────────┬───────────────┤
│ Candidate      │ Key Skills          │ Experience  │ Match Score   │
├────────────────┼─────────────────────┼─────────────┼───────────────┤
│ Sofia Grijalva │ Python, Django, AWS │ 5 years     │ 95% 🟢        │
├────────────────┼─────────────────────┼─────────────┼───────────────┤
│ Carlos López   │ Python, Flask       │ 3 years     │ 75% 🟡        │
├────────────────┼─────────────────────┼─────────────┼───────────────┤
│ Ana García     │ JavaScript, React   │ 4 years     │ 25% ⚪        │
└────────────────┴─────────────────────┴─────────────┴───────────────┘
```

**TableData for Comparison**:

```python
TableData(
    title="Candidate Comparison Table",
    headers=["Candidate", "Key Skills", "Experience", "Match Score"],
    rows=[
        TableRow(
            candidate_name="Sofia Grijalva",
            cv_id="cv_sofia_grijalva_abc123",
            columns={
                "Key Skills": "Python, Django, AWS",
                "Experience": "5 years"
            },
            match_score=95  # Green ≥90%
        ),
        TableRow(
            candidate_name="Carlos López",
            cv_id="cv_carlos_lopez_def456",
            columns={
                "Key Skills": "Python, Flask",
                "Experience": "3 years"
            },
            match_score=75  # Yellow 70-89%
        ),
        TableRow(
            candidate_name="Ana García",
            cv_id="cv_ana_garcia_ghi789",
            columns={
                "Key Skills": "JavaScript, React",
                "Experience": "4 years"
            },
            match_score=25  # Gray <70%
        )
    ]
)
```

### Use Case 2: Single Candidate (Individual Details)

> **Enhanced in v5.1** with Smart Chunking metadata

**Query**: "Tell me more about Sofia Grijalva" or "damelo todo sobre Matteo Rossi"

**How it Works (v5.1)**:

1. **Targeted Retrieval**: System detects single-candidate query and fetches ALL chunks for that candidate
2. **Enriched Metadata**: Chunks now include pre-calculated `current_role`, `total_experience_years`, `is_current`
3. **Summary Chunk**: Contains pre-built profile with career trajectory

**Output Structure**:

```
┌─────────────────────────────────────────────────────────────────────┐
│                   CANDIDATE PROFILE                                  │
├─────────────────┬───────────────────────────────────────────────────┤
│ Current Role    │ Lead Merchandising Strategist (2023-Present)      │  ← From metadata
├─────────────────┼───────────────────────────────────────────────────┤
│ Current Company │ Global Fashion Retail Corp                        │  ← From metadata
├─────────────────┼───────────────────────────────────────────────────┤
│ Experience      │ 6 years total                                     │  ← Pre-calculated
├─────────────────┼───────────────────────────────────────────────────┤
│ Key Skills      │ Python, Excel, SAP, Demand Forecasting            │
├─────────────────┼───────────────────────────────────────────────────┤
│ Career Path     │ 3 positions (Junior → Mid → Lead)                 │  ← From position_count
└─────────────────┴───────────────────────────────────────────────────┘
```

**Metadata Available for Single Candidate (v5.1)**:

```python
# From Summary Chunk
{
    "current_role": "Lead Merchandising Strategist",
    "current_company": "Global Fashion Retail Corp",
    "total_experience_years": 6.0,
    "position_count": 3,
    "is_summary": True
}

# From Position Chunks (one per job)
{
    "job_title": "Lead Merchandising Strategist",
    "company": "Global Fashion Retail Corp",
    "start_year": 2023,
    "end_year": None,  # None = Present
    "is_current": True,
    "duration_years": 2.0,
    "position_order": 1  # 1 = most recent
}
```

**TableData for Individual**:

```python
TableData(
    title="Candidate Details Table",
    headers=["Attribute", "Value"],
    rows=[
        TableRow(
            candidate_name="Sofia Grijalva",
            cv_id="cv_sofia_grijalva_abc123",
            columns={
                "Attribute": "Experience",
                "Value": "5 years in backend development"
            },
            match_score=95
        ),
        # Additional rows for each attribute...
    ]
)
```

### Key Differences

| Aspect | Comparison Mode | Individual Mode |
|--------|-----------------|-----------------|
| **Rows** | One row per candidate | One row per attribute |
| **Columns** | Multiple criteria columns | Key-Value pair |
| **Match Score** | Per candidate | Overall relevance |
| **Use Case** | "Find candidates with X" | "Tell me about candidate Y" |

### Deduplication Logic

The TableModule implements **robust deduplication** to handle cases where the same candidate appears multiple times:

```python
def _deduplicate_rows(self, rows: List[TableRow]) -> List[TableRow]:
    """
    Deduplicate by candidate NAME (not just cv_id).
    
    PRIORITY ORDER:
    1. Most recent upload (indexed_at timestamp)
    2. Higher match_score (more relevant)
    3. First occurrence (fallback)
    """
    seen_names: Dict[str, TableRow] = {}
    
    for row in rows:
        normalized_name = row.candidate_name.lower().strip()
        
        if normalized_name not in seen_names:
            seen_names[normalized_name] = row
        else:
            existing = seen_names[normalized_name]
            # Priority 1: Most recent wins
            if row.columns.get("_indexed_at", "") > existing.columns.get("_indexed_at", ""):
                seen_names[normalized_name] = row
            # Priority 2: Higher score wins
            elif row.match_score > existing.match_score:
                seen_names[normalized_name] = row
    
    return sorted(seen_names.values(), key=lambda r: r.match_score, reverse=True)
```

---

## Candidate Reference Formatting

All candidate mentions are formatted uniformly across ALL sections:

### Format Standard

```
[📄](cv:cv_xxx) **Candidate Name**
```

- **📄 icon**: Clickable link to open CV PDF
- **cv:prefix**: Required for frontend detection
- **Bold name**: Visual emphasis, NOT clickable

### Transformation Pipeline

```
LLM Output Variations           →    Unified Format
─────────────────────────────────────────────────────
[Name](cv_xxx)                  →    [📄](cv:cv_xxx) **Name**
[Name](cv:cv_xxx)               →    [📄](cv:cv_xxx) **Name**
**[Name](cv:cv_xxx)**           →    [📄](cv:cv_xxx) **Name**
**[Name](cv_xxx)**              →    [📄](cv:cv_xxx) **Name**
Sofia Grijalva (plain text)     →    [📄](cv:cv_xxx) **Sofia Grijalva**
```

### Implementation

```python
def _format_candidate_references(self, text: str, candidate_map: dict) -> str:
    """
    Unified formatting for candidate mentions.
    
    Args:
        text: Text containing candidate references
        candidate_map: {name: cv_id} from table data
    """
    # Step 1: Remove bold wrapper around links
    text = re.sub(r'\*\*\[([^\]]+)\]\(([^)]+)\)\*\*', r'[\1](\2)', text)
    
    # Step 2: Add cv: prefix if missing
    text = re.sub(r'\[([^\]]+)\]\((cv_[a-z0-9_-]+)\)', r'[\1](cv:\2)', text)
    
    # Step 3: Convert to icon + bold format
    text = re.sub(r'\[([^\]]+)\]\((cv:cv_[a-z0-9_-]+)\)', r'[📄](\2) **\1**', text)
    
    # Step 4: Detect plain text names and convert them
    for name, cv_id in candidate_map.items():
        if name not in text:
            continue
        # Only convert if not already formatted
        pattern = rf'(?<!\*\*){re.escape(name)}(?!\*\*)'
        text = re.sub(pattern, f'[📄](cv:{cv_id}) **{name}**', text, count=1)
    
    return text
```

---

## Visual Output Structure

The frontend renders StructuredOutput with specific visual styles:

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. THINKING PROCESS (Collapsible, Purple)                           │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ ▶ Show reasoning process                                        │ │
│ │   ┌───────────────────────────────────────────────────────────┐ │ │
│ │   │ Plain text analysis of candidates...                      │ │ │
│ │   │ No markdown rendering, collapsed by default               │ │ │
│ │   └───────────────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│ 2. DIRECT ANSWER (Yellow/Gold Border)                               │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ [📄](cv:cv_xxx) **Sofia Grijalva** is the best match with 5    │ │
│ │ years of Python experience.                                     │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│ 3. ANALYSIS (Cyan Border)                                           │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ ### Analysis                                                    │ │
│ │ Se analizaron 3 candidato(s) en base a los requisitos.         │ │
│ │ 2 candidato(s) tienen match score alto (≥70%).                 │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│ 4. CANDIDATE TABLE (Dynamic Headers, Colored Scores)                │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ ┌───────────────┬──────────────┬─────────────┬───────────────┐ │ │
│ │ │ Candidate     │ Skills       │ Experience  │ Match Score   │ │ │
│ │ ├───────────────┼──────────────┼─────────────┼───────────────┤ │ │
│ │ │ Sofia G. 📄   │ Python, AWS  │ 5 years     │ 95% 🟢        │ │ │
│ │ │ Carlos L. 📄  │ Python       │ 3 years     │ 75% 🟡        │ │ │
│ │ └───────────────┴──────────────┴─────────────┴───────────────┘ │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│ 5. CONCLUSION (Green Border)                                        │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ [📄](cv:cv_xxx) **Sofia Grijalva** is highly recommended for   │ │
│ │ the Senior Developer role.                                      │ │
│ └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

### Match Score Colors

| Score Range | Color | CSS Class |
|-------------|-------|-----------|
| ≥ 90% | 🟢 Green | `match-high` |
| 70-89% | 🟡 Yellow | `match-medium` |
| < 70% | ⚪ Gray | `match-low` |

---

## API Response Format

The RAG API returns both `answer` (formatted string) and `structured_output` (JSON):

```json
{
  "answer": ":::thinking\n...\n:::\n\n[📄](cv:cv_xxx) **Sofia**...\n\n### Analysis\n...",
  "structured_output": {
    "direct_answer": "Sofia Grijalva is the best match...",
    "raw_content": "[Original LLM output]",
    "thinking": "Detailed reasoning about candidates...",
    "analysis": "Se analizaron 3 candidato(s)...",
    "table_data": {
      "title": "Candidate Comparison Table",
      "headers": ["Candidate", "Key Skills", "Match Score"],
      "rows": [
        {
          "candidate_name": "Sofia Grijalva",
          "cv_id": "cv_sofia_grijalva_abc123",
          "columns": {"Key Skills": "Python, Django, AWS"},
          "match_score": 95
        }
      ]
    },
    "conclusion": "Sofia is highly recommended...",
    "cv_references": [],
    "parsing_warnings": [],
    "fallback_used": false
  },
  "sources": [{"cv_id": "cv_sofia_grijalva_abc123", "filename": "Sofia_Grijalva.pdf"}],
  "confidence_score": 0.92,
  "metrics": {"total_ms": 2345}
}
```

### Frontend Usage

```typescript
// Option 1: Render formatted answer (markdown string)
<MarkdownRenderer content={response.answer} />

// Option 2: Render structured components individually
<ThinkingDropdown content={response.structured_output.thinking} />
<DirectAnswer content={response.structured_output.direct_answer} />
<CandidateTable data={response.structured_output.table_data} />
<Conclusion content={response.structured_output.conclusion} />
```

---

## File Structure

```
backend/app/services/output_processor/
├── __init__.py              # Exports OutputProcessor, OutputOrchestrator
├── orchestrator.py          # Main entry point, coordinates all processing
├── processor.py             # Invokes modules, builds StructuredOutput
├── validators.py            # Output validation utilities
└── modules/
    ├── __init__.py          # Exports all 5 modules
    ├── thinking_module.py   # :::thinking::: extraction
    ├── direct_answer_module.py  # Direct answer extraction
    ├── analysis_module.py   # Analysis section + fallback generation
    ├── table_module.py      # Table parsing + fallback generation
    └── conclusion_module.py # :::conclusion::: extraction

backend/app/models/
└── structured_output.py     # StructuredOutput, TableData, TableRow, CVReference
```

---

## Best Practices

### DO

- ✅ Use `get_orchestrator()` singleton for processing
- ✅ Always provide chunks for fallback table generation
- ✅ Handle `fallback_used=True` in frontend (show warning)
- ✅ Use `table_data.rows` for iteration, not raw markdown

### DON'T

- ❌ Create parallel extraction functions outside modules
- ❌ Modify modules without explicit need
- ❌ Parse tables from `answer` string (use `structured_output.table_data`)
- ❌ Skip candidate reference formatting (breaks CV links)

---

---

## Enhanced Modules (v5.1.1)

> **NEW** - Three powerful analysis modules that provide deeper insights into candidate profiles.

### Overview

The v5.1.1 release introduces **3 new enhanced modules** that analyze CV metadata to provide actionable insights:

| Module | Purpose | When Active |
|--------|---------|-------------|
| **GapAnalysisModule** | Skills gap detection vs job requirements | When query mentions required skills |
| **RedFlagsModule** | Risk detection (job-hopping, gaps, etc.) | Always (if chunks have metadata) |
| **TimelineModule** | Career trajectory visualization | Always (if position data available) |

These modules work alongside the 5 core modules and are processed **after** the main LLM response.

---

### Gap Analysis Module

**File**: `modules/gap_analysis_module.py`

**Purpose**: Identifies what skills/requirements are missing from candidates relative to job requirements specified in the query.

#### Data Structure

```python
@dataclass
class SkillGap:
    skill: str                      # Missing skill name
    importance: str                 # "critical", "preferred", "nice_to_have"
    candidates_missing: List[str]   # Candidates without this skill
    candidates_have: List[str]      # Candidates with this skill

@dataclass
class GapAnalysisData:
    required_skills: List[str]      # Skills extracted from query
    skill_gaps: List[SkillGap]      # List of gaps found
    coverage_score: float           # 0-100% of requirements covered
    best_coverage_candidate: str    # Candidate with best coverage
    summary: str                    # Human-readable summary
```

#### Output Format

```json
{
  "gap_analysis": {
    "required_skills": ["Maya", "Houdini", "Python", "Leadership"],
    "skill_gaps": [
      {
        "skill": "Houdini",
        "importance": "critical",
        "candidates_missing": ["Juan García", "Ana López"],
        "candidates_have": ["Marco Rossi"]
      }
    ],
    "coverage_score": 75.0,
    "best_coverage_candidate": "Marco Rossi",
    "summary": "Best coverage: Marco Rossi (75%) | 2 critical gaps identified"
  }
}
```

#### Example Questions That Trigger Gap Analysis

- "¿Qué candidatos tienen todas las skills: Maya, Houdini y Python?"
- "Para el puesto de Lead 3D Artist, ¿qué gaps tienen los candidatos?"
- "¿Quién le falta Houdini pero tiene el resto de skills?"
- "¿Cuál es el candidato con mejor cobertura para mis requisitos?"

---

### Red Flags Module

**File**: `modules/red_flags_module.py`

**Purpose**: Detects potential risk indicators in candidate profiles.

#### Flag Types

| Flag Type | Severity | Description | Threshold |
|-----------|----------|-------------|-----------|
| `job_hopping` | High/Medium | Frequent job changes | avg tenure < 1.5 years |
| `employment_gap` | Medium | Gaps in employment | > 1 year |
| `short_tenure` | Low/Medium | Very short job stays | < 6 months |
| `missing_experience` | High | No experience section | Section not found |
| `missing_education` | Low | No education section | Section not found |

#### Data Structure

```python
@dataclass
class RedFlag:
    flag_type: str          # Type of flag detected
    severity: str           # "high", "medium", "low"
    description: str        # Human-readable description
    candidate_name: str     # Affected candidate
    details: Dict[str, Any] # Additional context

@dataclass
class RedFlagsData:
    flags: List[RedFlag]                        # All detected flags
    candidates_with_flags: Dict[str, List[str]] # {candidate: [flag_types]}
    high_risk_candidates: List[str]             # Candidates with high severity flags
    clean_candidates: List[str]                 # Candidates with no flags
    summary: str                                # Human-readable summary
```

#### Output Format

```json
{
  "red_flags": {
    "flags": [
      {
        "flag_type": "job_hopping",
        "severity": "high",
        "description": "Frequent job changes (avg tenure: 0.8 years, 6 positions)",
        "candidate_name": "Juan García",
        "details": {"job_hopping_score": 0.85, "position_count": 6}
      }
    ],
    "candidates_with_flags": {"Juan García": ["job_hopping"]},
    "high_risk_candidates": ["Juan García"],
    "clean_candidates": ["Marco Rossi", "Ana López"],
    "summary": "✓ 2 clean | ⚠️ High-risk: Juan García"
  }
}
```

#### Example Questions For Red Flags

- "¿Hay candidatos con job hopping?"
- "¿Quién tiene gaps de empleo?"
- "¿Cuáles son los candidatos más estables?"
- "Dame los candidatos sin red flags"
- "¿Hay algún candidato de alto riesgo?"

---

### Timeline Module

**File**: `modules/timeline_module.py`

**Purpose**: Generates chronological career timelines showing progression and transitions.

#### Transition Types

| Type | Description | Icon |
|------|-------------|------|
| `promotion` | Moved to higher seniority | 📈 |
| `lateral` | Same level, different role | • |
| `company_change` | Changed company | • |

#### Data Structure

```python
@dataclass
class TimelineEntry:
    year_start: int             # Start year
    year_end: Optional[int]     # End year (None = Present)
    title: str                  # Job title
    company: str                # Company name
    is_current: bool            # Currently employed here
    duration_years: float       # Duration at position
    transition_type: str        # Type of career move

@dataclass
class CandidateTimeline:
    candidate_name: str                 # Candidate name
    cv_id: str                          # CV identifier
    entries: List[TimelineEntry]        # Career entries
    career_span_years: float            # Total career length
    total_companies: int                # Number of companies
    progression_score: float            # 0-100 (higher = better progression)
    current_role: Optional[str]         # Current position

@dataclass
class TimelineData:
    timelines: List[CandidateTimeline]  # All candidate timelines
    summary: str                         # Comparison summary
```

#### Output Format

```json
{
  "timeline": {
    "timelines": [
      {
        "candidate_name": "Marco Rossi",
        "cv_id": "cv_abc123",
        "career_span_years": 12,
        "progression_score": 85.0,
        "current_role": "Lead 3D Artist",
        "total_companies": 4,
        "entries": [
          {"year_start": 2012, "year_end": 2015, "title": "Junior 3D Artist", "company": "StartupVFX", "transition_type": ""},
          {"year_start": 2015, "year_end": 2018, "title": "3D Artist", "company": "ILM", "transition_type": "promotion"},
          {"year_start": 2018, "year_end": 2021, "title": "Senior 3D Artist", "company": "Weta", "transition_type": "promotion"},
          {"year_start": 2021, "year_end": null, "title": "Lead 3D Artist", "company": "Pixar", "transition_type": "promotion"}
        ]
      }
    ],
    "summary": "Best progression: Marco Rossi | Longest career: 12 years"
  }
}
```

#### Example Questions For Timeline

- "¿Quién tiene la mejor progresión de carrera?"
- "Muéstrame el timeline de Marco Rossi"
- "¿Qué candidatos han tenido promociones consistentes?"
- "Compara las trayectorias de los 3 mejores candidatos"
- "¿Quién ha trabajado más tiempo en la misma empresa?"

---

### Enriched Metadata (Indexing)

The enhanced modules rely on **enriched metadata** extracted during CV indexing:

| Field | Type | Description |
|-------|------|-------------|
| `total_experience_years` | float | Total years of professional experience |
| `seniority_level` | string | Detected level: junior/mid/senior/lead/executive |
| `current_role` | string | Current job title |
| `current_company` | string | Current employer |
| `has_faang_experience` | bool | Worked at Big Tech (Google, Meta, etc.) |
| `job_hopping_score` | float | 0-1 rotation index (higher = more changes) |
| `avg_tenure_years` | float | Average time at each position |
| `skills` | string[] | Extracted technical skills |
| `companies_worked` | string[] | List of companies |
| `employment_gaps` | tuple[] | Detected employment gaps |

#### Summary Chunk

Each CV gets a special **summary chunk** (index 0) containing:

```
CANDIDATE SUMMARY: Marco Rossi
Experience: 12 years | Seniority: senior
Current: Lead 3D Artist @ Pixar
Top Skills: Maya, ZBrush, Houdini, Python
Career Path: Junior Artist (2012) → 3D Artist (2015) → Senior (2018) → Lead (2021)
Companies: ILM, Weta Digital, Pixar
Red Flags: None | Job Hopping Score: 0.2 (stable)
```

---

### Updated File Structure

```
backend/app/services/output_processor/
├── __init__.py              # Exports OutputProcessor, OutputOrchestrator
├── orchestrator.py          # Main entry point, coordinates all processing
├── processor.py             # Invokes modules, builds StructuredOutput
├── validators.py            # Output validation utilities
└── modules/
    ├── __init__.py          # Exports all 8 modules
    ├── thinking_module.py   # :::thinking::: extraction
    ├── direct_answer_module.py  # Direct answer extraction
    ├── analysis_module.py   # Analysis section + fallback generation
    ├── table_module.py      # Table parsing + fallback generation
    ├── conclusion_module.py # :::conclusion::: extraction
    ├── gap_analysis_module.py   # NEW: Skills gap detection
    ├── red_flags_module.py      # NEW: Risk detection
    └── timeline_module.py       # NEW: Career trajectory

backend/app/models/
└── structured_output.py     # StructuredOutput (now includes gap_analysis, red_flags, timeline)
```

---

### Updated StructuredOutput Model

```python
@dataclass
class StructuredOutput:
    # Core components (always present)
    direct_answer: str
    raw_content: str
    
    # Optional core components
    thinking: Optional[str] = None
    analysis: Optional[str] = None
    table_data: Optional[TableData] = None
    conclusion: Optional[str] = None
    
    # Enhanced components (v5.1.1) - NEW
    gap_analysis: Optional[Dict[str, Any]] = None
    red_flags: Optional[Dict[str, Any]] = None
    timeline: Optional[Dict[str, Any]] = None
    
    # Metadata
    cv_references: List[CVReference] = field(default_factory=list)
    parsing_warnings: List[str] = field(default_factory=list)
    fallback_used: bool = False
```

---

### Frontend Usage (Enhanced)

```typescript
// Core components
<ThinkingDropdown content={response.structured_output.thinking} />
<DirectAnswer content={response.structured_output.direct_answer} />
<CandidateTable data={response.structured_output.table_data} />
<Conclusion content={response.structured_output.conclusion} />

// Enhanced components (v5.1.1)
{response.structured_output.gap_analysis && (
  <GapAnalysisCard data={response.structured_output.gap_analysis} />
)}
{response.structured_output.red_flags && (
  <RedFlagsAlert data={response.structured_output.red_flags} />
)}
{response.structured_output.timeline && (
  <CareerTimeline data={response.structured_output.timeline} />
)}
```

---

> **Version History**
> 
> | Version | Date | Changes |
> |---------|------|---------|
> | 5.0.0 | Jan 2026 | Initial modular architecture with 5 modules |
> | 5.1.0 | Jan 2026 | Added candidate deduplication, fallback analysis |
> | 5.1.1 | Jan 2026 | **NEW**: GapAnalysisModule, RedFlagsModule, TimelineModule, enriched metadata indexing |
