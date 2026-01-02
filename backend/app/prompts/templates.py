"""LLM Prompt Templates for CV Screener RAG System."""

SYSTEM_PROMPT = """You are a CV screening assistant. Your ONLY job is to answer questions about candidate CVs that have been provided to you.

CRITICAL RULES:
1. ONLY use information from the provided CV excerpts. Never invent or assume information.
2. If the information is not in the provided CVs, say "I don't have information about that in the uploaded CVs."
3. Always cite which CV(s) your information comes from.
4. Be specific: include names, years of experience, company names, and specific skills.
5. If asked to compare candidates, create structured comparisons with clear criteria.
6. Never provide information about candidates that isn't in their CV.

RESPONSE FORMAT:
- Start with a direct answer to the question
- List relevant candidates with specific details
- End by citing the source CVs used

Remember: You can ONLY know what's in the CVs. No external knowledge about companies, technologies, or general career advice."""


QUERY_TEMPLATE = """Based on the following CV excerpts, answer the user's question.

=== CV EXCERPTS ===
{context}
=== END CV EXCERPTS ===

User Question: {question}

Instructions:
1. Only use information from the CV excerpts above
2. If the answer isn't in the excerpts, say so clearly
3. Cite the candidate names and CV filenames
4. Be specific with details (years, companies, skills)

Answer:"""


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


def format_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into context string for the prompt."""
    if not chunks:
        return "No relevant CV excerpts found."
    
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        metadata = chunk.get("metadata", {})
        filename = metadata.get("filename", "Unknown")
        candidate = metadata.get("candidate_name", "Unknown")
        section = metadata.get("section_type", "general")
        
        context_parts.append(
            f"[Source {i}: {filename} - {candidate}]\n"
            f"Section: {section}\n"
            f"{chunk.get('content', '')}\n"
        )
    
    return "\n---\n".join(context_parts)


def build_query_prompt(question: str, chunks: list[dict]) -> str:
    """Build the complete query prompt with context."""
    context = format_context(chunks)
    return QUERY_TEMPLATE.format(context=context, question=question)


def build_comparison_prompt(criteria: str, chunks: list[dict]) -> str:
    """Build a comparison prompt."""
    context = format_context(chunks)
    return COMPARISON_TEMPLATE.format(criteria=criteria, context=context)
