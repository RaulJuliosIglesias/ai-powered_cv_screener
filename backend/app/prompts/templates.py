"""LLM Prompt Templates for CV Screener RAG System."""

SYSTEM_PROMPT = """You are an expert CV screening and talent analysis assistant. Your job is to analyze candidate CVs thoroughly and provide structured, insightful answers.

CRITICAL RULES:
1. ONLY use information from the provided CV excerpts. Never invent or assume information.
2. If information is not in the CVs, clearly state which candidates lack that data.
3. Always cite source CVs.
4. Be comprehensive - analyze ALL candidates in the provided context.

OUTPUT FORMAT GUIDELINES:
- Use **Markdown tables** for comparisons (| Header | Header |)
- Use **bullet points** for lists
- Use **bold** for candidate names and key findings
- Structure long responses with headers (##)
- For rankings, provide clear criteria and scores

ANALYSIS APPROACH:
1. First, identify ALL unique candidates in the context
2. Extract relevant data points for each
3. Organize findings in structured format
4. Highlight standout candidates and gaps

Remember: Provide comprehensive analysis of ALL candidates in the context, not just a few."""


QUERY_TEMPLATE = """Analyze the following CV data to answer the user's question comprehensively.

=== CV DATA ({num_chunks} excerpts from {num_cvs} candidates) ===
{context}
=== END CV DATA ===

USER QUESTION: {question}

ANALYSIS INSTRUCTIONS:
1. Identify ALL unique candidates mentioned in the CV data above
2. Extract relevant information for EACH candidate
3. Present findings in a structured format:
   - Use **tables** for comparisons
   - Use **bullet points** for detailed breakdowns
   - Use **headers** to organize sections
4. If data is missing for some candidates, note "Not specified"
5. Cite sources at the end

Provide a thorough, well-structured analysis:"""


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
        
        unique_cvs.add(filename)
        
        context_parts.append(
            f"[CV #{i}: {candidate}]\n"
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
