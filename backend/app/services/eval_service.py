"""
Evaluation Service for CV Screener.

This module provides logging and metrics collection for RAG system evaluation.
All queries, responses, and metrics are logged for analysis and improvement.
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class QueryLogEntry:
    """Single query log entry."""
    timestamp: str
    session_id: Optional[str]
    query: str
    response: str
    sources: List[Dict[str, Any]]
    metrics: Dict[str, float]
    hallucination_check: Dict[str, Any]
    guardrail_passed: bool
    confidence_score: float
    mode: str = "local"


@dataclass
class DailyStats:
    """Daily statistics summary."""
    date: str
    total_queries: int
    avg_confidence: float
    guardrail_rejections: int
    avg_latency_ms: float
    avg_embedding_ms: float
    avg_search_ms: float
    avg_llm_ms: float
    low_confidence_count: int
    unique_sessions: int


class EvalService:
    """
    Evaluation service for logging and metrics.
    
    Features:
    - JSONL logging for all queries
    - Daily statistics aggregation
    - Low confidence query tracking
    - Metrics analysis
    """
    
    LOW_CONFIDENCE_THRESHOLD = 0.5
    
    def __init__(self, log_dir: str = None):
        """
        Initialize the evaluation service.
        
        Args:
            log_dir: Directory for log files. Defaults to ./eval_logs
        """
        if log_dir is None:
            # Default to project root / eval_logs
            log_dir = Path(__file__).parent.parent.parent.parent / "eval_logs"
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"EvalService initialized. Log dir: {self.log_dir}")
    
    def _get_log_file(self, date: str = None) -> Path:
        """Get log file path for a specific date."""
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        return self.log_dir / f"queries_{date}.jsonl"
    
    def log_query(
        self,
        query: str,
        response: str,
        sources: List[Dict[str, Any]],
        metrics: Dict[str, float],
        hallucination_check: Dict[str, Any],
        guardrail_passed: bool,
        session_id: Optional[str] = None,
        mode: str = "local"
    ) -> bool:
        """
        Log a query and its response.
        
        Args:
            query: User's question
            response: LLM's response
            sources: List of source documents used
            metrics: Performance metrics (latencies, tokens, etc.)
            hallucination_check: Result of hallucination verification
            guardrail_passed: Whether the query passed guardrails
            session_id: Optional session identifier
            mode: Operating mode (local/cloud)
            
        Returns:
            True if logging succeeded
        """
        try:
            confidence = hallucination_check.get("confidence_score", 0.0)
            
            entry = QueryLogEntry(
                timestamp=datetime.now().isoformat(),
                session_id=session_id,
                query=query,
                response=response[:2000] if len(response) > 2000 else response,  # Truncate long responses
                sources=sources,
                metrics=metrics,
                hallucination_check={
                    k: v for k, v in hallucination_check.items()
                    if k in ['is_valid', 'confidence_score', 'warnings', 'verified_cv_ids', 'unverified_cv_ids']
                },
                guardrail_passed=guardrail_passed,
                confidence_score=confidence,
                mode=mode
            )
            
            log_file = self._get_log_file()
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
            
            # Log warning for low confidence
            if confidence < self.LOW_CONFIDENCE_THRESHOLD:
                logger.warning(f"Low confidence query logged: {confidence:.2f}")
            else:
                logger.debug(f"Query logged. Confidence: {confidence:.2f}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to log query: {e}")
            return False
    
    def get_daily_stats(self, date: str = None) -> DailyStats:
        """
        Get statistics for a specific day.
        
        Args:
            date: Date string in YYYYMMDD format. Defaults to today.
            
        Returns:
            DailyStats dataclass with aggregated metrics
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')
        
        log_file = self._get_log_file(date)
        
        if not log_file.exists():
            return DailyStats(
                date=date,
                total_queries=0,
                avg_confidence=0.0,
                guardrail_rejections=0,
                avg_latency_ms=0.0,
                avg_embedding_ms=0.0,
                avg_search_ms=0.0,
                avg_llm_ms=0.0,
                low_confidence_count=0,
                unique_sessions=0
            )
        
        entries = self._read_log_file(log_file)
        
        if not entries:
            return DailyStats(
                date=date,
                total_queries=0,
                avg_confidence=0.0,
                guardrail_rejections=0,
                avg_latency_ms=0.0,
                avg_embedding_ms=0.0,
                avg_search_ms=0.0,
                avg_llm_ms=0.0,
                low_confidence_count=0,
                unique_sessions=0
            )
        
        # Calculate aggregates
        confidences = [e.get("confidence_score", 0) for e in entries]
        latencies = [e.get("metrics", {}).get("total_ms", 0) for e in entries]
        embedding_ms = [e.get("metrics", {}).get("embedding_ms", 0) for e in entries]
        search_ms = [e.get("metrics", {}).get("search_ms", 0) for e in entries]
        llm_ms = [e.get("metrics", {}).get("llm_ms", 0) for e in entries]
        
        return DailyStats(
            date=date,
            total_queries=len(entries),
            avg_confidence=sum(confidences) / len(confidences) if confidences else 0,
            guardrail_rejections=sum(1 for e in entries if not e.get("guardrail_passed", True)),
            avg_latency_ms=sum(latencies) / len(latencies) if latencies else 0,
            avg_embedding_ms=sum(embedding_ms) / len(embedding_ms) if embedding_ms else 0,
            avg_search_ms=sum(search_ms) / len(search_ms) if search_ms else 0,
            avg_llm_ms=sum(llm_ms) / len(llm_ms) if llm_ms else 0,
            low_confidence_count=sum(1 for c in confidences if c < self.LOW_CONFIDENCE_THRESHOLD),
            unique_sessions=len(set(e.get("session_id") for e in entries if e.get("session_id")))
        )
    
    def get_weekly_stats(self) -> Dict[str, DailyStats]:
        """Get statistics for the last 7 days."""
        stats = {}
        for i in range(7):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y%m%d')
            stats[date] = self.get_daily_stats(date)
        return stats
    
    def get_low_confidence_queries(
        self,
        threshold: float = None,
        limit: int = 20,
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Get queries with low confidence scores for review.
        
        Args:
            threshold: Confidence threshold. Defaults to LOW_CONFIDENCE_THRESHOLD
            limit: Maximum number of queries to return
            days: Number of days to look back
            
        Returns:
            List of low confidence query entries
        """
        if threshold is None:
            threshold = self.LOW_CONFIDENCE_THRESHOLD
        
        low_confidence = []
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y%m%d')
            log_file = self._get_log_file(date)
            
            if log_file.exists():
                entries = self._read_log_file(log_file)
                for entry in entries:
                    if entry.get("confidence_score", 1.0) < threshold:
                        low_confidence.append({
                            "date": date,
                            "query": entry.get("query", ""),
                            "response_preview": entry.get("response", "")[:200],
                            "confidence": entry.get("confidence_score", 0),
                            "guardrail_passed": entry.get("guardrail_passed", True),
                            "warnings": entry.get("hallucination_check", {}).get("warnings", [])
                        })
            
            if len(low_confidence) >= limit:
                break
        
        # Sort by confidence (lowest first)
        low_confidence.sort(key=lambda x: x.get("confidence", 0))
        return low_confidence[:limit]
    
    def get_guardrail_rejections(self, days: int = 7, limit: int = 50) -> List[Dict[str, Any]]:
        """Get queries that were rejected by guardrails."""
        rejections = []
        
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y%m%d')
            log_file = self._get_log_file(date)
            
            if log_file.exists():
                entries = self._read_log_file(log_file)
                for entry in entries:
                    if not entry.get("guardrail_passed", True):
                        rejections.append({
                            "date": date,
                            "timestamp": entry.get("timestamp", ""),
                            "query": entry.get("query", ""),
                            "response": entry.get("response", "")
                        })
            
            if len(rejections) >= limit:
                break
        
        return rejections[:limit]
    
    def _read_log_file(self, log_file: Path) -> List[Dict[str, Any]]:
        """Read all entries from a log file."""
        entries = []
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON line in {log_file}")
        except Exception as e:
            logger.error(f"Failed to read log file {log_file}: {e}")
        return entries
    
    def export_stats_json(self, days: int = 30) -> str:
        """Export statistics as JSON for external analysis."""
        stats = {}
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y%m%d')
            daily = self.get_daily_stats(date)
            if daily.total_queries > 0:
                stats[date] = asdict(daily)
        
        return json.dumps(stats, indent=2, ensure_ascii=False)


# Singleton instance
_eval_service: Optional[EvalService] = None


def get_eval_service() -> EvalService:
    """Get singleton instance of EvalService."""
    global _eval_service
    if _eval_service is None:
        _eval_service = EvalService()
    return _eval_service
