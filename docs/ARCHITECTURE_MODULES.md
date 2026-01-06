# CV Screener Architecture - Orchestration, Structures & Modules

> **Last Updated:** January 2026 - Full implementation complete (Phases 0-8) System (v6.0)

## Architecture Overview: MODULES vs STRUCTURES

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           NIVEL 1: MÓDULOS                                  │
│  (Componentes reutilizables - scripts en /modules/)                        │
├─────────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │
│  │ ThinkingModule  │  │ ConclusionModule│  │ DirectAnswerMod │            │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘            │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐            │
│  │ RiskTableModule │  │ TableModule     │  │ AnalysisModule  │            │
│  │ (5-factor table)│  │ (comparison)    │  │                 │            │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘            │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        NIVEL 2: ESTRUCTURAS                                 │
│  (Plantillas completas que combinan múltiples módulos)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │              SINGLE CANDIDATE STRUCTURE                              │  │
│  │  Thinking + Summary + Highlights + Career + Skills + RiskTable +     │  │
│  │  Conclusion                                                          │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │              RISK ASSESSMENT STRUCTURE                               │  │
│  │  Thinking + Risk Analysis + RiskTable (SAME MODULE!) + Assessment    │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │              COMPARISON STRUCTURE                                    │  │
│  │  Thinking + Analysis + CandidateTable + Conclusion                   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

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
