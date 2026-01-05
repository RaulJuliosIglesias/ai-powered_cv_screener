"""
Debug Logger - Comprehensive logging for CV Screener debugging.

Creates detailed logs for each chat session, from upload to response.
Saves logs to backend/debug_logs/ folder with session IDs.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from functools import wraps

# Create debug logs directory
DEBUG_LOGS_DIR = Path(__file__).parent.parent.parent / "debug_logs"
DEBUG_LOGS_DIR.mkdir(exist_ok=True)

# Current session log
_current_session_id: Optional[str] = None
_session_logs: Dict[str, List[Dict[str, Any]]] = {}


def get_session_log_path(session_id: str) -> Path:
    """Get path for session log file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return DEBUG_LOGS_DIR / f"session_{session_id[:8]}_{timestamp}.json"


def set_current_session(session_id: str) -> None:
    """Set the current session for logging."""
    global _current_session_id
    _current_session_id = session_id
    if session_id not in _session_logs:
        _session_logs[session_id] = []
    log_event("SESSION_START", {"session_id": session_id})


def log_event(event_type: str, data: Dict[str, Any], level: str = "INFO") -> None:
    """Log an event to the current session."""
    global _current_session_id, _session_logs
    
    event = {
        "timestamp": datetime.now().isoformat(),
        "event_type": event_type,
        "level": level,
        "data": _serialize_data(data)
    }
    
    # Also log to console
    logger = logging.getLogger("debug_logger")
    log_msg = f"[DEBUG_LOG] [{event_type}] {json.dumps(data, default=str)[:500]}"
    
    if level == "ERROR":
        logger.error(log_msg)
    elif level == "WARNING":
        logger.warning(log_msg)
    else:
        logger.info(log_msg)
    
    # Store in session logs
    if _current_session_id:
        if _current_session_id not in _session_logs:
            _session_logs[_current_session_id] = []
        _session_logs[_current_session_id].append(event)


def _serialize_data(data: Any) -> Any:
    """Serialize data for JSON, handling special types."""
    if isinstance(data, dict):
        return {k: _serialize_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_serialize_data(item) for item in data]
    elif hasattr(data, 'to_dict'):
        return data.to_dict()
    elif hasattr(data, '__dict__'):
        return {k: _serialize_data(v) for k, v in data.__dict__.items() if not k.startswith('_')}
    else:
        try:
            json.dumps(data)
            return data
        except (TypeError, ValueError):
            return str(data)


def save_session_log(session_id: str = None) -> Optional[str]:
    """Save session log to file and return path."""
    sid = session_id or _current_session_id
    if not sid or sid not in _session_logs:
        return None
    
    log_path = get_session_log_path(sid)
    
    log_data = {
        "session_id": sid,
        "generated_at": datetime.now().isoformat(),
        "events": _session_logs[sid]
    }
    
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False, default=str)
    
    logger = logging.getLogger("debug_logger")
    logger.info(f"[DEBUG_LOG] Saved session log to: {log_path}")
    
    return str(log_path)


def clear_session_log(session_id: str = None) -> None:
    """Clear session log from memory."""
    sid = session_id or _current_session_id
    if sid and sid in _session_logs:
        del _session_logs[sid]


# ============================================================================
# SPECIFIC LOGGING FUNCTIONS FOR KEY PIPELINE STAGES
# ============================================================================

def log_cv_upload(session_id: str, cv_id: str, filename: str, chunk_count: int) -> None:
    """Log CV upload event."""
    set_current_session(session_id)
    log_event("CV_UPLOAD", {
        "cv_id": cv_id,
        "filename": filename,
        "chunk_count": chunk_count
    })


def log_chunks_created(cv_id: str, chunks: List[Dict[str, Any]]) -> None:
    """Log chunks created during upload with metadata details."""
    chunk_summaries = []
    for i, chunk in enumerate(chunks):
        meta = chunk.get("metadata", {})
        chunk_summaries.append({
            "index": i,
            "section_type": meta.get("section_type"),
            "candidate_name": meta.get("candidate_name"),
            "job_hopping_score": meta.get("job_hopping_score"),
            "avg_tenure_years": meta.get("avg_tenure_years"),
            "total_experience_years": meta.get("total_experience_years"),
            "position_count": meta.get("position_count"),
            "employment_gaps_count": meta.get("employment_gaps_count"),
            "content_preview": chunk.get("content", "")[:100]
        })
    
    log_event("CHUNKS_CREATED", {
        "cv_id": cv_id,
        "total_chunks": len(chunks),
        "chunks": chunk_summaries
    })


def log_query_start(session_id: str, question: str, cv_ids: List[str]) -> None:
    """Log query start."""
    set_current_session(session_id)
    log_event("QUERY_START", {
        "question": question,
        "cv_ids": cv_ids,
        "cv_count": len(cv_ids)
    })


def log_query_understanding(understanding: Any) -> None:
    """Log query understanding result."""
    if understanding:
        log_event("QUERY_UNDERSTANDING", {
            "query_type": getattr(understanding, 'query_type', None),
            "is_single_candidate": getattr(understanding, 'is_single_candidate', None),
            "target_candidate": getattr(understanding, 'target_candidate', None),
            "reformulated_prompt": getattr(understanding, 'reformulated_prompt', None),
            "requirements": getattr(understanding, 'requirements', None),
        })


def log_retrieval(chunks: List[Dict[str, Any]], strategy: str = "unknown") -> None:
    """Log retrieval results with metadata."""
    chunk_details = []
    for i, chunk in enumerate(chunks[:10]):  # First 10
        meta = chunk.get("metadata", {})
        chunk_details.append({
            "index": i,
            "cv_id": meta.get("cv_id"),
            "candidate_name": meta.get("candidate_name"),
            "section_type": meta.get("section_type"),
            "job_hopping_score": meta.get("job_hopping_score"),
            "avg_tenure_years": meta.get("avg_tenure_years"),
            "total_experience_years": meta.get("total_experience_years"),
            "score": chunk.get("score"),
            "has_enriched_metadata": bool(meta.get("job_hopping_score"))
        })
    
    log_event("RETRIEVAL", {
        "total_chunks": len(chunks),
        "strategy": strategy,
        "sample_chunks": chunk_details,
        "all_metadata_keys": list(chunks[0].get("metadata", {}).keys()) if chunks else []
    })


def log_template_selection(template_name: str, candidate_name: str = None, detection_method: str = None) -> None:
    """Log which template was selected."""
    log_event("TEMPLATE_SELECTION", {
        "template": template_name,
        "candidate_name": candidate_name,
        "detection_method": detection_method
    })


def log_enriched_metadata_extraction(chunks: List[Dict[str, Any]], red_flags_section: str, stability_section: str) -> None:
    """Log enriched metadata extraction for LLM prompt."""
    first_chunk_meta = chunks[0].get("metadata", {}) if chunks else {}
    
    log_event("ENRICHED_METADATA_EXTRACTION", {
        "chunk_count": len(chunks),
        "first_chunk_metadata_keys": list(first_chunk_meta.keys()),
        "first_chunk_job_hopping_score": first_chunk_meta.get("job_hopping_score"),
        "first_chunk_avg_tenure_years": first_chunk_meta.get("avg_tenure_years"),
        "first_chunk_total_experience": first_chunk_meta.get("total_experience_years"),
        "red_flags_section_preview": red_flags_section[:300] if red_flags_section else None,
        "stability_section_preview": stability_section[:300] if stability_section else None,
        "has_pre_calculated_data": "Pre-calculated" in (red_flags_section or "")
    })


def log_llm_prompt(prompt: str, template_name: str) -> None:
    """Log the prompt sent to LLM."""
    log_event("LLM_PROMPT", {
        "template": template_name,
        "prompt_length": len(prompt),
        "prompt_preview": prompt[:1000] + "..." if len(prompt) > 1000 else prompt
    })


def log_llm_response(response: str, tokens: Dict[str, int] = None) -> None:
    """Log LLM response."""
    log_event("LLM_RESPONSE", {
        "response_length": len(response),
        "response_preview": response[:500] + "..." if len(response) > 500 else response,
        "tokens": tokens
    })


def log_orchestrator_processing(
    thinking: bool,
    table: bool,
    conclusion: bool,
    analysis: bool,
    red_flags_count: int = 0,
    gap_analysis_count: int = 0,
    timeline_count: int = 0
) -> None:
    """Log orchestrator processing results."""
    log_event("ORCHESTRATOR_PROCESSING", {
        "has_thinking": thinking,
        "has_table": table,
        "has_conclusion": conclusion,
        "has_analysis": analysis,
        "red_flags_detected": red_flags_count,
        "gap_analysis_skills": gap_analysis_count,
        "timeline_candidates": timeline_count
    })


def log_red_flags_module(flags: List[Any], high_risk: List[str], clean: List[str]) -> None:
    """Log RedFlagsModule results."""
    flag_details = []
    for flag in flags[:10]:  # First 10
        flag_details.append({
            "flag_type": getattr(flag, 'flag_type', None),
            "severity": getattr(flag, 'severity', None),
            "candidate_name": getattr(flag, 'candidate_name', None),
            "description": getattr(flag, 'description', None),
        })
    
    log_event("RED_FLAGS_MODULE", {
        "total_flags": len(flags),
        "high_risk_candidates": high_risk,
        "clean_candidates": clean,
        "flag_details": flag_details
    })


def log_final_response(answer: str, structured_output: Any) -> None:
    """Log final response."""
    log_event("FINAL_RESPONSE", {
        "answer_length": len(answer),
        "answer_preview": answer[:500] + "..." if len(answer) > 500 else answer,
        "has_structured_output": bool(structured_output),
        "structured_output_keys": list(structured_output.keys()) if isinstance(structured_output, dict) else None
    })
    
    # Auto-save session log
    save_session_log()


def log_error(stage: str, error: str, details: Dict[str, Any] = None) -> None:
    """Log an error."""
    log_event("ERROR", {
        "stage": stage,
        "error": error,
        "details": details or {}
    }, level="ERROR")


# ============================================================================
# DECORATOR FOR AUTOMATIC FUNCTION LOGGING
# ============================================================================

def log_function(stage_name: str):
    """Decorator to automatically log function entry/exit."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            log_event(f"{stage_name}_START", {
                "function": func.__name__,
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys())
            })
            try:
                result = await func(*args, **kwargs)
                log_event(f"{stage_name}_END", {
                    "function": func.__name__,
                    "success": True
                })
                return result
            except Exception as e:
                log_error(stage_name, str(e))
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            log_event(f"{stage_name}_START", {
                "function": func.__name__,
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys())
            })
            try:
                result = func(*args, **kwargs)
                log_event(f"{stage_name}_END", {
                    "function": func.__name__,
                    "success": True
                })
                return result
            except Exception as e:
                log_error(stage_name, str(e))
                raise
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator
