"""LLM Prompt Templates for CV Screener RAG System."""

SYSTEM_PROMPT = """You are an expert CV screening assistant. You ONLY answer questions about CVs and candidates.

CRITICAL GUARDRAILS:
- If the question is NOT about CVs, hiring, candidates, skills, or recruitment, respond with:
  "I can only help with CV screening and candidate analysis. Please ask a question about the uploaded CVs."
- If NO candidate matches the requested criteria, say so CLEARLY. Do NOT force or suggest candidates who don't meet the requirements.
- NEVER invent skills or experience that is not explicitly stated in the CVs.

YOUR RESPONSE MUST HAVE THIS EXACT STRUCTURE:

:::thinking
[Your internal reasoning: What is the user asking? Do any CVs match? If not, I must say no candidates match.]
:::

[YOUR MAIN RESPONSE - Answer directly. If no candidates match, say "None of the candidates have [requested skill/experience]."]

When you mention a candidate, write their name followed by their CV reference like this:
- Juan Pérez [CV:cv_abc123]

Use markdown tables when comparing multiple candidates.

:::conclusion
[Your final recommendation - If no match, clearly state "No suitable candidates found for this requirement."]
:::

EXAMPLE - When candidates match:

:::thinking
The user wants Python developers. I found 2 CVs with Python experience.
:::

| Candidate | Experience | Python Skills |
|-----------|------------|---------------|
| Juan Pérez [CV:cv_123] | 5 years | Django, Flask |
| Ana López [CV:cv_456] | 3 years | FastAPI |

:::conclusion
Juan Pérez [CV:cv_123] is the strongest Python candidate.
:::

EXAMPLE - When NO candidates match:

:::thinking
The user wants Python developers. I checked all CVs but none mention Python or related frameworks.
:::

**None of the candidates have Python experience.** After reviewing all CVs, no candidate lists Python or Python frameworks (Django, Flask, FastAPI, etc.) in their skills.

If you need Python expertise, consider expanding your candidate search.

:::conclusion
No suitable candidates found for Python development.
:::

RULES:
1. ALWAYS start with :::thinking block
2. ALWAYS end with :::conclusion block  
3. Use [CV:cv_id] format after candidate names
4. ONLY use information explicitly stated in CVs
5. Say "No candidates match" when criteria isn't met - NEVER force unsuitable candidates
6. REJECT off-topic questions (recipes, general knowledge, etc.)"""


QUERY_TEMPLATE = """Analyze these CV excerpts to answer the question.

=== CV DATA ({num_chunks} excerpts from {num_cvs} candidates) ===
{context}
=== END CV DATA ===

QUESTION: {question}

IMPORTANT RULES:
- If the question is NOT about CVs/candidates/hiring, respond: "I can only help with CV screening. Please ask about the uploaded CVs."
- If NO candidate has the requested skill/experience, say clearly: "None of the candidates match this requirement."
- Do NOT suggest candidates who don't meet the criteria just to give an answer.

RESPOND WITH:
1. :::thinking block (Is this CV-related? Do any candidates match?)
2. Your analysis - be honest if no matches
3. :::conclusion block

Your response:"""


GROUNDING_CHECK_TEMPLATE = """Before providing your final answer, verify:
1. Is this information explicitly stated in the provided CVs?
2. Am I making any assumptions not supported by the text?
3. Have I correctly attributed information to the right candidate?

If you cannot verify any claim from the CV text, do not include it.

Verified Answer:"""


COMPARISON_TEMPLATE = """Based on the CV excerpts provided, compare the candidates for the following criteria:

{criteria}

=== CV EXCERPTS ===
{context}
=== END CV EXCERPTS ===

Create a structured comparison table or list. Only include information that is explicitly stated in the CVs.
If a candidate lacks information for a criterion, note it as "Not specified in CV".

Comparison:"""


NO_RESULTS_TEMPLATE = """I searched through the uploaded CVs but couldn't find information relevant to your question: "{question}"

This could mean:
- None of the candidates have the specific qualifications you're asking about
- The information might be described differently in the CVs
- The question might be outside the scope of the CV content

Try rephrasing your question or asking about specific skills, experiences, or qualifications."""


WELCOME_MESSAGE = """Welcome! I can help you search through the indexed CVs. Try asking:

• "Who has Python experience?"
• "List candidates from Madrid"
• "Who worked at Google?"
• "Compare the top candidates for a senior developer role"
• "Which candidates have a Master's degree?"

I'll only provide information that's explicitly stated in the CVs."""


def format_context(chunks: list[dict]) -> tuple[str, int, int]:
    """Format retrieved chunks into context string for the prompt.
    Returns: (context_string, num_chunks, num_unique_cvs)
    """
    if not chunks:
        return "No relevant CV excerpts found.", 0, 0
    
    context_parts = []
    unique_cvs = set()
    
    for i, chunk in enumerate(chunks, 1):
        metadata = chunk.get("metadata", {})
        filename = metadata.get("filename", "Unknown")
        candidate = metadata.get("candidate_name", "Unknown")
        section = metadata.get("section_type", "general")
        cv_id = metadata.get("cv_id", "unknown")
        
        unique_cvs.add(filename)
        
        context_parts.append(
            f"[CV #{i}: {candidate}]\n"
            f"CV_ID: {cv_id}\n"
            f"File: {filename}\n"
            f"Section: {section}\n"
            f"Content:\n{chunk.get('content', '')}\n"
        )
    
    return "\n---\n".join(context_parts), len(chunks), len(unique_cvs)


def build_query_prompt(question: str, chunks: list[dict], total_cvs: int = None) -> str:
    """Build the complete query prompt with context.
    
    Args:
        question: User's question
        chunks: Retrieved CV chunks
        total_cvs: Total CVs in session (if known, use this instead of counting unique CVs in chunks)
    """
    context, num_chunks, num_cvs_in_chunks = format_context(chunks)
    # Use total_cvs if provided (more accurate), otherwise fall back to chunks count
    actual_num_cvs = total_cvs if total_cvs is not None else num_cvs_in_chunks
    return QUERY_TEMPLATE.format(
        context=context, 
        question=question,
        num_chunks=num_chunks,
        num_cvs=actual_num_cvs
    )


def build_comparison_prompt(criteria: str, chunks: list[dict]) -> str:
    """Build a comparison prompt."""
    context, _, _ = format_context(chunks)
    return COMPARISON_TEMPLATE.format(criteria=criteria, context=context)
