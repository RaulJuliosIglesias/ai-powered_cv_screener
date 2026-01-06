"""SSE streaming endpoint for real-time chat progress."""
import json
import logging
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import settings, Mode
from app.models.sessions import session_manager
from app.providers.cloud.sessions import supabase_session_manager
from app.services.rag_service_v5 import RAGServiceV5
from app.utils.debug_logger import log_query_start, log_final_response, save_session_log

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sessions", tags=["sessions-stream"])


def get_session_manager(mode: Mode):
    """Get the appropriate session manager based on mode."""
    if mode == Mode.CLOUD:
        return supabase_session_manager
    return session_manager


class ChatStreamRequest(BaseModel):
    message: str
    understanding_model: str
    reranking_model: str
    reranking_enabled: bool = True
    generation_model: str
    verification_model: str
    verification_enabled: bool = True


async def event_generator(rag_service, question: str, session_id: str, cv_ids: list, total_cvs: int, mgr, conversation_history: list = None, context_history: list = None):
    """Generate SSE events from RAG pipeline execution.
    
    Args:
        conversation_history: Short history (2 msgs) for LLM prompt
        context_history: Long history (10 msgs) for context resolution
    """
    final_response = None
    
    # DEBUG LOGGING: Log query start
    log_query_start(session_id, question, cv_ids)
    
    try:
        async for event in rag_service.query_stream(
            question=question,
            conversation_history=conversation_history,
            context_history=context_history,  # Pass long history for context resolution
            session_id=session_id,
            cv_ids=cv_ids,
            total_cvs_in_session=total_cvs
        ):
            event_type = event.get("event", "message")
            event_data = event.get("data", {})
            
            # Capture final response to save
            if event_type == "complete":
                final_response = event_data
            
            # Format as SSE
            yield f"event: {event_type}\n"
            yield f"data: {json.dumps(event_data)}\n\n"
        
        # Save assistant message to session with structured_output
        if final_response and final_response.get("answer"):
            structured_output_dict = None
            if final_response.get("structured_output"):
                structured_output_dict = final_response["structured_output"]
            
            pipeline_steps = final_response.get("pipeline_steps", [])
            sources = final_response.get("sources", [])
            
            mgr.add_message(
                session_id=session_id,
                role="assistant",
                content=final_response["answer"],
                sources=sources,
                pipeline_steps=pipeline_steps,
                structured_output=structured_output_dict
            )
            logger.info(f"[STREAM] Saved assistant message with {len(sources)} sources to session {session_id}")
            
            # DEBUG LOGGING: Log final response and save session log
            log_final_response(final_response["answer"], structured_output_dict)
            save_session_log(session_id)
            
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
    mgr = get_session_manager(mode)
    session = mgr.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get TWO different history lengths:
    # 1. LONG history (10 messages) for context resolution - to find ranking candidates
    # 2. SHORT history (2 messages) for LLM prompt - to save tokens
    
    # Long history for context resolver to find ranking results
    long_history = mgr.get_conversation_history(session_id, limit=10)
    context_history = [
        {"role": msg.role if hasattr(msg, 'role') else msg.get('role'), 
         "content": msg.content if hasattr(msg, 'content') else msg.get('content')}
        for msg in long_history
    ]
    
    # Short history for LLM prompt (last 2 messages only)
    short_history = mgr.get_conversation_history(session_id, limit=2)
    conversation_history = [
        {"role": msg.role if hasattr(msg, 'role') else msg.get('role'), 
         "content": msg.content if hasattr(msg, 'content') else msg.get('content')}
        for msg in short_history
    ]
    
    logger.info(f"[STREAM] Retrieved {len(context_history)} messages for context resolution, {len(conversation_history)} for LLM")
    
    # Save user message
    mgr.add_message(session_id, "user", request.message)
    
    # Get CV IDs for this session
    cv_ids = mgr.get_cv_ids_for_session(session_id)
    # Handle both dict (cloud) and Session object (local)
    total_cvs = len(session.get("cvs", [])) if isinstance(session, dict) else len(session.cvs)
    
    if not cv_ids:
        raise HTTPException(status_code=400, detail="No CVs in session")
    
    # Create RAG service with custom configuration
    logger.info(f"[STREAM] Creating RAG service with mode={mode}, models: understanding={request.understanding_model}, reranking={request.reranking_model}, generation={request.generation_model}, verification={request.verification_model}")
    
    try:
        rag_service = RAGServiceV5.from_factory(mode)
        logger.info("[STREAM] RAG service created successfully")
        
        # Configure pipeline settings with models from frontend
        rag_service.config.understanding_model = request.understanding_model
        rag_service.config.reranking_model = request.reranking_model
        rag_service.config.reranking_enabled = request.reranking_enabled
        rag_service.config.generation_model = request.generation_model
        rag_service.config.verification_model = request.verification_model
        rag_service.config.claim_verification_enabled = request.verification_enabled
        logger.info("[STREAM] Models configured in RAG service")
        
        # Now initialize providers with configured models
        logger.info("[STREAM] Calling lazy_initialize_providers()")
        rag_service.lazy_initialize_providers()
        logger.info(f"[STREAM] Providers initialized: {rag_service._providers_initialized}")
        
    except Exception as e:
        logger.exception(f"[STREAM] Error during RAG service initialization: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize RAG service: {str(e)}")
    
    return StreamingResponse(
        event_generator(rag_service, request.message, session_id, cv_ids, total_cvs, mgr, conversation_history, context_history),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
