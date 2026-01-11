# CV Screener Architecture - Orchestration, Structures & Modules

> **Last Updated:** January 2026 - Full implementation complete with **10 Structures** (9 rigid + 1 Adaptive) + **29+ Modules** + **6 Adaptive Modules** + Conversational Context (v9.0)

---

## 🎨 Interactive Visualization

**Open [`architecture-visualization.html`](./architecture-visualization.html) in a browser** to see an interactive D3.js visualization of the complete architecture with:
- Drag & zoom functionality
- Click nodes to see module details
- Filter buttons to focus on specific structures
- Visual distinction for shared modules

---

## 📊 Quick Stats

| Component | Count | Description |
|-----------|-------|-------------|
| **Structures** | 10 | 9 rigid + 1 Adaptive (dynamic schema-less) |
| **Modules** | 29+ | Reusable extraction/formatting components |
| **Adaptive Modules** | 6 | Dynamic schema-less components |
| **Query Types** | 10 | Including `adaptive` for dynamic queries |
| **Reusable Modules** | 6 | Shared across multiple structures |

---

## Architecture Overview

```
USER QUERY → ORCHESTRATOR → STRUCTURE → MODULES → OUTPUT
```

**Key Principles:**
- **Orchestrator**: Routes queries to the appropriate Structure based on `query_type`
- **Structures**: Complete output assemblers that combine multiple Modules
- **Modules**: Reusable components that can be shared across Structures
- **Query Types**: Classification that determines which Structure to use

---

## 🗺️ Complete Architecture Map

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                    ORCHESTRATOR                                       │
│                               (orchestrator.py)                                      │
│     Receives: raw_llm_output, chunks, query, query_type, conversation_history        │
│     Returns:  StructuredOutput + formatted_answer                                    │
└────────────────────────────────────────┬────────────────────────────────────────────┘
                                         │
         ┌───────────┬───────────┬───────┼───────┬───────────┬───────────┬───────────┐
         │           │           │       │       │           │           │           │
         ▼           ▼           ▼       ▼       ▼           ▼           ▼           ▼
    ┌─────────┐┌─────────┐┌──────────┐┌──────┐┌───────┐┌─────────┐┌──────┐┌──────┐┌───────┐
    │ single  ││  risk   ││comparison││search││ranking││job_match││ team ││verify││summary│
    │candidate││ assess  ││          ││      ││       ││         ││build ││      ││       │
    └────┬────┘└────┬────┘└────┬─────┘└──┬───┘└───┬───┘└────┬────┘└──┬───┘└──┬───┘└───┬───┘
         │          │          │         │        │         │        │       │        │
         ▼          ▼          ▼         ▼        ▼         ▼        ▼       ▼        ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              STRUCTURES (10)                                            │
├─────────────────────────────────────────────────────────────────────────────────────┤
│ 1. SingleCandidateStructure  │ 2. RiskAssessmentStructure  │ 3. ComparisonStructure     │
│ 4. SearchStructure           │ 5. RankingStructure         │ 6. JobMatchStructure       │
│ 7. TeamBuildStructure        │ 8. VerificationStructure    │ 9. SummaryStructure        │
│ 10. ⭐ AdaptiveStructureBuilder (dynamic schema-less output)                              │
└─────────────────────────────────────────────────────────────────────────────────────┘────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                   MODULES (29+)                                          │
├─────────────────────────────────────────────────────────────────────────────────────┤
│  CORE (4):     ThinkingModule, ConclusionModule, AnalysisModule, DirectAnswerModule     │
│  PROFILE (4):  HighlightsModule, CareerModule, SkillsModule, CredentialsModule          │
│  TABLES (6):   RiskTableModule, TableModule, ResultsTableModule, RankingTableModule,    │
│                RankingCriteriaModule, TopPickModule                                     │
│  RISK (2):     RedFlagsModule, TimelineModule                                           │
│  MATCH (3):    RequirementsModule, MatchScoreModule, GapAnalysisModule                  │
│  TEAM (4):     TeamRequirementsModule, TeamCompositionModule, SkillCoverageModule,      │
│                TeamRiskModule                                                           │
│  VERIFY (3):   ClaimModule, EvidenceModule, VerdictModule                               │
│  SUMMARY (3):  TalentPoolModule, SkillDistributionModule, ExperienceDistributionModule  │
└─────────────────────────────────────────────────────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         ⭐ ADAPTIVE MODULES (6) - v9.0 NEW                               │
├─────────────────────────────────────────────────────────────────────────────────────┤
│  QueryAnalyzer          - Detect intent, attributes, filters from natural language      │
│  SchemaInferenceEngine  - Infer table columns dynamically from query + data             │
│  SmartDataExtractor     - Extract data from chunks (metadata, content, computed)        │
│  DynamicTableGenerator  - Build tables with variable columns, adaptive formatting       │
│  AdaptiveAnalysisGen    - Generate contextual analysis, distribution stats, findings    │
│  AdaptiveStructureBuilder - Main orchestrator that coordinates all adaptive components  │
└─────────────────────────────────────────────────────────────────────────────────────┘────┘
```

---

## Query Type → Structure Mapping

| Query Type | Structure | Example Query |
|------------|-----------|---------------|
| `single_candidate` | SingleCandidateStructure | "Give me the full profile of Juan" |
| `red_flags` | RiskAssessmentStructure | "What red flags does María have?" |
| `comparison` | ComparisonStructure | "Compare Juan and María" |
| `search` | SearchStructure | "Find developers with Python" |
| `ranking` | RankingStructure | "Top 5 candidates for backend" |
| `job_match` | JobMatchStructure | "Who fits best for senior position?" |
| `team_build` | TeamBuildStructure | "Build a team of 3 developers" |
| `verification` | VerificationStructure | "Verify if Juan has AWS certification" |
| `summary` | SummaryStructure | "Overview of all candidates" |
| `adaptive` | **AdaptiveStructureBuilder** | "What technologies do they have?" |

---

## 🔍 Structure Identification Guide (Visual Elements)

Use this table to identify which structure is being rendered based on the visual modules displayed:

| Visual Elements You See | Structure Type | Frontend Component |
|------------------------|----------------|-------------------|
| **Profile Header + Highlights Table + Career + Skills + Risk Assessment** | `single_candidate` | `SingleCandidateProfile.jsx` |
| **Risk Assessment Table (5 factors) + Analysis** | `risk_assessment` | `RiskAssessmentStructure` in renderer |
| **Candidate Comparison Table + Winner Card** | `comparison` | `CandidateTable` + `WinnerCard` |
| **"X top matches" + Results Table** | `search` | `SearchResultsTable` |
| **Ranking Table + Top Pick Card + Criteria** | `ranking` | `RankingTable` + `TopPickCard` |
| **Match Score Cards + Requirements + Gap Analysis** | `job_match` | `MatchScoreCard` + `RequirementsList` |
| **Team Composition + Skill Coverage** | `team_build` | `TeamCompositionView` |
| **Verification Result (✓/✗/?) + Evidence** | `verification` | `VerificationResult` |
| **Pool Summary + Skill Distribution** | `summary` | `PoolSummary` |
| **Only Analysis + Conclusion (no specific modules)** | `fallback/legacy` | Standard markdown render |

### Quick Identification by Header Elements:

```
"☆ X top matches | Avg: XX%"     → SEARCH structure
"🏆 Top Pick" or "Winner" card   → RANKING or COMPARISON
"📊 Candidate Highlights" table  → SINGLE_CANDIDATE
"Risk Assessment" table (5 rows) → SINGLE_CANDIDATE or RISK_ASSESSMENT
"Match Score: XX%"               → JOB_MATCH
"Team Composition"               → TEAM_BUILD
"Verification Result"            → VERIFICATION
```

---

## 🏗️ Complete Structure Details

### 1. SingleCandidateStructure
**File:** `structures/single_candidate_structure.py`  
**Query Examples:** "dame todo el perfil de X", "full profile of X", "tell me everything about X"

```
┌─────────────────────────────────────────────────────────────────┐
│                   SingleCandidateStructure                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐            │
│  │  Thinking   │  │  Highlights  │  │   Career    │            │
│  │   Module    │  │    Module    │  │   Module    │            │
│  └─────────────┘  └──────────────┘  └─────────────┘            │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐            │
│  │   Skills    │  │ Credentials  │  │  RiskTable  │ ◄─ SHARED  │
│  │   Module    │  │    Module    │  │   Module    │            │
│  └─────────────┘  └──────────────┘  └─────────────┘            │
│  ┌─────────────┐                                               │
│  │ Conclusion  │                                               │
│  │   Module    │                                               │
│  └─────────────┘                                               │
└─────────────────────────────────────────────────────────────────┘
```

**Modules Used (7):**
| Module | Purpose | Output |
|--------|---------|--------|
| ThinkingModule | Extract reasoning | `:::thinking` block |
| HighlightsModule | Key candidate info | Table with category/value |
| CareerModule | Career trajectory | Timeline of positions |
| SkillsModule | Skills snapshot | Categorized skills table |
| CredentialsModule | Certifications/education | Credentials list |
| RiskTableModule | Risk assessment | 5-factor risk table |
| ConclusionModule | Final assessment | `:::conclusion` block |

---

### 2. RiskAssessmentStructure
**File:** `structures/risk_assessment_structure.py`  
**Query Examples:** "give me risks about X", "red flags for X", "any concerns about X"

```
┌─────────────────────────────────────────────────────────────────┐
│                   RiskAssessmentStructure                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐            │
│  │  Thinking   │  │  RiskTable   │ ◄─ SHARED     │ Conclusion  │
│  │   Module    │  │    Module    │  MODULE       │   Module    │
│  └─────────────┘  └──────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

**Modules Used (3):**
| Module | Purpose | Output |
|--------|---------|--------|
| ThinkingModule | Extract reasoning | `:::thinking` block |
| RiskTableModule | Risk assessment | 5-factor risk table (REUSED) |
| ConclusionModule | Final assessment | Assessment text |

---

### 3. ComparisonStructure
**File:** `structures/comparison_structure.py`  
**Query Examples:** "compare X and Y", "X vs Y", "difference between X and Y"

```
┌─────────────────────────────────────────────────────────────────┐
│                     ComparisonStructure                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐            │
│  │  Thinking   │  │   Analysis   │ ◄─ SHARED     │   Table     │
│  │   Module    │  │    Module    │  MODULE       │   Module    │
│  └─────────────┘  └──────────────┘  └─────────────┘            │
│  ┌─────────────┐                                               │
│  │ Conclusion  │ ◄─ SHARED MODULE                              │
│  │   Module    │                                               │
│  └─────────────┘                                               │
└─────────────────────────────────────────────────────────────────┘
```

**Modules Used (4):**
| Module | Purpose | Output |
|--------|---------|--------|
| ThinkingModule | Extract reasoning | `:::thinking` block |
| AnalysisModule | Comparison analysis | Analysis text (REUSED) |
| TableModule | Candidate comparison table | Side-by-side table |
| ConclusionModule | Winner recommendation | `:::conclusion` block |

---

### 4. SearchStructure
**File:** `structures/search_structure.py`  
**Query Examples:** "who has Python experience", "find candidates with React", "show me backend developers"

```
┌─────────────────────────────────────────────────────────────────┐
│                       SearchStructure                            │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │  Thinking   │  │DirectAnswer  │  │   Analysis   │ ◄─ SHARED │
│  │   Module    │  │   Module     │  │    Module    │           │
│  └─────────────┘  └──────────────┘  └──────────────┘           │
│  ┌──────────────┐ ┌─────────────┐                              │
│  │ ResultsTable │ │ Conclusion  │ ◄─ SHARED MODULE             │
│  │    Module    │ │   Module    │                              │
│  └──────────────┘ └─────────────┘                              │
└─────────────────────────────────────────────────────────────────┘
```

**Modules Used (5):**
| Module | Purpose | Output |
|--------|---------|--------|
| ThinkingModule | Extract reasoning | `:::thinking` block |
| DirectAnswerModule | Quick answer | Direct response text |
| AnalysisModule | Search analysis | Analysis text (REUSED) |
| ResultsTableModule | Search results | Results with scores |
| ConclusionModule | Summary | `:::conclusion` block |

---

### 5. RankingStructure
**File:** `structures/ranking_structure.py`  
**Query Examples:** "top 5 candidates for backend", "rank candidates for leadership", "best candidates for senior developer"

```
┌─────────────────────────────────────────────────────────────────┐
│                       RankingStructure                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │  Thinking   │  │   Analysis   │ ◄─ SHARED      │ Ranking    │
│  │   Module    │  │    Module    │  MODULE        │ Criteria   │
│  └─────────────┘  └──────────────┘  └──────────────┘           │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────┐             │
│  │ RankingTable │ │   TopPick    │ │ Conclusion  │ ◄─ SHARED   │
│  │    Module    │ │    Module    │ │   Module    │             │
│  └──────────────┘ └──────────────┘ └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

**Modules Used (6):**
| Module | Purpose | Output |
|--------|---------|--------|
| ThinkingModule | Extract reasoning | `:::thinking` block |
| AnalysisModule | Ranking analysis | Analysis text (REUSED) |
| RankingCriteriaModule | Define criteria | Criteria with weights |
| RankingTableModule | Ranked candidates | Ordered table with scores |
| TopPickModule | #1 recommendation | Top pick card with justification |
| ConclusionModule | Final recommendation | `:::conclusion` block |

---

### 6. JobMatchStructure
**File:** `structures/job_match_structure.py`  
**Query Examples:** "match candidates to this JD", "who fits this role", "evaluate against these requirements"

```
┌─────────────────────────────────────────────────────────────────┐
│                       JobMatchStructure                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │  Thinking   │  │   Analysis   │ ◄─ SHARED      │Requirements│
│  │   Module    │  │    Module    │  MODULE        │  Module    │
│  └─────────────┘  └──────────────┘  └──────────────┘           │
│  ┌──────────────┐ ┌──────────────┐ ┌─────────────┐             │
│  │ MatchScore   │ │ GapAnalysis  │ │ Conclusion  │ ◄─ SHARED   │
│  │    Module    │ │    Module    │ │   Module    │             │
│  └──────────────┘ └──────────────┘ └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

**Modules Used (6):**
| Module | Purpose | Output |
|--------|---------|--------|
| ThinkingModule | Extract reasoning | `:::thinking` block |
| AnalysisModule | Match analysis | Analysis text (REUSED) |
| RequirementsModule | JD requirements | Parsed requirements list |
| MatchScoreModule | Calculate match % | Match scores per candidate |
| GapAnalysisModule | Identify gaps | Skills/experience gaps |
| ConclusionModule | Best match | `:::conclusion` block |

---

### 7. TeamBuildStructure
**File:** `structures/team_build_structure.py`  
**Query Examples:** "build a team of 3 developers", "form a project team", "assemble a team for this project"

```
┌─────────────────────────────────────────────────────────────────┐
│                       TeamBuildStructure                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐          │
│  │  Thinking   │  │   Analysis   │ ◄─ SHARED       │   Team    │
│  │   Module    │  │    Module    │  MODULE         │Requirements│
│  └─────────────┘  └──────────────┘  └───────────────┘          │
│  ┌───────────────┐ ┌──────────────┐ ┌──────────────┐           │
│  │    Team       │ │    Skill     │ │   TeamRisk   │           │
│  │  Composition  │ │   Coverage   │ │    Module    │           │
│  └───────────────┘ └──────────────┘ └──────────────┘           │
│  ┌─────────────┐                                               │
│  │ Conclusion  │ ◄─ SHARED MODULE                              │
│  │   Module    │                                               │
│  └─────────────┘                                               │
└─────────────────────────────────────────────────────────────────┘
```

**Modules Used (7):**
| Module | Purpose | Output |
|--------|---------|--------|
| ThinkingModule | Extract reasoning | `:::thinking` block |
| AnalysisModule | Team analysis | Analysis text (REUSED) |
| TeamRequirementsModule | Define team roles | Role definitions |
| TeamCompositionModule | Assign candidates | Role → Candidate mapping |
| SkillCoverageModule | Coverage analysis | Team skill coverage % |
| TeamRiskModule | Team risks | Potential team issues |
| ConclusionModule | Team recommendation | `:::conclusion` block |

---

### 8. VerificationStructure
**File:** `structures/verification_structure.py`  
**Query Examples:** "verify if X has AWS certification", "confirm X worked at Google", "check if X has 5 years experience"

```
┌─────────────────────────────────────────────────────────────────┐
│                     VerificationStructure                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │  Thinking   │  │    Claim     │  │   Evidence   │           │
│  │   Module    │  │    Module    │  │    Module    │           │
│  └─────────────┘  └──────────────┘  └──────────────┘           │
│  ┌──────────────┐ ┌─────────────┐                              │
│  │   Verdict    │ │ Conclusion  │ ◄─ SHARED MODULE             │
│  │    Module    │ │   Module    │                              │
│  └──────────────┘ └─────────────┘                              │
└─────────────────────────────────────────────────────────────────┘
```

**Modules Used (5):**
| Module | Purpose | Output |
|--------|---------|--------|
| ThinkingModule | Extract reasoning | `:::thinking` block |
| ClaimModule | Parse claim | Claim subject/predicate |
| EvidenceModule | Find evidence | Supporting/contradicting evidence |
| VerdictModule | Issue verdict | CONFIRMED/PARTIAL/NOT_FOUND |
| ConclusionModule | Final verdict | `:::conclusion` block |

---

### 9. SummaryStructure
**File:** `structures/summary_structure.py`  
**Query Examples:** "overview of all candidates", "talent pool summary", "summarize the candidates"

```
┌─────────────────────────────────────────────────────────────────┐
│                       SummaryStructure                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐          │
│  │  Thinking   │  │  TalentPool  │  │    Skill      │          │
│  │   Module    │  │    Module    │  │ Distribution  │          │
│  └─────────────┘  └──────────────┘  └───────────────┘          │
│  ┌───────────────┐ ┌─────────────┐                             │
│  │  Experience   │ │ Conclusion  │ ◄─ SHARED MODULE            │
│  │ Distribution  │ │   Module    │                             │
│  └───────────────┘ └─────────────┘                             │
└─────────────────────────────────────────────────────────────────┘
```

**Modules Used (5):**
| Module | Purpose | Output |
|--------|---------|--------|
| ThinkingModule | Extract reasoning | `:::thinking` block |
| TalentPoolModule | Pool statistics | Total, avg experience, etc. |
| SkillDistributionModule | Skill breakdown | Skills by frequency |
| ExperienceDistributionModule | Experience breakdown | Experience levels |
| ConclusionModule | Pool assessment | `:::conclusion` block |

---

## 📦 Complete Module Inventory (29 Modules)

### Core Modules (Used by Most Structures)

| # | Module | File | Used By | Purpose |
|---|--------|------|---------|---------|
| 1 | **ThinkingModule** | `thinking_module.py` | ALL 9 | Extract `:::thinking` reasoning blocks |
| 2 | **ConclusionModule** | `conclusion_module.py` | ALL 9 | Extract `:::conclusion` final assessment |
| 3 | **AnalysisModule** | `analysis_module.py` | 6 structures | Extract analysis text between sections |
| 4 | **DirectAnswerModule** | `direct_answer_module.py` | Search | Extract direct response to query |

### Profile Modules (SingleCandidateStructure)

| # | Module | File | Purpose |
|---|--------|------|---------|
| 5 | **HighlightsModule** | `highlights_module.py` | Key candidate info table |
| 6 | **CareerModule** | `career_module.py` | Career trajectory timeline |
| 7 | **SkillsModule** | `skills_module.py` | Categorized skills snapshot |
| 8 | **CredentialsModule** | `credentials_module.py` | Certifications & education |

### Table/Ranking Modules

| # | Module | File | Used By | Purpose |
|---|--------|------|---------|---------|
| 9 | **TableModule** | `table_module.py` | Comparison | Candidate comparison table |
| 10 | **ResultsTableModule** | `results_table_module.py` | Search | Search results table |
| 11 | **RankingTableModule** | `ranking_table_module.py` | Ranking | Ranked candidates table |
| 12 | **RankingCriteriaModule** | `ranking_criteria_module.py` | Ranking | Extract/define ranking criteria |
| 13 | **TopPickModule** | `top_pick_module.py` | Ranking | #1 candidate recommendation |

### Risk Modules

| # | Module | File | Used By | Purpose |
|---|--------|------|---------|---------|
| 14 | **RiskTableModule** | `risk_table_module.py` | SingleCandidate, RiskAssessment | 5-factor risk assessment table |
| 15 | **RedFlagsModule** | `red_flags_module.py` | Legacy/Fallback | Red flags detection |
| 16 | **TimelineModule** | `timeline_module.py` | Legacy/Fallback | Career timeline analysis |

### Job Match Modules

| # | Module | File | Purpose |
|---|--------|------|---------|
| 17 | **RequirementsModule** | `requirements_module.py` | Parse job description requirements |
| 18 | **MatchScoreModule** | `match_score_module.py` | Calculate match percentages |
| 19 | **GapAnalysisModule** | `gap_analysis_module.py` | Identify skill/experience gaps |

### Team Build Modules

| # | Module | File | Purpose |
|---|--------|------|---------|
| 20 | **TeamRequirementsModule** | `team_requirements_module.py` | Define team role requirements |
| 21 | **TeamCompositionModule** | `team_composition_module.py` | Assign candidates to roles |
| 22 | **SkillCoverageModule** | `skill_coverage_module.py` | Analyze team skill coverage |
| 23 | **TeamRiskModule** | `team_risk_module.py` | Identify team risks |

### Verification Modules

| # | Module | File | Purpose |
|---|--------|------|---------|
| 24 | **ClaimModule** | `claim_module.py` | Parse verification claim |
| 25 | **EvidenceModule** | `evidence_module.py` | Find supporting/contradicting evidence |
| 26 | **VerdictModule** | `verdict_module.py` | Issue CONFIRMED/PARTIAL/NOT_FOUND |

### Summary Modules

| # | Module | File | Purpose |
|---|--------|------|---------|
| 27 | **TalentPoolModule** | `talent_pool_module.py` | Pool statistics |
| 28 | **SkillDistributionModule** | `skill_distribution_module.py` | Skill frequency analysis |
| 29 | **ExperienceDistributionModule** | `experience_distribution_module.py` | Experience level distribution |

---

## 🔄 Module Reusability Map

```
                           ┌─────────────────┐
                           │ ThinkingModule  │──────────────► ALL 9 STRUCTURES
                           └─────────────────┘

                           ┌─────────────────┐
                           │ConclusionModule │──────────────► ALL 9 STRUCTURES
                           └─────────────────┘

                           ┌─────────────────┐
                           │ AnalysisModule  │
                           └────────┬────────┘
    ┌────────────┬─────────────────┼─────────────────┬────────────┐
    │            │                 │                 │            │
    ▼            ▼                 ▼                 ▼            ▼
 Search      Ranking           JobMatch         TeamBuild    Comparison
Structure   Structure         Structure        Structure    Structure

                           ┌─────────────────┐
                           │ RiskTableModule │
                           └────────┬────────┘
              ┌─────────────────────┴─────────────────────┐
              │                                           │
              ▼                                           ▼
    SingleCandidateStructure                   RiskAssessmentStructure
```

### Module Usage Matrix

| Module | Single | Risk | Compare | Search | Rank | JobMatch | Team | Verify | Summary |
|--------|:------:|:----:|:-------:|:------:|:----:|:--------:|:----:|:------:|:-------:|
| ThinkingModule | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| ConclusionModule | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| AnalysisModule | - | - | ✅ | ✅ | ✅ | ✅ | ✅ | - | - |
| RiskTableModule | ✅ | ✅ | - | - | - | - | - | - | - |
| HighlightsModule | ✅ | - | - | - | - | - | - | - | - |
| CareerModule | ✅ | - | - | - | - | - | - | - | - |
| SkillsModule | ✅ | - | - | - | - | - | - | - | - |
| CredentialsModule | ✅ | - | - | - | - | - | - | - | - |
| TableModule | - | - | ✅ | - | - | - | - | - | - |
| ResultsTableModule | - | - | - | ✅ | - | - | - | - | - |
| DirectAnswerModule | - | - | - | ✅ | - | - | - | - | - |
| RankingTableModule | - | - | - | - | ✅ | - | - | - | - |
| RankingCriteriaModule | - | - | - | - | ✅ | - | - | - | - |
| TopPickModule | - | - | - | - | ✅ | - | - | - | - |
| RequirementsModule | - | - | - | - | - | ✅ | - | - | - |
| MatchScoreModule | - | - | - | - | - | ✅ | - | - | - |
| GapAnalysisModule | - | - | - | - | - | ✅ | - | - | - |
| TeamRequirementsModule | - | - | - | - | - | - | ✅ | - | - |
| TeamCompositionModule | - | - | - | - | - | - | ✅ | - | - |
| SkillCoverageModule | - | - | - | - | - | - | ✅ | - | - |
| TeamRiskModule | - | - | - | - | - | - | ✅ | - | - |
| ClaimModule | - | - | - | - | - | - | - | ✅ | - |
| EvidenceModule | - | - | - | - | - | - | - | ✅ | - |
| VerdictModule | - | - | - | - | - | - | - | ✅ | - |
| TalentPoolModule | - | - | - | - | - | - | - | - | ✅ |
| SkillDistributionModule | - | - | - | - | - | - | - | - | ✅ |
| ExperienceDistributionModule | - | - | - | - | - | - | - | - | ✅ |

### Key Concept: Module Reuse

The **RiskTableModule** is used by BOTH:
- `SingleCandidateStructure` (embedded in full profile)
- `RiskAssessmentStructure` (standalone risk view)

Same module, same output, different context.

---

## Query → Structure Routing

```
User Query → classify_query_for_structure() → Structure → Frontend Render

"dame todo el perfil de X"    → single_candidate → SingleCandidateProfile.jsx
"give me risks about X"       → red_flags        → RiskAssessmentProfile.jsx
"compare X and Y"             → comparison       → Standard multi-candidate view
"who has Python?"             → search           → Standard search response
```

---

## Post-Mortem: Risk Assessment Implementation

### Why It Took So Long

| Issue | Root Cause | Time Wasted |
|-------|------------|-------------|
| **Wrong layer diagnosis** | Initially thought problem was in orchestrator (backend), but actual problem was in LLM template + frontend parser | ~60% of effort |
| **Multiple implementation attempts** | Added Risk Assessment in 3 different places instead of understanding the correct data flow first | ~25% of effort |
| **Not tracing data flow** | Didn't trace `raw_content` → frontend parser → render flow from the start | ~15% of effort |

### The Correct Data Flow (CRITICAL TO UNDERSTAND)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DATA FLOW DIAGRAM                                      │
└─────────────────────────────────────────────────────────────────────────────────┘

1. USER QUERY
      │
      ▼
2. TEMPLATE SELECTION (templates.py)
   ├── SINGLE_CANDIDATE_TEMPLATE  → For individual candidate queries
   ├── QUERY_TEMPLATE             → For comparisons/multiple candidates
   ├── RED_FLAGS_TEMPLATE         → For red flags specific queries
   └── Others...
      │
      ▼
3. TEMPLATE FORMATTING (templates.py:build_single_candidate_prompt)
   - Passes: candidate_name, cv_id, context, question
   - Passes: {risk_assessment_section} ← PRE-CALCULATED from metadata
      │
      ▼
4. LLM GENERATES MARKDOWN OUTPUT
   - LLM follows template structure
   - Generates ALL sections including Risk Assessment
      │
      ▼
5. PROCESSOR (output_processor/processor.py)
   - Creates StructuredOutput object
   - raw_content = LLM's raw markdown output (UNCHANGED)
      │
      ▼
6. ORCHESTRATOR (output_processor/orchestrator.py)
   - Adds modules to formatted_answer (string)
   - BUT: raw_content in StructuredOutput is NEVER modified
      │
      ▼
7. RAG SERVICE RETURNS (rag_service_v5.py)
   - Returns: { answer: formatted_answer, structured_output: {..., raw_content} }
      │
      ▼
8. FRONTEND RECEIVES (StructuredOutputRenderer.jsx)
   - Extracts: raw_content from structured_output
   - IF single candidate detected:
       │
       ▼
9. PARSER (singleCandidateParser.js)
   - parseSingleCandidateProfile(raw_content)
   - Extracts: highlights, career, skills, credentials, riskAssessment
       │
       ▼
10. RENDERER (SingleCandidateProfile.jsx)
    - Renders each extracted section as visual component
```

### KEY INSIGHT

**The frontend parses `raw_content` (LLM output), NOT `formatted_answer` (orchestrator output).**

This means:
- Any module you want in SingleCandidateProfile MUST be in the LLM template
- The orchestrator's additions to `formatted_answer` are IGNORED for single candidate view
- The parser must have an `extract[Module]()` function for each module

---

## File Locations & Responsibilities

### Backend Files

| File | Purpose | Key Functions |
|------|---------|---------------|
| `backend/app/prompts/templates.py` | LLM prompt templates | `SINGLE_CANDIDATE_TEMPLATE`, `build_single_candidate_prompt()`, `_extract_enriched_metadata()` |
| `backend/app/services/output_processor/processor.py` | Creates StructuredOutput | `process()` |
| `backend/app/services/output_processor/orchestrator.py` | Formats final answer | `process()`, module formatting |
| `backend/app/services/rag_service_v5.py` | Main RAG pipeline | `query()`, template selection |

### Frontend Files

| File | Purpose | Key Functions |
|------|---------|---------------|
| `frontend/src/components/output/StructuredOutputRenderer.jsx` | Decides render path | Detects single vs multi candidate |
| `frontend/src/components/output/singleCandidateParser.js` | Parses LLM markdown | `extractHighlights()`, `extractRiskAssessment()`, etc. |
| `frontend/src/components/output/SingleCandidateProfile.jsx` | Renders single candidate | Visual components for each module |

---

## How to Add a New Module

### Step 1: Add to Template (templates.py)

Location: `SINGLE_CANDIDATE_TEMPLATE` (around line 450)

```python
### 📜 Credentials
...

---

### 🆕 Your New Module

{your_module_section}

---

:::conclusion
```

### Step 2: Generate Module Data (templates.py)

Location: `_extract_enriched_metadata()` (around line 1333)

```python
def _extract_enriched_metadata(self, chunks: list[dict]) -> dict[str, str]:
    sections = {
        "risk_assessment": "...",
        "your_module": "| Default | Data |",  # Add default
    }
    
    # Extract from chunk metadata
    for chunk in chunks:
        meta = chunk.get("metadata", {})
        your_data = meta.get("your_field")
        if your_data:
            sections["your_module"] = f"| Extracted | {your_data} |"
            break
    
    return sections
```

### Step 3: Pass to Template (templates.py)

Location: `build_single_candidate_prompt()` (around line 1301)

```python
formatted_prompt = SINGLE_CANDIDATE_TEMPLATE.format(
    candidate_name=candidate_name,
    cv_id=cv_id,
    context=ctx.text,
    question=question,
    risk_assessment_section=sections["risk_assessment"],
    your_module_section=sections["your_module"]  # Add here
)
```

### Step 4: Add Parser Function (singleCandidateParser.js)

Location: After `extractRiskAssessment()` (around line 350)

```javascript
export const extractYourModule = (content) => {
  if (!content) return [];
  
  // Find section header
  let start = content.indexOf('### 🆕 Your New Module');
  if (start === -1) return [];
  
  // Find boundary
  let end = content.indexOf('###', start + 25);
  if (end === -1) end = content.indexOf(':::', start + 25);
  if (end === -1) end = content.length;
  
  const section = content.substring(start, end);
  
  // Parse table rows
  const data = [];
  const rowPattern = /\|\s*\*\*([^|*]+)\*\*\s*\|\s*([^|]+)\|/g;
  let match;
  
  while ((match = rowPattern.exec(section)) !== null) {
    data.push({
      label: match[1].trim(),
      value: match[2].trim()
    });
  }
  
  return data;
};
```

### Step 5: Add to Profile Parser (singleCandidateParser.js)

Location: `parseSingleCandidateProfile()` (around line 400)

```javascript
return {
  candidateName: ...,
  // ... existing fields
  riskAssessment: extractRiskAssessment(content),
  yourModule: extractYourModule(content)  // Add here
};
```

### Step 6: Create Visual Component (SingleCandidateProfile.jsx)

Location: After `RiskAssessmentTable` component (around line 175)

```jsx
const YourModuleSection = ({ data }) => {
  if (!data || data.length === 0) return null;
  
  return (
    <div className="overflow-x-auto rounded-lg border border-blue-500/30">
      <table className="w-full">
        {/* Your table structure */}
      </table>
    </div>
  );
};
```

### Step 7: Add Prop and Render (SingleCandidateProfile.jsx)

Location: Component props (around line 180) and render (around line 290)

```jsx
const SingleCandidateProfile = ({ 
  // ... existing props
  riskAssessment,
  yourModule,  // Add prop
  onOpenCV 
}) => {
  return (
    <div>
      {/* ... existing sections */}
      
      {/* Your New Module */}
      {yourModule && yourModule.length > 0 && (
        <div className="p-4 bg-slate-800/50 rounded-xl border border-blue-500/30">
          <SectionHeader icon={YourIcon} title="Your Module" color="blue" />
          <YourModuleSection data={yourModule} />
        </div>
      )}
    </div>
  );
};
```

### Step 8: Pass Prop in Renderer (StructuredOutputRenderer.jsx)

Location: SingleCandidateProfile usage (around line 424)

```jsx
<SingleCandidateProfile
  // ... existing props
  riskAssessment={singleCandidateData.riskAssessment}
  yourModule={singleCandidateData.yourModule}  // Add here
  onOpenCV={onOpenCV}
/>
```

---

## How to Add a New Template Type

### Step 1: Define Template (templates.py)

```python
YOUR_NEW_TEMPLATE = """## YOUR TEMPLATE TITLE
**Context:** {context}

---

## USER QUERY
{question}

## RESPONSE FORMAT

:::thinking
[Reasoning]
:::

[Your custom structure]

:::conclusion
[Recommendation]
:::

Respond now:"""
```

### Step 2: Add Template Selection Logic

Location: `build_query_prompt()` or create new `build_your_template_prompt()`:

```python
def build_your_template_prompt(
    self,
    question: str,
    chunks: list[dict],
    custom_param: str
) -> str:
    ctx = format_context(chunks)
    
    return YOUR_NEW_TEMPLATE.format(
        context=ctx.text,
        question=question,
        custom_param=custom_param
    )
```

### Step 3: Add Detection Logic (if auto-detected)

Location: `detect_single_candidate_query()` or create new function:

```python
def detect_your_template_query(question: str, chunks: list[dict]) -> bool:
    keywords = ["specific", "keywords", "for", "your", "template"]
    q_lower = question.lower()
    return any(kw in q_lower for kw in keywords)
```

### Step 4: Integrate in RAG Service

Location: `rag_service_v5.py`, query processing:

```python
if detect_your_template_query(question, chunks):
    prompt = self._prompt_builder.build_your_template_prompt(...)
else:
    # existing logic
```

---

## Template Types Available

| Template | File Location | Use Case | Detection |
|----------|---------------|----------|-----------|
| `QUERY_TEMPLATE` | templates.py:235 | Multi-candidate comparisons | Default |
| `SINGLE_CANDIDATE_TEMPLATE` | templates.py:326 | Individual candidate analysis | Name in query + single CV |
| `RED_FLAGS_TEMPLATE` | templates.py:484 | Red flags specific queries | Keywords: "red flag", "risk" |
| `COMPARISON_TEMPLATE` | templates.py:561 | Side-by-side comparison | Keywords: "compare", "vs" |
| `RANKING_TEMPLATE` | templates.py:589 | Top N candidates | Keywords: "top", "best", "rank" |
| `VERIFICATION_TEMPLATE` | templates.py:623 | Claim verification | Keywords: "verify", "confirm" |
| `SUMMARIZE_TEMPLATE` | templates.py:647 | Profile summary | Keywords: "summary", "profile" |

---

## Current Modules in SingleCandidateProfile

| Module | Parser Function | Component | Template Section |
|--------|-----------------|-----------|------------------|
| Candidate Info | `extractCandidateInfo()` | Header | `## 👤 **[Name](cv:id)**` |
| Summary | `extractSummary()` | Paragraph | After header |
| Highlights | `extractHighlights()` | `HighlightsTable` | `### 📊 Candidate Highlights` |
| Career | `extractCareer()` | `CareerItem` | `### 💼 Career Trajectory` |
| Skills | `extractSkills()` | `SkillsTable` | `### 🛠️ Skills Snapshot` |
| Credentials | `extractCredentials()` | `CredentialsList` | `### 📜 Credentials` |
| Risk Assessment | `extractRiskAssessment()` | `RiskAssessmentTable` | `### Risk Assessment` |
| Assessment | `extractAssessment()` | Strengths list | `:::conclusion` |

---

## MODULAR ARCHITECTURE EXPLAINED

### User's Vision
Risk Assessment is **ONE reusable module** that gets inserted into different contexts:

| Query Type | Template Used | Risk Assessment Location |
|------------|---------------|-------------------------|
| "give me all about X" | `SINGLE_CANDIDATE_TEMPLATE` | Embedded in SingleCandidateProfile |
| "give me risks about X" | `RED_FLAGS_TEMPLATE` | Standalone RiskAssessmentProfile |
| "compare X and Y" | `COMPARISON_TEMPLATE` | (future: per-candidate) |

### How It Works

1. **Backend (`templates.py`)**: 
   - `_extract_enriched_metadata()` builds the Risk Assessment table from chunk metadata
   - Both `SINGLE_CANDIDATE_TEMPLATE` and `RED_FLAGS_TEMPLATE` use `{risk_assessment_section}`
   - The same pre-calculated data feeds both templates

2. **Frontend Detection (`singleCandidateParser.js`)**:
   - `isSingleCandidateResponse()` → detects full profile queries
   - `isRiskAssessmentResponse()` → detects standalone risk queries
   - `extractRiskAssessment()` → parses Risk Assessment table from markdown

3. **Frontend Rendering (`StructuredOutputRenderer.jsx`)**:
   - Priority 1: Check for Risk Assessment response → render `RiskAssessmentProfile`
   - Priority 2: Check for Single Candidate response → render `SingleCandidateProfile`
   - Priority 3: Standard multi-candidate rendering

4. **Table Parsing (`table_module.py`)**:
   - Now SKIPS Risk Assessment tables (detects by header "Factor" or risk indicators)
   - Only parses actual Candidate Comparison tables

---

## Issue Found: RED_FLAGS_TEMPLATE Bug

### Problem
Query "give me risks about Imani Jones" triggered `RED_FLAGS_TEMPLATE` instead of `SINGLE_CANDIDATE_TEMPLATE`.

The old `RED_FLAGS_TEMPLATE` was using separate `{red_flags_section}` and `{stability_metrics_section}` placeholders, but those weren't proper Risk Assessment tables - just brief text summaries. This caused the LLM to generate broken/incomplete output like:

```
⚠️ **Se detectaron las siguientes red flags para Imani Jones Concept:** | Stability Score | Stable | ---.
```

### Root Cause
1. **Detection**: `_is_red_flags_query()` detects keywords like "risk", "risks", "red flag"
2. **Template mismatch**: `RED_FLAGS_TEMPLATE` expected different parameters than the unified `risk_assessment_section`
3. **Incomplete data**: The LLM received fragmentary data and produced broken markdown

### Fix Applied
- Updated `RED_FLAGS_TEMPLATE` to use `{risk_assessment_section}` (the full 5-component table)
- Updated template formatting in `build_single_candidate_prompt()` to pass correct parameter
- Both templates now use the same unified Risk Assessment table

---

## Duplicate Code to Remove

The following code is now REDUNDANT and should be removed:

### 1. orchestrator.py - Lines 233-257, 648-755

```
_build_risk_assessment_section() - DUPLICATE
Risk Assessment fallback block - DUPLICATE
```

### 2. rag_service_v5.py - Lines 2229-2234, 2685-2783

```
_build_risk_assessment_failsafe() - DUPLICATE
Failsafe check block - DUPLICATE
```

These were added during debugging but the CORRECT implementation is now:
- **Template**: `templates.py` line 451-455
- **Data**: `templates.py` `_extract_enriched_metadata()` line 1385
- **Parser**: `singleCandidateParser.js` `extractRiskAssessment()`
- **Renderer**: `SingleCandidateProfile.jsx` `RiskAssessmentTable`

---

## Checklist for Future Module Additions

- [ ] Add section to LLM template with placeholder `{module_section}`
- [ ] Add data extraction in `_extract_enriched_metadata()`
- [ ] Pass placeholder to `.format()` call
- [ ] Add `extractModule()` function in parser
- [ ] Add to `parseSingleCandidateProfile()` return object
- [ ] Create visual component in `SingleCandidateProfile.jsx`
- [ ] Add prop to component
- [ ] Pass prop in `StructuredOutputRenderer.jsx`
- [ ] Test with real query
- [ ] Remove any duplicate implementations
