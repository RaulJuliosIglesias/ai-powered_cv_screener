"""
Claim-Level Verification Service for RAG v5.

Extracts individual claims from responses and verifies each against source context.
"""
import logging
import json
import re
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class Claim:
    """A single claim extracted from a response."""
    text: str
    candidate_name: Optional[str] = None
    claim_type: str = "general"  # skill, experience, education, company, general
    

@dataclass
class VerifiedClaim:
    """A claim with verification status."""
    claim: Claim
    status: str  # "verified", "unverified", "contradicted"
    evidence: Optional[str] = None
    confidence: float = 0.0


@dataclass
class ClaimVerificationResult:
    """Result of claim-level verification."""
    total_claims: int
    verified_claims: List[VerifiedClaim]
    unverified_claims: List[VerifiedClaim]
    contradicted_claims: List[VerifiedClaim]
    overall_score: float
    needs_regeneration: bool = False
    

CLAIM_EXTRACTION_PROMPT = """Extract all factual claims about candidates from this response.
Focus on claims about: skills, experience, companies, education, years of experience.

RESPONSE:
{response}

Return a JSON array of claims. Each claim should be a specific, verifiable statement.

Example output:
[
  {{"text": "Juan has 5 years of Python experience", "candidate": "Juan", "type": "experience"}},
  {{"text": "Maria worked at Google", "candidate": "Maria", "type": "company"}},
  {{"text": "Pedro knows React and TypeScript", "candidate": "Pedro", "type": "skill"}}
]

Extract claims (JSON array only):"""


CLAIM_VERIFICATION_PROMPT = """Verify if this claim is supported by the CV context.

CLAIM: {claim}

CV CONTEXT:
{context}

Respond with JSON:
{{
  "status": "verified" | "unverified" | "contradicted",
  "evidence": "quote from context that supports/contradicts, or null",
  "confidence": 0.0-1.0
}}

Verification:"""


class ClaimVerifierService:
    """
    Service for claim-level verification of LLM responses.
    
    Improves hallucination detection by:
    1. Extracting individual claims from response
    2. Verifying each claim against source context
    3. Flagging responses with too many unverified claims
    """
    
    def __init__(
        self,
        model: str,
        min_verified_ratio: float = 0.7
    ):
        if not model:
            raise ValueError("model parameter is required and cannot be empty")
        self.model = model
        self.min_verified_ratio = min_verified_ratio
        self.api_key = settings.openrouter_api_key or ""
        logger.info(f"ClaimVerifierService initialized")
    
    async def verify_response(
        self,
        response: str,
        context_chunks: List[Dict[str, Any]]
    ) -> ClaimVerificationResult:
        """
        Verify all claims in a response against context.
        
        Args:
            response: LLM response to verify
            context_chunks: Source chunks used to generate response
            
        Returns:
            ClaimVerificationResult with verification details
        """
        if not self.api_key:
            return self._fallback_result()
        
        try:
            # Step 1: Extract claims
            claims = await self._extract_claims(response)
            
            if not claims:
                return ClaimVerificationResult(
                    total_claims=0,
                    verified_claims=[],
                    unverified_claims=[],
                    contradicted_claims=[],
                    overall_score=1.0
                )
            
            # Step 2: Build context string
            context_str = self._build_context_string(context_chunks)
            
            # Step 3: Verify each claim
            verified = []
            unverified = []
            contradicted = []
            
            for claim in claims:
                result = await self._verify_claim(claim, context_str)
                
                if result.status == "verified":
                    verified.append(result)
                elif result.status == "contradicted":
                    contradicted.append(result)
                else:
                    unverified.append(result)
            
            # Calculate overall score
            total = len(claims)
            verified_count = len(verified)
            contradicted_count = len(contradicted)
            
            # Contradicted claims are worse than unverified
            score = (verified_count - contradicted_count * 2) / total if total > 0 else 1.0
            score = max(0.0, min(1.0, score))
            
            # Determine if regeneration needed
            needs_regen = (
                score < self.min_verified_ratio or
                contradicted_count > 0
            )
            
            logger.info(
                f"Claim verification: {verified_count}/{total} verified, "
                f"{contradicted_count} contradicted, score={score:.2f}"
            )
            
            return ClaimVerificationResult(
                total_claims=total,
                verified_claims=verified,
                unverified_claims=unverified,
                contradicted_claims=contradicted,
                overall_score=score,
                needs_regeneration=needs_regen
            )
            
        except Exception as e:
            logger.error(f"Claim verification failed: {e}")
            return self._fallback_result()
    
    async def _extract_claims(self, response: str) -> List[Claim]:
        """Extract claims from response."""
        prompt = CLAIM_EXTRACTION_PROMPT.format(response=response[:3000])
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.0,
                    "max_tokens": 1000
                }
            )
            resp.raise_for_status()
            data = resp.json()
        
        content = data["choices"][0]["message"]["content"].strip()
        
        # Parse JSON
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
        
        parsed = json.loads(content)
        
        claims = []
        for item in parsed:
            claims.append(Claim(
                text=item.get("text", ""),
                candidate_name=item.get("candidate"),
                claim_type=item.get("type", "general")
            ))
        
        return claims
    
    async def _verify_claim(self, claim: Claim, context: str) -> VerifiedClaim:
        """Verify a single claim against context."""
        # For efficiency, first do a quick heuristic check
        claim_lower = claim.text.lower()
        context_lower = context.lower()
        
        # Quick keyword check
        keywords = claim_lower.split()
        keyword_matches = sum(1 for kw in keywords if len(kw) > 3 and kw in context_lower)
        
        # If candidate name not in context, likely unverified
        if claim.candidate_name:
            name_parts = claim.candidate_name.lower().split()
            if not any(part in context_lower for part in name_parts):
                return VerifiedClaim(
                    claim=claim,
                    status="unverified",
                    evidence=None,
                    confidence=0.3
                )
        
        # Use LLM for detailed verification
        prompt = CLAIM_VERIFICATION_PROMPT.format(
            claim=claim.text,
            context=context[:5000]
        )
        
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
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
                resp.raise_for_status()
                data = resp.json()
            
            content = data["choices"][0]["message"]["content"].strip()
            
            # Parse JSON
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()
            
            parsed = json.loads(content)
            
            return VerifiedClaim(
                claim=claim,
                status=parsed.get("status", "unverified"),
                evidence=parsed.get("evidence"),
                confidence=parsed.get("confidence", 0.5)
            )
            
        except Exception as e:
            logger.warning(f"Claim verification LLM call failed: {e}")
            # Fallback to heuristic
            if keyword_matches >= len(keywords) * 0.5:
                return VerifiedClaim(claim=claim, status="verified", confidence=0.5)
            return VerifiedClaim(claim=claim, status="unverified", confidence=0.3)
    
    def _build_context_string(self, chunks: List[Dict[str, Any]]) -> str:
        """Build context string from chunks."""
        parts = []
        for chunk in chunks:
            content = chunk.get("content", "")
            metadata = chunk.get("metadata", {})
            filename = metadata.get("filename", "Unknown")
            candidate = metadata.get("candidate_name", "")
            
            header = f"[{filename}"
            if candidate:
                header += f" - {candidate}"
            header += "]"
            
            parts.append(f"{header}\n{content}")
        
        return "\n\n---\n\n".join(parts)
    
    def _fallback_result(self) -> ClaimVerificationResult:
        """Return fallback result when verification fails."""
        return ClaimVerificationResult(
            total_claims=0,
            verified_claims=[],
            unverified_claims=[],
            contradicted_claims=[],
            overall_score=0.7,
            needs_regeneration=False
        )


# Singleton
_claim_verifier: Optional[ClaimVerifierService] = None


def get_claim_verifier_service(
    model: str
) -> ClaimVerifierService:
    """Get singleton instance."""
    global _claim_verifier
    if _claim_verifier is None or _claim_verifier.model != model:
        _claim_verifier = ClaimVerifierService(model=model)
    return _claim_verifier
