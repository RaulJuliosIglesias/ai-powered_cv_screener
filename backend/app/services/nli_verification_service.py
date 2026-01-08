"""
NLI Verification Service for Hallucination Detection.

Uses Natural Language Inference (NLI) to verify if claims in LLM responses
are supported by the source context (CV chunks).

Benefits over LLM+Regex verification:
- Precise entailment detection (not just keyword matching)
- Catches subtle hallucinations that regex misses
- No false positives from paraphrased but correct claims
- FREE via HuggingFace Inference API

Model: microsoft/deberta-v3-base-mnli
Rate Limit: 30K requests/hour
"""
import logging
import time
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from app.providers.huggingface_client import get_huggingface_client, HuggingFaceClient

logger = logging.getLogger(__name__)


class ClaimStatus(str, Enum):
    """Status of a verified claim."""
    SUPPORTED = "supported"        # Entailment score > threshold
    CONTRADICTED = "contradicted"  # Contradiction score > threshold
    UNSUPPORTED = "unsupported"    # Neither entailed nor contradicted
    UNCERTAIN = "uncertain"        # Scores in gray zone, needs LLM judge


@dataclass
class VerifiedClaim:
    """Result of verifying a single claim."""
    claim: str
    status: ClaimStatus
    confidence: float
    entailment_score: float
    contradiction_score: float
    supporting_chunk_indices: List[int] = field(default_factory=list)
    source_text: Optional[str] = None  # Best supporting chunk text


@dataclass
class VerificationResult:
    """Result of verifying all claims in a response."""
    claims: List[VerifiedClaim]
    faithfulness_score: float  # 0-1, percentage of supported claims
    hallucination_count: int
    supported_count: int
    unsupported_count: int
    latency_ms: float
    method: str  # "nli" | "llm_fallback" | "disabled"
    metadata: Dict[str, Any] = field(default_factory=dict)


class NLIVerificationService:
    """
    Service for verifying claims using Natural Language Inference.
    
    How it works:
    1. Extract claims from LLM response (using patterns or LLM)
    2. For each claim, check entailment against each context chunk
    3. Classify claim as supported/contradicted/unsupported
    4. Compute overall faithfulness score
    
    Thresholds:
    - SUPPORTED: entailment > 0.7
    - CONTRADICTED: contradiction > 0.7
    - UNCERTAIN: 0.3 < entailment < 0.7 (may need LLM judge)
    
    Usage:
        service = NLIVerificationService()
        result = await service.verify_response(
            response="Maria has 5 years of Python experience",
            context_chunks=["Maria Garcia - Python developer, 5 years at DataCorp..."]
        )
        print(f"Faithfulness: {result.faithfulness_score:.2%}")
    """
    
    # Thresholds for claim classification
    THRESHOLD_SUPPORTED = 0.7
    THRESHOLD_CONTRADICTED = 0.7
    THRESHOLD_UNCERTAIN_LOW = 0.3
    THRESHOLD_UNCERTAIN_HIGH = 0.7
    
    # Limits to avoid too many API calls (claims × chunks = API calls)
    MAX_CLAIMS = 5  # Max claims to verify
    MAX_CHUNKS_PER_CLAIM = 3  # Max chunks to check per claim
    
    def __init__(
        self,
        hf_client: Optional[HuggingFaceClient] = None,
        enabled: bool = True
    ):
        """
        Initialize NLI verification service.
        
        Args:
            hf_client: HuggingFace client (uses singleton if None)
            enabled: Whether service is enabled
        """
        self.hf_client = hf_client or get_huggingface_client()
        self.enabled = enabled
        self.model = self.hf_client.config.NLI_MODEL
        
        logger.info(
            f"NLIVerificationService initialized: "
            f"model={self.model}, enabled={enabled}, "
            f"hf_available={self.hf_client.is_available}"
        )
    
    async def verify_response(
        self,
        response: str,
        context_chunks: List[str],
        claims: Optional[List[str]] = None
    ) -> VerificationResult:
        """
        Verify all claims in a response against context chunks.
        
        Args:
            response: LLM generated response text
            context_chunks: List of source context texts
            claims: Optional pre-extracted claims (will extract if None)
            
        Returns:
            VerificationResult with all verified claims and faithfulness score
        """
        start_time = time.perf_counter()
        
        # Handle disabled state
        if not self.enabled or not self.hf_client.is_available:
            return VerificationResult(
                claims=[],
                faithfulness_score=1.0,
                hallucination_count=0,
                supported_count=0,
                unsupported_count=0,
                latency_ms=0,
                method="disabled"
            )
        
        # Extract claims if not provided
        if claims is None:
            claims = self._extract_claims(response)
        
        if not claims:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return VerificationResult(
                claims=[],
                faithfulness_score=1.0,
                hallucination_count=0,
                supported_count=0,
                unsupported_count=0,
                latency_ms=latency_ms,
                method="nli",
                metadata={"note": "No claims extracted from response"}
            )
        
        # Limit claims to verify (to avoid too many API calls)
        claims_to_verify = claims[:self.MAX_CLAIMS]
        if len(claims) > self.MAX_CLAIMS:
            logger.info(f"[NLI] Limiting verification to {self.MAX_CLAIMS} of {len(claims)} claims")
        
        # Verify each claim
        verified_claims = []
        for claim in claims_to_verify:
            try:
                verified = await self._verify_single_claim(claim, context_chunks)
                verified_claims.append(verified)
            except Exception as e:
                logger.warning(f"Failed to verify claim '{claim[:50]}...': {e}")
                # Mark as uncertain on error
                verified_claims.append(VerifiedClaim(
                    claim=claim,
                    status=ClaimStatus.UNCERTAIN,
                    confidence=0.5,
                    entailment_score=0.0,
                    contradiction_score=0.0
                ))
        
        # Calculate metrics
        supported_count = sum(1 for c in verified_claims if c.status == ClaimStatus.SUPPORTED)
        contradicted_count = sum(1 for c in verified_claims if c.status == ClaimStatus.CONTRADICTED)
        unsupported_count = sum(1 for c in verified_claims if c.status == ClaimStatus.UNSUPPORTED)
        uncertain_count = sum(1 for c in verified_claims if c.status == ClaimStatus.UNCERTAIN)
        
        # Faithfulness = supported / total (contradicted counts as 0.5 penalty)
        total = len(verified_claims)
        if total > 0:
            faithfulness = (supported_count - contradicted_count * 0.5) / total
            faithfulness = max(0.0, min(1.0, faithfulness))
        else:
            faithfulness = 1.0
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        logger.info(
            f"[NLI VERIFY] Verified {total} claims in {latency_ms:.1f}ms: "
            f"supported={supported_count}, contradicted={contradicted_count}, "
            f"unsupported={unsupported_count}, uncertain={uncertain_count}, "
            f"faithfulness={faithfulness:.2%}"
        )
        
        return VerificationResult(
            claims=verified_claims,
            faithfulness_score=faithfulness,
            hallucination_count=contradicted_count,
            supported_count=supported_count,
            unsupported_count=unsupported_count,
            latency_ms=latency_ms,
            method="nli",
            metadata={
                "total_claims": total,
                "uncertain_count": uncertain_count,
                "model": self.model
            }
        )
    
    async def _verify_single_claim(
        self,
        claim: str,
        context_chunks: List[str]
    ) -> VerifiedClaim:
        """Verify a single claim against context chunks (limited for efficiency)."""
        
        best_entailment = 0.0
        best_contradiction = 0.0
        supporting_indices = []
        best_supporting_chunk = None
        
        # Limit chunks to check per claim
        chunks_to_check = context_chunks[:self.MAX_CHUNKS_PER_CLAIM]
        
        for i, chunk in enumerate(chunks_to_check):
            # Skip very short chunks
            if len(chunk.strip()) < 20:
                continue
            
            # Truncate long chunks for efficiency
            chunk_text = chunk[:1000] if len(chunk) > 1000 else chunk
            
            try:
                result = await self.hf_client.nli_inference(
                    premise=chunk_text,
                    hypothesis=claim
                )
                
                entailment = result["entailment"]
                contradiction = result["contradiction"]
                
                if entailment > self.THRESHOLD_SUPPORTED:
                    supporting_indices.append(i)
                    if entailment > best_entailment:
                        best_supporting_chunk = chunk_text[:200]
                
                best_entailment = max(best_entailment, entailment)
                best_contradiction = max(best_contradiction, contradiction)
                
            except Exception as e:
                logger.debug(f"NLI failed for chunk {i}: {e}")
                continue
        
        # Determine status
        if best_entailment > self.THRESHOLD_SUPPORTED:
            status = ClaimStatus.SUPPORTED
            confidence = best_entailment
        elif best_contradiction > self.THRESHOLD_CONTRADICTED:
            status = ClaimStatus.CONTRADICTED
            confidence = best_contradiction
        elif best_entailment > self.THRESHOLD_UNCERTAIN_LOW:
            status = ClaimStatus.UNCERTAIN
            confidence = best_entailment
        else:
            status = ClaimStatus.UNSUPPORTED
            confidence = 1.0 - max(best_entailment, best_contradiction)
        
        return VerifiedClaim(
            claim=claim,
            status=status,
            confidence=confidence,
            entailment_score=best_entailment,
            contradiction_score=best_contradiction,
            supporting_chunk_indices=supporting_indices,
            source_text=best_supporting_chunk
        )
    
    def _extract_claims(self, response: str) -> List[str]:
        """
        Extract verifiable claims from a response.
        
        Uses pattern-based extraction for:
        - Sentences with specific facts (numbers, names, dates)
        - Sentences with "has", "worked", "experience", etc.
        
        Note: For more accurate extraction, use LLM-based extraction.
        """
        claims = []
        
        # Split into sentences
        sentences = re.split(r'[.!?]\s+', response)
        
        # Patterns that indicate verifiable claims
        claim_patterns = [
            r'\d+\s*(?:years?|años?|months?|meses)',  # Duration
            r'(?:worked|trabajó|has|tiene|was|era|is|es)\s+(?:at|en|as|como|with|con)',  # Employment
            r'(?:experience|experiencia)\s+(?:in|en|with|con)',  # Experience
            r'(?:skills?|habilidades?|knowledge|conocimiento)',  # Skills
            r'(?:certified|certificado|degree|título|graduated|graduado)',  # Credentials
            r'(?:led|lideró|managed|gestionó|developed|desarrolló)',  # Achievements
            r'(?:Python|Java|JavaScript|SQL|React|Angular|AWS|Azure)',  # Technologies
            r'\b[A-Z][a-z]+\s+[A-Z][a-z]+\b',  # Names (First Last)
        ]
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue
            
            # Check if sentence contains verifiable patterns
            for pattern in claim_patterns:
                if re.search(pattern, sentence, re.IGNORECASE):
                    claims.append(sentence)
                    break
        
        # Deduplicate while preserving order
        seen = set()
        unique_claims = []
        for claim in claims:
            if claim.lower() not in seen:
                seen.add(claim.lower())
                unique_claims.append(claim)
        
        logger.debug(f"Extracted {len(unique_claims)} claims from response")
        return unique_claims[:20]  # Limit to 20 claims for efficiency
    
    async def compute_faithfulness(
        self,
        claims: List[str],
        context_chunks: List[str]
    ) -> float:
        """
        Compute faithfulness score for a list of claims.
        
        Faithfulness = (supported_claims - 0.5 * contradicted_claims) / total_claims
        
        Args:
            claims: List of claims to verify
            context_chunks: Source context chunks
            
        Returns:
            Float 0-1 representing faithfulness
        """
        if not claims:
            return 1.0
        
        result = await self.verify_response(
            response="",  # Not used when claims provided
            context_chunks=context_chunks,
            claims=claims
        )
        
        return result.faithfulness_score


# =============================================================================
# Singleton Instance
# =============================================================================

_nli_service: Optional[NLIVerificationService] = None


def get_nli_verification_service(enabled: bool = True) -> NLIVerificationService:
    """Get singleton instance of NLIVerificationService."""
    global _nli_service
    if _nli_service is None:
        _nli_service = NLIVerificationService(enabled=enabled)
    return _nli_service


def reset_nli_service():
    """Reset singleton (for testing)."""
    global _nli_service
    _nli_service = None
