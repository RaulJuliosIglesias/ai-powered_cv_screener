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

Analyze the user's question and extract:
1. What they're actually asking for
2. Resolve any references to previous messages (e.g., "el top candidate", "this person", "he", "she")
3. Break down complex queries into clear requirements
4. Identify if this is CV-related

USER QUERY: {query}

IMPORTANT: If the query contains references like "el top candidate", "the best one", "this person", "he/she", look at the conversation history above to identify WHO is being referred to, and include their FULL NAME in your reformulated prompt.

Respond in this EXACT JSON format (no markdown, just raw JSON):
{{
  "understood_query": "Clear restatement of what user wants (with resolved names)",
  "query_type": "ranking|comparison|search|filter|general",
  "requirements": [
    "requirement 1",
    "requirement 2"
  ],
  "is_cv_related": true,
  "reformulated_prompt": "A clear, structured prompt to send to the CV analysis model (with ALL names resolved)"
}}

EXAMPLES:

Query: "Rank all 33 candidates by experience and show if they worked at Google or Microsoft"
{{
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
}}

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
        
        # Parse JSON response
        return self._parse_llm_response(query, content, metadata)
    
    def _parse_llm_response(self, query: str, content: str, metadata: dict) -> QueryUnderstanding:
        """
        Parse LLM response into QueryUnderstanding.
        """
        # Clean up markdown if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()
        
        parsed = json.loads(content)
        
        query_type = parsed.get("query_type", "general")
        is_cv_related = parsed.get("is_cv_related", True)
        
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
            understood_query=parsed.get("understood_query", query),
            query_type=query_type,
            requirements=parsed.get("requirements", []),
            is_cv_related=is_cv_related,
            confidence=0.9,
            reformulated_prompt=parsed.get("reformulated_prompt", query),
            metadata=metadata
        )
    
    def _create_heuristic_fallback(self, query: str, error_reason: str) -> QueryUnderstanding:
        """
        Create QueryUnderstanding using heuristics when ALL LLM calls fail.
        
        This is the LAST RESORT - ensures the pipeline NEVER fails.
        """
        query_lower = query.lower()
        
        # Detect query type from keywords
        if any(kw in query_lower for kw in ['rank', 'best', 'top', 'order', 'sort', 'mejor', 'ordenar']):
            query_type = 'ranking'
        elif any(kw in query_lower for kw in ['compare', 'versus', 'vs', 'difference', 'comparar']):
            query_type = 'comparison'
        elif any(kw in query_lower for kw in ['filter', 'only', 'just', 'exclude', 'filtrar', 'solo']):
            query_type = 'filter'
        elif any(kw in query_lower for kw in ['who', 'which', 'find', 'search', 'has', 'know', 'quien', 'buscar']):
            query_type = 'search'
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
        if query_type in {'ranking', 'comparison', 'search', 'filter'}:
            is_cv_related = True
        
        logger.warning(
            f"[QUERY_UNDERSTANDING] Using HEURISTIC fallback: "
            f"type={query_type}, cv_related={is_cv_related}, reason={error_reason[:100]}"
        )
        
        return QueryUnderstanding(
            original_query=query,
            understood_query=query,  # Use original as-is
            query_type=query_type,
            requirements=[],  # Can't extract requirements without LLM
            is_cv_related=is_cv_related,
            confidence=0.5,  # Lower confidence for heuristic fallback
            reformulated_prompt=query,
            metadata={
                "fallback": True,
                "fallback_type": "heuristic",
                "error": error_reason,
                "openrouter_cost": 0.0  # No cost for heuristic
            }
        )
