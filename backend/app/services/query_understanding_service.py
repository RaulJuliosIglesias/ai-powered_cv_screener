"""
Query Understanding Service - Step 1 of 2-step RAG.

Uses a fast model to understand, reformulate, and structure the user's query
before sending it to the main generation model.
"""
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
import httpx

from app.config import settings, timeouts
from app.providers.cloud.llm import calculate_openrouter_cost

logger = logging.getLogger(__name__)


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

Analyze the user's question and extract:
1. What they're actually asking for
2. Break down complex queries into clear requirements
3. Identify if this is CV-related

USER QUERY: {query}

Respond in this EXACT JSON format (no markdown, just raw JSON):
{{
  "understood_query": "Clear restatement of what user wants",
  "query_type": "ranking|comparison|search|filter|general",
  "requirements": [
    "requirement 1",
    "requirement 2"
  ],
  "is_cv_related": true,
  "reformulated_prompt": "A clear, structured prompt to send to the CV analysis model"
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

Now analyze the user's query and respond with JSON only:"""


class QueryUnderstandingService:
    """
    Service for understanding and reformulating user queries.
    
    Uses a fast, cheap model for quick query analysis before
    the main RAG generation step.
    """
    
    def __init__(self, model: str):
        if not model:
            raise ValueError("model parameter is required and cannot be empty")
        self.model = model
        self.api_key = settings.openrouter_api_key or ""
        logger.info(f"QueryUnderstandingService initialized with model: {self.model}")
        logger.info(f"  API key available: {bool(self.api_key)}")
    
    async def understand(self, query: str) -> QueryUnderstanding:
        """
        Analyze and understand the user's query.
        
        Args:
            query: The user's original question
            
        Returns:
            QueryUnderstanding with parsed intent and reformulated prompt
        """
        if not self.api_key:
            raise ValueError("OpenRouter API key is required for query understanding")
        
        try:
            prompt = QUERY_UNDERSTANDING_PROMPT.format(query=query)
            
            # Use context manager to ensure client is closed after request
            from app.providers.base import get_openrouter_url
            async with httpx.AsyncClient(timeout=timeouts.HTTP_MEDIUM) as client:
                response = await client.post(
                    get_openrouter_url("chat/completions"),
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.1,
                        "max_tokens": 500
                    }
                )
                response.raise_for_status()
                data = response.json()
            
            content = data["choices"][0]["message"]["content"].strip()
            
            # Extract OpenRouter usage metadata and calculate cost
            metadata = {}
            if "usage" in data:
                usage = data["usage"]
                if isinstance(usage, dict):
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
                    metadata["prompt_tokens"] = prompt_tokens
                    metadata["completion_tokens"] = completion_tokens
                    metadata["total_tokens"] = prompt_tokens + completion_tokens
                    # Calculate cost from tokens and model pricing
                    metadata["openrouter_cost"] = calculate_openrouter_cost(
                        self.model, prompt_tokens, completion_tokens
                    )
                    logger.info(f"[QUERY_UNDERSTANDING] OpenRouter usage: {metadata}")
            else:
                logger.warning("[QUERY_UNDERSTANDING] No 'usage' field in OpenRouter response")
            
            # Parse JSON response
            import json
            # Clean up markdown if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()
            
            parsed = json.loads(content)
            
            query_type = parsed.get("query_type", "general")
            is_cv_related = parsed.get("is_cv_related", True)
            
            # IMPORTANT: If query_type indicates CV analysis intent, force is_cv_related=True
            # This fixes cases where LLM incorrectly marks "candidates" queries as non-CV
            cv_related_types = {"ranking", "comparison", "search", "filter"}
            if query_type in cv_related_types:
                is_cv_related = True
            
            # Also check for CV-related keywords as fallback
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
            
        except Exception as e:
            logger.error(f"Query understanding failed: {e}")
            raise
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
