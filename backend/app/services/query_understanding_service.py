"""
Query Understanding Service - Step 1 of 2-step RAG.

Uses a fast model to understand, reformulate, and structure the user's query
before sending it to the main generation model.
"""
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class QueryUnderstanding:
    """Result of query understanding step."""
    original_query: str
    understood_query: str
    query_type: str  # ranking, comparison, search, filter, general
    requirements: list  # List of requirements extracted
    is_cv_related: bool
    confidence: float
    reformulated_prompt: str


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
    
    # Default fast model for query understanding
    DEFAULT_MODEL = "google/gemini-2.0-flash-001"
    
    def __init__(self, model: Optional[str] = None):
        self.model = model or self.DEFAULT_MODEL
        self.api_key = settings.openrouter_api_key or ""
        # Don't create persistent client - use context manager per request
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
            logger.warning("No API key, returning original query")
            return self._fallback_understanding(query)
        
        try:
            prompt = QUERY_UNDERSTANDING_PROMPT.format(query=query)
            
            # Use context manager to ensure client is closed after request
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
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
                reformulated_prompt=parsed.get("reformulated_prompt", query)
            )
            
        except Exception as e:
            logger.error(f"Query understanding failed: {e}")
            return self._fallback_understanding(query)
    
    def _fallback_understanding(self, query: str) -> QueryUnderstanding:
        """Fallback when API fails - return original query."""
        return QueryUnderstanding(
            original_query=query,
            understood_query=query,
            query_type="general",
            requirements=[],
            is_cv_related=True,  # Assume CV-related
            confidence=0.5,
            reformulated_prompt=query
        )
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
