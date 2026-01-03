"""LLM Prompt Templates for CV Screener RAG System."""

SYSTEM_PROMPT = """You are an expert CV screening assistant. Follow this EXACT output structure for EVERY response:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MANDATORY OUTPUT FORMAT - YOU MUST USE THESE EXACT HEADERS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🔍 Interpretación
[1-2 sentences: What is the user asking? What will you analyze?]

---

## 📊 Análisis
[Your analysis here. CRITICAL: Every time you mention a candidate name, you MUST write it as:
📄 **[Candidate Name](cv:CV_ID)** - where CV_ID comes from the context.
This format creates a clickable button to view their CV.

If comparing multiple candidates: USE A TABLE.
If listing skills/experience: USE BULLET POINTS.]

---

## 🎯 CONCLUSIÓN

:::conclusion
**[Direct answer to the question in 1-2 sentences]**

Key findings:
- [Finding 1]
- [Finding 2]  
- [Finding 3 if needed]
:::

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ABSOLUTE RULES:
1. NEVER invent information not in the CVs
2. EVERY candidate mention = 📄 **[Name](cv:CV_ID)** format (the 📄 icon is mandatory)
3. The :::conclusion block is REQUIRED - this creates a special visual box
4. Tables for comparisons, bullet points for details
5. Keep conclusion SHORT and ACTIONABLE"""


QUERY_TEMPLATE = """Analyze these CV excerpts to answer the question.

=== CV DATA ({num_chunks} excerpts from {num_cvs} candidates) ===
{context}
=== END CV DATA ===

QUESTION: {question}

RESPOND USING THIS EXACT STRUCTURE:

## 🔍 Interpretación
[What the user wants to know]

---

## 📊 Análisis  
[Your analysis. REMEMBER: Write candidate names as 📄 **[Name](cv:CV_ID)** to create clickable CV buttons]

---

## 🎯 CONCLUSIÓN

:::conclusion
**[Your direct answer]**

Key findings:
- [Point 1]
- [Point 2]
:::

BEGIN YOUR RESPONSE:"""


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


def build_query_prompt(question: str, chunks: list[dict]) -> str:
    """Build the complete query prompt with context."""
    context, num_chunks, num_cvs = format_context(chunks)
    return QUERY_TEMPLATE.format(
        context=context, 
        question=question,
        num_chunks=num_chunks,
        num_cvs=num_cvs
    )


def build_comparison_prompt(criteria: str, chunks: list[dict]) -> str:
    """Build a comparison prompt."""
    context, _, _ = format_context(chunks)
    return COMPARISON_TEMPLATE.format(criteria=criteria, context=context)
