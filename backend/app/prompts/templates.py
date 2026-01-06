"""
LLM Prompt Templates for CV Screener RAG System.

This module provides a comprehensive set of prompt templates optimized for
CV analysis, candidate screening, and recruitment assistance. It implements
advanced prompt engineering techniques including structured reasoning,
guardrails, and dynamic context formatting.

Author: CV Screener RAG System
Version: 2.0.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, TypedDict, Callable
import re
from functools import lru_cache

from app.utils.debug_logger import log_enriched_metadata_extraction, log_event


# =============================================================================
# CONFIGURATION & CONSTANTS
# =============================================================================

class QueryType(Enum):
    """Classification of user query types for routing."""
    SEARCH = "search"              # Find candidates with X skill
    COMPARE = "compare"            # Compare candidates A vs B
    RANK = "rank"                  # Rank top N candidates for role
    SUMMARIZE = "summarize"        # Summarize a candidate's profile
    VERIFY = "verify"              # Verify specific claim about candidate
    AGGREGATE = "aggregate"        # Statistics across all CVs
    MATCH = "match"                # Match job description to candidates
    SINGLE_CANDIDATE = "single_candidate"  # Query about ONE specific candidate

class ResponseFormat(Enum):
    """Output format preferences."""
    FULL = "full"                  # Complete analysis with reasoning
    CONCISE = "concise"            # Brief, actionable response
    TABLE_ONLY = "table_only"      # Just the comparison table
    JSON = "json"                  # Structured JSON output


@dataclass(frozen=True)
class PromptConfig:
    """Configuration for prompt behavior."""
    max_candidates_in_table: int = 10
    show_confidence_scores: bool = True
    language: str = "auto"         # auto, en, es
    strict_mode: bool = True       # Stricter guardrails
    include_source_refs: bool = True
    reasoning_depth: str = "standard"  # minimal, standard, deep


DEFAULT_CONFIG = PromptConfig()


# =============================================================================
# TECHNICAL SKILLS TAXONOMY
# =============================================================================

TECHNICAL_SKILLS_TAXONOMY: dict[str, set[str]] = {
    "frontend": {
        "javascript", "typescript", "react", "vue", "angular", "svelte",
        "html", "css", "sass", "scss", "tailwind", "next.js", "nuxt",
        "webpack", "vite", "redux", "jquery", "bootstrap", "material-ui"
    },
    "backend": {
        "python", "java", "c#", "node.js", "go", "rust", "ruby", "php",
        "django", "flask", "fastapi", "spring", "express", ".net", "rails",
        "laravel", "graphql", "rest", "grpc"
    },
    "data": {
        "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
        "pandas", "numpy", "spark", "hadoop", "kafka", "airflow", "dbt",
        "tableau", "power bi", "data modeling"
    },
    "devops": {
        "docker", "kubernetes", "aws", "azure", "gcp", "terraform",
        "jenkins", "github actions", "gitlab ci", "ansible", "linux",
        "nginx", "prometheus", "grafana"
    },
    "ai_ml": {
        "machine learning", "deep learning", "tensorflow", "pytorch",
        "scikit-learn", "nlp", "computer vision", "llm", "transformers",
        "huggingface", "langchain", "openai", "rag"
    },
    "mobile": {
        "ios", "android", "swift", "kotlin", "react native", "flutter",
        "dart", "xamarin"
    }
}

NON_TECHNICAL_ROLES: set[str] = {
    "chef", "cook", "waiter", "bartender", "receptionist", "cleaner",
    "driver", "security", "cashier", "sales assistant", "publishing director",
    "editor", "journalist", "photographer", "artist", "concept artist",
    "illustrator", "graphic designer", "interior designer", "architect",
    "teacher", "professor", "nurse", "doctor", "lawyer", "accountant",
    "hr manager", "recruiter", "marketing manager", "event planner"
}

DESIGN_TOOLS_NOT_PROGRAMMING: set[str] = {
    "photoshop", "illustrator", "figma", "sketch", "indesign", "xd",
    "after effects", "premiere", "blender", "maya", "3ds max", "zbrush",
    "canva", "coreldraw"
}


# =============================================================================
# CORE SYSTEM PROMPT
# =============================================================================

SYSTEM_PROMPT = """You are an expert CV screening assistant with deep expertise in technical recruiting and talent assessment.

## IDENTITY & SCOPE
You EXCLUSIVELY handle CV analysis, candidate evaluation, and recruitment queries. For ANY off-topic request, respond:
> "I specialize in CV screening and candidate analysis. Please ask about the uploaded CVs, candidate qualifications, or hiring criteria."

## CORE PRINCIPLES

### 1. EVIDENCE-BASED ANALYSIS (STRICTLY ENFORCED)
- Extract information ONLY from provided CV text chunks
- NEVER infer, assume, or hallucinate skills/experience/names
- Use the EXACT candidate name from CV metadata - do NOT modify or translate names
- Use the EXACT cv_id provided in metadata - do NOT invent IDs
- Distinguish between explicit statements vs. reasonable inferences
- When uncertain, state: "The CV does not explicitly mention..."

**CRITICAL PROHIBITIONS:**
- NEVER include external URLs, websites, or links (e.g., github.com, linkedin.com, personal websites)
- NEVER change or translate candidate names
- NEVER attribute skills not explicitly mentioned in the CV
- NEVER invent or modify CV IDs

### 2. TECHNICAL ROLE ACCURACY
For developer/engineer/programmer roles, candidates MUST have EXPLICIT technical skills:

**Valid technical indicators:**
- Programming languages (Python, JavaScript, Java, etc.)
- Frameworks/libraries (React, Django, Spring, etc.)
- Technical tools (Docker, Git, AWS, etc.)
- Technical job titles with matching skills

**NOT valid for technical roles:**
- "Publishing Director" → NOT a developer
- "Chef" → NOT a programmer  
- "Concept Artist" → NOT frontend (unless HTML/CSS/JS listed)
- "Photoshop/Figma" alone → Design tools, NOT programming
- "Microsoft Office" → NOT technical skills

If NO candidate meets technical requirements, state clearly:
> "None of the analyzed candidates have the required technical skills for [role]."

### 3. RESPECT USER'S REQUESTED QUANTITY
**CRITICAL: If the user asks for N candidates (e.g., "top 3", "best 5"), you MUST provide EXACTLY N candidates.**
- If user asks for "top 3", provide 3 candidates even if only 1 is a perfect match
- Show the BEST AVAILABLE candidates, ranked by relevance
- Be honest about match quality (e.g., "partial match", "weak match") but NEVER omit candidates to meet requested count
- The Analysis section can include MORE candidates than requested for context
- The Conclusion should focus on the N requested candidates

### 4. HONEST ASSESSMENT
- Report negative findings ("weak match", "partial match") with same confidence as positive
- NEVER reduce the number of candidates below what the user requested
- Acknowledge when CV data is insufficient but still provide best available options

## RESPONSE STRUCTURE

Every response MUST follow this exact format:

```
:::thinking
[Internal reasoning process]
- What is being asked?
- What CVs/sections are relevant?
- Do any candidates actually match?
- What's my confidence level?
:::

[1-2 sentence direct answer to the question]

[Detailed analysis: table, comparison, or explanation as appropriate]

:::conclusion
[Actionable recommendation with candidate references]
[If no match: Clear statement + alternative suggestions if possible]
:::

## CANDIDATE REFERENCE FORMAT (MANDATORY)

Use this EXACT format for ALL candidate mentions - NO VARIATIONS:
**[Name](cv:cv_xxx)**

CORRECT: **[Juan García](cv:cv_12345678)**
WRONG: ** Juan García** cv_xxx [cv_xxx](cv_xxx) ❌
WRONG: **Juan García** cv_xxx ❌

RULES:
- NO spaces after ** or before **
- cv_id appears ONLY inside (cv:cv_xxx), not repeated elsewhere
- Use the exact name from CV metadata

## COMPARISON TABLES

Use this EXACT table format:
| Candidate | Skills | Experience | Match |
|-----------|--------|------------|-------|
| **[Name](cv:cv_xxx)** | Skills here | Experience here | ⭐⭐⭐ |

CRITICAL:
- Candidate column: ONLY **[Name](cv:cv_xxx)** format
- NO spaces inside **bold**
- Stars ⭐ (1-5) for match score

## SPECIAL CASES

If no candidates match, clearly state: "No candidates match the specified criteria." Then suggest alternatives if possible.

### Ambiguous Query
Ask ONE clarifying question, then proceed with best interpretation.

### Partial Matches
Report them transparently: "2 candidates partially match (missing X but have Y)."
"""


# =============================================================================
# QUERY TEMPLATES
# =============================================================================

QUERY_TEMPLATE = """## CV DATA CONTEXT
Retrieved: {num_chunks} excerpts from {num_cvs} candidate(s)
Total CVs in session: {total_cvs}

---
{context}
---

## USER QUERY
{question}

## MANDATORY RESPONSE FORMAT
You MUST respond using this exact structure:

:::thinking
[Your reasoning: What is being asked? Which candidates are relevant? What are the key criteria?]
:::

[Direct answer: 2-3 sentences directly answering the user's question. Start with a capital letter and provide context.]

### Analysis
[MANDATORY: Explain your reasoning for the selection shown in the table below. Why did you choose these specific candidates? What criteria did you use to evaluate them? If no candidates match, explain why you are showing certain candidates anyway (e.g., "I'm showing the closest matches even though none fully meet the criteria").]

[Table if comparing candidates - use EXACT format with NO spaces after **:
| Candidate | Criterion 1 | Criterion 2 | Match |
|-----------|-------------|-------------|-------|
| **[Name](cv:cv_xxx)** | Details | Details | ⭐⭐⭐ |
]

:::conclusion
[Actionable recommendation with specific candidate references using **[Name](cv:cv_xxx)** format]
:::

## CRITICAL RULES
- ALL sections (thinking, direct answer, analysis, table, conclusion) are MANDATORY
- Use **[Candidate Name](cv:CV_ID)** format for EVERY candidate mention - NO spaces after **
- The Analysis section MUST explain WHY you selected those candidates for the table
- Base everything on CV data only—no assumptions

## QUANTITY RULE (VERY IMPORTANT)
**If the user asks for N candidates (e.g., "top 3", "best 5", "dame los 3 mejores"):**
- The TABLE must contain EXACTLY N rows (or more for context)
- The CONCLUSION must reference EXACTLY N candidates
- NEVER return fewer candidates than requested
- Rank candidates by relevance: best match first, then partial matches, then weak matches
- Be honest about match quality but ALWAYS provide the requested quantity

Example: "dame los 3 mejores para QA" → Table with 3+ candidates, Conclusion mentions 3 candidates

Respond now:"""


QUERY_TEMPLATE_CONCISE = """## CV DATA ({num_chunks} excerpts, {num_cvs} candidates)
{context}

## QUERY: {question}

Provide a brief, direct answer. Use **[Name](cv:ID)** format for candidates.
Skip :::thinking block. Maximum 3 sentences + table if needed."""


QUERY_TEMPLATE_JSON = """## CV DATA
{context}

## QUERY: {question}

Respond in this exact JSON structure:
```json
{{
  "query_understood": "string - your interpretation of the query",
  "candidates_analyzed": number,
  "matches": [
    {{
      "name": "string",
      "cv_id": "string", 
      "match_score": number (0-100),
      "matching_criteria": ["string"],
      "missing_criteria": ["string"],
      "key_evidence": "string - quote from CV"
    }}
  ],
  "recommendation": "string",
  "confidence": "high|medium|low",
  "notes": "string - any caveats or additional context"
}}
"""

# =============================================================================
# SINGLE CANDIDATE TEMPLATE (Individual Analysis - NO Comparisons)
# =============================================================================

SINGLE_CANDIDATE_TEMPLATE = """## SINGLE CANDIDATE PROFILE ANALYSIS
**Target:** {candidate_name}
**CV ID:** {cv_id}

---
{context}
---

## USER QUERY
{question}

## QUERY-SPECIFIC RESPONSE RULES

### IF THE QUERY IS ABOUT RED FLAGS:
When the user asks about "red flags", "problemas", "concerns", "issues", or "banderas rojas":

1. **START YOUR RESPONSE BY DIRECTLY ADDRESSING RED FLAGS**
   - If there ARE red flags: "⚠️ **Se detectaron las siguientes red flags para [Name]:**..."
   - If there are NO red flags: "✅ **No se detectaron red flags significativas para [Name].** Su perfil muestra..."

2. **ALWAYS reference the pre-calculated metrics** in the Red Flags Analysis section below
3. **Focus your analysis on stability indicators**: job hopping score, average tenure, employment gaps
4. **Only show the abbreviated CV profile AFTER addressing the red flags question**

**Example response when NO red flags exist:**
```
:::thinking
Analyzing red flags for Carmen Rodriguez...
:::

✅ **No se detectaron red flags significativas para Carmen Rodriguez.**

Su perfil demuestra una trayectoria profesional estable:
- **Estabilidad laboral**: 4 años promedio por posición (excelente)  
- **Progresión de carrera**: Ascenso constante desde roles junior hasta C-level
- **Sin gaps de empleo**: Historial continuo sin interrupciones

[Brief profile summary - NOT the full CV]
```

---

## CRITICAL DATA EXTRACTION RULES (READ CAREFULLY)

### CURRENT ROLE DEFINITION
**Current Role = The MOST RECENT job** (the one with "Present" or the highest/most recent year)
- CVs list jobs in REVERSE chronological order (newest first)
- The FIRST job listed is typically the CURRENT role
- Look for "Present", "Actual", "Current" or the most recent year (e.g., 2023-Present)
- NEVER show an old job as "Current Role"

### TOTAL EXPERIENCE CALCULATION
**Total Experience = From EARLIEST job start year to NOW (or most recent end date)**
- Find the OLDEST job's start year
- Calculate: Current Year (or latest end year) - Oldest Start Year
- Example: Jobs from 2018-2021, 2021-2023, 2023-Present = **6+ years** (2018 to Present)

### CAREER TRAJECTORY
**Include ALL positions listed in the CV**, not just one
- List in reverse chronological order (newest first)
- Each position with its KEY achievement

---

## RESPONSE FORMAT

:::thinking
[Brief reasoning - 2-3 lines max]
- What is {candidate_name}'s CURRENT role? (Look for "Present" or most recent dates)
- How many TOTAL years of experience? (From oldest job to newest)
- What are ALL their positions?
:::

## 👤 **[{candidate_name}](cv:{cv_id})**

[One paragraph summary highlighting their CURRENT position and career progression. Be specific and accurate.]

---

### 📊 Candidate Highlights

| Category | Key Information |
|:---------|:----------------|
| **🎯 Current Role** | [MOST RECENT job title at Company (Year-Present)] |
| **⏱️ Total Experience** | [Calculate: from oldest job year to now] years in [field] |
| **🏆 Top Achievement** | [From their CURRENT or most senior role - with metrics] |
| **💡 Core Expertise** | [Top 3 skills from their highest-rated skills] |
| **🎓 Education** | [Highest degree - Institution, Year] |

---

### 💼 Career Trajectory

[List ALL positions from the CV in reverse chronological order]

**[Most Recent Job Title]** — *[Company]* ([Year-Present])
→ [Key achievement with metrics]

**[Previous Job Title]** — *[Company]* ([Year-Year])
→ [Key achievement]

**[Earlier Job Title]** — *[Company]* ([Year-Year])
→ [Key achievement]

[Continue for ALL positions in CV]

---

### 🛠️ Skills Snapshot

| Skill Area | Details | Level |
|:-----------|:--------|:------|
| **[Category]** | [Skills] | [X/10 if provided] |

---

### Credentials

[Only if present in CV]

- [Certification, Year]
- [Award or Course, Year]

---

### Risk Assessment

{risk_assessment_section}

---

:::conclusion
**Overall Assessment:** [Summary based on CURRENT role, career trajectory, and analysis modules above]

**Key Strengths:**
- [Strength from CURRENT role]
- [Strength from skills/achievements]
- [Strength from analysis modules - e.g., stable career, no gaps]

**Areas to Explore:**
[Based on analysis modules - if red flags exist, list them. Otherwise: "No significant concerns identified. Candidate appears to have a stable career trajectory."]
:::

## VALIDATION CHECKLIST (Before responding)
 Current Role shows the MOST RECENT position (with "Present" or latest year)
 Total Experience calculated from OLDEST job to PRESENT
 Career Trajectory includes ALL positions, not just one
 Top Achievement is from senior/current role, not oldest role
 Skills reflect highest proficiency levels mentioned
 Red flags section addresses any job-hopping, gaps, or concerns

Respond now:"""
# =============================================================================
# =============================================================================
# RED FLAGS SPECIFIC TEMPLATE (Red flags analysis FIRST, profile SECOND)
# =============================================================================

RED_FLAGS_TEMPLATE = """## RED FLAGS ANALYSIS REQUEST
**Target Candidate:** {candidate_name}
**CV ID:** {cv_id}

---
{context}
---

## USER QUERY
{question}

## IMPORTANT: THIS IS A RED FLAGS / RISK ANALYSIS QUERY
The user is asking about red flags, risks, concerns, or issues for this candidate.

## PRE-CALCULATED RISK ASSESSMENT DATA (COPY THIS TABLE EXACTLY)
{risk_assessment_section}

---

## MANDATORY RESPONSE FORMAT

:::thinking
[Brief analysis of the pre-calculated data above - 2-3 lines max]
:::

### 🚩 Risk Analysis for **[{candidate_name}](cv:{cv_id})**

[Based on the pre-calculated data, provide ONE of these assessments:]

**IF CLEAN PROFILE:**
✅ **No significant red flags detected for {candidate_name}.**

**IF ISSUES FOUND:**
⚠️ **Risk factors identified for {candidate_name}:**
- [List specific concerns from the data]

---

### ⚠️ Risk Assessment

{risk_assessment_section}

---

:::conclusion
**Assessment:** [1-2 sentences summarizing the risk profile based on the table above]
:::

Respond now:"""

# =============================================================================
# COMPARISON TEMPLATE
# =============================================================================

COMPARISON_TEMPLATE = """## COMPARISON REQUEST
Criteria: {criteria}

## CV DATA
{context}

## INSTRUCTIONS
Create a structured comparison addressing each criterion.

Format:
:::thinking
[Analyze each candidate against each criterion]
:::

[Brief overview of comparison findings]

| Candidate | {criteria_headers} | Overall |
|-----------|{criteria_separators}|---------|
[Data rows with **[Name](cv:ID)** format]

:::conclusion
[Ranked recommendation based on criteria alignment]
:::

Only include information explicitly stated in CVs. 
Mark missing data as "Not specified" rather than inferring."""

# =============================================================================
# RANKING TEMPLATE
# =============================================================================

RANKING_TEMPLATE = """## RANKING REQUEST
Role: {role}
Criteria: {criteria}
Number of candidates to rank: {top_n}

## CV DATA
{context}

## INSTRUCTIONS
Rank the top {top_n} candidates for {role} based on the specified criteria.

:::thinking
[Evaluate each candidate against role requirements]
[Consider both matching and missing qualifications]
:::

[Brief statement of ranking methodology]

### Rankings

1. **[Name](cv:ID)** - [Score/Rating]
   - Strengths: ...
   - Gaps: ...

[Continue for top N]

### Not Ranked (insufficient match)
[List any candidates who don't meet minimum requirements]

:::conclusion
[Summary recommendation with confidence level]
:::"""


VERIFICATION_TEMPLATE = """## VERIFICATION REQUEST
Claim to verify: "{claim}"
Candidate: {candidate_name}

## CV DATA
{context}

## INSTRUCTIONS
Verify whether the claim is supported by the CV data.

:::thinking
[Search for evidence supporting or contradicting the claim]
:::

**Verification Result:** [CONFIRMED / PARTIALLY CONFIRMED / NOT FOUND / CONTRADICTED]

Evidence from CV:
> "[Relevant quote from CV]"

:::conclusion
[Clear statement on claim validity with CV reference]
:::"""


SUMMARIZE_TEMPLATE = """## SUMMARIZATION REQUEST
Candidate: {candidate_name}
Focus areas: {focus_areas}

## CV DATA
{context}

## INSTRUCTIONS
Provide a concise professional summary of **[{candidate_name}](cv:{cv_id})**.

:::thinking
[Identify key qualifications, experience, and notable achievements]
:::

### Professional Summary

**Current/Most Recent Role:** [Role at Company]
**Experience:** [X years in field/industry]
**Key Skills:** [Top 5-7 skills from CV]

**Career Highlights:**
- [Notable achievement 1]
- [Notable achievement 2]
- [Notable achievement 3]

**Education:** [Highest degree, institution]

:::conclusion
[2-3 sentence executive summary positioning candidate for roles]
:::"""


JOB_MATCH_TEMPLATE = """## JOB MATCHING REQUEST

### Job Requirements
{job_description}

### Required Skills (must have)
{required_skills}

### Preferred Skills (nice to have)  
{preferred_skills}

## CV DATA
{context}

## INSTRUCTIONS
Match candidates to this job description.

:::thinking
[Analyze each candidate against required and preferred skills]
[Calculate match percentages]
:::

[Overview of matching results]

| Candidate | Required Skills | Preferred Skills | Experience Match | Overall Fit |
|-----------|-----------------|------------------|------------------|-------------|
[Use **[Name](cv:ID)** format, ✅/❌/⚠️ for skills]

### Detailed Analysis

**Strong Matches (>70%):**
[Analysis of top candidates]

**Partial Matches (40-70%):**
[Analysis with gaps highlighted]

**Not Recommended (<40%):**
[Brief explanation of disqualification]

:::conclusion
[Ranked recommendation for interview shortlist]
:::"""


AGGREGATE_TEMPLATE = """## AGGREGATE ANALYSIS REQUEST
Analysis type: {analysis_type}
Scope: All {num_cvs} CVs in session

## CV DATA
{context}

## INSTRUCTIONS
Provide aggregate statistics and insights.

:::thinking
[Compile data points across all CVs]
:::

### {analysis_type} Analysis

[Relevant statistics, distributions, or patterns]

[Visualization if appropriate - use simple ASCII charts]

:::conclusion
[Key insights and patterns discovered]
:::"""


# =============================================================================
# ERROR & EDGE CASE TEMPLATES
# =============================================================================

NO_RESULTS_TEMPLATE = """:::thinking
The user asked: "{question}"
After searching {num_cvs} CVs, I found no relevant matches.
Possible reasons: criteria too specific, skills described differently, or not present.
:::

**No matching candidates found.**

I searched through {num_cvs} CV(s) for: "{question}"

No candidates in the current dataset match this criteria. This could mean:
- None of the candidates have these specific qualifications
- The skills might be described using different terminology
- The experience level or requirements are not met

:::conclusion
**No suitable candidates found.**

Suggestions:
- Try broader search terms (e.g., "JavaScript" instead of "React 18")
- Search for related skills or technologies
- Check for alternative job titles or role descriptions
:::"""


NO_CVS_TEMPLATE = """**No CVs have been uploaded yet.**

To begin screening candidates:
1. Upload one or more CV files (PDF, DOCX, or TXT)
2. Wait for processing confirmation
3. Ask questions about the candidates

Example queries you can use after uploading:
- "Who has experience with Python?"
- "List all candidates with a Master's degree"
- "Compare candidates for a senior developer role"
"""


AMBIGUOUS_QUERY_TEMPLATE = """:::thinking
The query "{question}" is ambiguous. Multiple interpretations possible:
{interpretations}
:::

I want to give you the most accurate answer. Could you clarify:

**{clarifying_question}**

In the meantime, here's what I found assuming {assumed_interpretation}:

{preliminary_answer}

:::conclusion
Please clarify your query for a more precise analysis.
:::"""


OFF_TOPIC_RESPONSE = """I specialize exclusively in CV screening and candidate analysis.

**I can help you with:**
- Finding candidates with specific skills or experience
- Comparing candidates for a role
- Summarizing candidate profiles
- Verifying candidate qualifications
- Matching candidates to job descriptions

**Your question appears to be about:** {detected_topic}

Please rephrase your question to focus on the uploaded CVs or candidate evaluation."""


GUARDRAIL_VIOLATION_RESPONSE = """I cannot process this request as it falls outside my designated function.

As a CV screening assistant, I'm designed to:
✅ Analyze uploaded CVs and candidate qualifications
✅ Compare candidates based on skills and experience
✅ Provide recruitment-focused insights

I cannot:
❌ {specific_violation}

Please ask a question related to CV analysis or candidate screening."""


# =============================================================================
# WELCOME & HELP MESSAGES
# =============================================================================

WELCOME_MESSAGE = """# CV Screening Assistant

I'm ready to help you analyze candidate CVs. Here's what I can do:

## Quick Start Commands

| Command Type | Example |
|--------------|---------|
| **Search** | "Who has Python experience?" |
| **Compare** | "Compare Juan and María for the developer role" |
| **Rank** | "Rank top 5 candidates for senior backend" |
| **Summarize** | "Summarize Ana García's profile" |
| **Verify** | "Does Pedro have AWS certification?" |
| **Match** | "Match candidates to this job description: [paste JD]" |

## Tips for Best Results

- Be specific: "Python with Django" > "programming skills"
- Specify experience levels: "5+ years in Java"
- Mention required vs. preferred skills
- Ask about specific companies or industries

## Current Session
CVs loaded: {num_cvs}
Ready to query: {ready_status}

*All responses are based solely on uploaded CV content.*"""


HELP_MESSAGE = """## CV Screening Assistant - Help

### Available Query Types

**1. Skill Search**
- "Who knows React and TypeScript?"
- "Find candidates with machine learning experience"
- "List everyone with AWS certifications"

**2. Experience Filters**
- "Candidates with 5+ years in software development"
- "Who has worked at FAANG companies?"
- "Find senior-level engineers"

**3. Education**
- "Who has a Computer Science degree?"
- "Candidates with Master's or PhD"
- "Anyone from Stanford or MIT?"

**4. Location**
- "Candidates based in Madrid"
- "Who can work remotely?"
- "Find candidates in the EU"

**5. Comparisons**
- "Compare top 3 Python developers"
- "Juan vs María for tech lead role"
- "Rank candidates by React experience"

**6. Job Matching**
Paste a job description and ask:
- "Match candidates to this role: [JD]"
- "Who fits this job description best?"

### Response Format
All responses include:
- Reasoning (:::thinking block)
- Direct answer with evidence
- Clickable candidate references
- Actionable conclusion

### Limitations
- Only information in uploaded CVs is used
- Cannot verify external claims
- Cannot access internet or external databases
"""


# =============================================================================
# CONTEXT FORMATTING UTILITIES
# =============================================================================

@dataclass
class ChunkMetadata:
    """Structured metadata for a CV chunk."""
    cv_id: str
    filename: str
    candidate_name: str
    section_type: str
    page_number: int | None = None
    chunk_index: int | None = None
    total_chunks: int | None = None
    
    @classmethod
    def from_dict(cls, data: dict) -> ChunkMetadata:
        return cls(
            cv_id=data.get("cv_id", "unknown"),
            filename=data.get("filename", "Unknown"),
            candidate_name=data.get("candidate_name", "Unknown"),
            section_type=data.get("section_type", "general"),
            page_number=data.get("page_number"),
            chunk_index=data.get("chunk_index"),
            total_chunks=data.get("total_chunks")
        )


@dataclass 
class FormattedContext:
    """Result of context formatting operation."""
    text: str
    num_chunks: int
    num_unique_cvs: int
    candidate_names: list[str]
    cv_ids: list[str]
    

def format_context(
    chunks: list[dict],
    include_metadata: bool = True,
    max_chunk_length: int | None = None
) -> FormattedContext:
    """
    Format retrieved chunks into context string for the prompt.
    
    Args:
        chunks: List of chunk dictionaries with content and metadata
        include_metadata: Whether to include full metadata headers
        max_chunk_length: Optional truncation limit per chunk
        
    Returns:
        FormattedContext with formatted text and statistics
    """
    if not chunks:
        return FormattedContext(
            text="No relevant CV excerpts found.",
            num_chunks=0,
            num_unique_cvs=0,
            candidate_names=[],
            cv_ids=[]
        )
    
    context_parts: list[str] = []
    unique_cvs: set[str] = set()
    candidate_names: list[str] = []
    cv_ids: list[str] = []
    seen_candidates: set[str] = set()
    # Map: (candidate_name, content_signature) -> cv_id
    # This allows same name with DIFFERENT content to be treated as different people
    candidate_content_to_cv_id: dict[tuple[str, str], str] = {}
    # Track cv_ids we've already included to avoid duplicates
    included_cv_ids: set[str] = set()
    
    chunk_counter = 0
    for chunk in chunks:
        metadata = ChunkMetadata.from_dict(chunk.get("metadata", {}))
        content = chunk.get("content", "").strip()
        
        # SMART DEDUPLICATION:
        # - Same name + same/similar content = same person (duplicate CV upload)
        # - Same name + different content = different people (keep both)
        candidate_key = metadata.candidate_name.lower().strip() if metadata.candidate_name else ""
        
        # Create a content signature from first 200 chars (captures role/title usually)
        content_signature = content[:200].lower() if content else ""
        
        if candidate_key:
            # Check if this exact (name, content) combination exists
            is_duplicate = False
            for (stored_name, stored_sig), stored_cv_id in candidate_content_to_cv_id.items():
                if stored_name == candidate_key:
                    # Same name - check if content is similar (>70% overlap in signature)
                    if stored_cv_id != metadata.cv_id:
                        # Different cv_id - check content similarity
                        overlap = sum(1 for a, b in zip(content_signature, stored_sig) if a == b)
                        similarity = overlap / max(len(content_signature), len(stored_sig), 1)
                        if similarity > 0.7:
                            # Same person, duplicate CV - skip
                            is_duplicate = True
                            break
            
            if is_duplicate:
                continue
            
            # Not a duplicate - register this chunk
            if metadata.cv_id not in included_cv_ids:
                candidate_content_to_cv_id[(candidate_key, content_signature)] = metadata.cv_id
                included_cv_ids.add(metadata.cv_id)
                candidate_names.append(metadata.candidate_name)
                cv_ids.append(metadata.cv_id)
                seen_candidates.add(metadata.candidate_name)
        
        if max_chunk_length and len(content) > max_chunk_length:
            content = content[:max_chunk_length] + "... [truncated]"
        
        unique_cvs.add(metadata.filename)
        
        if include_metadata:
            header = (
                f"### CV #{chunk_counter+1}: {metadata.candidate_name}\n"
                f"- **CV_ID:** `{metadata.cv_id}`\n"
                f"- **File:** {metadata.filename}\n"
                f"- **Section:** {metadata.section_type}"
            )
            if metadata.page_number:
                header += f"\n- **Page:** {metadata.page_number}"
            
            context_parts.append(f"{header}\n\n{content}")
        else:
            context_parts.append(
                f"[{metadata.candidate_name} | {metadata.cv_id}]\n{content}"
            )
    
    return FormattedContext(
        text="\n\n---\n\n".join(context_parts),
        num_chunks=len(chunks),
        num_unique_cvs=len(unique_cvs),
        candidate_names=candidate_names,
        cv_ids=cv_ids
    )


def format_context_minimal(chunks: list[dict]) -> tuple[str, int, int]:
    """
    Legacy format_context function for backward compatibility.
    
    Returns:
        Tuple of (context_string, num_chunks, num_unique_cvs)
    """
    result = format_context(chunks, include_metadata=True)
    return result.text, result.num_chunks, result.num_unique_cvs


# =============================================================================
# PROMPT BUILDERS
# =============================================================================

class PromptBuilder:
    """Builder class for constructing prompts with various configurations."""
    
    def __init__(self, config: PromptConfig = DEFAULT_CONFIG):
        self.config = config
    
    def build_query_prompt(
        self,
        question: str,
        chunks: list[dict],
        total_cvs: int | None = None,
        response_format: ResponseFormat = ResponseFormat.FULL,
        conversation_history: list[dict[str, str]] | None = None
    ) -> str:
        """
        Build the complete query prompt with context.
        
        Args:
            question: User's question
            chunks: Retrieved CV chunks
            total_cvs: Total CVs in session (if known)
            response_format: Desired response format
            conversation_history: Recent chat history for context
            
        Returns:
            Formatted prompt string
        """
        ctx = format_context(chunks)
        actual_total = total_cvs if total_cvs is not None else ctx.num_unique_cvs
        
        template = {
            ResponseFormat.FULL: QUERY_TEMPLATE,
            ResponseFormat.CONCISE: QUERY_TEMPLATE_CONCISE,
            ResponseFormat.JSON: QUERY_TEMPLATE_JSON,
            ResponseFormat.TABLE_ONLY: QUERY_TEMPLATE_CONCISE,
        }.get(response_format, QUERY_TEMPLATE)
        
        # Build conversation history section if available
        history_section = ""
        if conversation_history:
            history_section = "## CONVERSATION HISTORY\n"
            for msg in conversation_history:
                role_label = "Usuario" if msg["role"] == "user" else "Asistente"
                history_section += f"{role_label}: {msg['content']}\n"
            history_section += "\n---\n\n"
        
        # Insert history before CV data context
        formatted_prompt = template.format(
            context=ctx.text,
            question=question,
            num_chunks=ctx.num_chunks,
            num_cvs=ctx.num_unique_cvs,
            total_cvs=actual_total
        )
        
        if history_section:
            # Insert after first line (before CV DATA CONTEXT)
            lines = formatted_prompt.split('\n', 1)
            if len(lines) > 1:
                formatted_prompt = history_section + formatted_prompt
            else:
                formatted_prompt = history_section + formatted_prompt
        
        return formatted_prompt
    
    def build_comparison_prompt(
        self,
        criteria: str | list[str],
        chunks: list[dict]
    ) -> str:
        """Build a comparison prompt for multiple candidates."""
        ctx = format_context(chunks)
        
        if isinstance(criteria, list):
            criteria_str = ", ".join(criteria)
            headers = " | ".join(criteria)
            separators = "|".join(["---"] * len(criteria))
        else:
            criteria_str = criteria
            headers = criteria
            separators = "---"
        
        return COMPARISON_TEMPLATE.format(
            criteria=criteria_str,
            criteria_headers=headers,
            criteria_separators=separators,
            context=ctx.text
        )
    
    def build_ranking_prompt(
        self,
        role: str,
        criteria: str | list[str],
        chunks: list[dict],
        top_n: int = 5
    ) -> str:
        """Build a ranking prompt for top N candidates."""
        ctx = format_context(chunks)
        criteria_str = ", ".join(criteria) if isinstance(criteria, list) else criteria
        
        return RANKING_TEMPLATE.format(
            role=role,
            criteria=criteria_str,
            top_n=top_n,
            context=ctx.text
        )
    
    def build_verification_prompt(
        self,
        claim: str,
        candidate_name: str,
        chunks: list[dict]
    ) -> str:
        """Build a verification prompt for a specific claim."""
        ctx = format_context(chunks)
        
        return VERIFICATION_TEMPLATE.format(
            claim=claim,
            candidate_name=candidate_name,
            context=ctx.text
        )
    
    def build_summary_prompt(
        self,
        candidate_name: str,
        cv_id: str,
        chunks: list[dict],
        focus_areas: str | list[str] = "all relevant areas"
    ) -> str:
        """Build a summarization prompt for a candidate."""
        ctx = format_context(chunks)
        focus = ", ".join(focus_areas) if isinstance(focus_areas, list) else focus_areas
        
        return SUMMARIZE_TEMPLATE.format(
            candidate_name=candidate_name,
            cv_id=cv_id,
            focus_areas=focus,
            context=ctx.text
        )
    
    def build_job_match_prompt(
        self,
        job_description: str,
        required_skills: list[str],
        preferred_skills: list[str],
        chunks: list[dict]
    ) -> str:
        """Build a job matching prompt."""
        ctx = format_context(chunks)
        
        return JOB_MATCH_TEMPLATE.format(
            job_description=job_description,
            required_skills="\n".join(f"- {s}" for s in required_skills),
            preferred_skills="\n".join(f"- {s}" for s in preferred_skills),
            context=ctx.text
        )
    
    def build_no_results_response(
        self,
        question: str,
        num_cvs: int
    ) -> str:
        """Build a response for when no results are found."""
        return NO_RESULTS_TEMPLATE.format(
            question=question,
            num_cvs=num_cvs
        )
    
    def build_single_candidate_prompt(
        self,
        question: str,
        candidate_name: str,
        cv_id: str,
        chunks: list[dict],
        conversation_history: list[dict[str, str]] | None = None
    ) -> str:
        """
        Build a prompt for analyzing a SINGLE specific candidate.
        
        This template is completely separate from comparison templates.
        It focuses entirely on one candidate without any comparisons.
        
        Args:
            question: User's question about the candidate
            candidate_name: Name of the target candidate
            cv_id: CV ID of the target candidate
            chunks: Retrieved CV chunks (should be filtered to this candidate)
            conversation_history: Recent chat history for context
            
        Returns:
            Formatted prompt string for single candidate analysis
        """
        ctx = format_context(chunks)
        
        # Extract enriched metadata for modular analysis sections
        sections = self._extract_enriched_metadata(chunks)
        
        # Build conversation history section if available
        history_section = ""
        if conversation_history:
            history_section = "## CONVERSATION HISTORY\n"
            for msg in conversation_history:
                role_label = "Usuario" if msg["role"] == "user" else "Asistente"
                history_section += f"{role_label}: {msg['content']}\n"
            history_section += "\n---\n\n"
        
        # DETECT RED FLAGS QUERIES - Use specialized template
        is_red_flags_query = self._is_red_flags_query(question)
        
        if is_red_flags_query:
            # Use RED_FLAGS_TEMPLATE which puts red flags analysis FIRST
            formatted_prompt = RED_FLAGS_TEMPLATE.format(
                candidate_name=candidate_name,
                cv_id=cv_id,
                context=ctx.text,
                question=question,
                risk_assessment_section=sections["risk_assessment"]
            )
        else:
            # Use standard SINGLE_CANDIDATE_TEMPLATE with Risk Assessment data
            formatted_prompt = SINGLE_CANDIDATE_TEMPLATE.format(
                candidate_name=candidate_name,
                cv_id=cv_id,
                context=ctx.text,
                question=question,
                risk_assessment_section=sections["risk_assessment"]
            )
        
        # Prepend history if available
        if history_section:
            formatted_prompt = history_section + formatted_prompt
        
        return formatted_prompt
    
    def _is_red_flags_query(self, question: str) -> bool:
        """Detect if the user's question is specifically about red flags."""
        question_lower = question.lower()
        red_flags_keywords = [
            "red flag", "redflags", "red-flag",
            "bandera roja", "banderas rojas",
            "problema", "problemas", "concern", "concerns", "issue", "issues",
            "warning", "warnings", "alert", "alertas",
            "job hopping", "job-hopping", "cambio de trabajo",
            "gap", "gaps", "hueco", "huecos",
            "estabilidad", "stability", "inestabilidad", "unstable",
            "riesgo", "risk", "risky"
        ]
        for keyword in red_flags_keywords:
            if keyword in question_lower:
                return True
        return False
    
    def _extract_enriched_metadata(self, chunks: list[dict]) -> dict[str, str]:
        """Extract enriched metadata from chunks for Risk Assessment module."""
        import logging
        logger = logging.getLogger(__name__)
        
        # Default values
        sections = {
            "risk_assessment": "| Factor | Status | Details |\n|--------|--------|---------||\n| Data | N/A | No pre-calculated metrics available |",
            "red_flags": "**Status:** N/A",
            "stability_metrics": "**Status:** N/A"
        }
        
        for i, chunk in enumerate(chunks):
            meta = chunk.get("metadata", {})
            if i == 0:
                logger.info(f"[ENRICHED_METADATA] First chunk keys: {list(meta.keys())}")
            
            job_hopping_score = meta.get("job_hopping_score")
            total_exp = meta.get("total_experience_years")
            avg_tenure = meta.get("avg_tenure_years")
            position_count = meta.get("position_count")
            employment_gaps = meta.get("employment_gaps_count", 0)
            current_role = meta.get("current_role", "N/A")
            current_company = meta.get("current_company", "N/A")
            
            if job_hopping_score is not None or total_exp is not None:
                score = float(job_hopping_score) if job_hopping_score else 0
                tenure = float(avg_tenure) if avg_tenure else 0
                exp = float(total_exp) if total_exp else 0
                gaps = int(employment_gaps) if employment_gaps else 0
                
                # Determine statuses
                if score < 0.3:
                    jh_status, jh_icon = "Low", "✅"
                elif score < 0.5:
                    jh_status, jh_icon = "Moderate", "⚡"
                else:
                    jh_status, jh_icon = "High", "⚠️"
                
                gaps_status = "None" if gaps == 0 else f"{gaps} detected"
                gaps_icon = "✅" if gaps == 0 else "⚠️"
                
                stability = "Stable" if score < 0.3 else "Moderate" if score < 0.6 else "Unstable"
                stability_icon = "✅" if score < 0.3 else "⚡" if score < 0.6 else "⚠️"
                
                exp_level = "Entry" if exp < 3 else "Mid" if exp < 7 else "Senior" if exp < 15 else "Executive"
                
                has_flags = score > 0.5 or tenure < 1.5 or gaps > 0
                rf_status = "Issues Found" if has_flags else "None Detected"
                rf_icon = "⚠️" if has_flags else "✅"
                
                # Build unified Risk Assessment table
                sections["risk_assessment"] = f"""| Factor | Status | Details |
|:-------|:------:|:--------|
| **🚩 Red Flags** | {rf_icon} {rf_status} | {"High mobility or gaps" if has_flags else "Clean profile"} |
| **🔄 Job Hopping** | {jh_icon} {jh_status} | Score: {score:.0%}, Avg tenure: {tenure:.1f} yrs |
| **⏸️ Employment Gaps** | {gaps_icon} {gaps_status} | {"Continuous history" if gaps == 0 else "Verify in interview"} |
| **📊 Stability** | {stability_icon} {stability} | {position_count or 'N/A'} positions over {exp:.0f} years |
| **🎯 Experience** | {exp_level} | {current_role} @ {current_company} |"""
                
                sections["red_flags"] = f"{rf_icon} **{rf_status}**" if not has_flags else f"{rf_icon} **Issues:** High mobility ({score:.0%})"
                sections["stability_metrics"] = f"| Metric | Value |\n|--------|-------|\n| **Experience** | {exp:.1f} years |\n| **Avg Tenure** | {tenure:.1f} yrs |\n| **Stability** | {stability} |"
                
                break
        
        return sections

@lru_cache(maxsize=128)
def classify_query(question: str) -> QueryType:
    """
    Classify a user query to determine the appropriate template.
    
    Args:
        question: The user's question
        
    Returns:
        QueryType enum value
    """
    q = question.lower()
    
    # Comparison patterns
    if any(p in q for p in ["compare", "vs", "versus", "difference between", "mejor entre"]):
        return QueryType.COMPARE
    
    # Ranking patterns
    if any(p in q for p in ["rank", "top", "best", "order by", "mejores", "ordenar"]):
        return QueryType.RANK
    
    # Summarization patterns
    if any(p in q for p in ["summarize", "summary", "profile", "resume", "resumen", "perfil"]):
        return QueryType.SUMMARIZE
    
    # Verification patterns
    if any(p in q for p in ["verify", "confirm", "does", "did", "has", "have", "verificar", "tiene"]):
        return QueryType.VERIFY
    
    # Aggregation patterns
    if any(p in q for p in ["how many", "count", "total", "average", "statistics", "cuántos"]):
        return QueryType.AGGREGATE
    
    # Job matching patterns
    if any(p in q for p in ["match", "fit", "suitable for", "job description", "encaja"]):
        return QueryType.MATCH
    
    # Default to search
    return QueryType.SEARCH


def is_technical_query(question: str) -> bool:
    """Check if query is asking for technical/developer candidates."""
    technical_keywords = {
        "developer", "engineer", "programmer", "coding", "software",
        "frontend", "backend", "full stack", "fullstack", "devops",
        "desarrollador", "ingeniero", "programador"
    }
    q = question.lower()
    return any(kw in q for kw in technical_keywords)


def detect_off_topic(question: str) -> tuple[bool, str | None]:
    """
    Detect if a question is off-topic for CV screening.
    
    Returns:
        Tuple of (is_off_topic, detected_topic)
    """
    off_topic_patterns = {
        r"\b(weather|clima)\b": "weather",
        r"\b(recipe|receta|cook|cocinar)\b": "cooking",
        r"\b(joke|chiste|funny)\b": "entertainment",
        r"\b(write (me )?a (story|poem|song))\b": "creative writing",
        r"\b(translate|traducir)\b": "translation",
        r"\b(code|program|script)(?!.*(candidate|cv|resume|experience))": "general programming",
        r"\b(investment|stock|crypto)\b": "finance",
    }
    
    q = question.lower()
    for pattern, topic in off_topic_patterns.items():
        if re.search(pattern, q):
            return True, topic
    
    return False, None


# =============================================================================
# SINGLE CANDIDATE DETECTION
# =============================================================================

@dataclass
class SingleCandidateDetection:
    """Result of single candidate detection."""
    is_single_candidate: bool
    candidate_name: str | None = None
    cv_id: str | None = None
    confidence: float = 0.0
    detection_method: str = "none"


def detect_single_candidate_query(
    question: str,
    chunks: list[dict],
    candidate_names: list[str] | None = None
) -> SingleCandidateDetection:
    """
    Detect if a query is about a SINGLE specific candidate.
    
    This function determines whether to use SINGLE_CANDIDATE_TEMPLATE
    or the standard QUERY_TEMPLATE (for comparisons/multiple candidates).
    
    Detection methods (in priority order):
    1. Explicit name mention in query
    2. Only one unique candidate in retrieved chunks
    3. Query patterns indicating single focus
    
    Args:
        question: User's question
        chunks: Retrieved CV chunks
        candidate_names: Optional list of known candidate names
        
    Returns:
        SingleCandidateDetection with detection result
    """
    q_lower = question.lower()
    
    # First check: Is this explicitly a multi-candidate query?
    if is_multi_candidate_query(question):
        return SingleCandidateDetection(
            is_single_candidate=False,
            detection_method="explicit_multi_candidate_query"
        )
    
    # Extract unique candidates from chunks
    unique_candidates: dict[str, str] = {}  # name -> cv_id
    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        name = metadata.get("candidate_name", "")
        cv_id = metadata.get("cv_id", "")
        if name and name not in unique_candidates:
            unique_candidates[name] = cv_id
    
    # Method 1: Check if query explicitly mentions a candidate name
    if candidate_names:
        for name in candidate_names:
            name_lower = name.lower()
            if name_lower in q_lower:
                cv_id = unique_candidates.get(name, "")
                return SingleCandidateDetection(
                    is_single_candidate=True,
                    candidate_name=name,
                    cv_id=cv_id,
                    confidence=0.95,
                    detection_method="explicit_name_in_query"
                )
    
    # Also check names from chunks
    for name, cv_id in unique_candidates.items():
        name_lower = name.lower()
        if name_lower in q_lower:
            return SingleCandidateDetection(
                is_single_candidate=True,
                candidate_name=name,
                cv_id=cv_id,
                confidence=0.95,
                detection_method="explicit_name_in_query"
            )
        # Check first name only (if multi-word name)
        name_parts = name.split()
        if len(name_parts) > 1:
            first_name = name_parts[0].lower()
            if len(first_name) > 3 and first_name in q_lower:
                return SingleCandidateDetection(
                    is_single_candidate=True,
                    candidate_name=name,
                    cv_id=cv_id,
                    confidence=0.85,
                    detection_method="first_name_in_query"
                )
    
    # Method 2: Only one candidate in retrieved chunks
    if len(unique_candidates) == 1:
        name, cv_id = list(unique_candidates.items())[0]
        single_focus_patterns = [
            r"\bhis\b", r"\bher\b", r"\btheir\b",
            r"\bthis candidate\b", r"\beste candidato\b",
            r"'s\b",
        ]
        
        for pattern in single_focus_patterns:
            if re.search(pattern, q_lower):
                return SingleCandidateDetection(
                    is_single_candidate=True,
                    candidate_name=name,
                    cv_id=cv_id,
                    confidence=0.90,
                    detection_method="single_chunk_with_focus_pattern"
                )
        
        return SingleCandidateDetection(
            is_single_candidate=True,
            candidate_name=name,
            cv_id=cv_id,
            confidence=0.75,
            detection_method="single_candidate_in_chunks"
        )
    
    # Multiple candidates, no explicit single focus
    return SingleCandidateDetection(
        is_single_candidate=False,
        candidate_name=None,
        cv_id=None,
        confidence=0.0,
        detection_method="multiple_candidates"
    )


def extract_candidate_name_from_query(question: str) -> str | None:
    """
    Extract a candidate name from a query BEFORE retrieval.
    
    This enables targeted retrieval - filtering chunks by candidate_name
    when the user asks about a specific person.
    
    Patterns detected:
    - "dame todo sobre [Name]"
    - "tell me about [Name]"
    - "háblame de [Name]"
    - "quién es [Name]"
    - "who is [Name]"
    - "información sobre [Name]"
    - "[Name]'s profile/experience/skills"
    
    Returns:
        Extracted candidate name or None if not detected
    """
    # Patterns that indicate a single candidate query with name capture
    # The name is expected to be 2-3 capitalized words (e.g., "Ling Wei", "Juan García")
    # Name pattern: First name (capitalized) + optional middle/last name(s)
    NAME_PATTERN = r"([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+){1,2})"
    
    patterns = [
        # Spanish patterns - extended to catch variations like "damelo", "dámelo", "dame lo"
        rf"(?:d[aá]me(?:lo)?|dime|mu[eé]strame|proporciona)\s+(?:todo|información|detalles|datos|el perfil)\s+(?:sobre|de|acerca de)\s+{NAME_PATTERN}",
        rf"(?:h[aá]blame|cu[eé]ntame)\s+(?:sobre|de)\s+{NAME_PATTERN}",
        rf"(?:qui[eé]n|quien)\s+es\s+{NAME_PATTERN}",
        rf"perfil\s+de\s+{NAME_PATTERN}",
        rf"cv\s+de\s+{NAME_PATTERN}",
        rf"(?:todo|información)\s+(?:sobre|de)\s+{NAME_PATTERN}",
        rf"analiza(?:r)?\s+(?:a|el cv de)?\s*{NAME_PATTERN}",
        
        # English patterns
        rf"(?:tell me|give me|show me|provide)\s+(?:everything|all|information|details)\s+(?:about|on)\s+{NAME_PATTERN}",
        rf"(?:who is|what about)\s+{NAME_PATTERN}",
        rf"{NAME_PATTERN}(?:'s)?\s+(?:profile|cv|resume|experience|skills|background)",
        rf"about\s+{NAME_PATTERN}\b",
        rf"information\s+(?:on|about)\s+{NAME_PATTERN}",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            candidate_name = match.group(1).strip()
            # Clean up: remove trailing non-name words
            stop_words = {'group', 'team', 'cv', 'profile', 'resume', 'please', 'por favor'}
            words = candidate_name.split()
            cleaned_words = []
            for word in words:
                if word.lower() in stop_words:
                    break
                cleaned_words.append(word)
            candidate_name = ' '.join(cleaned_words)
            
            # Validate: must be at least 2 words (first + last name) and look like a name
            if len(candidate_name) >= 2 and candidate_name.lower() not in {'the', 'all', 'top', 'best', 'candidate', 'candidates'}:
                return candidate_name
    
    return None


def is_multi_candidate_query(question: str) -> bool:
    """
    Detect if a query explicitly asks about MULTIPLE candidates.
    These queries should ALWAYS use comparison templates.
    """
    q_lower = question.lower()
    
    multi_candidate_patterns = [
        r"\ball\b.*\bcandidates?\b",
        r"\beveryone\b",
        r"\btodos\b.*\bcandidatos?\b",
        r"\bcompare\b",
        r"\brank\b",
        r"\btop\s+\d+\b",
        r"\bbest\b.*\bcandidates?\b",
        r"\bmejores?\b",
        r"\bvs\b",
        r"\bversus\b",
        r"\bwhich\s+candidate\b",
        r"\bqué candidato\b",
        r"\bcuál\b.*\bcandidato\b",
        r"\border\b",
        r"\blist\b.*\bcandidates?\b",
    ]
    
    return any(re.search(pattern, q_lower) for pattern in multi_candidate_patterns)


# =============================================================================
# LEGACY COMPATIBILITY FUNCTIONS
# =============================================================================

def build_query_prompt(
    question: str,
    chunks: list[dict],
    total_cvs: int | None = None
) -> str:
    """Legacy function - use PromptBuilder for new code."""
    builder = PromptBuilder()
    return builder.build_query_prompt(question, chunks, total_cvs)


def build_comparison_prompt(criteria: str, chunks: list[dict]) -> str:
    """Legacy function - use PromptBuilder for new code."""
    builder = PromptBuilder()
    return builder.build_comparison_prompt(criteria, chunks)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Enums
    "QueryType",
    "ResponseFormat",
    
    # Config
    "PromptConfig",
    "DEFAULT_CONFIG",
    
    # Core prompts
    "SYSTEM_PROMPT",
    "QUERY_TEMPLATE",
    "SINGLE_CANDIDATE_TEMPLATE",
    "COMPARISON_TEMPLATE",
    "RANKING_TEMPLATE",
    "VERIFICATION_TEMPLATE",
    "SUMMARIZE_TEMPLATE",
    "JOB_MATCH_TEMPLATE",
    "AGGREGATE_TEMPLATE",
    
    # Messages
    "WELCOME_MESSAGE",
    "HELP_MESSAGE",
    "NO_RESULTS_TEMPLATE",
    "NO_CVS_TEMPLATE",
    "OFF_TOPIC_RESPONSE",
    
    # Taxonomies
    "TECHNICAL_SKILLS_TAXONOMY",
    "NON_TECHNICAL_ROLES",
    "DESIGN_TOOLS_NOT_PROGRAMMING",
    
    # Classes
    "PromptBuilder",
    "FormattedContext",
    "ChunkMetadata",
    "SingleCandidateDetection",
    
    # Functions
    "format_context",
    "format_context_minimal",
    "classify_query",
    "is_technical_query",
    "detect_off_topic",
    "detect_single_candidate_query",
    "is_multi_candidate_query",
    "extract_candidate_name_from_query",
    
    # Legacy
    "build_query_prompt",
    "build_comparison_prompt",
]