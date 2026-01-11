"""
Query Understanding Service - Step 1 of 2-step RAG.

Uses a fast model to understand, reformulate, and structure the user's query
before sending it to the main generation model.

Features:
- Retry with exponential backoff for rate limits (429)
- Model fallback chain (only FREE models)
- Heuristic fallback as last resort (never fails)
"""
import logging
import asyncio
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import httpx

from app.config import settings, timeouts
from app.providers.cloud.llm import calculate_openrouter_cost

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURATION: Free Model Fallback Chain
# =============================================================================

# GUARANTEED FREE MODELS (all end with :free)
# These are verified OpenRouter free models as of 2024
FREE_MODEL_FALLBACK_CHAIN = [
    "google/gemini-2.0-flash-exp:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-3-27b-it:free",
    "deepseek/deepseek-r1-0528:free",
    "mistralai/mistral-7b-instruct:free",
]

# Retry configuration
MAX_RETRIES_PER_MODEL = 3
RETRY_BASE_DELAY_SECONDS = 1.5  # 1.5s, 3s, 4.5s

# Safety: Only allow :free models in fallback
ONLY_FREE_MODELS_IN_FALLBACK = True


@dataclass
class QueryUnderstanding:
    """Result of query understanding analysis."""
    original_query: str
    understood_query: str
    query_type: str  # ranking, comparison, search, filter, general
    requirements: list  # List of requirements extracted
    is_cv_related: bool
    confidence: float
    query_variations: list = field(default_factory=list)
    hyde_document: str | None = None
    reformulated_prompt: str | None = None
    metadata: dict = field(default_factory=dict)  # OpenRouter usage metadata


QUERY_UNDERSTANDING_PROMPT = """You are a query understanding assistant for a CV screening system.

{conversation_context}

Your task is to REINTERPRET and EXPAND the user's query into a clear, detailed understanding.

CRITICAL RULES:
1. The "understood_query" MUST be an EXPANDED reinterpretation - NEVER just repeat the user's words
2. Resolve ALL references ("them", "the 3", "those candidates", "he/she", "el top candidate")
3. If the user says "compare the 3 of them", identify WHO "them" refers to from context
4. Add explicit detail about WHAT is being compared/analyzed
5. Break down vague queries into specific, actionable requirements

USER QUERY: {query}

IMPORTANT: 
- "understood_query" should read like a THOUGHT PROCESS explaining what the user really wants
- It should be 2-3x longer than the original query with added specificity
- Include candidate names if they can be resolved from conversation history
- Explain the implicit intent behind short/vague queries

Respond in this EXACT JSON format (no markdown, just raw JSON):
{{
  "understood_query": "EXPANDED reinterpretation showing your understanding (NOT a copy of the original)",
  "query_type": "ranking|comparison|search|red_flags|single_candidate|job_match|team_build|summary|general",
  "requirements": [
    "requirement 1",
    "requirement 2"
  ],
  "is_cv_related": true,
  "reformulated_prompt": "A clear, structured prompt to send to the CV analysis model (with ALL names resolved)"
}}

QUERY_TYPE GUIDE:
- "ranking": User wants candidates ONLY ranked/ordered by criteria WITHOUT building a team (e.g., "Rank by experience", "Who are the best 5?")
- "comparison": User wants to compare specific candidates side-by-side
- "search": User wants to find candidates with specific skills/experience
- "red_flags": User asks for RISK ASSESSMENT, red flags, job hopping analysis, stability concerns
- "single_candidate": User wants FULL PROFILE of ONE specific candidate (everything about, full profile, analyze X)
- "job_match": User wants to match candidates against job requirements
- "team_build": User wants to BUILD/FORM/CREATE a TEAM from candidates (e.g., "Can I build a team with the top 3?", "Form a project team", "Create a team of developers") - CRITICAL: If query mentions "team" + "build/form/create/with", it's ALWAYS team_build NOT ranking
- "summary": User wants a summary/overview of candidates
- "general": Non-CV related queries

EXAMPLES:

Query: "Compare #1 vs #2 in the ranking"
{
  "understood_query": "Compare the top two candidates from the previous ranking",
  "query_type": "comparison",
  "requirements": [
    "Identify #1 and #2 candidates from previous ranking",
    "Compare their experience, skills, and qualifications",
    "Highlight differences and similarities"
  ],
  "is_cv_related": true,
  "reformulated_prompt": "Create a detailed comparison between the #1 and #2 ranked candidates from the previous ranking. Compare their years of experience, technical skills, career progression, and key qualifications. Highlight what makes each candidate strong and where they differ."
}

Query: "Rank all 33 candidates by experience and show if they worked at Google or Microsoft"
{
  "understood_query": "Rank ALL candidates by years of experience, and for each candidate, indicate if they have worked at major tech companies like Google or Microsoft",
  "query_type": "ranking",
  "requirements": [
    "Rank ALL 33 candidates (not filter)",
    "Order by total years of experience",
    "For each candidate, check if they worked at Google, Microsoft, or similar major tech companies",
    "Show company names if applicable"
  ],
  "is_cv_related": true,
  "reformulated_prompt": "Create a complete ranking of ALL candidates ordered by their total years of professional experience. For EACH candidate, include: 1) Their name, 2) Total years of experience, 3) Whether they have worked at major tech companies (Google, Microsoft, Amazon, Meta, Apple, etc.) and which ones. Do NOT filter out candidates - show ALL of them even if they haven't worked at major companies."
}

Query: "Who knows Python?"
{{
  "understood_query": "Find candidates who have Python programming experience",
  "query_type": "search",
  "requirements": [
    "Search for Python skill in CVs",
    "Include related Python frameworks if mentioned"
  ],
  "is_cv_related": true,
  "reformulated_prompt": "Find all candidates who have Python programming experience. Include their proficiency level if mentioned, and any Python-related frameworks or libraries they know (Django, Flask, FastAPI, etc.)."
}}

Query: "Make a risk assessment of Sofia Rodriguez"
{{
  "understood_query": "The user wants a risk assessment analyzing potential red flags, job stability, and hiring concerns for Sofia Rodriguez. This includes evaluating job hopping patterns, employment gaps, career progression, and any warning signs.",
  "query_type": "red_flags",
  "requirements": [
    "Analyze job hopping score and employment stability",
    "Identify any employment gaps",
    "Evaluate career progression consistency",
    "Flag any potential concerns for hiring"
  ],
  "is_cv_related": true,
  "reformulated_prompt": "Perform a comprehensive risk assessment for Sofia Rodriguez. Analyze job stability (tenure at each position), employment gaps, career progression, and identify any red flags or concerns that a hiring manager should consider."
}}

Query: "Give me the full profile of John Smith" or "Tell me everything about John"
{{
  "understood_query": "The user wants a complete, detailed profile of John Smith including all their experience, skills, education, career trajectory, and any other relevant information from their CV.",
  "query_type": "single_candidate",
  "requirements": [
    "Extract complete work history",
    "List all skills and competencies",
    "Include education and certifications",
    "Summarize career progression"
  ],
  "is_cv_related": true,
  "reformulated_prompt": "Provide a comprehensive profile of John Smith. Include their complete work history, all skills and technologies, education, certifications, and a summary of their career trajectory and key achievements."
}}

Query: "Can I build a team with the top 3?"
{{
  "understood_query": "The user wants to BUILD a TEAM using the top 3 ranked candidates from the pool. This requires team composition analysis, skill complementarity assessment, and team balance evaluation - NOT just a ranking list.",
  "query_type": "team_build",
  "requirements": [
    "Identify the top 3 candidates based on overall qualifications",
    "Analyze how these 3 candidates work together as a team",
    "Assess skill complementarity and coverage",
    "Identify team composition strengths and potential gaps",
    "Evaluate team balance and roles"
  ],
  "is_cv_related": true,
  "reformulated_prompt": "Analyze whether the top 3 candidates can form an effective team. Identify the top 3 candidates, then evaluate: 1) How their skills complement each other, 2) What roles each would fill, 3) Team skill coverage and gaps, 4) Team balance in seniority and experience, 5) Potential collaboration strengths and risks."
}}

Query: "Give me a recipe for chocolate cake"
{{
  "understood_query": "User is asking for cooking instructions",
  "query_type": "general",
  "requirements": [],
  "is_cv_related": false,
  "reformulated_prompt": ""
}}

CONTEXT RESOLUTION EXAMPLE (VERY IMPORTANT):

Conversation History:
Usuario: Who is best for a leadership role?
Asistente: Isabel Mendoza is the top choice with 100% score for leadership...

USER QUERY: "dime mas sobre el top candidate"

{{
  "understood_query": "Provide detailed information about Isabel Mendoza (the top candidate from the previous ranking)",
  "query_type": "search",
  "requirements": [
    "Extract full profile for Isabel Mendoza",
    "Include leadership experience details",
    "Show comprehensive candidate information"
  ],
  "is_cv_related": true,
  "reformulated_prompt": "Provide a comprehensive profile and detailed analysis of Isabel Mendoza, including all leadership experience, team management roles, strategic accomplishments, skills, and career trajectory."
}}

VAGUE REFERENCE EXAMPLE (CRITICAL - DO NOT JUST COPY THE QUERY):

Conversation History:
Usuario: Who has the most experience?
Asistente: 1. John Smith (15 years), 2. Maria Garcia (12 years), 3. David Lee (10 years)...

USER QUERY: "compare the 3 of them"

{{
  "understood_query": "The user wants to compare the top 3 candidates from the previous experience ranking: John Smith (15 years experience), Maria Garcia (12 years experience), and David Lee (10 years experience). This comparison should analyze their skills, career trajectories, strengths and weaknesses to help decide between them.",
  "query_type": "comparison",
  "requirements": [
    "Compare John Smith, Maria Garcia, and David Lee side by side",
    "Analyze their experience, skills, and qualifications",
    "Identify strengths and weaknesses of each",
    "Provide recommendation on which is best for different scenarios"
  ],
  "is_cv_related": true,
  "reformulated_prompt": "Create a detailed comparison table of John Smith, Maria Garcia, and David Lee. For each candidate, analyze: years of experience, technical skills, leadership experience, career progression, education, and key achievements. Highlight what makes each unique and provide recommendations for different hiring needs."
}}

SHORT QUERY EXPANSION EXAMPLE:

USER QUERY: "tell me more"

{{
  "understood_query": "The user wants additional details about the topic or candidate discussed in the previous message. Since this is a follow-up, I should expand on the last response with more comprehensive information, deeper analysis, or additional relevant details that weren't covered before.",
  "query_type": "search",
  "requirements": [
    "Identify what was discussed previously",
    "Provide additional details not yet covered",
    "Go deeper into the analysis"
  ],
  "is_cv_related": true,
  "reformulated_prompt": "Provide additional comprehensive details about the previously discussed topic/candidate, including information not yet covered in prior responses."
}}

TALENT POOL EXAMPLES:

Query: "How many candidates have senior experience?"
{{
  "understood_query": "The user wants to know how many candidates in the talent pool have senior-level experience. This requires analyzing all candidates to identify those with senior job titles, extensive experience, or senior-level responsibilities.",
  "query_type": "summary",
  "requirements": [
    "Analyze ALL candidates in the talent pool",
    "Identify senior experience indicators (job titles, years of experience, responsibilities)",
    "Count and list all senior candidates"
  ],
  "is_cv_related": true,
  "reformulated_prompt": "Analyze the entire talent pool and identify all candidates who have senior-level experience. Look for senior job titles (Senior, Lead, Principal, Director, Manager), extensive years of experience (typically 5+ years), and senior-level responsibilities. Provide the total count and list each senior candidate with their specific senior qualifications."
}}

Query: "cuáles son los talentos senior que hay"
{{
  "understood_query": "El usuario quiere conocer todos los candidatos con experiencia senior en el pool de talentos. Esto requiere analizar todos los CVs para identificar talentos senior y presentarlos como un overview completo.",
  "query_type": "summary",
  "requirements": [
    "Analizar TODOS los candidatos del talent pool",
    "Identificar indicadores de experiencia senior",
    "Presentar overview completo del talento senior disponible"
  ],
  "is_cv_related": true,
  "reformulated_prompt": "Analizar el pool completo de talentos e identificar todos los candidatos con experiencia senior. Buscar títulos senior, años de experiencia relevantes, y responsabilidades de nivel senior. Presentar un overview completo del talento senior disponible incluyendo nombres, roles senior, y experiencia clave."
}}

Query: "tell me about all the candidates"
{{
  "understood_query": "The user wants a comprehensive overview of all candidates in the talent pool, including their key skills, experience levels, and characteristics.",
  "query_type": "summary",
  "requirements": [
    "Provide overview of ALL candidates",
    "Summarize key characteristics of the talent pool",
    "Include experience distribution and skills overview"
  ],
  "is_cv_related": true,
  "reformulated_prompt": "Provide a comprehensive overview of the entire talent pool. Include all candidates with their key characteristics, experience levels, primary skills, and a summary of the overall talent composition and distribution."
}}

Now analyze the user's query and respond with JSON only:"""


class QueryUnderstandingService:
    """
    Service for understanding and reformulating user queries.
    
    Uses a fast, cheap model for quick query analysis before
    the main RAG generation step.
    
    RESILIENCE FEATURES:
    - Level 1: Retry with exponential backoff (same model)
    - Level 2: Fallback to alternative FREE models
    - Level 3: Heuristic fallback (NEVER fails)
    """
    
    def __init__(self, model: str):
        if not model:
            raise ValueError("model parameter is required and cannot be empty")
        self.model = model
        self.api_key = settings.openrouter_api_key or ""
        logger.info(f"QueryUnderstandingService initialized with model: {self.model}")
        logger.info(f"  API key available: {bool(self.api_key)}")
        logger.info(f"  Fallback models: {len(FREE_MODEL_FALLBACK_CHAIN)} free models available")
    
    def _get_models_to_try(self) -> List[str]:
        """
        Build ordered list of models to try.
        Primary model first, then free fallbacks.
        """
        models = [self.model]
        
        # Add fallback models (only those not already in list)
        for fallback in FREE_MODEL_FALLBACK_CHAIN:
            if fallback != self.model:
                # Safety check: only allow :free models in fallback
                if ONLY_FREE_MODELS_IN_FALLBACK and not fallback.endswith(':free'):
                    continue
                models.append(fallback)
        
        return models
    
    async def understand(self, query: str, conversation_history: List[Dict[str, str]] = None, progress_callback=None) -> QueryUnderstanding:
        """
        Analyze and understand the user's query with 3-level fallback.
        
        This method NEVER raises exceptions - it always returns a result.
        
        Args:
            query: The user's original question
            progress_callback: Optional async callback(status: str, details: str) for progress updates
            
        Returns:
            QueryUnderstanding with parsed intent and reformulated prompt
        """
        async def report_progress(status: str, details: str = ""):
            """Helper to report progress if callback is provided."""
            if progress_callback:
                try:
                    await progress_callback(status, details)
                except Exception as e:
                    logger.warning(f"Progress callback failed: {e}")
        
        if not self.api_key:
            logger.warning("No API key available, using heuristic fallback")
            await report_progress("fallback", "No API key, using heuristics")
            return self._create_heuristic_fallback(query, "No API key")
        
        models_to_try = self._get_models_to_try()
        last_error = None
        total_models = len(models_to_try)
        
        # Try each model with retries
        for model_idx, model in enumerate(models_to_try):
            is_fallback = model_idx > 0
            model_short = model.split('/')[-1].split(':')[0]  # Extract short name
            
            if is_fallback:
                await report_progress("trying_fallback", f"Trying fallback {model_idx}/{total_models-1}: {model_short}")
            
            for attempt in range(MAX_RETRIES_PER_MODEL):
                try:
                    result = await self._call_llm(query, model, conversation_history)
                    
                    # Success!
                    if is_fallback:
                        logger.warning(f"[QUERY_UNDERSTANDING] Succeeded with fallback model: {model}")
                        result.metadata["used_fallback_model"] = model
                    
                    return result
                    
                except httpx.HTTPStatusError as e:
                    last_error = e
                    
                    if e.response.status_code == 429:
                        # Rate limited - retry with backoff
                        wait_time = RETRY_BASE_DELAY_SECONDS * (attempt + 1)
                        logger.warning(
                            f"[QUERY_UNDERSTANDING] Rate limited (429) on {model}, "
                            f"attempt {attempt + 1}/{MAX_RETRIES_PER_MODEL}, waiting {wait_time}s..."
                        )
                        await report_progress(
                            "retrying", 
                            f"Rate limited, retry {attempt + 1}/{MAX_RETRIES_PER_MODEL} in {wait_time:.0f}s"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        # Other HTTP error - skip to next model
                        logger.warning(
                            f"[QUERY_UNDERSTANDING] HTTP {e.response.status_code} on {model}, "
                            f"trying next model..."
                        )
                        break
                        
                except httpx.TimeoutException as e:
                    last_error = e
                    logger.warning(f"[QUERY_UNDERSTANDING] Timeout on {model}, trying next model...")
                    await report_progress("timeout", f"Timeout on {model_short}")
                    break
                    
                except json.JSONDecodeError as e:
                    last_error = e
                    logger.warning(f"[QUERY_UNDERSTANDING] Invalid JSON from {model}, trying next model...")
                    break
                    
                except Exception as e:
                    last_error = e
                    logger.warning(f"[QUERY_UNDERSTANDING] Error on {model}: {type(e).__name__}: {e}")
                    break
        
        # ALL models failed - use heuristic fallback (Level 3)
        logger.error(
            f"[QUERY_UNDERSTANDING] All {len(models_to_try)} models failed. "
            f"Using heuristic fallback. Last error: {last_error}"
        )
        await report_progress("fallback", "Using heuristic analysis")
        return self._create_heuristic_fallback(query, str(last_error))
    
    async def _call_llm(self, query: str, model: str, conversation_history: List[Dict[str, str]] = None) -> QueryUnderstanding:
        """
        Make a single LLM call for query understanding.
        
        Raises exceptions on failure (handled by caller).
        """
        from app.providers.base import get_openrouter_url
        
        # Build conversation context section
        conversation_context = ""
        if conversation_history and len(conversation_history) > 0:
            conversation_context = "## CONVERSATION HISTORY (for reference resolution):\n"
            for msg in conversation_history:
                role_label = "Usuario" if msg.get("role") == "user" else "Asistente"
                content = msg.get("content", "")
                # Limit each message to 300 chars to avoid overwhelming the prompt
                if len(content) > 300:
                    content = content[:300] + "..."
                conversation_context += f"{role_label}: {content}\n"
            conversation_context += "\n---\n"
        
        prompt = QUERY_UNDERSTANDING_PROMPT.format(
            query=query,
            conversation_context=conversation_context
        )
        
        async with httpx.AsyncClient(timeout=timeouts.HTTP_MEDIUM) as client:
            response = await client.post(
                get_openrouter_url("chat/completions"),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 500
                }
            )
            response.raise_for_status()
            data = response.json()
        
        content = data["choices"][0]["message"]["content"].strip()
        
        # Extract usage metadata
        metadata = {"model_used": model}
        if "usage" in data:
            usage = data["usage"]
            if isinstance(usage, dict):
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                metadata["prompt_tokens"] = prompt_tokens
                metadata["completion_tokens"] = completion_tokens
                metadata["total_tokens"] = prompt_tokens + completion_tokens
                metadata["openrouter_cost"] = calculate_openrouter_cost(
                    model, prompt_tokens, completion_tokens
                )
                logger.info(f"[QUERY_UNDERSTANDING] Success with {model}: {metadata['total_tokens']} tokens")
        
        # Parse JSON response (pass conversation_history for context resolution)
        return self._parse_llm_response(query, content, metadata, conversation_history)
    
    def _parse_llm_response(self, query: str, content: str, metadata: dict, conversation_history: List[Dict[str, str]] = None) -> QueryUnderstanding:
        """
        Parse LLM response into QueryUnderstanding.
        """
        import re
        
        # Clean up markdown code blocks if present
        if "```" in content:
            # Extract content between code blocks
            match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
            if match:
                content = match.group(1)
            else:
                # Fallback: split on ``` and take middle part
                parts = content.split("```")
                if len(parts) >= 2:
                    content = parts[1]
                    if content.startswith("json"):
                        content = content[4:]
        
        content = content.strip()
        
        # Try to find JSON object in content (handles LLM adding extra text)
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            content = json_match.group(0)
        
        # Handle common JSON formatting issues from LLMs
        # Remove trailing commas before closing braces/brackets
        content = re.sub(r',\s*([\]}])', r'\1', content)
        
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as e:
            # If JSON parsing fails, try to extract key values manually
            logger.warning(f"[QUERY_UNDERSTANDING] JSON parse error: {e}, attempting manual extraction")
            parsed = self._extract_json_manually(content, query)
        
        query_type = parsed.get("query_type", "general")
        is_cv_related = parsed.get("is_cv_related", True)
        
        # Get understood_query from LLM response
        understood_query = parsed.get("understood_query", query)
        
        # CRITICAL: Validate that understood_query is actually an expansion
        # If the LLM just copied the query, we need to expand it ourselves
        understood_query = self._ensure_query_expansion(query, understood_query, query_type, parsed.get("requirements", []), conversation_history)
        
        # CRITICAL: Override query_type if strong quantitative comparison patterns detected
        # This fixes cases where LLM incorrectly classifies "Who has the most experience" as "search"
        query_lower = query.lower()
        
        # Quantitative comparison patterns - these should be RANKING, not search
        quantitative_patterns = [
            'who has the most', 'who has the least', 'who has more', 'who has less',
            'most total experience', 'least total experience', 'highest experience', 'lowest experience',
            'most years', 'least years', 'most experience', 'least experience',
            'quién tiene más', 'quién tiene menos', 'más experiencia', 'menos experiencia'
        ]
        
        if any(pattern in query_lower for pattern in quantitative_patterns):
            if query_type != "ranking":
                logger.warning(f"[QUERY_UNDERSTANDING] Overriding query_type from '{query_type}' to 'ranking' due to quantitative comparison pattern")
                query_type = "ranking"
        
        # Comparison keywords - these should be COMPARISON
        comparison_keywords = ['compare', 'versus', 'vs', 'vs.', 'comparar', 'comparación', 'difference between']
        if any(kw in query_lower for kw in comparison_keywords):
            if query_type != "comparison":
                logger.warning(f"[QUERY_UNDERSTANDING] Overriding query_type from '{query_type}' to 'comparison' due to comparison keywords")
                query_type = "comparison"
        
        # Force is_cv_related=True for CV-related query types
        cv_related_types = {"ranking", "comparison", "search", "filter"}
        if query_type in cv_related_types:
            is_cv_related = True
        
        # Also check for CV-related keywords
        cv_keywords = ["candidate", "cv", "resume", "shortlist", "rank", "experience", "skill"]
        query_lower = query.lower()
        if any(kw in query_lower for kw in cv_keywords):
            is_cv_related = True
        
        return QueryUnderstanding(
            original_query=query,
            understood_query=understood_query,
            query_type=query_type,
            requirements=parsed.get("requirements", []),
            is_cv_related=is_cv_related,
            confidence=0.9,
            reformulated_prompt=parsed.get("reformulated_prompt", query),
            metadata=metadata
        )
    
    def _ensure_query_expansion(self, original: str, understood: str, query_type: str, requirements: list, conversation_history: List[Dict[str, str]] = None) -> str:
        """
        Ensure the understood_query is actually an expansion, not a copy.
        
        If the LLM returned something too similar to the original,
        we generate an expanded version ourselves using conversation context.
        """
        original_normalized = original.lower().strip()
        understood_normalized = understood.lower().strip()
        
        # Check if understood is too similar to original
        is_too_similar = (
            understood_normalized == original_normalized or
            len(understood) < len(original) * 1.3 or  # Should be at least 30% longer
            self._similarity_ratio(original_normalized, understood_normalized) > 0.85
        )
        
        if not is_too_similar:
            return understood  # LLM did its job correctly
        
        logger.warning(f"[QUERY_UNDERSTANDING] Detected lazy understood_query, expanding: '{original}' -> '{understood}'")
        
        # Generate expanded version based on query_type AND conversation context
        expanded = self._generate_expanded_understanding(original, query_type, requirements, conversation_history)
        
        logger.info(f"[QUERY_UNDERSTANDING] Auto-expanded to: '{expanded}'")
        return expanded
    
    def _similarity_ratio(self, s1: str, s2: str) -> float:
        """Calculate simple similarity ratio between two strings."""
        if not s1 or not s2:
            return 0.0
        
        # Simple word overlap ratio
        words1 = set(s1.split())
        words2 = set(s2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)
    
    def _generate_expanded_understanding(self, query: str, query_type: str, requirements: list, conversation_history: List[Dict[str, str]] = None) -> str:
        """
        Generate an expanded understanding when LLM fails to do so.
        
        This provides meaningful context about what the user is asking,
        including candidate names extracted from conversation history.
        """
        query_lower = query.lower()
        
        # Extract candidate names from conversation history
        candidates_from_context = self._extract_candidates_from_history(conversation_history)
        candidates_str = ""
        if candidates_from_context:
            candidates_str = f" The candidates referenced are: {', '.join(candidates_from_context)}."
        
        # Build requirements string if available
        req_str = ""
        if requirements:
            req_str = f" This involves: {', '.join(requirements[:3])}."
        
        # Type-specific expansions
        if query_type == "comparison":
            if "3" in query or "three" in query_lower:
                if candidates_from_context and len(candidates_from_context) >= 3:
                    top_3 = candidates_from_context[:3]
                    return f"The user wants to compare these 3 specific candidates: {', '.join(top_3)}. This comparison should analyze their relative strengths, weaknesses, experience levels, skills, and qualifications to help make a hiring decision.{req_str}"
                return f"The user wants to compare 3 candidates from the current context.{candidates_str} This comparison should analyze their relative strengths, weaknesses, experience levels, skills, and qualifications to help make a hiring decision.{req_str}"
            elif "2" in query or "two" in query_lower:
                if candidates_from_context and len(candidates_from_context) >= 2:
                    top_2 = candidates_from_context[:2]
                    return f"The user wants to compare these 2 candidates head-to-head: {', '.join(top_2)}. This comparison should highlight differences in experience, skills, and fit for the role.{req_str}"
                return f"The user wants to compare 2 candidates head-to-head.{candidates_str} This comparison should highlight differences in experience, skills, and fit for the role.{req_str}"
            else:
                return f"The user requests a detailed comparison between the referenced candidates.{candidates_str} This should include side-by-side analysis of their qualifications, experience, and suitability.{req_str}"
        
        elif query_type == "ranking":
            return f"The user wants candidates ranked according to specific criteria.{candidates_str} This ranking should order all relevant candidates and provide justification for the ordering.{req_str}"
        
        elif query_type == "search":
            return f"The user is searching for specific information about candidates or their qualifications.{candidates_str} This requires extracting relevant details from the CV data.{req_str}"
        
        elif query_type == "red_flags":
            # Extract candidate name from query if present
            candidate_mention = ""
            if candidates_from_context:
                candidate_mention = f" for {candidates_from_context[0]}"
            return f"The user wants a RISK ASSESSMENT{candidate_mention}. This requires analyzing job hopping patterns, employment gaps, career stability, and identifying any red flags or concerns that could impact hiring decisions.{req_str}"
        
        elif query_type == "single_candidate":
            candidate_mention = ""
            if candidates_from_context:
                candidate_mention = f" of {candidates_from_context[0]}"
            return f"The user wants a COMPLETE PROFILE{candidate_mention}. This requires extracting all available information including work history, skills, education, certifications, and career trajectory from the CV.{req_str}"
        
        elif query_type == "job_match":
            return f"The user wants to evaluate how well candidates match specific job requirements.{candidates_str} This requires comparing candidate qualifications against the job criteria.{req_str}"
        
        elif query_type == "team_build":
            return f"The user wants to build or recommend a team from the available candidates.{candidates_str} This requires analyzing complementary skills and team composition.{req_str}"
        
        elif query_type == "summary":
            return f"The user wants a summary or overview of the candidates.{candidates_str} This requires providing a high-level view of the candidate pool.{req_str}"
        
        elif query_type == "filter":
            return f"The user wants to filter candidates based on specific criteria.{candidates_str} This should identify which candidates meet the requirements and which don't.{req_str}"
        
        else:
            # General expansion for vague queries
            if any(word in query_lower for word in ['more', 'detail', 'expand', 'tell', 'explain']):
                return f"The user is requesting additional details or elaboration on the previously discussed topic or candidate.{candidates_str} This follow-up requires deeper analysis.{req_str}"
            elif any(word in query_lower for word in ['them', 'those', 'these', 'they']):
                return f"The user is referencing candidates or topics from the previous context.{candidates_str} The query involves analyzing the referenced subjects in more detail.{req_str}"
            else:
                return f"The user query requires understanding the context from the conversation and providing a relevant response about the candidates or analysis requested.{candidates_str}{req_str}"
    
    def _extract_candidates_from_history(self, conversation_history: List[Dict[str, str]] = None) -> List[str]:
        """
        Extract candidate names mentioned in conversation history.
        
        Looks for patterns like:
        - "1. Name", "2. Name", "#1 Name"
        - "Top candidate: Name"
        - Names in ranking tables
        """
        if not conversation_history:
            return []
        
        import re
        candidates = []
        
        # Look through assistant messages (where rankings/names appear)
        for msg in conversation_history:
            if msg.get("role") != "assistant":
                continue
            
            content = msg.get("content", "")
            
            # Pattern 1: Numbered lists like "1. John Smith" or "#1 John Smith"
            numbered_pattern = r'(?:^|\n)\s*(?:#?\d+[.):]\s*|•\s*)([A-Z][a-záéíóúñ]+(?:\s+[A-Z][a-záéíóúñ]+)+)'
            matches = re.findall(numbered_pattern, content, re.MULTILINE)
            candidates.extend(matches)
            
            # Pattern 2: Table rows with names (| Name |)
            table_pattern = r'\|\s*([A-Z][a-záéíóúñ]+(?:\s+[A-Z][a-záéíóúñ]+)+)\s*\|'
            matches = re.findall(table_pattern, content)
            candidates.extend(matches)
            
            # Pattern 3: "Top candidate: Name" or "Best match: Name"
            top_pattern = r'(?:top|best|#1)\s*(?:candidate|match)?[:\s]+([A-Z][a-záéíóúñ]+(?:\s+[A-Z][a-záéíóúñ]+)+)'
            matches = re.findall(top_pattern, content, re.IGNORECASE)
            candidates.extend(matches)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_candidates = []
        for c in candidates:
            c_normalized = c.strip()
            if c_normalized and c_normalized.lower() not in seen:
                seen.add(c_normalized.lower())
                unique_candidates.append(c_normalized)
        
        logger.info(f"[QUERY_UNDERSTANDING] Extracted {len(unique_candidates)} candidates from history: {unique_candidates[:5]}")
        return unique_candidates
    
    def _extract_json_manually(self, content: str, query: str) -> dict:
        """
        Manually extract key values from malformed JSON-like content.
        
        This handles cases where the LLM returns something that looks like JSON
        but has formatting issues that break standard parsing.
        """
        import re
        
        result = {
            "understood_query": query,
            "query_type": "general",
            "requirements": [],
            "is_cv_related": True,
            "reformulated_prompt": query
        }
        
        # Try to extract understood_query
        match = re.search(r'"understood_query"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', content, re.DOTALL)
        if match:
            result["understood_query"] = match.group(1).replace('\\"', '"').replace('\\n', ' ')
        
        # Try to extract query_type
        match = re.search(r'"query_type"\s*:\s*"([^"]+)"', content)
        if match:
            result["query_type"] = match.group(1)
        
        # Try to extract is_cv_related
        match = re.search(r'"is_cv_related"\s*:\s*(true|false)', content, re.IGNORECASE)
        if match:
            result["is_cv_related"] = match.group(1).lower() == "true"
        
        # Try to extract reformulated_prompt
        match = re.search(r'"reformulated_prompt"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', content, re.DOTALL)
        if match:
            result["reformulated_prompt"] = match.group(1).replace('\\"', '"').replace('\\n', ' ')
        
        # Try to extract requirements array
        match = re.search(r'"requirements"\s*:\s*\[(.*?)\]', content, re.DOTALL)
        if match:
            req_content = match.group(1)
            reqs = re.findall(r'"([^"]+)"', req_content)
            result["requirements"] = reqs
        
        logger.info(f"[QUERY_UNDERSTANDING] Manual extraction result: type={result['query_type']}")
        return result
    
    def _create_heuristic_fallback(self, query: str, error_reason: str) -> QueryUnderstanding:
        """
        Create QueryUnderstanding using heuristics when ALL LLM calls fail.
        
        This is the LAST RESORT - ensures the pipeline NEVER fails.
        """
        query_lower = query.lower()
        
        # Detect query type from keywords - PRIORITY ORDER MATTERS
        # Check specific types first before generic ones
        
        # 1. RED FLAGS / RISK ASSESSMENT (highest priority for risk queries)
        if any(kw in query_lower for kw in ['risk', 'red flag', 'job hopping', 'stability', 'gap', 'concern', 'warning', 'riesgo', 'bandera roja']):
            query_type = 'red_flags'
        
        # 2. SINGLE CANDIDATE / FULL PROFILE
        elif any(kw in query_lower for kw in ['full profile', 'everything about', 'all about', 'todo sobre', 'perfil completo', 'dame todo', 'tell me about', 'analyze']):
            query_type = 'single_candidate'
        
        # 3. COMPARISON
        elif any(kw in query_lower for kw in ['compare', 'versus', 'vs', 'vs.', 'difference', 'comparar', 'comparación']):
            query_type = 'comparison'
        
        # 4. TEAM BUILD (MUST come BEFORE ranking - 'top 3 for team' should be team_build not ranking)
        elif any(kw in query_lower for kw in [
            'build a team', 'build team', 'create a team', 'create team',
            'form a team', 'form team', 'team with', 'team from', 'team of',
            'formar equipo', 'crear equipo', 'equipo con', 'equipo de'
        ]):
            query_type = 'team_build'
        
        # 5. RANKING (now checks that it's not a team_build query)
        elif any(kw in query_lower for kw in ['rank', 'best', 'top', 'order', 'sort', 'mejor', 'ordenar']) and 'compare' not in query_lower and 'team' not in query_lower:
            query_type = 'ranking'
        
        # 6. JOB MATCH
        elif any(kw in query_lower for kw in ['match', 'fit for', 'suitable for', 'qualified for', 'encaja', 'apto para']):
            query_type = 'job_match'
        
        # 7. TALENT POOL / SUMMARY (Priority before search)
        elif any(kw in query_lower for kw in [
            'summary', 'overview', 'resumen', 'vista general',
            'talent pool', 'talents', 'todos los', 'all candidates',
            'how many candidates', 'cuantos candidatos', 'cuántos candidatos',
            'tell me about all', 'what candidates', 'que candidatos',
            'show me all', 'todos los candidatos'
        ]):
            query_type = 'summary'
        
        # 8. SEARCH (generic CV search)
        elif any(kw in query_lower for kw in ['who', 'which', 'find', 'search', 'has', 'know', 'quien', 'buscar']):
            query_type = 'search'
        
        # 9. GENERAL (non-CV)
        else:
            query_type = 'general'
        
        # Detect if CV-related
        cv_keywords = [
            'candidate', 'cv', 'resume', 'experience', 'skill', 'python', 
            'developer', 'engineer', 'work', 'job', 'year', 'company',
            'candidato', 'experiencia', 'habilidad', 'trabajo', 'empresa'
        ]
        is_cv_related = any(kw in query_lower for kw in cv_keywords)
        
        # If query type suggests CV analysis, force is_cv_related
        cv_related_types = {'ranking', 'comparison', 'search', 'red_flags', 'single_candidate', 'job_match', 'team_build', 'summary'}
        if query_type in cv_related_types:
            is_cv_related = True
        
        logger.warning(
            f"[QUERY_UNDERSTANDING] Using HEURISTIC fallback: "
            f"type={query_type}, cv_related={is_cv_related}, reason={error_reason[:100]}"
        )
        
        # Generate expanded understanding even in fallback mode
        expanded_query = self._generate_expanded_understanding(query, query_type, [])
        
        return QueryUnderstanding(
            original_query=query,
            understood_query=expanded_query,  # Use expanded version, not original
            query_type=query_type,
            requirements=[],  # Can't extract requirements without LLM
            is_cv_related=is_cv_related,
            confidence=0.5,  # Lower confidence for heuristic fallback
            reformulated_prompt=expanded_query,  # Also use expanded version
            metadata={
                "fallback": True,
                "fallback_type": "heuristic",
                "error": error_reason,
                "openrouter_cost": 0.0  # No cost for heuristic
            }
        )
