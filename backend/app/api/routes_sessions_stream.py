"""SSE streaming endpoint for real-time chat progress."""
import json
import logging
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import settings, Mode
from app.models.sessions import session_manager
from app.services.rag_service_v5 import RAGServiceV5

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sessions", tags=["sessions-stream"])


class ChatStreamRequest(BaseModel):
    message: str


async def event_generator(rag_service, question: str, session_id: str, cv_ids: list, total_cvs: int):
    """Generate SSE events from RAG pipeline execution."""
    try:
        async for event in rag_service.query_stream(
            question=question,
            session_id=session_id,
            cv_ids=cv_ids,
            total_cvs_in_session=total_cvs
        ):
            event_type = event.get("event", "message")
            event_data = event.get("data", {})
            
            # Format as SSE
            yield f"event: {event_type}\n"
            yield f"data: {json.dumps(event_data)}\n\n"
            
    except Exception as e:
        logger.exception(f"Stream error: {e}")
        yield f"event: error\n"
        yield f"data: {json.dumps({'message': str(e)})}\n\n"


@router.post("/{session_id}/chat-stream")
async def chat_stream(
    session_id: str,
    request: ChatStreamRequest,
    mode: Mode = Query(default=settings.default_mode)
):
    """
    Stream chat response with real-time progress updates via SSE.
    
    Events emitted:
    - step: Pipeline step progress (running/completed)
    - complete: Final response with full data
    - error: Error occurred
    """
    mgr = session_manager
    session = mgr.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Save user message
    mgr.add_message(session_id, "user", request.message)
    
    # Get CV IDs for this session
    cv_ids = mgr.get_cv_ids_for_session(session_id)
    total_cvs = len(session.cvs)
    
    if not cv_ids:
        raise HTTPException(status_code=400, detail="No CVs in session")
    
    # Create RAG service
    logger.info(f"[STREAM] Creating RAG service with mode={mode}")
    rag_service = RAGServiceV5.from_factory(mode)
    
    return StreamingResponse(
        event_generator(rag_service, request.message, session_id, cv_ids, total_cvs),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
