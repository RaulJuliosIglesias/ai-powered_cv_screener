from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import deque
import json
import os
import logging


@dataclass
class UsageRecord:
    """Record of API usage."""
    timestamp: datetime
    operation: str  # "embedding" | "completion" | "query"
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    latency_ms: float = 0


class UsageTracker:
    """Track all API usage and costs."""
    
    PRICING = {
        "text-embedding-3-small": {
            "input": 0.00002 / 1000,  # $0.00002 per 1K tokens
        },
        "gemini-1.5-flash": {
            "input": 0.000075 / 1000,   # $0.075/1M input
            "output": 0.0003 / 1000,    # $0.30/1M output
        }
    }
    
    def __init__(self, log_file: str = "usage_log.jsonl"):
        self.log_file = log_file
        self.session_usage: List[UsageRecord] = []
        self.logger = logging.getLogger("cv_screener.usage")
    
    def record(
        self,
        operation: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int = 0,
        latency_ms: float = 0,
    ) -> UsageRecord:
        """Record an API usage event."""
        pricing = self.PRICING.get(model, {"input": 0, "output": 0})
        
        cost = (
            prompt_tokens * pricing.get("input", 0) +
            completion_tokens * pricing.get("output", 0)
        )
        
        record = UsageRecord(
            timestamp=datetime.now(),
            operation=operation,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            estimated_cost_usd=cost,
            latency_ms=latency_ms,
        )
        
        self.session_usage.append(record)
        self._persist(record)
        
        return record
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics for current session."""
        if not self.session_usage:
            return {
                "total_requests": 0,
                "total_tokens": 0,
                "total_cost_usd": 0,
                "average_latency_ms": 0,
                "by_operation": {},
            }
        
        return {
            "total_requests": len(self.session_usage),
            "total_tokens": sum(r.total_tokens for r in self.session_usage),
            "total_cost_usd": sum(r.estimated_cost_usd for r in self.session_usage),
            "average_latency_ms": sum(r.latency_ms for r in self.session_usage) / len(self.session_usage),
            "by_operation": self._group_by_operation(),
        }
    
    def _persist(self, record: UsageRecord):
        """Persist usage record to file."""
        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps({
                    "timestamp": record.timestamp.isoformat(),
                    "operation": record.operation,
                    "model": record.model,
                    "prompt_tokens": record.prompt_tokens,
                    "completion_tokens": record.completion_tokens,
                    "total_tokens": record.total_tokens,
                    "cost_usd": record.estimated_cost_usd,
                    "latency_ms": record.latency_ms,
                }) + "\n")
        except Exception as e:
            self.logger.error(f"Failed to persist usage record: {e}")
    
    def _group_by_operation(self) -> Dict[str, Dict]:
        """Group usage by operation type."""
        groups = {}
        for record in self.session_usage:
            if record.operation not in groups:
                groups[record.operation] = {"count": 0, "tokens": 0, "cost": 0}
            groups[record.operation]["count"] += 1
            groups[record.operation]["tokens"] += record.total_tokens
            groups[record.operation]["cost"] += record.estimated_cost_usd
        return groups
    
    def get_total_stats(self) -> Dict[str, Any]:
        """Get total statistics from log file."""
        total_requests = 0
        total_tokens = 0
        total_cost = 0.0
        total_latency = 0.0
        
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, "r") as f:
                    for line in f:
                        try:
                            record = json.loads(line)
                            total_requests += 1
                            total_tokens += record.get("total_tokens", 0)
                            total_cost += record.get("cost_usd", 0)
                            total_latency += record.get("latency_ms", 0)
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            self.logger.error(f"Failed to read usage log: {e}")
        
        return {
            "total_requests": total_requests,
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost,
            "average_latency_ms": total_latency / total_requests if total_requests > 0 else 0,
        }


class QueryLogger:
    """Log all queries for analysis and debugging."""
    
    def __init__(self, log_file: str = "queries.jsonl"):
        self.log_file = log_file
        self.logger = logging.getLogger("cv_screener.queries")
    
    def log_query(
        self,
        query: str,
        retrieved_chunks: List[Dict],
        response: str,
        sources: List[str],
        latency_ms: float,
        validation_result: Optional[Dict] = None,
        usage: Optional[Dict] = None,
    ):
        """Log a query and its response."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "num_chunks_retrieved": len(retrieved_chunks),
            "chunk_scores": [c.get("score", 0) for c in retrieved_chunks],
            "response_length": len(response),
            "sources_cited": sources,
            "latency_ms": latency_ms,
            "validation": validation_result,
            "usage": usage,
        }
        
        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            self.logger.error(f"Failed to log query: {e}")
        
        self.logger.info(
            f"Query processed: {query[:50]}... | "
            f"Latency: {latency_ms:.0f}ms | "
            f"Sources: {len(sources)}"
        )


class RateLimiter:
    """Prevent excessive API calls."""
    
    def __init__(
        self,
        max_requests_per_minute: int = 60,
        max_tokens_per_minute: int = 100000,
    ):
        self.max_rpm = max_requests_per_minute
        self.max_tpm = max_tokens_per_minute
        self.request_times: deque = deque()
        self.token_usage: deque = deque()  # (timestamp, tokens)
    
    def check_limit(self, estimated_tokens: int = 1000) -> tuple[bool, float]:
        """Check if request is within limits. Returns (allowed, wait_seconds)."""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        
        # Clean old entries
        while self.request_times and self.request_times[0] < minute_ago:
            self.request_times.popleft()
        while self.token_usage and self.token_usage[0][0] < minute_ago:
            self.token_usage.popleft()
        
        # Check request limit
        if len(self.request_times) >= self.max_rpm:
            wait = (self.request_times[0] - minute_ago).total_seconds()
            return False, max(0, wait)
        
        # Check token limit
        current_tokens = sum(t[1] for t in self.token_usage)
        if current_tokens + estimated_tokens > self.max_tpm:
            wait = (self.token_usage[0][0] - minute_ago).total_seconds()
            return False, max(0, wait)
        
        return True, 0
    
    def record_request(self, tokens_used: int):
        """Record a request for rate limiting."""
        now = datetime.now()
        self.request_times.append(now)
        self.token_usage.append((now, tokens_used))
