# Test Suite: Orchestration, Structures and Modules

## Purpose

This document provides a complete set of test queries to verify that the **Orchestrator → Structures → Modules** system works correctly.

For each query, the following is specified:
- The **question/query** to execute
- The expected **query_type**
- The **Structure** that should process the query
- The **Modules** it should use
- The expected **output fields** in the frontend

---

## How to Use This Document

1. **Execute the query** in the CV Screener chat
2. **Verify in backend logs** that it shows:
   ```
   [ORCHESTRATOR] ROUTING query_type=X to appropriate structure
   [ORCHESTRATOR] Using XStructure
   ```
3. **Verify in frontend console** that it shows:
   ```
   [STRUCTURED_OUTPUT] ROUTING: structure_type=X
   ```
4. **Visually verify** that expected components are displayed

---

# TESTS BY STRUCTURE

---

## 1. SingleCandidateStructure

### Query Type: `single_candidate`

| # | Test Query | Language |
|---|------------|----------|
| 1.1 | "Give me the full profile of Juan Pérez" | EN |
| 1.2 | "Tell me everything about Maria Garcia" | EN |
| 1.3 | "Full profile of the candidate with most experience" | EN |
| 1.4 | "Tell me about the senior candidate" | EN |

### Expected Structure

```
┌─────────────────────────────────────────────┐
│         SINGLE CANDIDATE STRUCTURE          │
├─────────────────────────────────────────────┤
│ ✅ ThinkingSection (collapsible)            │
│ ✅ SingleCandidateProfile                   │
│    ├── Summary                              │
│    ├── Highlights (key info table)          │
│    ├── Career Trajectory                    │
│    ├── Skills Snapshot                      │
│    ├── Credentials                          │
│    └── Risk Assessment Table                │
└─────────────────────────────────────────────┘
```

### Backend Modules

| Module | File | Purpose |
|--------|------|---------|
| ThinkingModule | `thinking_module.py` | Extracts :::thinking::: section |
| HighlightsModule | `highlights_module.py` | Key information table |
| CareerModule | `career_module.py` | Professional trajectory |
| SkillsModule | `skills_module.py` | Skills snapshot |
| CredentialsModule | `credentials_module.py` | Certifications/education |
| RiskTableModule | `risk_table_module.py` | 5 risk factors table |
| ConclusionModule | `conclusion_module.py` | Final assessment |

### Output Fields (structuredOutput)

```javascript
{
  structure_type: "single_candidate",
  thinking: "...",
  single_candidate_data: {
    candidate_name: "Juan Pérez",
    cv_id: "cv_xxx",
    summary: "...",
    highlights: [...],
    career: [...],
    skills: [...],
    credentials: [...],
    risk_table: { factors: [...] },
    conclusion: "..."
  }
}
```

### Expected Log (Backend)

```
[ORCHESTRATOR] ROUTING query_type=single_candidate to appropriate structure
[ORCHESTRATOR] Using SingleCandidateStructure for Juan Pérez
[SINGLE_CANDIDATE_STRUCTURE] Assembling profile for Juan Pérez
```

---

## 2. RiskAssessmentStructure

### Query Type: `red_flags` / `risk_assessment`

| # | Test Query | Language |
|---|------------|----------|
| 2.1 | "What red flags does Juan Pérez have?" | EN |
| 2.2 | "Give me risks about Maria Garcia" | EN |
| 2.3 | "Concerns about the senior candidate" | EN |
| 2.4 | "Risk analysis for Juan" | EN |
| 2.5 | "What are the warning signs for this candidate?" | EN |

### Expected Structure

```
┌─────────────────────────────────────────────┐
│         RISK ASSESSMENT STRUCTURE           │
├─────────────────────────────────────────────┤
│ ✅ ThinkingSection (collapsible)            │
│ ✅ RiskAssessmentProfile                    │
│    ├── Risk Analysis (text)                 │
│    ├── Risk Assessment Table (5 factors)    │
│    └── Assessment/Conclusion                │
└─────────────────────────────────────────────┘
```

### Backend Modules

| Module | File | Purpose |
|--------|------|---------|
| ThinkingModule | `thinking_module.py` | Extracts :::thinking::: |
| AnalysisModule | `analysis_module.py` | Risk analysis text |
| RiskTableModule | `risk_table_module.py` | 5 factors table (SHARED) |
| ConclusionModule | `conclusion_module.py` | Final assessment |

### Output Fields (structuredOutput)

```javascript
{
  structure_type: "risk_assessment",
  thinking: "...",
  risk_assessment_data: {
    candidate_name: "Juan Pérez",
    cv_id: "cv_xxx",
    risk_analysis: "...",
    risk_table: { factors: [...] },
    assessment: "..."
  }
}
```

---

## 3. ComparisonStructure

### Query Type: `comparison`

| # | Test Query | Language |
|---|----------------|--------|
| 3.1 | "Compara Juan y María" | ES |
| 3.2 | "Compare years of experience" | EN |
| 3.3 | "Juan vs María for backend role" | EN |
| 3.4 | "Diferencias entre los candidatos senior" | ES |
| 3.5 | "Compare education levels of all candidates" | EN |
| 3.6 | "Which candidate has more Python experience?" | EN |

### Expected Structure

```
┌─────────────────────────────────────────────┐
│           COMPARISON STRUCTURE              │
├─────────────────────────────────────────────┤
│ ✅ ThinkingSection (collapsible)            │
│ ✅ DirectAnswerSection (optional)           │
│ ✅ CandidateTable (CRÍTICO - tabla compar.) │
│ ✅ WinnerCard (si hay 2+ candidatos)        │
│ ✅ AnalysisSection                          │
│ ✅ ConclusionSection                        │
└─────────────────────────────────────────────┘
```

### Backend Modules

| Module | File | Purpose |
|--------|---------|-----------|
| ThinkingModule | `thinking_module.py` | Extracts :::thinking::: |
| AnalysisModule | `analysis_module.py` | Analysis text |
| TableModule | `table_module.py` | **Comparison table** |
| ConclusionModule | `conclusion_module.py` | Conclusion/recommendation |

### Output Fields (structuredOutput)

```javascript
{
  structure_type: "comparison",
  thinking: "...",
  direct_answer: "...",
  table_data: {
    title: "Candidate Comparison",
    headers: ["Candidate", "Experience", "Skills", "Score"],
    rows: [
      { candidate_name: "Juan", cv_id: "cv_xxx", columns: {...}, match_score: 85 },
      { candidate_name: "María", cv_id: "cv_yyy", columns: {...}, match_score: 78 }
    ]
  },
  analysis: "...",
  conclusion: "..."
}
```

### ⚠️ Critical Verification

**La tabla de comparación DEBE aparecer.** Si no aparece:
1. Verificar que `table_data` tiene `rows` con datos
2. Verificar que el orchestrator pasa `table_data` a `structured.table_data`
3. Verificar que el frontend renderiza `CandidateTable`

---

## 4. SearchStructure

### Query Type: `search`

| # | Test Query | Language |
|---|----------------|--------|
| 4.1 | "Busca desarrolladores con Python" | ES |
| 4.2 | "Who has React experience?" | EN |
| 4.3 | "Find candidates with AWS certification" | EN |
| 4.4 | "Candidatos con más de 5 años de experiencia" | ES |
| 4.5 | "Show me frontend developers" | EN |

### Expected Structure

```
┌─────────────────────────────────────────────┐
│             SEARCH STRUCTURE                │
├─────────────────────────────────────────────┤
│ ✅ ThinkingSection (collapsible)            │
│ ✅ DirectAnswerSection                      │
│ ✅ SearchResultsTable                       │
│ ✅ AnalysisSection                          │
│ ✅ ConclusionSection                        │
└─────────────────────────────────────────────┘
```

### Backend Modules

| Module | File | Purpose |
|--------|---------|-----------|
| ThinkingModule | `thinking_module.py` | Extracts :::thinking::: |
| DirectAnswerModule | `direct_answer_module.py` | Direct answer |
| ResultsTableModule | `results_table_module.py` | Results table |
| AnalysisModule | `analysis_module.py` | Results analysis |
| ConclusionModule | `conclusion_module.py` | Conclusion |

### Output Fields (structuredOutput)

```javascript
{
  structure_type: "search",
  thinking: "...",
  direct_answer: "...",
  results_table: {
    results: [
      { candidate_name: "...", cv_id: "...", match_score: 90, ... }
    ],
    query_terms: ["Python", "developer"]
  },
  total_results: 5,
  analysis: "...",
  conclusion: "..."
}
```

---

## 5. RankingStructure

### Query Type: `ranking`

| # | Test Query | Language |
|---|----------------|--------|
| 5.1 | "Top 5 candidatos para backend" | ES |
| 5.2 | "Rank candidates for senior position" | EN |
| 5.3 | "Best candidates for this role" | EN |
| 5.4 | "Ordena los candidatos por experiencia" | ES |
| 5.5 | "Who are the top 3 for frontend?" | EN |

### Expected Structure

```
┌─────────────────────────────────────────────┐
│            RANKING STRUCTURE                │
├─────────────────────────────────────────────┤
│ ✅ ThinkingSection (collapsible)            │
│ ✅ TopPickCard (#1 destacado)               │
│ ✅ RankingTable (lista ordenada)            │
│ ✅ AnalysisSection                          │
│ ✅ ConclusionSection                        │
└─────────────────────────────────────────────┘
```

### Backend Modules

| Module | File | Purpose |
|--------|---------|-----------|
| ThinkingModule | `thinking_module.py` | Extracts :::thinking::: |
| RankingCriteriaModule | `ranking_criteria_module.py` | Ranking criteria |
| RankingTableModule | `ranking_table_module.py` | Ranked table |
| TopPickModule | `top_pick_module.py` | Highlights #1 |
| AnalysisModule | `analysis_module.py` | Analysis |
| ConclusionModule | `conclusion_module.py` | Conclusion |

### Output Fields (structuredOutput)

```javascript
{
  structure_type: "ranking",
  thinking: "...",
  ranking_table: {
    ranked: [
      { rank: 1, candidate_name: "...", cv_id: "...", score: 95, ... }
    ]
  },
  top_pick: {
    candidate_name: "...",
    cv_id: "...",
    overall_score: 95,
    justification: "...",
    key_strengths: [...]
  },
  analysis: "...",
  conclusion: "..."
}
```

---

## 6. JobMatchStructure

### Query Type: `job_match`

| # | Test Query | Language |
|---|----------------|--------|
| 6.1 | "Who would fit a senior position?" | EN |
| 6.2 | "Match candidates to frontend role" | EN |
| 6.3 | "Quién encaja mejor para puesto de backend?" | ES |
| 6.4 | "Evaluate candidates for Python developer role" | EN |
| 6.5 | "Who fits a DevOps position?" | EN |

### Expected Structure

```
┌─────────────────────────────────────────────┐
│           JOB MATCH STRUCTURE               │
├─────────────────────────────────────────────┤
│ ✅ ThinkingSection (collapsible)            │
│ ✅ TopPickCard (best match con %)           │
│ ✅ MatchScoreCard (todos los scores)        │
│ ✅ AnalysisSection                          │
│ ✅ ConclusionSection                        │
└─────────────────────────────────────────────┘
```

### Backend Modules

| Module | File | Purpose |
|--------|---------|-----------|
| ThinkingModule | `thinking_module.py` | Extracts :::thinking::: |
| RequirementsModule | `requirements_module.py` | Extracts requirements from JD/query |
| MatchScoreModule | `match_score_module.py` | Calculates match % |
| GapAnalysisModule | `gap_analysis_module.py` | What each candidate is missing |
| AnalysisModule | `analysis_module.py` | Analysis |
| ConclusionModule | `conclusion_module.py` | Conclusion |

### Output Fields (structuredOutput)

```javascript
{
  structure_type: "job_match",
  thinking: "...",
  best_match: {
    candidate_name: "...",
    cv_id: "...",
    overall_score: 85,        // ← CRÍTICO: debe tener score
    justification: "...",
    key_strengths: [...]
  },
  match_scores: {
    matches: [
      { 
        candidate_name: "...", 
        cv_id: "...", 
        overall_match: 85,    // ← CRÍTICO: NO debe ser 0%
        met_requirements: [...],
        missing_requirements: [...],
        strengths: [...]
      }
    ],
    total_requirements: 3
  },
  gap_analysis: {...},
  analysis: "...",
  conclusion: "..."
}
```

### ⚠️ Critical Verification

1. **TopPickCard debe mostrar %**: Si muestra `undefined%` → falta `overall_score`
2. **MatchScoreCard NO debe mostrar 0%**: Si todos son 0% → problema con RequirementsModule
3. **No debe mostrar "Missing: [query text]"**: Si aparece → el query se usó como requirement

---

## 7. TeamBuildStructure

### Query Type: `team_build`

| # | Test Query | Language |
|---|----------------|--------|
| 7.1 | "Build a team of 3 developers" | EN |
| 7.2 | "Forma un equipo para proyecto web" | ES |
| 7.3 | "Assemble a frontend and backend team" | EN |
| 7.4 | "Create a balanced development team" | EN |

### Expected Structure

```
┌─────────────────────────────────────────────┐
│          TEAM BUILD STRUCTURE               │
├─────────────────────────────────────────────┤
│ ✅ ThinkingSection (collapsible)            │
│ ✅ TeamCompositionView                      │
│    ├── Proposed Team (assignments)          │
│    ├── Skill Coverage                       │
│    └── Team Risks                           │
│ ✅ AnalysisSection                          │
│ ✅ ConclusionSection                        │
└─────────────────────────────────────────────┘
```

### Backend Modules

| Module | File | Purpose |
|--------|---------|-----------|
| ThinkingModule | `thinking_module.py` | Extracts :::thinking::: |
| TeamRequirementsModule | `team_requirements_module.py` | Required roles |
| TeamCompositionModule | `team_composition_module.py` | Assignments |
| SkillCoverageModule | `skill_coverage_module.py` | Skills coverage |
| TeamRiskModule | `team_risk_module.py` | Team risks |
| AnalysisModule | `analysis_module.py` | Analysis |
| ConclusionModule | `conclusion_module.py` | Conclusion |

### Output Fields (structuredOutput)

```javascript
{
  structure_type: "team_build",
  thinking: "...",
  team_composition: {
    assignments: [
      { role_name: "...", candidate_name: "...", cv_id: "...", fit_score: 85, ... }
    ],
    unassigned_roles: [...]
  },
  skill_coverage: {
    overall_coverage: 80,
    gaps: [...]
  },
  team_risks: {
    risks: [...],
    overall_risk_level: "medium"
  },
  analysis: "...",
  conclusion: "..."
}
```

---

## 8. VerificationStructure

### Query Type: `verification`

| # | Test Query | Language |
|---|----------------|--------|
| 8.1 | "Verify if Juan has AWS certification" | EN |
| 8.2 | "Confirma que María trabajó en Google" | ES |
| 8.3 | "Check if candidate has 5+ years experience" | EN |
| 8.4 | "Does Juan have a Master's degree?" | EN |

### Expected Structure

```
┌─────────────────────────────────────────────┐
│         VERIFICATION STRUCTURE              │
├─────────────────────────────────────────────┤
│ ✅ ThinkingSection (collapsible)            │
│ ✅ VerificationResult                       │
│    ├── Claim (qué se verifica)              │
│    ├── Evidence (pruebas encontradas)       │
│    └── Verdict (CONFIRMED/PARTIAL/NOT FOUND)│
│ ✅ ConclusionSection                        │
└─────────────────────────────────────────────┘
```

### Backend Modules

| Module | File | Purpose |
|--------|---------|-----------|
| ThinkingModule | `thinking_module.py` | Extracts :::thinking::: |
| ClaimModule | `claim_module.py` | Parses the claim |
| EvidenceModule | `evidence_module.py` | Searches evidence in CV |
| VerdictModule | `verdict_module.py` | Issues verdict |
| ConclusionModule | `conclusion_module.py` | Conclusion |

### Output Fields (structuredOutput)

```javascript
{
  structure_type: "verification",
  thinking: "...",
  claim: {
    subject: "Juan Pérez",
    claim_type: "certification",
    claim_value: "AWS certification"
  },
  evidence: {
    evidence: [
      { source: "...", excerpt: "...", relevance: 0.9 }
    ],
    total_found: 2
  },
  verdict: {
    status: "CONFIRMED",  // CONFIRMED | PARTIAL | NOT_FOUND | CONTRADICTED
    confidence: 0.95,
    explanation: "..."
  },
  conclusion: "..."
}
```

---

## 9. SummaryStructure

### Query Type: `summary`

| # | Test Query | Language |
|---|----------------|--------|
| 9.1 | "Overview of all candidates" | EN |
| 9.2 | "Resumen del pool de talento" | ES |
| 9.3 | "Talent pool summary" | EN |
| 9.4 | "Give me statistics about candidates" | EN |

### Expected Structure

```
┌─────────────────────────────────────────────┐
│            SUMMARY STRUCTURE                │
├─────────────────────────────────────────────┤
│ ✅ ThinkingSection (collapsible)            │
│ ✅ PoolSummary                              │
│    ├── Talent Pool Overview (donut chart)   │
│    ├── Experience Distribution              │
│    └── Top Skills                           │
│ ✅ ConclusionSection                        │
└─────────────────────────────────────────────┘
```

### Backend Modules

| Module | File | Purpose |
|--------|---------|-----------|
| ThinkingModule | `thinking_module.py` | Extracts :::thinking::: |
| TalentPoolModule | `talent_pool_module.py` | Pool statistics |
| SkillDistributionModule | `skill_distribution_module.py` | Skills distribution |
| ExperienceDistributionModule | `experience_distribution_module.py` | Jr/Mid/Sr distribution |
| ConclusionModule | `conclusion_module.py` | Conclusion |

### Output Fields (structuredOutput)

```javascript
{
  structure_type: "summary",
  thinking: "...",
  talent_pool: {
    total_candidates: 15,
    experience_distribution: { junior: 3, mid: 7, senior: 4, principal: 1 }
  },
  skill_distribution: {
    skills: [
      { skill: "Python", candidate_count: 10, percentage: 66.7 }
    ]
  },
  experience_distribution: {
    average_years: 5.2,
    junior: 3,
    mid: 7,
    senior: 4,
    principal: 1
  },
  conclusion: "..."
}
```

---

# MATRIZ DE VERIFICACIÓN RÁPIDA

| Structure | Query Type | Componente Principal | Campo Crítico |
|-----------|------------|---------------------|---------------|
| SingleCandidate | `single_candidate` | SingleCandidateProfile | `single_candidate_data` |
| RiskAssessment | `red_flags` | RiskAssessmentProfile | `risk_assessment_data` |
| Comparison | `comparison` | CandidateTable | `table_data.rows` |
| Search | `search` | SearchResultsTable | `results_table.results` |
| Ranking | `ranking` | RankingTable + TopPick | `ranking_table.ranked` |
| JobMatch | `job_match` | MatchScoreCard + TopPick | `match_scores.matches` |
| TeamBuild | `team_build` | TeamCompositionView | `team_composition.assignments` |
| Verification | `verification` | VerificationResult | `verdict.status` |
| Summary | `summary` | PoolSummary | `talent_pool.total_candidates` |

---

# CHECKLIST DE DEBUGGING

## Si el componente no aparece:

1. **Verificar logs del backend:**
   ```
   [ORCHESTRATOR] ROUTING query_type=X
   [ORCHESTRATOR] Using XStructure
   ```

2. **Verificar consola del frontend:**
   ```
   [STRUCTURED_OUTPUT] ROUTING: structure_type=X
   ```

3. **Verificar que el campo existe en structuredOutput:**
   - Añadir `console.log(structuredOutput)` en el frontend
   - Verificar que el campo esperado tiene datos

4. **Verificar flujo de datos backend:**
   - Structure.assemble() devuelve los datos
   - Orchestrator._build_structured_output() los pasa a StructuredOutput
   - StructuredOutput.to_dict() los serializa correctamente

---

# TESTS DE CONTEXTO CONVERSACIONAL (NUEVO)

Estas queries prueban que el `conversation_history` fluye correctamente.

| # | Secuencia de Queries | Verificar |
|---|---------------------|-----------|
| C1 | 1. "Dame perfil de Juan" → 2. "¿Qué red flags tiene?" | La 2ª query debe detectar que se refiere a Juan |
| C2 | 1. "Compara Juan y María" → 2. "¿Cuál es mejor para backend?" | La 2ª debe usar mismo contexto de comparación |
| C3 | 1. "Busca developers Python" → 2. "¿Cuál tiene más experiencia?" | La 2ª debe filtrar en resultados previos |

---

*Documento actualizado: Enero 2026*
*Versión: 1.0*
