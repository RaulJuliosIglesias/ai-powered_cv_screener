"""
Confidence Score Calculator for RAG v5.

Calculates confidence based on multiple REAL factors with full traceability.
NO hardcoded values - every score is derived from actual data.

Confidence measures: "How confident are we that this response is correct?"
"""
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Configurable constants for source coverage calculation
EXPECTED_CHUNKS_FOR_GOOD_COVERAGE = 5  # Expected number of chunks for good coverage
EXPECTED_UNIQUE_CVS_FOR_DIVERSITY = 3  # Expected number of unique CVs for diversity score


ADAPTIVE_THRESHOLDS = {
    'factual_simple': {
        'high': 0.90,
        'good': 0.75,
        'moderate': 0.60,
        'low': 0.40
    },
    'comparison': {
        'high': 0.80,
        'good': 0.65,
        'moderate': 0.50,
        'low': 0.35
    },
    'analysis': {
        'high': 0.75,
        'good': 0.60,
        'moderate': 0.45,
        'low': 0.30
    },
    'default': {
        'high': 0.85,
        'good': 0.70,
        'moderate': 0.50,
        'low': 0.30
    }
}


@dataclass
class FactorExplanation:
    """Detailed explanation for a single confidence factor."""
    score: float
    weight: float
    contribution: float
    calculation_method: str  # How was this score calculated?
    raw_data: Dict[str, Any]  # The actual data used
    is_measured: bool = True  # True if from real data, False if unavailable


@dataclass
class ConfidenceFactors:
    """Individual factors that contribute to overall confidence."""
    
    # Source quality (0.0-1.0)
    source_coverage: float = 0.0
    source_coverage_explanation: Optional[FactorExplanation] = None
    
    source_relevance: float = 0.0
    source_relevance_explanation: Optional[FactorExplanation] = None
    
    # Response quality (0.0-1.0)
    claim_verification: float = 0.0
    claim_verification_explanation: Optional[FactorExplanation] = None
    
    response_completeness: float = 0.0
    response_completeness_explanation: Optional[FactorExplanation] = None
    
    # Consistency (0.0-1.0)
    internal_consistency: float = 0.0
    internal_consistency_explanation: Optional[FactorExplanation] = None
    
    # Metadata
    has_verification: bool = False
    has_reasoning: bool = False
    query_type: str = "unknown"
    
    # Count of factors that were actually measured vs unavailable
    measured_factors: int = 0
    total_factors: int = 5


class ConfidenceCalculator:
    """
    Calculate confidence score based on REAL, TRACEABLE factors.
    
    PRINCIPLES:
    1. NO hardcoded values - every score comes from actual measurements
    2. Full traceability - explain exactly how each factor was calculated
    3. Transparency - if data is unavailable, mark it clearly and adjust weights
    4. Real metrics - use actual verification results, not heuristics
    
    Confidence represents: "How confident is the system that this response is correct?"
    """
    
    # Base weights when ALL factors are available (sum to 1.0)
    BASE_WEIGHTS = {
        'source_coverage': 0.15,       # 15% - Did we retrieve relevant sources?
        'source_relevance': 0.15,      # 15% - Are sources highly relevant?
        'claim_verification': 0.40,    # 40% - Are claims verified? (MOST IMPORTANT)
        'response_completeness': 0.15, # 15% - Does response have all components?
        'internal_consistency': 0.15   # 15% - Is response self-consistent?
    }
    
    def __init__(self):
        pass
    
    def calculate(
        self,
        verification_result: Optional[Any] = None,
        reasoning_trace: Optional[str] = None,
        chunks: Optional[List[Dict[str, Any]]] = None,
        query_understanding: Optional[Any] = None,
        structured_output: Optional[Any] = None
    ) -> tuple[float, Dict[str, Any]]:
        """
        Calculate overall confidence score with full traceability.
        
        Returns:
            Tuple of (confidence_score, detailed_explanation_dict)
        """
        factors = self._calculate_factors(
            verification_result=verification_result,
            reasoning_trace=reasoning_trace,
            chunks=chunks,
            query_understanding=query_understanding,
            structured_output=structured_output
        )
        
        # Calculate dynamic weights based on available factors
        active_weights = self._calculate_active_weights(factors)
        
        # Calculate weighted score using ONLY measured factors
        score = 0.0
        for factor_name, weight in active_weights.items():
            factor_value = getattr(factors, factor_name, 0.0)
            score += factor_value * weight
        
        # Build detailed explanation
        explanation = self._build_explanation(factors, active_weights, score)
        
        logger.info(f"[CONFIDENCE] Score: {score:.1%} | Measured: {factors.measured_factors}/{factors.total_factors} factors")
        
        return score, explanation
    
    def _calculate_active_weights(self, factors: ConfidenceFactors) -> Dict[str, float]:
        """
        Redistribute weights based on which factors have real data.
        Factors without real data get weight=0, and their weight is distributed to others.
        """
        available_factors = {}
        unavailable_weight = 0.0
        
        # Check which factors have real measurements
        factor_availability = {
            'source_coverage': factors.source_coverage_explanation and factors.source_coverage_explanation.is_measured,
            'source_relevance': factors.source_relevance_explanation and factors.source_relevance_explanation.is_measured,
            'claim_verification': factors.claim_verification_explanation and factors.claim_verification_explanation.is_measured,
            'response_completeness': factors.response_completeness_explanation and factors.response_completeness_explanation.is_measured,
            'internal_consistency': factors.internal_consistency_explanation and factors.internal_consistency_explanation.is_measured
        }
        
        # Separate available and unavailable
        for factor, is_available in factor_availability.items():
            if is_available:
                available_factors[factor] = self.BASE_WEIGHTS[factor]
            else:
                unavailable_weight += self.BASE_WEIGHTS[factor]
        
        # If no factors available, return equal weights as fallback
        if not available_factors:
            return {k: 1.0 / len(self.BASE_WEIGHTS) for k in self.BASE_WEIGHTS}
        
        # Redistribute unavailable weight proportionally to available factors
        total_available_weight = sum(available_factors.values())
        if total_available_weight > 0 and unavailable_weight > 0:
            redistribution_factor = (total_available_weight + unavailable_weight) / total_available_weight
            for factor in available_factors:
                available_factors[factor] *= redistribution_factor
        
        return available_factors
    
    def _calculate_factors(
        self,
        verification_result: Optional[Any],
        reasoning_trace: Optional[str],
        chunks: Optional[List[Dict[str, Any]]],
        query_understanding: Optional[Any],
        structured_output: Optional[Any]
    ) -> ConfidenceFactors:
        """Calculate individual confidence factors with full traceability."""
        
        factors = ConfidenceFactors()
        measured_count = 0
        
        # 1. SOURCE COVERAGE - Based on actual chunk count and diversity
        factors.source_coverage, factors.source_coverage_explanation = self._calc_source_coverage(chunks)
        if factors.source_coverage_explanation.is_measured:
            measured_count += 1
        
        # 2. SOURCE RELEVANCE - Based on ACTUAL similarity scores from vector search
        factors.source_relevance, factors.source_relevance_explanation = self._calc_source_relevance(chunks)
        if factors.source_relevance_explanation.is_measured:
            measured_count += 1
        
        # 3. CLAIM VERIFICATION - Based on ACTUAL verification results (CRITICAL)
        factors.claim_verification, factors.claim_verification_explanation = self._calc_claim_verification(verification_result)
        factors.has_verification = verification_result is not None
        if factors.claim_verification_explanation.is_measured:
            measured_count += 1
        
        # 4. RESPONSE COMPLETENESS - Based on actual structured output components
        factors.response_completeness, factors.response_completeness_explanation = self._calc_response_completeness(structured_output)
        if factors.response_completeness_explanation.is_measured:
            measured_count += 1
        
        # 5. INTERNAL CONSISTENCY - Based on actual alignment checks
        factors.internal_consistency, factors.internal_consistency_explanation = self._calc_internal_consistency(structured_output)
        if factors.internal_consistency_explanation.is_measured:
            measured_count += 1
        
        # Metadata
        factors.has_reasoning = bool(reasoning_trace)
        factors.measured_factors = measured_count
        
        if query_understanding:
            factors.query_type = getattr(query_understanding, 'query_type', 'unknown')
        
        return factors
    
    def _calc_source_coverage(self, chunks: Optional[List[Dict[str, Any]]]) -> tuple[float, FactorExplanation]:
        """
        Calculate source coverage based on actual retrieved chunks.
        
        Formula: score = min(1.0, num_chunks / expected_chunks)
        Where expected_chunks varies by query type (default: 5 for good coverage)
        """
        if not chunks:
            return 0.0, FactorExplanation(
                score=0.0,
                weight=self.BASE_WEIGHTS['source_coverage'],
                contribution=0.0,
                calculation_method="No chunks retrieved",
                raw_data={"num_chunks": 0, "expected_chunks": 5},
                is_measured=True  # This IS a real measurement: we measured 0 chunks
            )
        
        num_chunks = len(chunks)
        unique_cvs = len(set(c.get('metadata', {}).get('cv_id', f'unknown_{i}') for i, c in enumerate(chunks)))
        
        # Score based on actual coverage (using configurable constants)
        # Use both chunk count and CV diversity
        chunk_score = min(1.0, num_chunks / EXPECTED_CHUNKS_FOR_GOOD_COVERAGE)
        cv_diversity_score = min(1.0, unique_cvs / EXPECTED_UNIQUE_CVS_FOR_DIVERSITY)
        
        # Combined score (weighted average: 60% chunks, 40% diversity)
        score = chunk_score * 0.6 + cv_diversity_score * 0.4
        
        return score, FactorExplanation(
            score=score,
            weight=self.BASE_WEIGHTS['source_coverage'],
            contribution=score * self.BASE_WEIGHTS['source_coverage'],
            calculation_method=f"({num_chunks} chunks / {EXPECTED_CHUNKS_FOR_GOOD_COVERAGE} expected) × 0.6 + ({unique_cvs} unique CVs / {EXPECTED_UNIQUE_CVS_FOR_DIVERSITY} expected) × 0.4",
            raw_data={
                "num_chunks": num_chunks,
                "unique_cvs": unique_cvs,
                "expected_chunks": EXPECTED_CHUNKS_FOR_GOOD_COVERAGE,
                "chunk_score": round(chunk_score, 3),
                "cv_diversity_score": round(cv_diversity_score, 3)
            },
            is_measured=True
        )
    
    def _calc_source_relevance(self, chunks: Optional[List[Dict[str, Any]]]) -> tuple[float, FactorExplanation]:
        """
        Calculate source relevance based on ACTUAL similarity scores from vector search.
        
        Formula: score = average of chunk similarity scores (already 0-1 from vector search)
        """
        if not chunks:
            return 0.0, FactorExplanation(
                score=0.0,
                weight=self.BASE_WEIGHTS['source_relevance'],
                contribution=0.0,
                calculation_method="No chunks to measure relevance",
                raw_data={"scores": [], "avg_score": 0},
                is_measured=False  # Cannot measure without data
            )
        
        # Extract actual similarity scores from chunks
        scores = []
        for chunk in chunks:
            # Score comes from vector search (cosine similarity, already 0-1)
            score = chunk.get('score')
            if score is not None:
                scores.append(float(score))
        
        if not scores:
            return 0.0, FactorExplanation(
                score=0.0,
                weight=self.BASE_WEIGHTS['source_relevance'],
                contribution=0.0,
                calculation_method="Chunks found but no similarity scores available",
                raw_data={"num_chunks": len(chunks), "scores_available": False},
                is_measured=False
            )
        
        avg_score = sum(scores) / len(scores)
        min_score = min(scores)
        max_score = max(scores)
        
        return avg_score, FactorExplanation(
            score=avg_score,
            weight=self.BASE_WEIGHTS['source_relevance'],
            contribution=avg_score * self.BASE_WEIGHTS['source_relevance'],
            calculation_method=f"Average of {len(scores)} vector similarity scores",
            raw_data={
                "num_scores": len(scores),
                "avg_score": round(avg_score, 3),
                "min_score": round(min_score, 3),
                "max_score": round(max_score, 3),
                "all_scores": [round(s, 3) for s in scores[:10]]  # First 10 for brevity
            },
            is_measured=True
        )
    
    def _calc_claim_verification(self, verification_result: Optional[Any]) -> tuple[float, FactorExplanation]:
        """
        Calculate claim verification score based on ACTUAL verification results.
        
        This is the MOST IMPORTANT factor - no heuristics, only real verification data.
        """
        if verification_result is None:
            return 0.0, FactorExplanation(
                score=0.0,
                weight=self.BASE_WEIGHTS['claim_verification'],
                contribution=0.0,
                calculation_method="Verification not performed - cannot assess claim accuracy",
                raw_data={"verification_performed": False},
                is_measured=False  # CRITICAL: Mark as not measured
            )
        
        # Extract real verification data
        total_claims = getattr(verification_result, 'total_claims', 0)
        verified_claims = getattr(verification_result, 'verified_claims', [])
        unverified_claims = getattr(verification_result, 'unverified_claims', [])
        contradicted_claims = getattr(verification_result, 'contradicted_claims', [])
        
        verified_count = len(verified_claims) if isinstance(verified_claims, list) else 0
        unverified_count = len(unverified_claims) if isinstance(unverified_claims, list) else 0
        contradicted_count = len(contradicted_claims) if isinstance(contradicted_claims, list) else 0
        
        # Handle case where no claims were extracted
        if total_claims == 0:
            # This could be valid (e.g., "no candidates match" has no verifiable claims)
            # Check if this was intentional based on the response type
            groundedness = getattr(verification_result, 'groundedness_score', None)
            if groundedness is not None:
                return groundedness, FactorExplanation(
                    score=groundedness,
                    weight=self.BASE_WEIGHTS['claim_verification'],
                    contribution=groundedness * self.BASE_WEIGHTS['claim_verification'],
                    calculation_method="No verifiable claims extracted (response may be negative/summary)",
                    raw_data={
                        "total_claims": 0,
                        "groundedness_score": groundedness,
                        "note": "Score from verifier's groundedness assessment"
                    },
                    is_measured=True
                )
            else:
                return 0.0, FactorExplanation(
                    score=0.0,
                    weight=self.BASE_WEIGHTS['claim_verification'],
                    contribution=0.0,
                    calculation_method="No claims extracted and no groundedness score",
                    raw_data={"total_claims": 0},
                    is_measured=False
                )
        
        # Calculate score: verified add, contradicted strongly subtract
        # Formula: (verified - 2×contradicted) / total, clamped to [0, 1]
        raw_score = (verified_count - 2 * contradicted_count) / total_claims
        score = max(0.0, min(1.0, raw_score))
        
        return score, FactorExplanation(
            score=score,
            weight=self.BASE_WEIGHTS['claim_verification'],
            contribution=score * self.BASE_WEIGHTS['claim_verification'],
            calculation_method=f"({verified_count} verified - 2×{contradicted_count} contradicted) / {total_claims} total claims",
            raw_data={
                "total_claims": total_claims,
                "verified_count": verified_count,
                "unverified_count": unverified_count,
                "contradicted_count": contradicted_count,
                "verified_claims": verified_claims[:3] if isinstance(verified_claims, list) else [],  # Sample
                "contradicted_claims": contradicted_claims[:3] if isinstance(contradicted_claims, list) else []
            },
            is_measured=True
        )
    
    def _calc_response_completeness(self, structured_output: Optional[Any]) -> tuple[float, FactorExplanation]:
        """
        Calculate response completeness based on actual structured output components.
        
        Components checked:
        - direct_answer: Present and non-empty
        - table_data: Present with rows
        - conclusion: Present and non-empty
        - analysis_points: Present with content
        """
        if structured_output is None:
            return 0.0, FactorExplanation(
                score=0.0,
                weight=self.BASE_WEIGHTS['response_completeness'],
                contribution=0.0,
                calculation_method="No structured output available",
                raw_data={"structured_output_available": False},
                is_measured=False
            )
        
        components = {}
        
        # Check each component
        direct_answer = getattr(structured_output, 'direct_answer', None)
        components['direct_answer'] = bool(direct_answer and str(direct_answer).strip())
        
        table_data = getattr(structured_output, 'table_data', None)
        if table_data:
            rows = getattr(table_data, 'rows', [])
            components['table_data'] = len(rows) > 0
            components['table_rows_count'] = len(rows)
        else:
            components['table_data'] = False
            components['table_rows_count'] = 0
        
        conclusion = getattr(structured_output, 'conclusion', None)
        components['conclusion'] = bool(conclusion and str(conclusion).strip())
        
        analysis = getattr(structured_output, 'analysis_points', None)
        components['analysis_points'] = bool(analysis and len(analysis) > 0)
        
        # Calculate score: each component contributes equally
        present_count = sum([
            components['direct_answer'],
            components['table_data'],
            components['conclusion'],
            components['analysis_points']
        ])
        
        score = present_count / 4.0
        
        return score, FactorExplanation(
            score=score,
            weight=self.BASE_WEIGHTS['response_completeness'],
            contribution=score * self.BASE_WEIGHTS['response_completeness'],
            calculation_method=f"{present_count}/4 components present",
            raw_data={
                "direct_answer_present": components['direct_answer'],
                "table_present": components['table_data'],
                "table_rows": components['table_rows_count'],
                "conclusion_present": components['conclusion'],
                "analysis_present": components['analysis_points']
            },
            is_measured=True
        )
    
    def _calc_internal_consistency(self, structured_output: Optional[Any]) -> tuple[float, FactorExplanation]:
        """
        Calculate internal consistency by checking alignment between components.
        
        Checks:
        1. Table has candidates ↔ Conclusion discusses candidates (not "no match")
        2. Direct answer sentiment ↔ Conclusion sentiment
        """
        if structured_output is None:
            return 0.0, FactorExplanation(
                score=0.0,
                weight=self.BASE_WEIGHTS['internal_consistency'],
                contribution=0.0,
                calculation_method="No structured output to check consistency",
                raw_data={"structured_output_available": False},
                is_measured=False
            )
        
        checks = []
        check_details = {}
        
        # Check 1: Table ↔ Conclusion alignment
        table_data = getattr(structured_output, 'table_data', None)
        conclusion = getattr(structured_output, 'conclusion', None)
        
        if table_data and conclusion:
            rows = getattr(table_data, 'rows', [])
            has_candidates = len(rows) > 0
            
            conclusion_text = str(conclusion).lower()
            no_match_phrases = [
                'no candidates match', 'no candidate match',
                'none of the candidates', 'no suitable candidate',
                'ningún candidato', 'ninguno de los candidatos',
                'no hay candidatos', 'sin candidatos'
            ]
            conclusion_says_no_match = any(phrase in conclusion_text for phrase in no_match_phrases)
            
            # Consistency: table has candidates XOR conclusion says no match
            is_consistent = has_candidates != conclusion_says_no_match
            checks.append(is_consistent)
            check_details['table_conclusion_alignment'] = {
                'table_has_candidates': has_candidates,
                'conclusion_says_no_match': conclusion_says_no_match,
                'is_consistent': is_consistent
            }
        
        # Check 2: Direct answer ↔ Conclusion sentiment (if both exist)
        direct_answer = getattr(structured_output, 'direct_answer', None)
        if direct_answer and conclusion:
            da_text = str(direct_answer).lower()
            conc_text = str(conclusion).lower()
            
            # Simple sentiment check: both positive or both negative
            da_negative = any(w in da_text for w in ['no ', 'ningún', 'ninguno', 'not ', 'cannot'])
            conc_negative = any(w in conc_text for w in ['no ', 'ningún', 'ninguno', 'not ', 'cannot'])
            
            sentiments_match = da_negative == conc_negative
            checks.append(sentiments_match)
            check_details['answer_conclusion_sentiment'] = {
                'direct_answer_negative': da_negative,
                'conclusion_negative': conc_negative,
                'sentiments_match': sentiments_match
            }
        
        if not checks:
            return 0.0, FactorExplanation(
                score=0.0,
                weight=self.BASE_WEIGHTS['internal_consistency'],
                contribution=0.0,
                calculation_method="Insufficient components for consistency check",
                raw_data={"checks_performed": 0},
                is_measured=False
            )
        
        score = sum(checks) / len(checks)
        
        return score, FactorExplanation(
            score=score,
            weight=self.BASE_WEIGHTS['internal_consistency'],
            contribution=score * self.BASE_WEIGHTS['internal_consistency'],
            calculation_method=f"{sum(checks)}/{len(checks)} consistency checks passed",
            raw_data={
                "checks_performed": len(checks),
                "checks_passed": sum(checks),
                "details": check_details
            },
            is_measured=True
        )
    
    def _build_explanation(
        self,
        factors: ConfidenceFactors,
        active_weights: Dict[str, float],
        final_score: float
    ) -> Dict[str, Any]:
        """Build comprehensive explanation dictionary."""
        
        factor_explanations = {}
        
        for factor_name in self.BASE_WEIGHTS.keys():
            explanation = getattr(factors, f'{factor_name}_explanation', None)
            if explanation:
                factor_explanations[factor_name] = {
                    "score": round(explanation.score, 3),
                    "weight": round(active_weights.get(factor_name, 0), 3),
                    "contribution": round(explanation.score * active_weights.get(factor_name, 0), 3),
                    "calculation": explanation.calculation_method,
                    "data": explanation.raw_data,
                    "is_measured": explanation.is_measured
                }
        
        return {
            "final_score": round(final_score, 3),
            "final_score_percent": f"{final_score:.1%}",
            "factors_measured": factors.measured_factors,
            "factors_total": factors.total_factors,
            "measurement_coverage": f"{factors.measured_factors}/{factors.total_factors}",
            "factors": factor_explanations,
            "weights_used": {k: round(v, 3) for k, v in active_weights.items()},
            "metadata": {
                "has_verification": factors.has_verification,
                "has_reasoning": factors.has_reasoning,
                "query_type": factors.query_type
            },
            "interpretation": self._get_score_interpretation(final_score, factors)
        }
    
    def _get_score_interpretation(self, score: float, factors: ConfidenceFactors) -> str:
        """
        Provide ADAPTIVE interpretation based on query type and context.
        """
        if not factors.has_verification:
            return (f"Score {score:.0%}: Claim verification not performed - "
                    f"confidence based only on source quality")
        
        query_type = factors.query_type
        if query_type in ["search", "verify"]:
            thresholds = ADAPTIVE_THRESHOLDS['factual_simple']
        elif query_type in ["ranking", "comparison"]:
            thresholds = ADAPTIVE_THRESHOLDS['comparison']
        elif query_type in ["summarize", "aggregate"]:
            thresholds = ADAPTIVE_THRESHOLDS['analysis']
        else:
            thresholds = ADAPTIVE_THRESHOLDS['default']
        
        if score >= thresholds['high']:
            level = "High"
            desc = "claims well-verified, excellent source coverage"
        elif score >= thresholds['good']:
            level = "Good"
            desc = "most claims verified, adequate sources"
        elif score >= thresholds['moderate']:
            level = "Moderate"
            desc = "some unverified claims or limited sources"
        elif score >= thresholds['low']:
            level = "Low"
            desc = "significant unverified or contradicted claims"
        else:
            level = "Very low"
            desc = "response may contain errors"
        
        return f"Score {score:.0%} ({level} for {query_type}): {desc}"


# Singleton instance
_calculator = None

def get_confidence_calculator() -> ConfidenceCalculator:
    """Get singleton confidence calculator instance."""
    global _calculator
    if _calculator is None:
        _calculator = ConfidenceCalculator()
    return _calculator
