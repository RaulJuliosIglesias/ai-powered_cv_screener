"""
RAGAS Evaluation Service for RAG Quality Metrics.

Implements RAGAS-style metrics for evaluating RAG pipeline quality:
- Faithfulness: Are claims in the answer supported by context?
- Answer Relevancy: Is the answer relevant to the question?
- Context Relevancy: Is the retrieved context relevant?
- Context Recall: Did we retrieve all necessary information?

This is a lightweight implementation that uses NLI for faithfulness
and embedding similarity for relevancy metrics, avoiding the need
for expensive LLM calls for every evaluation.

Reference: https://docs.ragas.io/
"""
import logging
import time
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from app.providers.huggingface_client import get_huggingface_client, HuggingFaceClient
from app.services.nli_verification_service import (
    NLIVerificationService, 
    get_nli_verification_service,
    VerificationResult
)

logger = logging.getLogger(__name__)


@dataclass
class RAGASMetrics:
    """RAGAS evaluation metrics for a single query-response pair."""
    faithfulness: float  # 0-1: Are claims supported by context?
    answer_relevancy: float  # 0-1: Is answer relevant to question?
    context_relevancy: float  # 0-1: Is context relevant to question?
    context_precision: float  # 0-1: Precision of retrieved context
    overall_score: float  # Weighted average of all metrics
    
    # Detailed breakdown
    claims_verified: int = 0
    claims_supported: int = 0
    claims_contradicted: int = 0
    context_chunks_used: int = 0
    
    # Timing
    latency_ms: float = 0.0


@dataclass
class EvaluationRecord:
    """Record of a single evaluation for logging/analysis."""
    timestamp: str
    query: str
    response: str
    context_chunks: List[str]
    metrics: RAGASMetrics
    session_id: Optional[str] = None
    query_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class RAGASEvaluationService:
    """
    Service for evaluating RAG pipeline quality using RAGAS-style metrics.
    
    Metrics computed:
    1. Faithfulness (via NLI): Claims in answer supported by context
    2. Answer Relevancy (via zero-shot): Answer addresses the question
    3. Context Relevancy (via zero-shot): Retrieved context is relevant
    4. Context Precision: Useful chunks / total chunks
    
    Usage:
        service = RAGASEvaluationService()
        metrics = await service.evaluate(
            query="Who has Python experience?",
            response="Maria has 5 years of Python experience at DataCorp.",
            context_chunks=["Maria Garcia - Python developer..."]
        )
        print(f"Faithfulness: {metrics.faithfulness:.2%}")
        print(f"Overall: {metrics.overall_score:.2%}")
    """
    
    # Weights for overall score calculation
    WEIGHT_FAITHFULNESS = 0.4
    WEIGHT_ANSWER_RELEVANCY = 0.3
    WEIGHT_CONTEXT_RELEVANCY = 0.2
    WEIGHT_CONTEXT_PRECISION = 0.1
    
    # Labels for relevancy classification
    RELEVANCY_LABELS = [
        "highly relevant and directly addresses the question",
        "somewhat relevant but incomplete",
        "not relevant to the question"
    ]
    
    def __init__(
        self,
        hf_client: Optional[HuggingFaceClient] = None,
        nli_service: Optional[NLIVerificationService] = None,
        log_evaluations: bool = True,
        log_dir: str = "eval_logs"
    ):
        """
        Initialize RAGAS evaluation service.
        
        Args:
            hf_client: HuggingFace client for zero-shot classification
            nli_service: NLI service for faithfulness computation
            log_evaluations: Whether to log evaluations to file
            log_dir: Directory for evaluation logs
        """
        self.hf_client = hf_client or get_huggingface_client()
        self.nli_service = nli_service or get_nli_verification_service()
        self.log_evaluations = log_evaluations
        self.log_dir = Path(log_dir)
        
        if log_evaluations:
            self.log_dir.mkdir(exist_ok=True)
        
        logger.info(
            f"RAGASEvaluationService initialized: "
            f"log_evaluations={log_evaluations}, log_dir={log_dir}"
        )
    
    async def evaluate(
        self,
        query: str,
        response: str,
        context_chunks: List[str],
        session_id: Optional[str] = None,
        query_type: Optional[str] = None
    ) -> RAGASMetrics:
        """
        Evaluate a query-response pair using RAGAS metrics.
        
        Args:
            query: User's question
            response: LLM's generated response
            context_chunks: Retrieved context chunks
            session_id: Optional session ID for logging
            query_type: Optional query type for analysis
            
        Returns:
            RAGASMetrics with all computed scores
        """
        start_time = time.perf_counter()
        
        # Handle edge cases
        if not response or not response.strip():
            return RAGASMetrics(
                faithfulness=0.0,
                answer_relevancy=0.0,
                context_relevancy=0.0,
                context_precision=0.0,
                overall_score=0.0,
                latency_ms=0.0
            )
        
        # Compute metrics in parallel where possible
        faithfulness_result = await self._compute_faithfulness(response, context_chunks)
        answer_relevancy = await self._compute_answer_relevancy(query, response)
        context_relevancy, context_precision = await self._compute_context_metrics(
            query, context_chunks
        )
        
        # Calculate overall score
        overall = (
            self.WEIGHT_FAITHFULNESS * faithfulness_result.faithfulness_score +
            self.WEIGHT_ANSWER_RELEVANCY * answer_relevancy +
            self.WEIGHT_CONTEXT_RELEVANCY * context_relevancy +
            self.WEIGHT_CONTEXT_PRECISION * context_precision
        )
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        metrics = RAGASMetrics(
            faithfulness=faithfulness_result.faithfulness_score,
            answer_relevancy=answer_relevancy,
            context_relevancy=context_relevancy,
            context_precision=context_precision,
            overall_score=overall,
            claims_verified=len(faithfulness_result.claims),
            claims_supported=faithfulness_result.supported_count,
            claims_contradicted=faithfulness_result.hallucination_count,
            context_chunks_used=len(context_chunks),
            latency_ms=latency_ms
        )
        
        # Log evaluation
        if self.log_evaluations:
            await self._log_evaluation(
                query=query,
                response=response,
                context_chunks=context_chunks,
                metrics=metrics,
                session_id=session_id,
                query_type=query_type
            )
        
        logger.info(
            f"[RAGAS] Evaluation complete in {latency_ms:.1f}ms: "
            f"faithfulness={metrics.faithfulness:.2f}, "
            f"answer_rel={metrics.answer_relevancy:.2f}, "
            f"context_rel={metrics.context_relevancy:.2f}, "
            f"overall={metrics.overall_score:.2f}"
        )
        
        return metrics
    
    async def _compute_faithfulness(
        self,
        response: str,
        context_chunks: List[str]
    ) -> VerificationResult:
        """Compute faithfulness using NLI verification."""
        try:
            return await self.nli_service.verify_response(
                response=response,
                context_chunks=context_chunks
            )
        except Exception as e:
            logger.warning(f"Faithfulness computation failed: {e}")
            return VerificationResult(
                claims=[],
                faithfulness_score=0.5,  # Neutral on failure
                hallucination_count=0,
                supported_count=0,
                unsupported_count=0,
                latency_ms=0,
                method="error"
            )
    
    async def _compute_answer_relevancy(
        self,
        query: str,
        response: str
    ) -> float:
        """Compute answer relevancy using zero-shot classification."""
        if not self.hf_client.is_available:
            return 0.5  # Neutral if unavailable
        
        try:
            # Combine query and response for classification
            text = f"Question: {query}\n\nAnswer: {response[:500]}"
            
            result = await self.hf_client.zero_shot_classification(
                text=text,
                candidate_labels=self.RELEVANCY_LABELS
            )
            
            # Parse scores
            labels = result.get("labels", [])
            scores = result.get("scores", [])
            score_dict = dict(zip(labels, scores))
            
            # High relevancy = high score for first label
            high_relevancy = score_dict.get(self.RELEVANCY_LABELS[0], 0.0)
            medium_relevancy = score_dict.get(self.RELEVANCY_LABELS[1], 0.0)
            
            # Weighted combination
            relevancy = high_relevancy * 1.0 + medium_relevancy * 0.5
            return min(1.0, relevancy)
            
        except Exception as e:
            logger.warning(f"Answer relevancy computation failed: {e}")
            return 0.5
    
    async def _compute_context_metrics(
        self,
        query: str,
        context_chunks: List[str]
    ) -> tuple[float, float]:
        """
        Compute context relevancy and precision.
        
        Returns:
            (context_relevancy, context_precision)
        """
        if not context_chunks:
            return 0.0, 0.0
        
        if not self.hf_client.is_available:
            return 0.5, 0.5
        
        try:
            relevant_count = 0
            total_relevancy_score = 0.0
            
            # Sample chunks for efficiency (max 5)
            sample_chunks = context_chunks[:5]
            
            for chunk in sample_chunks:
                # Classify each chunk
                text = f"Question: {query}\n\nContext: {chunk[:300]}"
                
                result = await self.hf_client.zero_shot_classification(
                    text=text,
                    candidate_labels=[
                        "relevant context for answering the question",
                        "irrelevant context"
                    ]
                )
                
                labels = result.get("labels", [])
                scores = result.get("scores", [])
                score_dict = dict(zip(labels, scores))
                
                relevancy = score_dict.get("relevant context for answering the question", 0.0)
                total_relevancy_score += relevancy
                
                if relevancy > 0.5:
                    relevant_count += 1
            
            # Context relevancy = average relevancy score
            context_relevancy = total_relevancy_score / len(sample_chunks)
            
            # Context precision = relevant chunks / total chunks
            context_precision = relevant_count / len(sample_chunks)
            
            return context_relevancy, context_precision
            
        except Exception as e:
            logger.warning(f"Context metrics computation failed: {e}")
            return 0.5, 0.5
    
    async def _log_evaluation(
        self,
        query: str,
        response: str,
        context_chunks: List[str],
        metrics: RAGASMetrics,
        session_id: Optional[str],
        query_type: Optional[str]
    ):
        """Log evaluation to file for analysis."""
        try:
            record = EvaluationRecord(
                timestamp=datetime.utcnow().isoformat(),
                query=query,
                response=response[:1000],  # Truncate for storage
                context_chunks=[c[:500] for c in context_chunks[:5]],  # Truncate
                metrics=metrics,
                session_id=session_id,
                query_type=query_type
            )
            
            # Append to daily log file
            date_str = datetime.utcnow().strftime("%Y-%m-%d")
            log_file = self.log_dir / f"ragas_eval_{date_str}.jsonl"
            
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "timestamp": record.timestamp,
                    "session_id": record.session_id,
                    "query_type": record.query_type,
                    "query": record.query,
                    "response_preview": record.response[:200],
                    "metrics": {
                        "faithfulness": record.metrics.faithfulness,
                        "answer_relevancy": record.metrics.answer_relevancy,
                        "context_relevancy": record.metrics.context_relevancy,
                        "context_precision": record.metrics.context_precision,
                        "overall_score": record.metrics.overall_score,
                        "claims_verified": record.metrics.claims_verified,
                        "claims_supported": record.metrics.claims_supported,
                        "latency_ms": record.metrics.latency_ms
                    }
                }, ensure_ascii=False) + "\n")
                
        except Exception as e:
            logger.warning(f"Failed to log evaluation: {e}")
    
    async def get_aggregate_metrics(
        self,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get aggregate metrics from evaluation logs.
        
        Args:
            days: Number of days to aggregate
            
        Returns:
            Aggregate statistics
        """
        from datetime import timedelta
        
        metrics_list = []
        
        for i in range(days):
            date = datetime.utcnow() - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            log_file = self.log_dir / f"ragas_eval_{date_str}.jsonl"
            
            if log_file.exists():
                with open(log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        try:
                            record = json.loads(line)
                            metrics_list.append(record.get("metrics", {}))
                        except:
                            continue
        
        if not metrics_list:
            return {"error": "No evaluation data found"}
        
        # Compute averages
        n = len(metrics_list)
        return {
            "total_evaluations": n,
            "days_analyzed": days,
            "avg_faithfulness": sum(m.get("faithfulness", 0) for m in metrics_list) / n,
            "avg_answer_relevancy": sum(m.get("answer_relevancy", 0) for m in metrics_list) / n,
            "avg_context_relevancy": sum(m.get("context_relevancy", 0) for m in metrics_list) / n,
            "avg_context_precision": sum(m.get("context_precision", 0) for m in metrics_list) / n,
            "avg_overall_score": sum(m.get("overall_score", 0) for m in metrics_list) / n,
            "avg_latency_ms": sum(m.get("latency_ms", 0) for m in metrics_list) / n
        }


# =============================================================================
# Singleton Instance
# =============================================================================

_ragas_service: Optional[RAGASEvaluationService] = None


def get_ragas_evaluation_service(
    log_evaluations: bool = True
) -> RAGASEvaluationService:
    """Get singleton instance of RAGASEvaluationService."""
    global _ragas_service
    if _ragas_service is None:
        _ragas_service = RAGASEvaluationService(log_evaluations=log_evaluations)
    return _ragas_service


def reset_ragas_service():
    """Reset singleton (for testing)."""
    global _ragas_service
    _ragas_service = None
