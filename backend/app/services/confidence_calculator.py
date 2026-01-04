"""
Confidence Score Calculator for RAG v5.

Calculates confidence based on multiple factors, not just claim verification.
Confidence measures: "How confident are we that this response is correct?"
"""
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceFactors:
    """Individual factors that contribute to overall confidence."""
    
    # Source quality (0.0-1.0)
    source_coverage: float = 0.0  # How many relevant sources were found
    source_relevance: float = 0.0  # Average relevance score of sources
    
    # Response quality (0.0-1.0)
    claim_groundedness: float = 0.0  # Claims supported by sources
    response_completeness: float = 0.0  # Response addresses the query
    
    # Consistency (0.0-1.0)
    internal_consistency: float = 0.0  # Response is internally consistent
    reasoning_quality: float = 0.0  # Reasoning trace is coherent
    
    # Metadata
    has_verification: bool = False
    has_reasoning: bool = False
    query_type: str = "unknown"


class ConfidenceCalculator:
    """
    Calculate confidence score based on multiple factors.
    
    Confidence represents: "How confident is the system that this response is correct?"
    
    NOT: "Did we find matching candidates?"
    
    A response of "No candidates match" can have HIGH confidence if:
    - All CVs were properly analyzed
    - The conclusion is well-supported by the data
    - The reasoning is sound
    """
    
    def __init__(self):
        # Weights for different factors (must sum to 1.0)
        self.weights = {
            'source_coverage': 0.20,      # 20% - Did we retrieve relevant sources?
            'source_relevance': 0.15,     # 15% - Are sources highly relevant?
            'claim_groundedness': 0.25,   # 25% - Are claims supported?
            'response_completeness': 0.20, # 20% - Does response address query?
            'internal_consistency': 0.10,  # 10% - Is response self-consistent?
            'reasoning_quality': 0.10      # 10% - Is reasoning sound?
        }
    
    def calculate(
        self,
        verification_result: Optional[Any] = None,
        reasoning_trace: Optional[str] = None,
        chunks: Optional[List[Dict[str, Any]]] = None,
        query_understanding: Optional[Any] = None,
        structured_output: Optional[Any] = None
    ) -> tuple[float, Dict[str, Any]]:
        """
        Calculate overall confidence score.
        
        Args:
            verification_result: ClaimVerificationResult from claim verifier
            reasoning_trace: Reasoning trace from reasoning service
            chunks: Retrieved source chunks
            query_understanding: Query understanding result
            structured_output: Structured output from processor
            
        Returns:
            Tuple of (confidence_score, explanation_dict)
        """
        factors = self._calculate_factors(
            verification_result=verification_result,
            reasoning_trace=reasoning_trace,
            chunks=chunks,
            query_understanding=query_understanding,
            structured_output=structured_output
        )
        
        # Calculate weighted average
        score = (
            factors.source_coverage * self.weights['source_coverage'] +
            factors.source_relevance * self.weights['source_relevance'] +
            factors.claim_groundedness * self.weights['claim_groundedness'] +
            factors.response_completeness * self.weights['response_completeness'] +
            factors.internal_consistency * self.weights['internal_consistency'] +
            factors.reasoning_quality * self.weights['reasoning_quality']
        )
        
        # Build explanation
        explanation = {
            "score": round(score, 3),
            "factors": {
                "source_coverage": {
                    "score": round(factors.source_coverage, 3),
                    "weight": self.weights['source_coverage'],
                    "contribution": round(factors.source_coverage * self.weights['source_coverage'], 3)
                },
                "source_relevance": {
                    "score": round(factors.source_relevance, 3),
                    "weight": self.weights['source_relevance'],
                    "contribution": round(factors.source_relevance * self.weights['source_relevance'], 3)
                },
                "claim_groundedness": {
                    "score": round(factors.claim_groundedness, 3),
                    "weight": self.weights['claim_groundedness'],
                    "contribution": round(factors.claim_groundedness * self.weights['claim_groundedness'], 3)
                },
                "response_completeness": {
                    "score": round(factors.response_completeness, 3),
                    "weight": self.weights['response_completeness'],
                    "contribution": round(factors.response_completeness * self.weights['response_completeness'], 3)
                },
                "internal_consistency": {
                    "score": round(factors.internal_consistency, 3),
                    "weight": self.weights['internal_consistency'],
                    "contribution": round(factors.internal_consistency * self.weights['internal_consistency'], 3)
                },
                "reasoning_quality": {
                    "score": round(factors.reasoning_quality, 3),
                    "weight": self.weights['reasoning_quality'],
                    "contribution": round(factors.reasoning_quality * self.weights['reasoning_quality'], 3)
                }
            },
            "metadata": {
                "has_verification": factors.has_verification,
                "has_reasoning": factors.has_reasoning,
                "query_type": factors.query_type
            }
        }
        
        logger.info(f"[CONFIDENCE] Calculated score: {score:.3f}")
        logger.debug(f"[CONFIDENCE] Factors: {explanation['factors']}")
        
        return score, explanation
    
    def _calculate_factors(
        self,
        verification_result: Optional[Any],
        reasoning_trace: Optional[str],
        chunks: Optional[List[Dict[str, Any]]],
        query_understanding: Optional[Any],
        structured_output: Optional[Any]
    ) -> ConfidenceFactors:
        """Calculate individual confidence factors."""
        
        factors = ConfidenceFactors()
        
        # 1. Source Coverage: Did we retrieve relevant sources?
        if chunks:
            num_chunks = len(chunks)
            if num_chunks >= 5:
                factors.source_coverage = 1.0
            elif num_chunks >= 3:
                factors.source_coverage = 0.8
            elif num_chunks >= 1:
                factors.source_coverage = 0.6
            else:
                factors.source_coverage = 0.3
        else:
            factors.source_coverage = 0.3
        
        # 2. Source Relevance: Average relevance score
        if chunks:
            relevance_scores = [chunk.get('score', 0.5) for chunk in chunks]
            avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.5
            factors.source_relevance = min(1.0, avg_relevance)
        else:
            factors.source_relevance = 0.5
        
        # 3. Claim Groundedness: Are claims supported by sources?
        if verification_result:
            factors.has_verification = True
            factors.claim_groundedness = verification_result.groundedness_score
        else:
            # No verification - use heuristic based on sources
            factors.claim_groundedness = 0.7 if chunks else 0.5
        
        # 4. Response Completeness: Does response address the query?
        if structured_output:
            # Check if we have key components
            has_direct_answer = bool(structured_output.direct_answer)
            has_table = bool(structured_output.table_data)
            has_conclusion = bool(structured_output.conclusion)
            
            completeness_score = 0.0
            if has_direct_answer:
                completeness_score += 0.4
            if has_table:
                completeness_score += 0.3
            if has_conclusion:
                completeness_score += 0.3
            
            factors.response_completeness = completeness_score
        else:
            factors.response_completeness = 0.5
        
        # 5. Internal Consistency: Is response self-consistent?
        # Check if direct_answer, table, and conclusion are aligned
        if structured_output:
            consistency_checks = []
            
            # Check if conclusion aligns with table
            if structured_output.table_data and structured_output.conclusion:
                table_rows = structured_output.table_data.rows if hasattr(structured_output.table_data, 'rows') else []
                has_candidates = len(table_rows) > 0
                
                conclusion_text = structured_output.conclusion.lower()
                conclusion_says_no_match = any(phrase in conclusion_text for phrase in [
                    'no candidates match',
                    'no match',
                    'none of the candidates',
                    'not suitable'
                ])
                
                # Consistency: If table is empty or low scores, conclusion should say no match
                # If table has candidates, conclusion should discuss them
                is_consistent = (has_candidates and not conclusion_says_no_match) or \
                               (not has_candidates and conclusion_says_no_match)
                consistency_checks.append(is_consistent)
            
            # Average consistency
            if consistency_checks:
                factors.internal_consistency = sum(consistency_checks) / len(consistency_checks)
            else:
                factors.internal_consistency = 0.7  # Neutral if can't check
        else:
            factors.internal_consistency = 0.5
        
        # 6. Reasoning Quality: Is reasoning trace coherent?
        if reasoning_trace:
            factors.has_reasoning = True
            # Simple heuristic: longer, structured reasoning = higher quality
            reasoning_length = len(reasoning_trace)
            if reasoning_length > 500:
                factors.reasoning_quality = 0.9
            elif reasoning_length > 200:
                factors.reasoning_quality = 0.7
            else:
                factors.reasoning_quality = 0.5
        else:
            factors.reasoning_quality = 0.6  # Neutral if no reasoning
        
        # Query type metadata
        if query_understanding:
            factors.query_type = getattr(query_understanding, 'query_type', 'unknown')
        
        return factors


# Singleton instance
_calculator = None

def get_confidence_calculator() -> ConfidenceCalculator:
    """Get singleton confidence calculator instance."""
    global _calculator
    if _calculator is None:
        _calculator = ConfidenceCalculator()
    return _calculator
