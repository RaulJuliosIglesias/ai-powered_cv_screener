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

### 1. EVIDENCE-BASED ANALYSIS
- Extract information ONLY from provided CV text
- NEVER infer, assume, or hallucinate skills/experience
- Distinguish between explicit statements vs. reasonable inferences
- When uncertain, state: "The CV does not explicitly mention..."

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

### 3. HONEST ASSESSMENT
- Report negative findings ("no match") with same confidence as positive
- Never force unsuitable candidates to fill a recommendation
- Acknowledge when CV data is insufficient for the query

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
```

## CANDIDATE REFERENCE FORMAT (MANDATORY)

EVERY candidate mention MUST be a clickable reference:
`**[Candidate Name](cv:CV_ID)**`

Examples:
- Table: `| **[Ana García](cv:cv_042)** | 5 years | Python, Django |`
- Text: `The strongest candidate is **[Juan López](cv:cv_017)**.`
- List: `1. **[María Ruiz](cv:cv_089)** - Senior experience in React`

## COMPARISON TABLES

When comparing candidates, use this structure:
| Candidate | [Criterion 1] | [Criterion 2] | Match Score |
|-----------|---------------|---------------|-------------|
| **[Name](cv:ID)** | Detail | Detail | ⭐⭐⭐ |

Match Score Legend:
- ⭐⭐⭐⭐⭐ Excellent match (90%+)
- ⭐⭐⭐⭐ Strong match (75-89%)
- ⭐⭐⭐ Good match (60-74%)
- ⭐⭐ Partial match (40-59%)
- ⭐ Weak match (<40%)
- ❌ Does not match

## SPECIAL CASES

### No Results
```
:::thinking
[Explain what was searched and why nothing matched]
:::

**No candidates match the criteria.** After reviewing [N] CVs, none list [specific requirement].

:::conclusion
No suitable candidates found. Consider:
- Broadening the search criteria
- Checking for alternative skill names
- Reviewing candidates with adjacent experience
:::
```

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

## INSTRUCTIONS
1. Begin with :::thinking block analyzing the query and available data
2. Provide direct answer (1-2 sentences) BEFORE any table
3. Include detailed analysis if query warrants it
4. End with :::conclusion containing actionable recommendation
5. Use **[Candidate Name](cv:CV_ID)** format for ALL candidate mentions
6. If no candidates match, state this explicitly—do not force recommendations

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
```"""


# =============================================================================
# SPECIALIZED TEMPLATES
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
    
    for i, chunk in enumerate(chunks, 1):
        metadata = ChunkMetadata.from_dict(chunk.get("metadata", {}))
        content = chunk.get("content", "").strip()
        
        if max_chunk_length and len(content) > max_chunk_length:
            content = content[:max_chunk_length] + "... [truncated]"
        
        unique_cvs.add(metadata.filename)
        
        if metadata.candidate_name not in seen_candidates:
            seen_candidates.add(metadata.candidate_name)
            candidate_names.append(metadata.candidate_name)
            cv_ids.append(metadata.cv_id)
        
        if include_metadata:
            header = (
                f"### CV #{i}: {metadata.candidate_name}\n"
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
        response_format: ResponseFormat = ResponseFormat.FULL
    ) -> str:
        """
        Build the complete query prompt with context.
        
        Args:
            question: User's question
            chunks: Retrieved CV chunks
            total_cvs: Total CVs in session (if known)
            response_format: Desired response format
            
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
        
        return template.format(
            context=ctx.text,
            question=question,
            num_chunks=ctx.num_chunks,
            num_cvs=ctx.num_unique_cvs,
            total_cvs=actual_total
        )
    
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


# =============================================================================
# QUERY CLASSIFICATION
# =============================================================================

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
    
    # Functions
    "format_context",
    "format_context_minimal",
    "classify_query",
    "is_technical_query",
    "detect_off_topic",
    
    # Legacy
    "build_query_prompt",
    "build_comparison_prompt",
]