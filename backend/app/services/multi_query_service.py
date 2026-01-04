"""
Multi-Query Generation Service for RAG v5.

Generates multiple semantic variations of a query to improve retrieval coverage.
"""
import logging
import json
from typing import List, Optional
from dataclasses import dataclass
import httpx

from app.config import settings, timeouts

logger = logging.getLogger(__name__)


@dataclass
class MultiQueryResult:
    """Result of multi-query generation."""
    original_query: str
    variations: List[str]
    hyde_document: Optional[str] = None
    entities: dict = None
    
    def __post_init__(self):
        if self.entities is None:
            self.entities = {}


MULTI_QUERY_PROMPT = """You are a query expansion assistant for a CV/resume screening system.

Given a user query, generate 3-4 semantic variations that capture different ways to search for the same information.
Also extract key entities (skills, companies, roles, years of experience).

USER QUERY: {query}

Respond in this EXACT JSON format (no markdown, just raw JSON):
{{
  "variations": [
    "variation 1 - different phrasing",
    "variation 2 - focus on specific skills/keywords",
    "variation 3 - broader or narrower scope"
  ],
  "entities": {{
    "skills": ["skill1", "skill2"],
    "companies": ["company1"],
    "roles": ["role1"],
    "experience_years": null,
    "education": []
  }}
}}

EXAMPLES:

Query: "Who knows Python?"
{{
  "variations": [
    "Candidates with Python programming experience",
    "Developers skilled in Python, Django, Flask, FastAPI",
    "Software engineers with Python in their tech stack",
    "Python developers with backend experience"
  ],
  "entities": {{
    "skills": ["Python", "Django", "Flask", "FastAPI"],
    "companies": [],
    "roles": ["Developer", "Software Engineer"],
    "experience_years": null,
    "education": []
  }}
}}

Query: "Senior engineers with 5+ years at Google"
{{
  "variations": [
    "Experienced engineers who worked at Google",
    "Senior software engineers with Google experience",
    "Candidates with 5 or more years at major tech companies like Google",
    "Tech leads or senior developers from Google"
  ],
  "entities": {{
    "skills": [],
    "companies": ["Google"],
    "roles": ["Senior Engineer", "Tech Lead"],
    "experience_years": 5,
    "education": []
  }}
}}

Now analyze the query and respond with JSON only:"""


HYDE_PROMPT = """You are a CV/resume content generator. Given a query about candidates, 
write a SHORT hypothetical CV excerpt (2-3 sentences) that would perfectly answer this query.

Query: {query}

Write a brief CV excerpt that would be an ideal match for this query.
Focus on specific skills, experience, and achievements.
Write as if it's actual CV content, not a description.

CV Excerpt:"""


class MultiQueryService:
    """
    Service for generating multiple query variations and HyDE documents.
    
    This improves retrieval by:
    1. Multi-Query: Search with multiple phrasings to catch more relevant docs
    2. HyDE: Generate hypothetical ideal document to improve semantic matching
    3. Entity Extraction: Enable hybrid keyword search
    """
    
    def __init__(self, model: str, hyde_enabled: bool = True):
        if not model:
            raise ValueError("model parameter is required and cannot be empty")
        self.model = model
        self.hyde_enabled = hyde_enabled
        self.api_key = settings.openrouter_api_key or ""
        logger.info(f"MultiQueryService initialized with model: {self.model}")
    
    async def generate(self, query: str) -> MultiQueryResult:
        """
        Generate query variations, entities, and optionally HyDE document.
        
        Args:
            query: Original user query
            
        Returns:
            MultiQueryResult with variations, entities, and hyde_document
        """
        if not self.api_key:
            logger.warning("No API key, returning original query only")
            return MultiQueryResult(
                original_query=query,
                variations=[query]
            )
        
        try:
            # Generate variations and entities
            variations, entities = await self._generate_variations(query)
            
            # Generate HyDE document if enabled
            hyde_doc = None
            if self.hyde_enabled:
                hyde_doc = await self._generate_hyde(query)
            
            return MultiQueryResult(
                original_query=query,
                variations=variations,
                hyde_document=hyde_doc,
                entities=entities
            )
            
        except Exception as e:
            logger.error(f"Multi-query generation failed: {e}")
            return MultiQueryResult(
                original_query=query,
                variations=[query]
            )
    
    async def _generate_variations(self, query: str) -> tuple[List[str], dict]:
        """Generate query variations and extract entities."""
        prompt = MULTI_QUERY_PROMPT.format(query=query)
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
                    "temperature": 0.3,
                    "max_tokens": 500
                }
            )
            response.raise_for_status()
            data = response.json()
        
        content = data["choices"][0]["message"]["content"].strip()
        
        # Parse JSON
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()
        
        parsed = json.loads(content)
        
        variations = parsed.get("variations", [query])
        # Always include original query
        if query not in variations:
            variations.insert(0, query)
        
        entities = parsed.get("entities", {})
        
        logger.info(f"Generated {len(variations)} query variations")
        return variations, entities
    
    async def _generate_hyde(self, query: str) -> str:
        """Generate hypothetical document for HyDE."""
        prompt = HYDE_PROMPT.format(query=query)
        from app.providers.base import get_openrouter_url
        
        async with httpx.AsyncClient(timeout=timeouts.HTTP_SHORT) as client:
            response = await client.post(
                get_openrouter_url("chat/completions"),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.5,
                    "max_tokens": 200
                }
            )
            response.raise_for_status()
            data = response.json()
        
        hyde_doc = data["choices"][0]["message"]["content"].strip()
        logger.debug(f"Generated HyDE document: {hyde_doc[:100]}...")
        return hyde_doc


# Singleton
_multi_query_service: Optional[MultiQueryService] = None


def get_multi_query_service(
    model: str,
    hyde_enabled: bool = True
) -> MultiQueryService:
    """Get singleton instance."""
    global _multi_query_service
    if _multi_query_service is None or _multi_query_service.model != model:
        _multi_query_service = MultiQueryService(model=model, hyde_enabled=hyde_enabled)
    return _multi_query_service
