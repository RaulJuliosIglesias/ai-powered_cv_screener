# CV Screener Architecture: Orchestration, Structures & Modules

## Overview

This document defines the complete architecture for the CV Screener output system. The architecture follows a three-layer pattern:

```
USER QUERY → QUERY TYPE → STRUCTURE → MODULES → OUTPUT
```

**Key Principles:**
- **Orchestrator**: Routes queries to the appropriate Structure
- **Structures**: Complete output assemblers that combine Modules
- **Modules**: Reusable components that can be shared across Structures
- **Query Types**: Classification that determines which Structure to use

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATOR                                │
│                    (Router / Entry Point)                           │
│                                                                     │
│   Receives: raw_llm_output, chunks, query, query_type               │
│   Returns:  StructuredOutput + formatted_answer                     │
└────────────────────────────────┬────────────────────────────────────┘
                                 │
                                 │ Routes based on query_type
                                 │
    ┌────────────────────────────┼────────────────────────────────────┐
    │            │               │               │                    │
    ▼            ▼               ▼               ▼                    ▼
┌────────┐ ┌──────────┐ ┌────────────┐ ┌────────┐ ┌────────────────┐
│single_ │ │risk_     │ │comparison  │ │search  │ │ ... more       │
│candidate│ │assessment│ │            │ │        │ │ query_types    │
└────┬───┘ └────┬─────┘ └─────┬──────┘ └───┬────┘ └───────┬────────┘
     │          │             │            │              │
     ▼          ▼             ▼            ▼              ▼
┌─────────┐ ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌─────────────────┐
│Single   │ │Risk     │ │Comparison│ │Search   │ │ ... more        │
│Candidate│ │Assessment│ │Structure│ │Structure│ │ Structures      │
│Structure│ │Structure│ │          │ │         │ │                 │
└────┬────┘ └────┬────┘ └────┬─────┘ └────┬────┘ └────────┬────────┘
     │          │            │            │               │
     ▼          ▼            ▼            ▼               ▼
 MODULES    MODULES      MODULES     MODULES          MODULES
```

---

## 1. QUERY TYPES

Query Types are the classification layer that determines which Structure to use.

| Query Type | Trigger Examples | Structure |
|------------|------------------|-----------|
| `single_candidate` | "dame todo el perfil de X", "full profile of X", "tell me about X" | SingleCandidateStructure |
| `risk_assessment` | "give me risks about X", "red flags for X", "concerns about X" | RiskAssessmentStructure |
| `comparison` | "compare X and Y", "X vs Y", "difference between X and Y" | ComparisonStructure |
| `search` | "who has Python", "candidates with React experience" | SearchStructure |
| `job_match` | "match candidates to this JD", "who fits this role" | JobMatchStructure |
| `ranking` | "top 5 for backend", "rank candidates for this position" | RankingStructure |
| `team_build` | "build a team of 3 developers", "form a project team" | TeamBuildStructure |
| `verification` | "verify if X has AWS certification", "confirm X worked at Google" | VerificationStructure |
| `summary` | "overview of all candidates", "talent pool summary" | SummaryStructure |

---

## 2. STRUCTURES

Structures are complete output assemblers that combine multiple Modules to create a specific output format.

### 2.1 SingleCandidateStructure

**Query Type**: `single_candidate`  
**Purpose**: Display complete profile of ONE specific candidate

```
┌─────────────────────────────────────────────────────────┐
│              SINGLE CANDIDATE STRUCTURE                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐                                        │
│  │  Thinking   │  ← ThinkingModule                      │
│  │   Module    │                                        │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │   Summary   │  ← (Text extraction from LLM)          │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │ Highlights  │  ← HighlightsModule                    │
│  │   Table     │                                        │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │   Career    │  ← CareerModule                        │
│  │ Trajectory  │                                        │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │   Skills    │  ← SkillsModule                        │
│  │  Snapshot   │                                        │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │ Credentials │  ← CredentialsModule                   │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │ Risk Table  │  ← RiskTableModule (REUSABLE)          │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │ Conclusion  │  ← ConclusionModule                    │
│  └─────────────┘                                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Modules Used:**
- ThinkingModule
- HighlightsModule
- CareerModule
- SkillsModule
- CredentialsModule
- RiskTableModule *(shared with RiskAssessmentStructure)*
- ConclusionModule

---

### 2.2 RiskAssessmentStructure

**Query Type**: `risk_assessment`  
**Purpose**: Risk-focused analysis of a candidate

```
┌─────────────────────────────────────────────────────────┐
│               RISK ASSESSMENT STRUCTURE                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐                                        │
│  │  Thinking   │  ← ThinkingModule                      │
│  │   Module    │                                        │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │    Risk     │  ← AnalysisModule                      │
│  │  Analysis   │                                        │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │ Risk Table  │  ← RiskTableModule (SAME MODULE)       │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │ Conclusion  │  ← ConclusionModule                    │
│  │ (Assessment)│                                        │
│  └─────────────┘                                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Modules Used:**
- ThinkingModule
- AnalysisModule
- RiskTableModule *(shared with SingleCandidateStructure)*
- ConclusionModule

---

### 2.3 ComparisonStructure

**Query Type**: `comparison`  
**Purpose**: Side-by-side comparison of multiple candidates

```
┌─────────────────────────────────────────────────────────┐
│                 COMPARISON STRUCTURE                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐                                        │
│  │  Thinking   │  ← ThinkingModule                      │
│  │   Module    │                                        │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │  Analysis   │  ← AnalysisModule                      │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │ Comparison  │  ← ComparisonTableModule               │
│  │   Table     │                                        │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │ Conclusion  │  ← ConclusionModule                    │
│  └─────────────┘                                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Modules Used:**
- ThinkingModule
- AnalysisModule
- ComparisonTableModule
- ConclusionModule

---

### 2.4 SearchStructure

**Query Type**: `search`  
**Purpose**: Find candidates matching specific criteria

```
┌─────────────────────────────────────────────────────────┐
│                   SEARCH STRUCTURE                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐                                        │
│  │  Thinking   │  ← ThinkingModule                      │
│  │   Module    │                                        │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │   Direct    │  ← DirectAnswerModule                  │
│  │   Answer    │                                        │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │  Results    │  ← ResultsTableModule                  │
│  │   Table     │                                        │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │ Conclusion  │  ← ConclusionModule                    │
│  └─────────────┘                                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Modules Used:**
- ThinkingModule
- DirectAnswerModule
- ResultsTableModule
- ConclusionModule

---

### 2.5 JobMatchStructure

**Query Type**: `job_match`  
**Purpose**: Match candidates against a job description

```
┌─────────────────────────────────────────────────────────┐
│                  JOB MATCH STRUCTURE                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐                                        │
│  │  Thinking   │  ← ThinkingModule                      │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │ Requirements│  ← RequirementsModule                  │
│  │  Breakdown  │     (extracts JD requirements)         │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │    Match    │  ← MatchScoreModule                    │
│  │   Scores    │     (% match per candidate)            │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │    Gap      │  ← GapAnalysisModule                   │
│  │  Analysis   │     (what's missing per candidate)     │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │ Conclusion  │  ← ConclusionModule                    │
│  └─────────────┘                                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Modules Used:**
- ThinkingModule
- RequirementsModule
- MatchScoreModule
- GapAnalysisModule
- ConclusionModule

---

### 2.6 RankingStructure

**Query Type**: `ranking`  
**Purpose**: Rank candidates for a specific role

```
┌─────────────────────────────────────────────────────────┐
│                   RANKING STRUCTURE                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐                                        │
│  │  Thinking   │  ← ThinkingModule                      │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │   Ranking   │  ← RankingCriteriaModule               │
│  │  Criteria   │     (evaluation criteria)              │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │   Ranked    │  ← RankingTableModule                  │
│  │    List     │     (ordered table with scores)        │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │   Top Pick  │  ← TopPickModule                       │
│  │  Highlight  │     (highlights #1 with justification) │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │ Conclusion  │  ← ConclusionModule                    │
│  └─────────────┘                                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Modules Used:**
- ThinkingModule
- RankingCriteriaModule
- RankingTableModule
- TopPickModule
- ConclusionModule

---

### 2.7 TeamBuildStructure

**Query Type**: `team_build`  
**Purpose**: Assemble a team of candidates for a project

```
┌─────────────────────────────────────────────────────────┐
│                 TEAM BUILD STRUCTURE                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐                                        │
│  │  Thinking   │  ← ThinkingModule                      │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │    Team     │  ← TeamRequirementsModule              │
│  │Requirements │     (roles needed)                     │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │  Proposed   │  ← TeamCompositionModule               │
│  │    Team     │     (candidates assigned to roles)     │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │   Skill     │  ← SkillCoverageModule                 │
│  │  Coverage   │     (team skill coverage analysis)     │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │  Team Risk  │  ← TeamRiskModule                      │
│  │  Analysis   │     (gaps, dependencies, conflicts)    │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │ Conclusion  │  ← ConclusionModule                    │
│  └─────────────┘                                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Modules Used:**
- ThinkingModule
- TeamRequirementsModule
- TeamCompositionModule
- SkillCoverageModule
- TeamRiskModule
- ConclusionModule

---

### 2.8 VerificationStructure

**Query Type**: `verification`  
**Purpose**: Verify specific claims about a candidate

```
┌─────────────────────────────────────────────────────────┐
│                VERIFICATION STRUCTURE                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐                                        │
│  │  Thinking   │  ← ThinkingModule                      │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │   Claim     │  ← ClaimModule                         │
│  │ Statement   │     (what is being verified)           │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │  Evidence   │  ← EvidenceModule                      │
│  │   Found     │     (CV excerpts as proof)             │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │   Verdict   │  ← VerdictModule                       │
│  │             │     (CONFIRMED/PARTIAL/NOT FOUND)      │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │ Conclusion  │  ← ConclusionModule                    │
│  └─────────────┘                                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Modules Used:**
- ThinkingModule
- ClaimModule
- EvidenceModule
- VerdictModule
- ConclusionModule

---

### 2.9 SummaryStructure

**Query Type**: `summary`  
**Purpose**: Overview of the entire talent pool

```
┌─────────────────────────────────────────────────────────┐
│                   SUMMARY STRUCTURE                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐                                        │
│  │  Thinking   │  ← ThinkingModule                      │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │    Pool     │  ← TalentPoolModule                    │
│  │  Overview   │     (total candidates, distribution)   │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │   Skills    │  ← SkillDistributionModule             │
│  │Distribution │     (skills available in pool)         │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │ Experience  │  ← ExperienceDistributionModule        │
│  │   Levels    │     (Jr/Mid/Sr breakdown)              │
│  └─────────────┘                                        │
│  ┌─────────────┐                                        │
│  │ Conclusion  │  ← ConclusionModule                    │
│  └─────────────┘                                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Modules Used:**
- ThinkingModule
- TalentPoolModule
- SkillDistributionModule
- ExperienceDistributionModule
- ConclusionModule

---

## 3. MODULES

Modules are reusable components that can be shared across multiple Structures.

### 3.1 Core Modules (Used by ALL Structures)

| Module | Responsibility | Output |
|--------|----------------|--------|
| **ThinkingModule** | Extract/format :::thinking::: block | Collapsible reasoning section |
| **ConclusionModule** | Extract/format :::conclusion::: block | Final recommendation/assessment |

---

### 3.2 Content Modules

| Module | Responsibility | Used By |
|--------|----------------|---------|
| **AnalysisModule** | Extract analysis text paragraph | RiskAssessment, Comparison |
| **DirectAnswerModule** | Extract direct answer to query | Search |
| **HighlightsModule** | Key information table (Category \| Info) | SingleCandidate |
| **CareerModule** | Career trajectory with achievements | SingleCandidate |
| **SkillsModule** | Skills snapshot table | SingleCandidate |
| **CredentialsModule** | Certifications and credentials list | SingleCandidate |

---

### 3.3 Table Modules

| Module | Responsibility | Used By |
|--------|----------------|---------|
| **RiskTableModule** | 5-factor risk assessment table | SingleCandidate, RiskAssessment |
| **ComparisonTableModule** | Multi-candidate comparison table | Comparison |
| **ResultsTableModule** | Search results with match scores | Search |
| **RankingTableModule** | Ordered ranking with scores | Ranking |

---

### 3.4 Analysis Modules

| Module | Responsibility | Used By |
|--------|----------------|---------|
| **RequirementsModule** | Extract and categorize JD requirements | JobMatch |
| **MatchScoreModule** | Calculate candidate vs requirements match % | JobMatch, Ranking |
| **GapAnalysisModule** | Identify what candidate is missing | JobMatch, SingleCandidate |
| **RankingCriteriaModule** | Define and weight ranking criteria | Ranking |
| **TopPickModule** | Highlight #1 candidate with justification | Ranking, JobMatch |

---

### 3.5 Team Modules

| Module | Responsibility | Used By |
|--------|----------------|---------|
| **TeamRequirementsModule** | Define roles needed for a team | TeamBuild |
| **TeamCompositionModule** | Assign candidates to team roles | TeamBuild |
| **SkillCoverageModule** | Analyze team skill coverage | TeamBuild |
| **TeamRiskModule** | Identify team gaps and risks | TeamBuild |

---

### 3.6 Verification Modules

| Module | Responsibility | Used By |
|--------|----------------|---------|
| **ClaimModule** | Parse the claim to verify | Verification |
| **EvidenceModule** | Find evidence in CV | Verification |
| **VerdictModule** | Issue verdict with confidence level | Verification |

---

### 3.7 Aggregation Modules

| Module | Responsibility | Used By |
|--------|----------------|---------|
| **TalentPoolModule** | Pool statistics (total, distribution) | Summary |
| **SkillDistributionModule** | Skill distribution across pool | Summary |
| **ExperienceDistributionModule** | Jr/Mid/Sr distribution | Summary |

---

## 4. MODULE REUSABILITY MAP

This diagram shows how modules are shared across structures:

```
                        ┌─────────────────┐
                        │ ThinkingModule  │
                        └────────┬────────┘
                                 │
    ┌────────────────────────────┼────────────────────────────┐
    │    │    │    │    │    │    │    │    │                │
    ▼    ▼    ▼    ▼    ▼    ▼    ▼    ▼    ▼                ▼
 Single Risk Comp Search Job  Rank Team Verify Summary    (ALL)
 Cand.  Ass. aris.       Match ing  Build



                        ┌─────────────────┐
                        │ConclusionModule │
                        └────────┬────────┘
                                 │
    ┌────────────────────────────┼────────────────────────────┐
    │    │    │    │    │    │    │    │    │                │
    ▼    ▼    ▼    ▼    ▼    ▼    ▼    ▼    ▼                ▼
 Single Risk Comp Search Job  Rank Team Verify Summary    (ALL)
 Cand.  Ass. aris.       Match ing  Build



                        ┌─────────────────┐
                        │ RiskTableModule │
                        └────────┬────────┘
                                 │
              ┌──────────────────┴──────────────────┐
              │                                     │
              ▼                                     ▼
       SingleCandidate                      RiskAssessment
          Structure                           Structure



                        ┌─────────────────┐
                        │MatchScoreModule │
                        └────────┬────────┘
                                 │
              ┌──────────────────┴──────────────────┐
              │                                     │
              ▼                                     ▼
          JobMatch                              Ranking
          Structure                            Structure



                        ┌─────────────────┐
                        │GapAnalysisModule│
                        └────────┬────────┘
                                 │
              ┌──────────────────┴──────────────────┐
              │                                     │
              ▼                                     ▼
          JobMatch                           SingleCandidate
          Structure                            Structure



                        ┌─────────────────┐
                        │  AnalysisModule │
                        └────────┬────────┘
                                 │
              ┌──────────────────┴──────────────────┐
              │                                     │
              ▼                                     ▼
       RiskAssessment                          Comparison
          Structure                             Structure
```

---

## 5. COMPLETE ARCHITECTURE SUMMARY

### Query Types → Structures → Modules

| Query Type | Structure | Modules |
|------------|-----------|---------|
| `single_candidate` | SingleCandidateStructure | Thinking, Highlights, Career, Skills, Credentials, RiskTable, Conclusion |
| `risk_assessment` | RiskAssessmentStructure | Thinking, Analysis, RiskTable, Conclusion |
| `comparison` | ComparisonStructure | Thinking, Analysis, ComparisonTable, Conclusion |
| `search` | SearchStructure | Thinking, DirectAnswer, ResultsTable, Conclusion |
| `job_match` | JobMatchStructure | Thinking, Requirements, MatchScore, GapAnalysis, Conclusion |
| `ranking` | RankingStructure | Thinking, RankingCriteria, RankingTable, TopPick, Conclusion |
| `team_build` | TeamBuildStructure | Thinking, TeamRequirements, TeamComposition, SkillCoverage, TeamRisk, Conclusion |
| `verification` | VerificationStructure | Thinking, Claim, Evidence, Verdict, Conclusion |
| `summary` | SummaryStructure | Thinking, TalentPool, SkillDistribution, ExperienceDistribution, Conclusion |

---

## 6. FILE STRUCTURE

```
backend/app/services/output_processor/
├── orchestrator.py                    # Entry point - routes to structures
├── processor.py                       # Legacy processor
│
├── structures/                        # Structure assemblers
│   ├── __init__.py
│   ├── single_candidate_structure.py
│   ├── risk_assessment_structure.py
│   ├── comparison_structure.py
│   ├── search_structure.py
│   ├── job_match_structure.py
│   ├── ranking_structure.py
│   ├── team_build_structure.py
│   ├── verification_structure.py
│   └── summary_structure.py
│
└── modules/                           # Reusable components
    ├── __init__.py
    │
    ├── # Core Modules
    ├── thinking_module.py
    ├── conclusion_module.py
    │
    ├── # Content Modules
    ├── analysis_module.py
    ├── direct_answer_module.py
    ├── highlights_module.py
    ├── career_module.py
    ├── skills_module.py
    ├── credentials_module.py
    │
    ├── # Table Modules
    ├── risk_table_module.py
    ├── comparison_table_module.py
    ├── results_table_module.py
    ├── ranking_table_module.py
    │
    ├── # Analysis Modules
    ├── requirements_module.py
    ├── match_score_module.py
    ├── gap_analysis_module.py
    ├── ranking_criteria_module.py
    ├── top_pick_module.py
    │
    ├── # Team Modules
    ├── team_requirements_module.py
    ├── team_composition_module.py
    ├── skill_coverage_module.py
    ├── team_risk_module.py
    │
    ├── # Verification Modules
    ├── claim_module.py
    ├── evidence_module.py
    ├── verdict_module.py
    │
    └── # Aggregation Modules
        ├── talent_pool_module.py
        ├── skill_distribution_module.py
        └── experience_distribution_module.py
```

---

## 7. IMPLEMENTATION PRIORITY

### Phase 1: Core (Already Implemented)
- [x] SingleCandidateStructure
- [x] RiskAssessmentStructure
- [x] ComparisonStructure
- [x] ThinkingModule
- [x] ConclusionModule
- [x] RiskTableModule

### Phase 2: Search & Ranking
- [ ] SearchStructure
- [ ] RankingStructure
- [ ] ResultsTableModule
- [ ] RankingTableModule
- [ ] RankingCriteriaModule
- [ ] TopPickModule

### Phase 3: Job Matching
- [ ] JobMatchStructure
- [ ] RequirementsModule
- [ ] MatchScoreModule
- [ ] GapAnalysisModule

### Phase 4: Team Building
- [ ] TeamBuildStructure
- [ ] TeamRequirementsModule
- [ ] TeamCompositionModule
- [ ] SkillCoverageModule
- [ ] TeamRiskModule

### Phase 5: Verification & Summary
- [ ] VerificationStructure
- [ ] SummaryStructure
- [ ] ClaimModule
- [ ] EvidenceModule
- [ ] VerdictModule
- [ ] TalentPoolModule
- [ ] SkillDistributionModule
- [ ] ExperienceDistributionModule

---

## 8. DESIGN PRINCIPLES

1. **Single Responsibility**: Each Module does ONE thing
2. **Open/Closed**: Add new Structures without modifying existing ones
3. **Composition over Inheritance**: Structures compose Modules
4. **DRY**: Modules are reusable across Structures
5. **Consistent Naming**: Query Type name ≈ Structure name
6. **Loose Coupling**: Modules don't depend on each other
7. **High Cohesion**: Related functionality grouped in same Module
