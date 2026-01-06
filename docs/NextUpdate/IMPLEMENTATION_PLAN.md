# Implementation Plan: CV Screener Architecture Transformation

## Document Purpose

This document provides the complete, realistic implementation plan to transform the current CV Screener from its existing state to the new Orchestration/Structures/Modules architecture defined in `ORCHESTRATION_STRUCTURES_MODULES.md`.

**Reference Document**: `docs/NextUpdate/ORCHESTRATION_STRUCTURES_MODULES.md`

---

# PART 1: CURRENT STATE ANALYSIS

## 1.1 Current Backend Structure

```
backend/app/services/output_processor/
├── orchestrator.py              ✅ EXISTS - Partially updated with structure routing
├── processor.py                 ✅ EXISTS - Legacy processor (to be deprecated)
│
├── structures/                  ✅ EXISTS - 3 structures implemented
│   ├── __init__.py              ✅ Exports 3 structures
│   ├── single_candidate_structure.py    ✅ IMPLEMENTED
│   ├── risk_assessment_structure.py     ✅ IMPLEMENTED
│   └── comparison_structure.py          ✅ IMPLEMENTED
│
└── modules/                     ⚠️ EXISTS - Needs fixes and expansion
    ├── __init__.py              ❌ BROKEN - imports non-existent risk_assessment_module
    ├── thinking_module.py       ✅ IMPLEMENTED
    ├── conclusion_module.py     ✅ IMPLEMENTED
    ├── direct_answer_module.py  ✅ IMPLEMENTED
    ├── analysis_module.py       ✅ IMPLEMENTED
    ├── table_module.py          ✅ IMPLEMENTED
    ├── risk_table_module.py     ✅ IMPLEMENTED (this is the correct file)
    ├── gap_analysis_module.py   ✅ IMPLEMENTED
    ├── red_flags_module.py      ✅ IMPLEMENTED
    └── timeline_module.py       ✅ IMPLEMENTED
```

## 1.2 Current Structures Status

| Structure | File | Status | Uses Modules |
|-----------|------|--------|--------------|
| SingleCandidateStructure | `single_candidate_structure.py` | ✅ Implemented | ThinkingModule, RiskTableModule, ConclusionModule + inline extraction |
| RiskAssessmentStructure | `risk_assessment_structure.py` | ✅ Implemented | ThinkingModule, RiskTableModule, ConclusionModule |
| ComparisonStructure | `comparison_structure.py` | ✅ Implemented | ThinkingModule, AnalysisModule, TableModule, ConclusionModule |
| SearchStructure | - | ❌ Not Implemented | - |
| JobMatchStructure | - | ❌ Not Implemented | - |
| RankingStructure | - | ❌ Not Implemented | - |
| TeamBuildStructure | - | ❌ Not Implemented | - |
| VerificationStructure | - | ❌ Not Implemented | - |
| SummaryStructure | - | ❌ Not Implemented | - |

## 1.3 Current Modules Status

| Module | File | Status | Used By |
|--------|------|--------|---------|
| ThinkingModule | `thinking_module.py` | ✅ | All structures |
| ConclusionModule | `conclusion_module.py` | ✅ | All structures |
| DirectAnswerModule | `direct_answer_module.py` | ✅ | Legacy processor |
| AnalysisModule | `analysis_module.py` | ✅ | ComparisonStructure |
| TableModule | `table_module.py` | ✅ | ComparisonStructure |
| RiskTableModule | `risk_table_module.py` | ✅ | SingleCandidate, RiskAssessment |
| GapAnalysisModule | `gap_analysis_module.py` | ✅ | Legacy (not in structures yet) |
| RedFlagsModule | `red_flags_module.py` | ✅ | Legacy (not in structures yet) |
| TimelineModule | `timeline_module.py` | ✅ | Legacy (not in structures yet) |
| HighlightsModule | - | ❌ Not Implemented | SingleCandidate (inline) |
| CareerModule | - | ❌ Not Implemented | SingleCandidate (inline) |
| SkillsModule | - | ❌ Not Implemented | SingleCandidate (inline) |
| CredentialsModule | - | ❌ Not Implemented | SingleCandidate (inline) |
| ResultsTableModule | - | ❌ Not Implemented | Search |
| RankingTableModule | - | ❌ Not Implemented | Ranking |
| ... (20+ more modules needed) | - | ❌ | - |

## 1.4 Current Query Type Detection

**File**: `backend/app/prompts/templates.py`

| Function | Purpose | Status |
|----------|---------|--------|
| `classify_query()` | Returns QueryType enum | ✅ Exists but incomplete |
| `classify_query_for_structure()` | Returns structure query_type string | ✅ Recently added |
| `detect_single_candidate_query()` | Detects single candidate queries | ✅ Exists |

**Current Query Types Detected**:
- `single_candidate` ✅
- `red_flags` → `risk_assessment` ⚠️ (naming inconsistency)
- `comparison` ✅
- `search` ✅ (but no SearchStructure)

---

# PART 2: CV INDEXING ANALYSIS

## 2.1 Current Indexing Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                     CV INDEXING PIPELINE                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  PDF Upload (routes_sessions.py)                                    │
│       │                                                             │
│       ▼                                                             │
│  extract_text_from_pdf() - pdf_service.py                          │
│       │                                                             │
│       ▼                                                             │
│  SmartChunkingService.chunk_cv() - smart_chunking_service.py       │
│       │                                                             │
│       ├─→ extract_structured_data()                                 │
│       │       ├─→ Extract candidate name                            │
│       │       ├─→ Parse positions (title, company, dates)           │
│       │       ├─→ Extract skills                                    │
│       │       └─→ Calculate metrics (experience, job hopping)       │
│       │                                                             │
│       ├─→ Create "summary" chunk (chunk 0)                          │
│       ├─→ Create "experience" chunks (1 per position)               │
│       ├─→ Create "skills" chunk                                     │
│       └─→ Create "full_cv" chunk                                    │
│       │                                                             │
│       ▼                                                             │
│  rag_service_v5.index_documents()                                  │
│       │                                                             │
│       ▼                                                             │
│  vector_store.add_chunks()                                         │
│       │                                                             │
│       ▼                                                             │
│  ChromaDB / Supabase pgvector                                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 2.2 Current Metadata Fields

| Field | Type | Extracted From | Used For |
|-------|------|----------------|----------|
| `candidate_name` | string | Name patterns | All queries |
| `cv_id` | string | Generated UUID | Identification |
| `filename` | string | Upload filename | Reference |
| `section_type` | string | Parser logic | Filtering |
| `total_experience_years` | float | Date calculations | Ranking, Risk |
| `current_role` | string | Most recent position | Display, Search |
| `current_company` | string | Most recent position | Display, Search |
| `job_hopping_score` | float | Tenure calculation | Risk Assessment |
| `avg_tenure_years` | float | Position durations | Risk Assessment |
| `position_count` | int | Count of positions | Risk Assessment |
| `employment_gaps_count` | int | Gap detection | Risk Assessment |
| `skills` | string | Skill extraction | Search, JobMatch |
| `seniority_level` | string | Experience inference | Ranking |
| `has_faang` | bool | Company matching | Comparison |
| `is_current` | bool | Position status | Timeline |
| `start_year` | int | Date parsing | Timeline |
| `end_year` | int | Date parsing | Timeline |
| `duration_years` | float | Calculation | Timeline |

## 2.3 Missing Metadata Fields (ENHANCEMENT REQUIRED)

| Field | Type | Extraction Method | Use Cases |
|-------|------|-------------------|-----------|
| `languages` | list[string] | Regex patterns for language names | TeamBuild, JobMatch, Search |
| `language_proficiency` | dict | "Native", "Fluent", "Intermediate" | TeamBuild, JobMatch |
| `education_level` | string | Degree patterns (PhD, Master, Bachelor) | Ranking, JobMatch |
| `education_institution` | string | University name extraction | Verification |
| `education_field` | string | Major/field of study | JobMatch |
| `graduation_year` | int | Date from education section | Verification |
| `certifications` | list[string] | Certification name patterns | Verification, JobMatch |
| `certification_dates` | dict | Expiry dates for certs | Verification |
| `hobbies` | list[string] | Hobbies/Interests section | TeamBuild (culture fit) |
| `volunteer_work` | list[string] | Volunteer section | TeamBuild |
| `publications` | int | Count of publications | Academic roles |
| `awards` | list[string] | Award patterns | Ranking |
| `location` | string | City/Country extraction | TeamBuild, Search |
| `remote_preference` | string | Remote/Hybrid/Onsite patterns | TeamBuild |
| `notice_period` | string | Notice period patterns | TeamBuild |
| `portfolio_url` | string | URL patterns | Verification |
| `linkedin_url` | string | LinkedIn URL pattern | Verification |
| `github_url` | string | GitHub URL pattern | Verification |

---

# PART 3: TEMPLATES NAMING TRANSFORMATION

## 3.1 Template Renaming Required

| Current Name | New Name | File Location |
|--------------|----------|---------------|
| `QUERY_TEMPLATE` | `COMPARISON_TEMPLATE` | `templates.py:~235` |
| `QUERY_TEMPLATE_CONCISE` | `COMPARISON_TEMPLATE_CONCISE` | `templates.py:~287` |
| `QUERY_TEMPLATE_JSON` | `COMPARISON_TEMPLATE_JSON` | `templates.py:~300` |

## 3.2 Function Renaming Required

| Current Name | New Name | File Location |
|--------------|----------|---------------|
| `build_query_prompt()` | `build_comparison_prompt()` | `templates.py:~1682` |
| `PromptBuilder.build_query_prompt()` | `PromptBuilder.build_comparison_prompt()` | `templates.py:~1150` |

## 3.3 New Templates Required

| Template Name | Structure | Purpose |
|---------------|-----------|---------|
| `SEARCH_TEMPLATE` | SearchStructure | Search results with match scores |
| `TEAM_BUILD_TEMPLATE` | TeamBuildStructure | Team composition prompts |

## 3.4 Files That Reference QUERY_TEMPLATE (Must Update)

| File | References | Action |
|------|------------|--------|
| `templates.py` | Definition + usage | Rename |
| `rag_service_v5.py` | `build_query_prompt()` calls | Update calls |
| `tests/test_rag_service.py` | Test cases | Update tests |
| `docs/RAG_WORKFLOW.md` | Documentation | Update docs |
| `docs/ARCHITECTURE_MODULES.md` | Documentation | Update docs |

---

# PART 4: IMPLEMENTATION PHASES

## PHASE 0: CRITICAL FIXES (Day 1)

### Objective
Make current code work without runtime errors.

### Tasks

#### 0.1 Fix modules/__init__.py Import
- **File**: `backend/app/services/output_processor/modules/__init__.py`
- **Issue**: Line 23 imports from `risk_assessment_module` which doesn't exist
- **Fix**: Change to import from `risk_table_module`

```
BEFORE:
from .risk_assessment_module import RiskAssessmentModule, RiskAssessmentData, RiskFactor

AFTER:
from .risk_table_module import RiskTableModule, RiskAssessmentData, RiskFactor
```

- **Also update __all__**:
```
BEFORE: "RiskAssessmentModule"
AFTER:  "RiskTableModule"
```

#### 0.2 Verify Orchestrator Routing
- [ ] Test `single_candidate` query → SingleCandidateStructure
- [ ] Test `risk_assessment` query → RiskAssessmentStructure
- [ ] Test `comparison` query → ComparisonStructure
- [ ] Verify no runtime exceptions

#### 0.3 Fix Enriched Metadata Flow
- **Issue**: Logs show `[ENRICHED_METADATA] No chunk with enriched metadata found!`
- **Cause**: Chunks don't have `job_hopping_score` etc. when retrieved
- **Files to check**:
  - `smart_chunking_service.py` - Verify metadata is added
  - `vector_store.py` - Verify metadata is stored
  - `rag_service_v5.py` - Verify metadata is preserved in retrieval

### Acceptance Criteria Phase 0
- [ ] No import errors when starting server
- [ ] All 3 existing structures route correctly
- [ ] RiskTableModule receives enriched metadata
- [ ] No `[ENRICHED_METADATA] No chunk` warnings

---

## PHASE 1: CONSOLIDATE & CLEAN (Days 2-4)

### Objective
Extract inline code into proper modules, rename templates for consistency.

### Tasks

#### 1.1 Extract SingleCandidateStructure Inline Methods into Modules

##### 1.1.1 Create HighlightsModule
- **Create file**: `modules/highlights_module.py`
- **Extract from**: `SingleCandidateStructure._extract_highlights()`
- **Interface**:
```python
class HighlightsModule:
    def extract(self, llm_output: str) -> List[Dict[str, str]]
    def format(self, highlights: List[Dict[str, str]]) -> str
```

##### 1.1.2 Create CareerModule
- **Create file**: `modules/career_module.py`
- **Extract from**: `SingleCandidateStructure._extract_career()`
- **Interface**:
```python
class CareerModule:
    def extract(self, llm_output: str) -> List[Dict[str, str]]
    def format(self, career: List[Dict[str, str]]) -> str
```

##### 1.1.3 Create SkillsModule
- **Create file**: `modules/skills_module.py`
- **Extract from**: `SingleCandidateStructure._extract_skills()`
- **Interface**:
```python
class SkillsModule:
    def extract(self, llm_output: str) -> List[Dict[str, str]]
    def format(self, skills: List[Dict[str, str]]) -> str
```

##### 1.1.4 Create CredentialsModule
- **Create file**: `modules/credentials_module.py`
- **Extract from**: `SingleCandidateStructure._extract_credentials()`
- **Interface**:
```python
class CredentialsModule:
    def extract(self, llm_output: str) -> List[str]
    def format(self, credentials: List[str]) -> str
```

#### 1.2 Update SingleCandidateStructure to Use New Modules
- **File**: `structures/single_candidate_structure.py`
- [ ] Import new modules
- [ ] Replace `self._extract_highlights()` with `self.highlights_module.extract()`
- [ ] Replace `self._extract_career()` with `self.career_module.extract()`
- [ ] Replace `self._extract_skills()` with `self.skills_module.extract()`
- [ ] Replace `self._extract_credentials()` with `self.credentials_module.extract()`
- [ ] Remove inline `_extract_*` methods

#### 1.3 Update modules/__init__.py
- [ ] Add exports for new modules:
  - `HighlightsModule`
  - `CareerModule`
  - `SkillsModule`
  - `CredentialsModule`

#### 1.4 Rename Templates
- **File**: `backend/app/prompts/templates.py`

##### 1.4.1 Rename QUERY_TEMPLATE
- [ ] Find and replace `QUERY_TEMPLATE` → `COMPARISON_TEMPLATE`
- [ ] Find and replace `QUERY_TEMPLATE_CONCISE` → `COMPARISON_TEMPLATE_CONCISE`
- [ ] Find and replace `QUERY_TEMPLATE_JSON` → `COMPARISON_TEMPLATE_JSON`

##### 1.4.2 Rename build_query_prompt
- [ ] Rename `build_query_prompt()` function → `build_comparison_prompt()`
- [ ] Rename `PromptBuilder.build_query_prompt()` → `PromptBuilder.build_comparison_prompt()`
- [ ] Keep old function name as deprecated alias for backward compatibility

##### 1.4.3 Update All References
- [ ] Update `rag_service_v5.py` calls to use new function name
- [ ] Update test files
- [ ] Update documentation files

#### 1.5 Clean Up Query Type Naming
- [ ] Ensure `red_flags` query type maps to `risk_assessment` structure
- [ ] Update `classify_query_for_structure()` to return consistent names

### Acceptance Criteria Phase 1
- [ ] All 4 new modules created and working
- [ ] SingleCandidateStructure uses modules instead of inline methods
- [ ] All templates renamed without breaking changes
- [ ] No deprecated warnings in logs
- [ ] All existing tests pass

---

## PHASE 2: INDEXING ENHANCEMENT (Days 5-7)

### Objective
Enhance CV indexing to extract additional metadata for new structures.

### Tasks

#### 2.1 Update SmartChunkingService

##### 2.1.1 Add Language Extraction
- **File**: `backend/app/services/smart_chunking_service.py`
- **Method**: `_extract_languages()`
- **Patterns to detect**:
```python
LANGUAGE_PATTERNS = [
    r'(?:languages?|idiomas?)[\s:]+([^\n]+)',
    r'(?:native|fluent|intermediate|basic)\s+(?:in\s+)?(\w+)',
    r'(English|Spanish|French|German|Chinese|Japanese|Portuguese|Italian|Russian|Arabic|Hindi|Korean)[\s,]*(native|fluent|intermediate|basic)?',
]
```

##### 2.1.2 Add Education Extraction
- **Method**: `_extract_education()`
- **Fields to extract**:
  - `education_level`: PhD, Master, Bachelor, Associate, High School
  - `education_institution`: University/college name
  - `education_field`: Major/field of study
  - `graduation_year`: Year of graduation

##### 2.1.3 Add Certifications Extraction
- **Method**: `_extract_certifications()`
- **Patterns**:
```python
CERT_PATTERNS = [
    r'(?:certified|certification|certificate)[\s:]+([^\n,]+)',
    r'(AWS|Azure|GCP|PMP|CISSP|CCNA|MCSE|CPA|CFA|PHR|SHRM)[\s-]*([\w\s]+)?',
]
```

##### 2.1.4 Add Hobbies/Interests Extraction
- **Method**: `_extract_hobbies()`
- **Section headers**: "Hobbies", "Interests", "Activities", "Personal"

##### 2.1.5 Add Location Extraction
- **Method**: `_extract_location()`
- **Patterns**: City, State/Province, Country

##### 2.1.6 Add URL Extraction
- **Method**: `_extract_urls()`
- **Fields**:
  - `linkedin_url`
  - `github_url`
  - `portfolio_url`

#### 2.2 Update Chunk Metadata Structure

##### 2.2.1 Update Summary Chunk Metadata
```python
"metadata": {
    # Existing fields
    "section_type": "summary",
    "candidate_name": ...,
    "current_role": ...,
    "current_company": ...,
    "total_experience_years": ...,
    "job_hopping_score": ...,
    "avg_tenure_years": ...,
    "employment_gaps_count": ...,
    "position_count": ...,
    
    # NEW FIELDS
    "languages": "English,Spanish,French",  # comma-separated
    "language_primary": "English",
    "education_level": "Master",
    "education_field": "Computer Science",
    "education_institution": "MIT",
    "certifications": "AWS Solutions Architect,PMP",
    "location": "San Francisco, CA",
    "linkedin_url": "https://linkedin.com/in/...",
    "github_url": "https://github.com/...",
    "hobbies": "hiking,photography,chess",
}
```

#### 2.3 Update Vector Store

##### 2.3.1 Update add_chunks() Method
- **File**: `backend/app/services/vector_store.py`
- [ ] Add handling for new metadata fields
- [ ] Ensure ChromaDB-compatible types (no lists, convert to comma-separated)

##### 2.3.2 Add New Filter Options
- [ ] Add `filter_by_language()` helper
- [ ] Add `filter_by_education()` helper
- [ ] Add `filter_by_certification()` helper

#### 2.4 Update Existing CVs (Migration Script)

##### 2.4.1 Create Re-indexing Script
- **File**: `scripts/reindex_with_enhanced_metadata.py`
- **Purpose**: Re-process existing CVs with new metadata extraction
- **Steps**:
  1. List all existing CV PDFs
  2. Re-extract text
  3. Re-chunk with new SmartChunkingService
  4. Update vector store entries

### Acceptance Criteria Phase 2
- [ ] New CVs indexed with all new metadata fields
- [ ] Language extraction working (tested with multilingual CVs)
- [ ] Education extraction working
- [ ] Certifications extraction working
- [ ] Hobbies extraction working
- [ ] Re-indexing script tested and documented

---

## PHASE 3: SEARCH & RANKING STRUCTURES (Days 8-11)

### Objective
Implement SearchStructure and RankingStructure with their modules.

### Tasks

#### 3.1 Create SearchStructure

##### 3.1.1 Create ResultsTableModule
- **File**: `modules/results_table_module.py`
- **Purpose**: Generate search results table with match scores
- **Interface**:
```python
@dataclass
class SearchResult:
    candidate_name: str
    cv_id: str
    match_score: float
    matching_skills: List[str]
    experience_years: float
    current_role: str

class ResultsTableModule:
    def extract(self, chunks: List[Dict], query: str) -> List[SearchResult]
    def format(self, results: List[SearchResult]) -> str
```

##### 3.1.2 Create SearchStructure
- **File**: `structures/search_structure.py`
- **Modules used**:
  - ThinkingModule
  - DirectAnswerModule
  - ResultsTableModule
  - ConclusionModule

##### 3.1.3 Create SEARCH_TEMPLATE
- **File**: `templates.py`
- **Purpose**: LLM prompt for search queries

#### 3.2 Create RankingStructure

##### 3.2.1 Create RankingCriteriaModule
- **File**: `modules/ranking_criteria_module.py`
- **Purpose**: Define and extract ranking criteria from query
- **Interface**:
```python
@dataclass
class RankingCriterion:
    name: str
    weight: float
    description: str

class RankingCriteriaModule:
    def extract(self, query: str, llm_output: str) -> List[RankingCriterion]
    def format(self, criteria: List[RankingCriterion]) -> str
```

##### 3.2.2 Create RankingTableModule
- **File**: `modules/ranking_table_module.py`
- **Purpose**: Generate ranked candidate table
- **Interface**:
```python
@dataclass
class RankedCandidate:
    rank: int
    candidate_name: str
    cv_id: str
    overall_score: float
    criterion_scores: Dict[str, float]

class RankingTableModule:
    def extract(self, llm_output: str, chunks: List[Dict]) -> List[RankedCandidate]
    def format(self, ranked: List[RankedCandidate]) -> str
```

##### 3.2.3 Create TopPickModule
- **File**: `modules/top_pick_module.py`
- **Purpose**: Highlight #1 candidate with detailed justification
- **Interface**:
```python
class TopPickModule:
    def extract(self, ranked: List[RankedCandidate], llm_output: str) -> Dict
    def format(self, top_pick: Dict) -> str
```

##### 3.2.4 Create RankingStructure
- **File**: `structures/ranking_structure.py`
- **Modules used**:
  - ThinkingModule
  - RankingCriteriaModule
  - RankingTableModule
  - TopPickModule
  - ConclusionModule

#### 3.3 Update Orchestrator
- [ ] Add routing for `search` → SearchStructure
- [ ] Add routing for `ranking` → RankingStructure

#### 3.4 Update Query Classification
- [ ] Ensure `classify_query_for_structure()` detects ranking queries
- [ ] Add patterns: "top 5", "rank", "best candidates", "order by"

### Acceptance Criteria Phase 3
- [ ] SearchStructure returns formatted results table
- [ ] RankingStructure returns ranked list with scores
- [ ] TopPickModule highlights best candidate
- [ ] Both structures accessible via orchestrator routing
- [ ] Query type detection works for search and ranking

---

## PHASE 4: JOB MATCHING STRUCTURE (Days 12-14)

### Objective
Implement JobMatchStructure for matching candidates to job descriptions.

### Tasks

#### 4.1 Create RequirementsModule
- **File**: `modules/requirements_module.py`
- **Purpose**: Extract and categorize requirements from job description
- **Interface**:
```python
@dataclass
class Requirement:
    name: str
    category: str  # "required", "preferred", "nice_to_have"
    type: str      # "skill", "experience", "education", "certification"

class RequirementsModule:
    def extract(self, job_description: str) -> List[Requirement]
    def format(self, requirements: List[Requirement]) -> str
```

#### 4.2 Create MatchScoreModule
- **File**: `modules/match_score_module.py`
- **Purpose**: Calculate match percentage between candidate and requirements
- **Interface**:
```python
@dataclass
class CandidateMatch:
    candidate_name: str
    cv_id: str
    overall_match: float  # 0-100%
    met_requirements: List[str]
    missing_requirements: List[str]
    partial_requirements: List[str]

class MatchScoreModule:
    def calculate(self, requirements: List[Requirement], chunks: List[Dict]) -> List[CandidateMatch]
    def format(self, matches: List[CandidateMatch]) -> str
```

#### 4.3 Create JobMatchStructure
- **File**: `structures/job_match_structure.py`
- **Modules used**:
  - ThinkingModule
  - RequirementsModule
  - MatchScoreModule
  - GapAnalysisModule (existing, reused)
  - ConclusionModule

#### 4.4 Enhance JOB_MATCH_TEMPLATE
- **File**: `templates.py`
- [ ] Update template to request structured output
- [ ] Add requirement categorization instructions
- [ ] Add match scoring instructions

#### 4.5 Update Orchestrator
- [ ] Add routing for `job_match` → JobMatchStructure

### Acceptance Criteria Phase 4
- [ ] RequirementsModule extracts JD requirements correctly
- [ ] MatchScoreModule calculates accurate match percentages
- [ ] GapAnalysisModule shows what candidates are missing
- [ ] JobMatchStructure produces actionable output
- [ ] Job match queries route correctly

---

## PHASE 5: TEAM BUILDING STRUCTURE (Days 15-18)

### Objective
Implement TeamBuildStructure for composing teams.

### Tasks

#### 5.1 Create TeamRequirementsModule
- **File**: `modules/team_requirements_module.py`
- **Purpose**: Define roles needed for team
- **Interface**:
```python
@dataclass
class TeamRole:
    role_name: str
    required_skills: List[str]
    seniority: str
    count: int

class TeamRequirementsModule:
    def extract(self, query: str, llm_output: str) -> List[TeamRole]
    def format(self, roles: List[TeamRole]) -> str
```

#### 5.2 Create TeamCompositionModule
- **File**: `modules/team_composition_module.py`
- **Purpose**: Assign candidates to team roles
- **Interface**:
```python
@dataclass
class TeamAssignment:
    role: TeamRole
    candidate_name: str
    cv_id: str
    fit_score: float
    strengths: List[str]

class TeamCompositionModule:
    def compose(self, roles: List[TeamRole], chunks: List[Dict]) -> List[TeamAssignment]
    def format(self, assignments: List[TeamAssignment]) -> str
```

#### 5.3 Create SkillCoverageModule
- **File**: `modules/skill_coverage_module.py`
- **Purpose**: Analyze team skill coverage
- **Interface**:
```python
@dataclass
class SkillCoverage:
    skill: str
    covered_by: List[str]  # candidate names
    coverage_level: str    # "strong", "moderate", "weak", "none"

class SkillCoverageModule:
    def analyze(self, assignments: List[TeamAssignment]) -> List[SkillCoverage]
    def format(self, coverage: List[SkillCoverage]) -> str
```

#### 5.4 Create TeamRiskModule
- **File**: `modules/team_risk_module.py`
- **Purpose**: Identify team composition risks
- **Interface**:
```python
@dataclass
class TeamRisk:
    risk_type: str      # "skill_gap", "single_point_of_failure", "seniority_imbalance"
    severity: str       # "high", "medium", "low"
    description: str
    mitigation: str

class TeamRiskModule:
    def analyze(self, assignments: List[TeamAssignment], coverage: List[SkillCoverage]) -> List[TeamRisk]
    def format(self, risks: List[TeamRisk]) -> str
```

#### 5.5 Create TeamBuildStructure
- **File**: `structures/team_build_structure.py`
- **Modules used**:
  - ThinkingModule
  - TeamRequirementsModule
  - TeamCompositionModule
  - SkillCoverageModule
  - TeamRiskModule
  - ConclusionModule

#### 5.6 Create TEAM_BUILD_TEMPLATE
- **File**: `templates.py`
- **Purpose**: LLM prompt for team building queries

#### 5.7 Update Orchestrator
- [ ] Add routing for `team_build` → TeamBuildStructure

### Acceptance Criteria Phase 5
- [ ] Team roles extracted from query
- [ ] Candidates assigned to appropriate roles
- [ ] Skill coverage analysis shows gaps
- [ ] Team risks identified with mitigations
- [ ] Complete team composition output

---

## PHASE 6: VERIFICATION & SUMMARY STRUCTURES (Days 19-22)

### Objective
Implement VerificationStructure and SummaryStructure.

### Tasks

#### 6.1 Create VerificationStructure Modules

##### 6.1.1 Create ClaimModule
- **File**: `modules/claim_module.py`
- **Purpose**: Parse claim to verify
```python
@dataclass
class Claim:
    subject: str        # candidate name
    claim_type: str     # "experience", "certification", "education", "skill"
    claim_value: str    # what to verify

class ClaimModule:
    def parse(self, query: str) -> Claim
    def format(self, claim: Claim) -> str
```

##### 6.1.2 Create EvidenceModule
- **File**: `modules/evidence_module.py`
- **Purpose**: Find evidence in CV
```python
@dataclass
class Evidence:
    source: str         # chunk reference
    excerpt: str        # relevant text
    relevance: float    # how relevant to claim

class EvidenceModule:
    def find(self, claim: Claim, chunks: List[Dict]) -> List[Evidence]
    def format(self, evidence: List[Evidence]) -> str
```

##### 6.1.3 Create VerdictModule
- **File**: `modules/verdict_module.py`
- **Purpose**: Issue verification verdict
```python
@dataclass
class Verdict:
    status: str         # "CONFIRMED", "PARTIAL", "NOT_FOUND", "CONTRADICTED"
    confidence: float
    explanation: str

class VerdictModule:
    def evaluate(self, claim: Claim, evidence: List[Evidence]) -> Verdict
    def format(self, verdict: Verdict) -> str
```

##### 6.1.4 Create VerificationStructure
- **File**: `structures/verification_structure.py`

#### 6.2 Create SummaryStructure Modules

##### 6.2.1 Create TalentPoolModule
- **File**: `modules/talent_pool_module.py`
- **Purpose**: Pool statistics
```python
@dataclass
class PoolStats:
    total_candidates: int
    experience_distribution: Dict[str, int]  # {"junior": 5, "mid": 10, "senior": 3}
    location_distribution: Dict[str, int]

class TalentPoolModule:
    def analyze(self, chunks: List[Dict]) -> PoolStats
    def format(self, stats: PoolStats) -> str
```

##### 6.2.2 Create SkillDistributionModule
- **File**: `modules/skill_distribution_module.py`
```python
@dataclass
class SkillStats:
    skill: str
    candidate_count: int
    percentage: float

class SkillDistributionModule:
    def analyze(self, chunks: List[Dict]) -> List[SkillStats]
    def format(self, stats: List[SkillStats]) -> str
```

##### 6.2.3 Create ExperienceDistributionModule
- **File**: `modules/experience_distribution_module.py`
```python
class ExperienceDistributionModule:
    def analyze(self, chunks: List[Dict]) -> Dict[str, Any]
    def format(self, distribution: Dict) -> str
```

##### 6.2.4 Create SummaryStructure
- **File**: `structures/summary_structure.py`

#### 6.3 Update Orchestrator
- [ ] Add routing for `verification` → VerificationStructure
- [ ] Add routing for `summary` → SummaryStructure

### Acceptance Criteria Phase 6
- [ ] Claims parsed correctly from queries
- [ ] Evidence found and cited
- [ ] Verdicts issued with confidence levels
- [ ] Pool summary shows all statistics
- [ ] Skill and experience distributions calculated

---

## PHASE 7: FRONTEND INTEGRATION (Days 23-26)

### Objective
Update frontend to render all structure types correctly.

### Tasks

#### 7.1 Create Reusable Frontend Components

##### 7.1.1 Create RiskAssessmentTable Component
- **File**: `frontend/src/components/output/modules/RiskAssessmentTable.jsx`
- **Props**: `{ data: { factors: [...] } }`
- **Used by**: SingleCandidateProfile, RiskAssessmentProfile

##### 7.1.2 Create RankingTable Component
- **File**: `frontend/src/components/output/modules/RankingTable.jsx`
- **Props**: `{ ranked: [...], criteria: [...] }`

##### 7.1.3 Create MatchScoreCard Component
- **File**: `frontend/src/components/output/modules/MatchScoreCard.jsx`
- **Props**: `{ match: { overall, met, missing } }`

##### 7.1.4 Create TeamCompositionView Component
- **File**: `frontend/src/components/output/modules/TeamCompositionView.jsx`
- **Props**: `{ team: { roles, assignments, coverage, risks } }`

##### 7.1.5 Create VerificationResult Component
- **File**: `frontend/src/components/output/modules/VerificationResult.jsx`
- **Props**: `{ claim, evidence, verdict }`

##### 7.1.6 Create PoolSummary Component
- **File**: `frontend/src/components/output/modules/PoolSummary.jsx`
- **Props**: `{ stats: {...} }`

#### 7.2 Create New Profile Views

##### 7.2.1 Create SearchResultsView
- **File**: `frontend/src/components/output/SearchResultsView.jsx`

##### 7.2.2 Create RankingView
- **File**: `frontend/src/components/output/RankingView.jsx`

##### 7.2.3 Create JobMatchView
- **File**: `frontend/src/components/output/JobMatchView.jsx`

##### 7.2.4 Create TeamBuildView
- **File**: `frontend/src/components/output/TeamBuildView.jsx`

##### 7.2.5 Create VerificationView
- **File**: `frontend/src/components/output/VerificationView.jsx`

##### 7.2.6 Create SummaryView
- **File**: `frontend/src/components/output/SummaryView.jsx`

#### 7.3 Update StructuredOutputRenderer
- **File**: `frontend/src/components/output/StructuredOutputRenderer.jsx`
- [ ] Add routing for `structure_type`:
```javascript
switch (structuredOutput.structure_type) {
    case "single_candidate": return <SingleCandidateProfile {...} />;
    case "risk_assessment": return <RiskAssessmentProfile {...} />;
    case "comparison": return <ComparisonView {...} />;
    case "search": return <SearchResultsView {...} />;
    case "ranking": return <RankingView {...} />;
    case "job_match": return <JobMatchView {...} />;
    case "team_build": return <TeamBuildView {...} />;
    case "verification": return <VerificationView {...} />;
    case "summary": return <SummaryView {...} />;
    default: return <StandardResponse {...} />;
}
```

#### 7.4 Update Parsers
- **File**: `frontend/src/components/output/singleCandidateParser.js`
- [ ] Update to use `structure_type` from backend
- [ ] Remove frontend-side structure detection (backend handles this now)

### Acceptance Criteria Phase 7
- [ ] All 9 structure types render correctly in frontend
- [ ] Reusable components work across multiple views
- [ ] No frontend console errors
- [ ] Responsive design maintained
- [ ] Loading states handled

---

## PHASE 8: TESTING & DOCUMENTATION (Days 27-30)

### Objective
Comprehensive testing and documentation update.

### Tasks

#### 8.1 Unit Tests

##### 8.1.1 Module Unit Tests
- [ ] Test each new module's `extract()` method
- [ ] Test each new module's `format()` method
- [ ] Test edge cases (empty input, malformed data)

##### 8.1.2 Structure Unit Tests
- [ ] Test each structure's `assemble()` method
- [ ] Test module composition
- [ ] Test output format

##### 8.1.3 Orchestrator Tests
- [ ] Test routing for all 9 query types
- [ ] Test fallback behavior
- [ ] Test error handling

#### 8.2 Integration Tests

##### 8.2.1 End-to-End Query Tests
- [ ] Test single_candidate flow
- [ ] Test risk_assessment flow
- [ ] Test comparison flow
- [ ] Test search flow
- [ ] Test ranking flow
- [ ] Test job_match flow
- [ ] Test team_build flow
- [ ] Test verification flow
- [ ] Test summary flow

##### 8.2.2 Frontend Integration Tests
- [ ] Test each view renders correctly
- [ ] Test error states
- [ ] Test loading states

#### 8.3 Documentation Updates

##### 8.3.1 Update ARCHITECTURE_MODULES.md
- [ ] Add new structures
- [ ] Add new modules
- [ ] Update diagrams

##### 8.3.2 Update RAG_WORKFLOW.md
- [ ] Update template references
- [ ] Update flow diagrams

##### 8.3.3 Create API Documentation
- [ ] Document structure_type responses
- [ ] Document query type detection

##### 8.3.4 Update README.md
- [ ] Add new features section
- [ ] Update architecture overview

### Acceptance Criteria Phase 8
- [ ] 80%+ code coverage on new code
- [ ] All integration tests pass
- [ ] Documentation complete and accurate
- [ ] No known bugs

---

# PART 5: COMPLETE FILE CHECKLIST

## Files to CREATE

### Structures (6 new)
- [ ] `structures/search_structure.py`
- [ ] `structures/job_match_structure.py`
- [ ] `structures/ranking_structure.py`
- [ ] `structures/team_build_structure.py`
- [ ] `structures/verification_structure.py`
- [ ] `structures/summary_structure.py`

### Modules (20+ new)
- [ ] `modules/highlights_module.py`
- [ ] `modules/career_module.py`
- [ ] `modules/skills_module.py`
- [ ] `modules/credentials_module.py`
- [ ] `modules/results_table_module.py`
- [ ] `modules/ranking_table_module.py`
- [ ] `modules/ranking_criteria_module.py`
- [ ] `modules/top_pick_module.py`
- [ ] `modules/requirements_module.py`
- [ ] `modules/match_score_module.py`
- [ ] `modules/team_requirements_module.py`
- [ ] `modules/team_composition_module.py`
- [ ] `modules/skill_coverage_module.py`
- [ ] `modules/team_risk_module.py`
- [ ] `modules/claim_module.py`
- [ ] `modules/evidence_module.py`
- [ ] `modules/verdict_module.py`
- [ ] `modules/talent_pool_module.py`
- [ ] `modules/skill_distribution_module.py`
- [ ] `modules/experience_distribution_module.py`

### Frontend Components (12 new)
- [ ] `components/output/modules/RiskAssessmentTable.jsx`
- [ ] `components/output/modules/RankingTable.jsx`
- [ ] `components/output/modules/MatchScoreCard.jsx`
- [ ] `components/output/modules/TeamCompositionView.jsx`
- [ ] `components/output/modules/VerificationResult.jsx`
- [ ] `components/output/modules/PoolSummary.jsx`
- [ ] `components/output/SearchResultsView.jsx`
- [ ] `components/output/RankingView.jsx`
- [ ] `components/output/JobMatchView.jsx`
- [ ] `components/output/TeamBuildView.jsx`
- [ ] `components/output/VerificationView.jsx`
- [ ] `components/output/SummaryView.jsx`

### Scripts (1 new)
- [ ] `scripts/reindex_with_enhanced_metadata.py`

## Files to MODIFY

### Backend
- [ ] `modules/__init__.py` - Fix imports, add new exports
- [ ] `structures/__init__.py` - Add new structure exports
- [ ] `orchestrator.py` - Add routing for all 9 structures
- [ ] `templates.py` - Rename templates, add new templates
- [ ] `smart_chunking_service.py` - Add new metadata extraction
- [ ] `vector_store.py` - Handle new metadata fields
- [ ] `rag_service_v5.py` - Update function calls

### Frontend
- [ ] `StructuredOutputRenderer.jsx` - Add structure_type routing
- [ ] `singleCandidateParser.js` - Simplify (backend does detection)

### Documentation
- [ ] `docs/ARCHITECTURE_MODULES.md`
- [ ] `docs/RAG_WORKFLOW.md`
- [ ] `README.md`

## Files to DELETE

- [ ] `modules/risk_assessment_module.py` (if exists, already renamed)

---

# PART 6: TIMELINE SUMMARY

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| Phase 0 | Day 1 | Critical fixes, no runtime errors |
| Phase 1 | Days 2-4 | 4 new modules, templates renamed |
| Phase 2 | Days 5-7 | Enhanced indexing with 15+ new metadata fields |
| Phase 3 | Days 8-11 | SearchStructure, RankingStructure |
| Phase 4 | Days 12-14 | JobMatchStructure |
| Phase 5 | Days 15-18 | TeamBuildStructure |
| Phase 6 | Days 19-22 | VerificationStructure, SummaryStructure |
| Phase 7 | Days 23-26 | Frontend integration (12 new components) |
| Phase 8 | Days 27-30 | Testing & documentation |

**Total Estimated Duration**: 30 days

---

# PART 7: RISK MITIGATION

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Import errors after renaming | High | High | Grep all references before renaming |
| Frontend not rendering new structures | Medium | High | Test each structure individually |
| Query misclassification | Medium | Medium | Comprehensive keyword patterns + fallbacks |
| Metadata extraction failures | Medium | Medium | Graceful degradation, default values |
| Performance degradation | Low | Medium | Profile after each phase |
| Breaking existing functionality | Medium | High | Maintain backward compatibility aliases |

---

# PART 8: SUCCESS METRICS

| Metric | Target |
|--------|--------|
| Query type routing accuracy | 95%+ |
| All 9 structures rendering correctly | 100% |
| Module reuse (avg modules per structure) | 3+ |
| New metadata fields extracted | 15+ |
| Code coverage on new code | 80%+ |
| Frontend render errors | 0 |
| Response time degradation | < 10% |
| User satisfaction (if measurable) | Improved |
