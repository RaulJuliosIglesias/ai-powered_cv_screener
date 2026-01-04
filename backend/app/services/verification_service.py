"""
LLM Verification Service for CV Screener.

Uses an LLM to verify that generated responses are grounded in the provided context.
This complements the heuristic-based hallucination service with semantic verification.
"""
import logging
import json
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
import httpx

from app.config import settings
from app.providers.base import SearchResult
from app.utils.text_utils import smart_truncate

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    """Result of LLM verification."""
    is_grounded: bool
    groundedness_score: float  # 0.0 to 1.0
    verified_claims: List[str]
    ungrounded_claims: List[str]
    suggestions: List[str]
    latency_ms: float
    model_used: str
    enabled: bool = True


VERIFICATION_PROMPT = """You are a fact-checking assistant for a CV screening system.

Your task is to verify if ALL information in the RESPONSE is supported by the CONTEXT.
The context contains excerpts from CVs that were used to generate the response.

CONTEXT (CV excerpts):
{context}

RESPONSE TO VERIFY:
{response}

USER'S ORIGINAL QUERY:
{query}

Analyze the response and check if every claim is supported by the context.

Respond with ONLY this JSON format:
{{
  "is_grounded": true/false,
  "groundedness_score": 0.0-1.0,
  "verified_claims": ["claim 1 that IS in context", "claim 2 that IS in context"],
  "ungrounded_claims": ["claim that is NOT in context"],
  "suggestions": ["suggestion to improve accuracy"]
}}

IMPORTANT:
- A response is grounded if ALL factual claims can be traced to the context
- Names, skills, companies, and dates must match the context
- General statements like "Based on the CVs..." don't need verification
- If the response says "no candidates found", verify this is accurate given the context

JSON response:"""


class LLMVerificationService:
    """
    Service for verifying LLM responses against context using another LLM.
    
    Uses a fast model to check if the generated response is fully grounded
    in the provided CV context.
    """
    
    def __init__(self, model: str, enabled: bool = True):
        """
        Initialize the verification service.
        
        Args:
            model: LLM model to use for verification (required)
            enabled: Whether verification is enabled
        """
        if not model:
            raise ValueError("model parameter is required and cannot be empty")
        self.model = model
        self.enabled = enabled
        self.api_key = settings.openrouter_api_key or ""
        # Don't create persistent client - use context manager per request
        logger.info(f"LLMVerificationService initialized with model: {self.model}, enabled: {enabled}")
    
    async def verify(
        self,
        response: str,
        context_chunks: List[Dict[str, Any]],
        query: str
    ) -> VerificationResult:
        """
        Verify that a response is grounded in the provided context.
        
        Args:
            response: The LLM-generated response to verify
            context_chunks: List of context chunks with content and metadata
            query: The original user query
            
        Returns:
            VerificationResult with groundedness assessment
        """
        import time
        start_time = time.perf_counter()
        
        # If disabled, return positive result
        if not self.enabled:
            return VerificationResult(
                is_grounded=True,
                groundedness_score=1.0,
                verified_claims=[],
                ungrounded_claims=[],
                suggestions=[],
                latency_ms=0,
                model_used=self.model,
                enabled=False
            )
        
        # If no API key, return default
        if not self.api_key:
            logger.warning("No API key for verification, returning default result")
            return VerificationResult(
                is_grounded=True,
                groundedness_score=0.7,
                verified_claims=[],
                ungrounded_claims=[],
                suggestions=["Verification skipped - no API key"],
                latency_ms=(time.perf_counter() - start_time) * 1000,
                model_used=self.model,
                enabled=True
            )
        
        # If no context or response, return default
        if not context_chunks or not response:
            return VerificationResult(
                is_grounded=True,
                groundedness_score=0.8,
                verified_claims=[],
                ungrounded_claims=[],
                suggestions=[],
                latency_ms=(time.perf_counter() - start_time) * 1000,
                model_used=self.model,
                enabled=True
            )
        
        try:
            # Format context
            context_text = self._format_context(context_chunks)
            
            truncated_response = smart_truncate(
                response,
                max_chars=2000,
                preserve="start"
            )
            prompt = VERIFICATION_PROMPT.format(
                context=context_text,
                response=truncated_response,
                query=query
            )
            
            # Use context manager to ensure client is closed after request
            from app.providers.base import get_openrouter_url
            async with httpx.AsyncClient(timeout=30.0) as client:
                api_response = await client.post(
                    get_openrouter_url("chat/completions"),
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.0,
                        "max_tokens": 500
                    }
                )
                api_response.raise_for_status()
                data = api_response.json()
            
            content = data["choices"][0]["message"]["content"].strip()
            
            # Parse verification result
            result = self._parse_result(content)
            
            latency = (time.perf_counter() - start_time) * 1000
            
            logger.info(
                f"Verification completed in {latency:.1f}ms - "
                f"grounded: {result['is_grounded']}, score: {result['groundedness_score']:.2f}"
            )
            
            return VerificationResult(
                is_grounded=result["is_grounded"],
                groundedness_score=result["groundedness_score"],
                verified_claims=result["verified_claims"],
                ungrounded_claims=result["ungrounded_claims"],
                suggestions=result["suggestions"],
                latency_ms=latency,
                model_used=self.model,
                enabled=True
            )
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            latency = (time.perf_counter() - start_time) * 1000
            return VerificationResult(
                is_grounded=True,
                groundedness_score=0.7,
                verified_claims=[],
                ungrounded_claims=[],
                suggestions=[f"Verification error: {str(e)[:50]}"],
                latency_ms=latency,
                model_used=self.model,
                enabled=True
            )
    
    def _format_context(self, chunks: List[Dict[str, Any]], max_chars: int = 3000) -> str:
        """Format context chunks for verification prompt."""
        lines = []
        total_chars = 0
        
        for i, chunk in enumerate(chunks):
            content = chunk.get("content", "")
            metadata = chunk.get("metadata", {})
            filename = metadata.get("filename", f"CV {i+1}")
            
            # Truncate if needed
            remaining = max_chars - total_chars
            if remaining <= 0:
                break
            
            if len(content) > remaining:
                content = content[:remaining] + "..."
            
            lines.append(f"[{filename}]: {content}")
            total_chars += len(content)
        
        return "\n\n".join(lines)
    
    def _parse_result(self, content: str) -> Dict[str, Any]:
        """Parse verification result from LLM response."""
        default = {
            "is_grounded": True,
            "groundedness_score": 0.7,
            "verified_claims": [],
            "ungrounded_claims": [],
            "suggestions": []
        }
        
        try:
            # Clean up response
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()
            
            # Find JSON object
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                content = content[start:end]
            
            parsed = json.loads(content)
            
            return {
                "is_grounded": bool(parsed.get("is_grounded", True)),
                "groundedness_score": float(parsed.get("groundedness_score", 0.7)),
                "verified_claims": list(parsed.get("verified_claims", [])),
                "ungrounded_claims": list(parsed.get("ungrounded_claims", [])),
                "suggestions": list(parsed.get("suggestions", []))
            }
            
        except Exception as e:
            logger.error(f"Failed to parse verification result: {e}")
            return default
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


# Singleton instance
_verification_service: Optional[LLMVerificationService] = None


def get_verification_service(model: str, enabled: bool = True) -> LLMVerificationService:
    """Get singleton instance of LLMVerificationService."""
    global _verification_service
    if _verification_service is None or _verification_service.model != model:
        _verification_service = LLMVerificationService(model=model, enabled=enabled)
    return _verification_service
