"""
Re-ranking Service for CV Screener.

Uses an LLM to re-rank search results by semantic relevance to the query.
This improves upon pure vector similarity by considering contextual relevance.
"""
import logging
import json
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
import httpx

from app.config import settings
from app.providers.base import SearchResult

logger = logging.getLogger(__name__)


def _get_attr(obj, key, default=None):
    """Get attribute from object or dict."""
    if isinstance(obj, dict):
        if key == 'cv_id':
            return obj.get('metadata', {}).get('cv_id', obj.get('cv_id', default))
        elif key == 'content':
            return obj.get('content', obj.get('text', default))
        elif key == 'filename':
            return obj.get('metadata', {}).get('filename', obj.get('filename', default))
        elif key == 'similarity':
            return obj.get('similarity', obj.get('score', default or 0.5))
        return obj.get(key, default)
    return getattr(obj, key, default)


@dataclass
class RerankResult:
    """Result of re-ranking operation."""
    original_results: List[SearchResult]
    reranked_results: List[SearchResult]
    scores: Dict[str, float]  # cv_id -> relevance score
    latency_ms: float
    model_used: str
    enabled: bool = True


RERANKING_PROMPT = """You are a relevance scoring assistant for a CV screening system.

Score how relevant each CV chunk is to the user's query on a scale of 0-10.
- 10 = Perfectly relevant, directly answers the query
- 7-9 = Highly relevant, contains key information
- 4-6 = Moderately relevant, some useful information
- 1-3 = Slightly relevant, tangentially related
- 0 = Not relevant at all

USER QUERY: {query}

CV CHUNKS TO SCORE:
{chunks}

Respond with ONLY a JSON array of scores in the same order as the chunks:
[score1, score2, score3, ...]

Example response: [8, 5, 9, 2, 7]

Scores (JSON array only):"""


class RerankingService:
    """
    Service for re-ranking search results using LLM.
    
    Uses a fast model to score relevance of each chunk to the query,
    then reorders results by this score.
    """
    
    DEFAULT_MODEL = "google/gemini-2.0-flash-001"
    
    def __init__(self, model: Optional[str] = None, enabled: bool = True):
        """
        Initialize the re-ranking service.
        
        Args:
            model: LLM model to use for scoring
            enabled: Whether re-ranking is enabled
        """
        self.model = model or self.DEFAULT_MODEL
        self.enabled = enabled
        self.api_key = settings.openrouter_api_key or ""
        # Don't create persistent client - use context manager per request
        logger.info(f"RerankingService initialized with model: {self.model}, enabled: {enabled}")
    
    async def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_k: int = None
    ) -> RerankResult:
        """
        Re-rank search results by relevance to query.
        
        Args:
            query: The user's query
            results: List of search results to re-rank
            top_k: Optional limit on results (None = return all, just reordered)
            
        Returns:
            RerankResult with reordered results
        """
        import time
        start_time = time.perf_counter()
        
        # If disabled or no results, return as-is (ALL results, not truncated)
        if not self.enabled or not results:
            return RerankResult(
                original_results=results,
                reranked_results=results,  # Return ALL results
                scores={},
                latency_ms=0,
                model_used=self.model,
                enabled=False
            )
        
        # If no API key, return original order (ALL results)
        if not self.api_key:
            logger.warning("No API key for reranking, returning original order")
            return RerankResult(
                original_results=results,
                reranked_results=results,  # Return ALL results
                scores={_get_attr(r, 'cv_id'): _get_attr(r, 'similarity', 0.5) for r in results},
                latency_ms=(time.perf_counter() - start_time) * 1000,
                model_used=self.model,
                enabled=True
            )
        
        try:
            # Format chunks for scoring
            chunks_text = self._format_chunks(results)
            prompt = RERANKING_PROMPT.format(query=query, chunks=chunks_text)
            
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
                        "temperature": 0.0,
                        "max_tokens": 200
                    }
                )
                response.raise_for_status()
                data = response.json()
            
            content = data["choices"][0]["message"]["content"].strip()
            
            # Parse scores
            scores = self._parse_scores(content, len(results))
            
            # Create scored results
            scored_results = []
            score_dict = {}
            for i, result in enumerate(results):
                score = scores[i] if i < len(scores) else 0
                # Combine LLM score with original similarity
                similarity = _get_attr(result, 'similarity', 0.5)
                combined_score = (score / 10.0) * 0.7 + similarity * 0.3
                scored_results.append((result, combined_score, score))
                cv_id = _get_attr(result, 'cv_id')
                if cv_id:
                    score_dict[cv_id] = score
            
            # Sort by combined score
            scored_results.sort(key=lambda x: x[1], reverse=True)
            
            # Extract reranked results (all of them, optionally limited by top_k)
            reranked = [r[0] for r in scored_results]
            if top_k is not None:
                reranked = reranked[:top_k]
            
            latency = (time.perf_counter() - start_time) * 1000
            
            logger.info(f"Reranked {len(results)} results in {latency:.1f}ms")
            
            return RerankResult(
                original_results=results,
                reranked_results=reranked,
                scores=score_dict,
                latency_ms=latency,
                model_used=self.model,
                enabled=True
            )
            
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            latency = (time.perf_counter() - start_time) * 1000
            # On error, return ALL results in original order
            return RerankResult(
                original_results=results,
                reranked_results=results,  # Return ALL results
                scores={_get_attr(r, 'cv_id'): _get_attr(r, 'similarity', 0.5) for r in results},
                latency_ms=latency,
                model_used=self.model,
                enabled=True
            )
    
    def _format_chunks(self, results: List[SearchResult], max_chars: int = 300) -> str:
        """Format chunks for the scoring prompt."""
        lines = []
        for i, result in enumerate(results):
            content = _get_attr(result, 'content', '')[:max_chars]
            full_content = _get_attr(result, 'content', '')
            if len(full_content) > max_chars:
                content += "..."
            filename = _get_attr(result, 'filename', 'Unknown')
            lines.append(f"[{i+1}] {filename}: {content}")
        return "\n\n".join(lines)
    
    def _parse_scores(self, content: str, expected_count: int) -> List[float]:
        """Parse scores from LLM response."""
        try:
            # Clean up response
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()
            
            # Find JSON array
            start = content.find("[")
            end = content.rfind("]") + 1
            if start >= 0 and end > start:
                content = content[start:end]
            
            scores = json.loads(content)
            
            # Validate and normalize
            validated = []
            for score in scores:
                try:
                    s = float(score)
                    validated.append(max(0, min(10, s)))
                except:
                    validated.append(5.0)
            
            # Pad if needed
            while len(validated) < expected_count:
                validated.append(5.0)
            
            return validated
            
        except Exception as e:
            logger.error(f"Failed to parse reranking scores: {e}")
            return [5.0] * expected_count
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


# Singleton instance
_reranking_service: Optional[RerankingService] = None


def get_reranking_service(model: Optional[str] = None, enabled: bool = True) -> RerankingService:
    """Get singleton instance of RerankingService."""
    global _reranking_service
    if _reranking_service is None or _reranking_service.model != (model or RerankingService.DEFAULT_MODEL):
        _reranking_service = RerankingService(model=model, enabled=enabled)
    return _reranking_service
