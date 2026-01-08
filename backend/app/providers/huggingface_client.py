"""
HuggingFace Inference API Client.

Provides access to FREE HuggingFace models for:
- Zero-Shot Classification (guardrails)
- Natural Language Inference (hallucination detection)
- Cross-Encoder Reranking (fast document reranking)

All models have 30K req/hour rate limit on free tier.
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import httpx

from app.config import settings, timeouts

logger = logging.getLogger(__name__)


@dataclass
class HuggingFaceConfig:
    """Configuration for HuggingFace models."""
    # Zero-Shot Classification (also used for NLI - bart-large-mnli supports both)
    ZEROSHOT_MODEL: str = "facebook/bart-large-mnli"
    # Natural Language Inference (bart-large-mnli is actively maintained)
    NLI_MODEL: str = "facebook/bart-large-mnli"
    # Cross-Encoder Reranking
    RERANKER_MODEL: str = "BAAI/bge-reranker-base"
    # Named Entity Recognition (optional)
    NER_MODEL: str = "dslim/bert-base-NER"
    
    # Timeouts
    TIMEOUT: float = 30.0
    RETRY_DELAY: float = 1.0
    MAX_RETRIES: int = 3


class HuggingFaceClient:
    """
    Client for HuggingFace Inference API.
    
    Provides async methods for:
    - zero_shot_classification: Classify text into candidate labels
    - nli_inference: Natural Language Inference (entailment detection)
    - rerank: Cross-encoder document reranking
    - extract_entities: Named Entity Recognition
    
    All methods include fallback handling for API failures.
    """
    
    # Updated to new HuggingFace Router endpoint (2024+)
    BASE_URL = "https://router.huggingface.co/hf-inference/models"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize HuggingFace client.
        
        Args:
            api_key: HuggingFace API key. If None, uses settings.huggingface_api_key
        """
        self.api_key = api_key or getattr(settings, 'huggingface_api_key', None)
        self.config = HuggingFaceConfig()
        self.headers = {
            "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
            "Content-Type": "application/json"
        }
        self._initialized = bool(self.api_key)
        
        if not self._initialized:
            logger.warning("HuggingFace API key not configured. HuggingFace features will be disabled.")
        else:
            logger.info("HuggingFaceClient initialized successfully")
    
    @property
    def is_available(self) -> bool:
        """Check if client is properly configured."""
        return self._initialized
    
    async def _make_request(
        self,
        model: str,
        payload: Dict[str, Any],
        timeout: float = None
    ) -> Dict[str, Any]:
        """
        Make request to HuggingFace Inference API with retry logic.
        
        Args:
            model: Model ID (e.g., "microsoft/deberta-v3-base-mnli")
            payload: Request payload
            timeout: Request timeout in seconds
            
        Returns:
            API response as dict
            
        Raises:
            Exception: If all retries fail
        """
        if not self._initialized:
            raise RuntimeError("HuggingFace client not initialized (missing API key)")
        
        url = f"{self.BASE_URL}/{model}"
        timeout = timeout or self.config.TIMEOUT
        
        last_error = None
        for attempt in range(self.config.MAX_RETRIES):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(
                        url,
                        headers=self.headers,
                        json=payload
                    )
                    
                    # Handle model loading (503)
                    if response.status_code == 503:
                        data = response.json()
                        estimated_time = data.get("estimated_time", 20)
                        logger.info(f"Model {model} is loading, waiting {estimated_time}s...")
                        await asyncio.sleep(min(estimated_time, 30))
                        continue
                    
                    response.raise_for_status()
                    return response.json()
                    
            except httpx.HTTPStatusError as e:
                last_error = e
                logger.warning(f"HuggingFace API error (attempt {attempt + 1}): {e}")
                if attempt < self.config.MAX_RETRIES - 1:
                    await asyncio.sleep(self.config.RETRY_DELAY * (attempt + 1))
                    
            except Exception as e:
                last_error = e
                logger.warning(f"HuggingFace request failed (attempt {attempt + 1}): {e}")
                if attempt < self.config.MAX_RETRIES - 1:
                    await asyncio.sleep(self.config.RETRY_DELAY * (attempt + 1))
        
        raise last_error or Exception("All HuggingFace API retries failed")
    
    # =========================================================================
    # Zero-Shot Classification
    # =========================================================================
    
    async def zero_shot_classification(
        self,
        text: str,
        candidate_labels: List[str],
        model: str = None,
        multi_label: bool = False
    ) -> Dict[str, Any]:
        """
        Classify text into candidate labels using zero-shot classification.
        
        Args:
            text: Text to classify
            candidate_labels: List of possible labels
            model: Model to use (default: deberta-v3-base-zeroshot)
            multi_label: Whether to allow multiple labels
            
        Returns:
            {
                "sequence": str,
                "labels": List[str],
                "scores": List[float]
            }
            
        Example:
            >>> result = await client.zero_shot_classification(
            ...     "Who has Python experience?",
            ...     ["CV-related question", "off-topic question"]
            ... )
            >>> result["labels"][0]  # Most likely label
            "CV-related question"
        """
        model = model or self.config.ZEROSHOT_MODEL
        
        payload = {
            "inputs": text,
            "parameters": {
                "candidate_labels": candidate_labels,
                "multi_label": multi_label
            }
        }
        
        result = await self._make_request(model, payload)
        logger.debug(f"Zero-shot classification: '{text[:50]}...' -> {result.get('labels', [])[0] if result.get('labels') else 'N/A'}")
        return result
    
    # =========================================================================
    # Natural Language Inference
    # =========================================================================
    
    async def nli_inference(
        self,
        premise: str,
        hypothesis: str,
        model: str = None
    ) -> Dict[str, float]:
        """
        Perform Natural Language Inference to check if premise entails hypothesis.
        Uses zero-shot classification with NLI labels for BART-large-MNLI compatibility.
        
        Args:
            premise: The context/evidence text
            hypothesis: The claim to verify
            model: Model to use (default: bart-large-mnli)
            
        Returns:
            {
                "entailment": float,  # Score for claim being supported
                "neutral": float,     # Score for claim being unrelated
                "contradiction": float # Score for claim being contradicted
            }
            
        Example:
            >>> result = await client.nli_inference(
            ...     premise="Maria Garcia has 5 years of Python experience at DataCorp",
            ...     hypothesis="Maria has Python experience"
            ... )
            >>> result["entailment"]  # Should be high (>0.7)
            0.94
        """
        model = model or self.config.NLI_MODEL
        
        # BART-large-MNLI uses zero-shot classification format
        # Premise is the input, hypothesis becomes the candidate label
        payload = {
            "inputs": premise,
            "parameters": {
                "candidate_labels": [hypothesis],
                "multi_label": False
            }
        }
        
        result = await self._make_request(model, payload)
        
        # Parse result into structured format
        scores = {
            "entailment": 0.0,
            "neutral": 0.33,  # Default neutral
            "contradiction": 0.0
        }
        
        # BART zero-shot returns: {"sequence": str, "labels": [str], "scores": [float]}
        if isinstance(result, dict) and "scores" in result:
            # The score represents how well the hypothesis matches the premise
            entailment_score = result["scores"][0] if result["scores"] else 0.0
            scores["entailment"] = entailment_score
            scores["contradiction"] = max(0, 1.0 - entailment_score - 0.33)  # Estimate
            scores["neutral"] = 1.0 - scores["entailment"] - scores["contradiction"]
        elif isinstance(result, list):
            # Fallback for other model formats
            for item in result:
                label = item.get("label", "").lower()
                score = item.get("score", 0.0)
                if "entail" in label:
                    scores["entailment"] = score
                elif "neutral" in label:
                    scores["neutral"] = score
                elif "contradict" in label:
                    scores["contradiction"] = score
        
        logger.debug(f"NLI: entailment={scores['entailment']:.2f}, contradiction={scores['contradiction']:.2f}")
        return scores
    
    async def verify_claim(
        self,
        claim: str,
        context_chunks: List[str],
        threshold_supported: float = 0.7,
        threshold_contradicted: float = 0.7
    ) -> Dict[str, Any]:
        """
        Verify if a claim is supported by any of the context chunks.
        
        Args:
            claim: The claim to verify
            context_chunks: List of context texts to check against
            threshold_supported: Min entailment score to consider supported
            threshold_contradicted: Min contradiction score to consider contradicted
            
        Returns:
            {
                "claim": str,
                "status": "supported" | "contradicted" | "unsupported",
                "confidence": float,
                "supporting_chunks": List[int],  # Indices of supporting chunks
                "best_entailment": float,
                "best_contradiction": float
            }
        """
        best_entailment = 0.0
        best_contradiction = 0.0
        supporting_chunks = []
        
        for i, chunk in enumerate(context_chunks):
            try:
                result = await self.nli_inference(premise=chunk, hypothesis=claim)
                
                if result["entailment"] > threshold_supported:
                    supporting_chunks.append(i)
                    best_entailment = max(best_entailment, result["entailment"])
                
                best_contradiction = max(best_contradiction, result["contradiction"])
                
            except Exception as e:
                logger.warning(f"NLI failed for chunk {i}: {e}")
                continue
        
        # Determine status
        if best_entailment > threshold_supported:
            status = "supported"
            confidence = best_entailment
        elif best_contradiction > threshold_contradicted:
            status = "contradicted"
            confidence = best_contradiction
        else:
            status = "unsupported"
            confidence = 1 - max(best_entailment, best_contradiction)
        
        return {
            "claim": claim,
            "status": status,
            "confidence": confidence,
            "supporting_chunks": supporting_chunks,
            "best_entailment": best_entailment,
            "best_contradiction": best_contradiction
        }
    
    # =========================================================================
    # Cross-Encoder Reranking
    # =========================================================================
    
    async def rerank(
        self,
        query: str,
        documents: List[str],
        model: str = None
    ) -> List[Dict[str, Any]]:
        """
        Rerank documents by relevance to query using cross-encoder.
        
        Args:
            query: The search query
            documents: List of document texts to rerank
            model: Model to use (default: bge-reranker-base)
            
        Returns:
            List of dicts sorted by relevance:
            [
                {"document": str, "score": float, "index": int},
                ...
            ]
            
        Note:
            Cross-encoder is ~100x faster than LLM reranking:
            - LLM: ~500ms per document
            - Cross-encoder: ~50ms for 10 documents
        """
        if not documents:
            return []
        
        model = model or self.config.RERANKER_MODEL
        
        # Format as query-document pairs
        pairs = [[query, doc] for doc in documents]
        
        payload = {
            "inputs": pairs
        }
        
        result = await self._make_request(model, payload)
        
        # Parse scores
        scores = []
        if isinstance(result, list):
            for i, item in enumerate(result):
                if isinstance(item, dict):
                    score = item.get("score", 0.0)
                elif isinstance(item, (int, float)):
                    score = float(item)
                else:
                    score = 0.0
                scores.append({
                    "document": documents[i] if i < len(documents) else "",
                    "score": score,
                    "index": i
                })
        
        # Sort by score descending
        scores.sort(key=lambda x: x["score"], reverse=True)
        
        logger.debug(f"Reranked {len(documents)} documents")
        return scores
    
    # =========================================================================
    # Named Entity Recognition (Optional)
    # =========================================================================
    
    async def extract_entities(
        self,
        text: str,
        model: str = None
    ) -> List[Dict[str, Any]]:
        """
        Extract named entities from text.
        
        Args:
            text: Text to analyze
            model: Model to use (default: bert-base-NER)
            
        Returns:
            List of entities:
            [
                {
                    "entity": str,  # Entity type (PER, ORG, LOC, etc.)
                    "word": str,    # Entity text
                    "score": float, # Confidence
                    "start": int,   # Start position
                    "end": int      # End position
                }
            ]
        """
        model = model or self.config.NER_MODEL
        
        payload = {
            "inputs": text
        }
        
        result = await self._make_request(model, payload)
        
        if isinstance(result, list):
            return result
        return []


# =============================================================================
# Singleton Instance
# =============================================================================

_huggingface_client: Optional[HuggingFaceClient] = None


def get_huggingface_client() -> HuggingFaceClient:
    """Get singleton instance of HuggingFaceClient."""
    global _huggingface_client
    if _huggingface_client is None:
        _huggingface_client = HuggingFaceClient()
    return _huggingface_client


def reset_huggingface_client():
    """Reset singleton (for testing)."""
    global _huggingface_client
    _huggingface_client = None
