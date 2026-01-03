"""Session management API routes."""
import uuid
import io
import logging
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, File, UploadFile, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import pdfplumber

from app.config import settings, Mode

# Directory to store uploaded PDFs - in project root /storage/
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PDF_STORAGE_DIR = _PROJECT_ROOT / "storage"
PDF_STORAGE_DIR.mkdir(exist_ok=True)
from app.models.sessions import session_manager, Session, ChatMessage, CVInfo
from app.providers.cloud.sessions import supabase_session_manager
from app.providers.factory import ProviderFactory
from app.services.chunking_service import ChunkingService


def get_session_manager(mode: Mode):
    """Get the appropriate session manager based on mode."""
    if mode == Mode.CLOUD:
        return supabase_session_manager
    return session_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def extract_text_from_pdf(content: bytes, filename: str) -> str:
    """Extract text from PDF bytes."""
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            text_parts = []
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            return "\n".join(text_parts)
    except Exception as e:
        logger.error(f"Failed to extract text from {filename}: {e}")
        raise ValueError(f"Could not extract text from {filename}")


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class CreateSessionRequest(BaseModel):
    name: str
    description: str = ""


class UpdateSessionRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class SessionResponse(BaseModel):
    id: str
    name: str
    description: str
    cv_count: int
    message_count: int
    created_at: str
    updated_at: str


class SessionDetailResponse(BaseModel):
    id: str
    name: str
    description: str
    cvs: List[CVInfo]
    messages: List[ChatMessage]
    created_at: str
    updated_at: str


class SessionListResponse(BaseModel):
    sessions: List[SessionResponse]
    total: int


class ChatRequest(BaseModel):
    message: str
    understanding_model: Optional[str] = None  # Model for query understanding (Step 1)
    reranking_model: Optional[str] = None      # Model for re-ranking (Step 2)
    reranking_enabled: Optional[bool] = True   # Enable/disable re-ranking
    generation_model: Optional[str] = None     # Model for response generation (Step 3)
    verification_model: Optional[str] = None   # Model for verification (Step 4)
    verification_enabled: Optional[bool] = True  # Enable/disable verification


class ChatResponse(BaseModel):
    response: str
    sources: List[dict] = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)
    confidence_score: Optional[float] = None
    guardrail_passed: Optional[bool] = None
    query_understanding: Optional[dict] = None  # Info about how query was understood
    reranking_info: Optional[dict] = None       # Re-ranking step info
    verification_info: Optional[dict] = None    # Verification step info


class UploadResponse(BaseModel):
    job_id: str
    files_received: int
    status: str


# Job tracking
jobs = {}


# ============================================
# SESSION CRUD ENDPOINTS
# ============================================

@router.get("", response_model=SessionListResponse)
async def list_sessions(mode: Mode = Query(default=settings.default_mode)):
    """List all sessions."""
    mgr = get_session_manager(mode)
    sessions = mgr.list_sessions()
    
    # Handle both local (Session objects) and cloud (dicts) formats
    result = []
    for s in sessions:
        if isinstance(s, dict):
            result.append(SessionResponse(
                id=s["id"],
                name=s["name"],
                description=s.get("description", ""),
                cv_count=s.get("cv_count", len(s.get("cvs", []))),
                message_count=s.get("message_count", len(s.get("messages", []))),
                created_at=s["created_at"],
                updated_at=s["updated_at"]
            ))
        else:
            result.append(SessionResponse(
                id=s.id,
                name=s.name,
                description=s.description,
                cv_count=len(s.cvs),
                message_count=len(s.messages),
                created_at=s.created_at,
                updated_at=s.updated_at
            ))
    
    return SessionListResponse(sessions=result, total=len(result))


@router.post("", response_model=SessionDetailResponse)
async def create_session(request: CreateSessionRequest, mode: Mode = Query(default=settings.default_mode)):
    """Create a new session."""
    mgr = get_session_manager(mode)
    session = mgr.create_session(request.name, request.description)
    
    if isinstance(session, dict):
        return SessionDetailResponse(
            id=session["id"],
            name=session["name"],
            description=session.get("description", ""),
            cvs=session.get("cvs", []),
            messages=session.get("messages", []),
            created_at=session["created_at"],
            updated_at=session["updated_at"]
        )
    return SessionDetailResponse(
        id=session.id,
        name=session.name,
        description=session.description,
        cvs=session.cvs,
        messages=session.messages,
        created_at=session.created_at,
        updated_at=session.updated_at
    )


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(session_id: str, mode: Mode = Query(default=settings.default_mode)):
    """Get a session by ID."""
    mgr = get_session_manager(mode)
    session = mgr.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if isinstance(session, dict):
        return SessionDetailResponse(
            id=session["id"],
            name=session["name"],
            description=session.get("description", ""),
            cvs=session.get("cvs", []),
            messages=session.get("messages", []),
            created_at=session["created_at"],
            updated_at=session["updated_at"]
        )
    return SessionDetailResponse(
        id=session.id,
        name=session.name,
        description=session.description,
        cvs=session.cvs,
        messages=session.messages,
        created_at=session.created_at,
        updated_at=session.updated_at
    )


@router.put("/{session_id}", response_model=SessionDetailResponse)
async def update_session(session_id: str, request: UpdateSessionRequest, mode: Mode = Query(default=settings.default_mode)):
    """Update a session."""
    mgr = get_session_manager(mode)
    session = mgr.update_session(session_id, request.name, request.description)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if isinstance(session, dict):
        return SessionDetailResponse(
            id=session["id"],
            name=session["name"],
            description=session.get("description", ""),
            cvs=session.get("cvs", []),
            messages=session.get("messages", []),
            created_at=session["created_at"],
            updated_at=session["updated_at"]
        )
    return SessionDetailResponse(
        id=session.id,
        name=session.name,
        description=session.description,
        cvs=session.cvs,
        messages=session.messages,
        created_at=session.created_at,
        updated_at=session.updated_at
    )


@router.delete("/{session_id}")
async def delete_session(session_id: str, mode: Mode = Query(default=settings.default_mode)):
    """Delete a session and optionally its CVs from vector store."""
    mgr = get_session_manager(mode)
    session = mgr.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Delete CVs from vector store
    rag_service = ProviderFactory.get_rag_service(mode=mode)
    cvs = session.get("cvs", []) if isinstance(session, dict) else session.cvs
    for cv in cvs:
        cv_id = cv.get("id") if isinstance(cv, dict) else cv.id
        await rag_service.vector_store.delete_cv(cv_id)
    
    # Delete session
    mgr.delete_session(session_id)
    return {"success": True, "message": f"Session {session_id} deleted"}


# ============================================
# CV MANAGEMENT ENDPOINTS
# ============================================

async def process_cvs_for_session(
    job_id: str,
    session_id: str,
    file_data: List[tuple],
    mode: Mode
):
    """Background task to process CVs and add them to a session."""
    logger.info(f"[{job_id}] Processing {len(file_data)} CVs for session {session_id}")
    
    try:
        chunking_service = ChunkingService()
        rag_service = ProviderFactory.get_rag_service(mode=mode)
    except Exception as e:
        logger.error(f"[{job_id}] Service init failed: {e}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["errors"].append(str(e))
        return
    
    for idx, (filename, content) in enumerate(file_data):
        try:
            # Update current file being processed
            jobs[job_id]["current_file"] = filename
            jobs[job_id]["current_phase"] = "extracting"
            
            # Extract text
            text = extract_text_from_pdf(content, filename)
            logger.info(f"[{job_id}] Extracted {len(text)} chars from {filename}")
            
            # Create CV ID
            cv_id = f"cv_{uuid.uuid4().hex[:8]}"
            
            # Save PDF to disk for later viewing
            jobs[job_id]["current_phase"] = "saving"
            pdf_path = PDF_STORAGE_DIR / f"{cv_id}.pdf"
            with open(pdf_path, "wb") as f:
                f.write(content)
            logger.info(f"[{job_id}] Saved PDF to {pdf_path}")
            
            # Chunk the document
            jobs[job_id]["current_phase"] = "chunking"
            chunks = chunking_service.chunk_cv(text=text, cv_id=cv_id, filename=filename)
            logger.info(f"[{job_id}] Created {len(chunks)} chunks for {filename}")
            
            # Index chunks (create embeddings)
            jobs[job_id]["current_phase"] = "embedding"
            await rag_service.index_documents(chunks)
            
            # Add CV to session (use mode-based manager)
            jobs[job_id]["current_phase"] = "indexing"
            mgr = get_session_manager(mode)
            mgr.add_cv_to_session(session_id, cv_id, filename, len(chunks))
            
            # Mark file as completed
            jobs[job_id]["processed_files"] += 1
            jobs[job_id]["current_phase"] = "done"
            logger.info(f"[{job_id}] Completed {idx + 1}/{len(file_data)}: {filename}")
            
        except Exception as e:
            logger.error(f"[{job_id}] Error processing {filename}: {e}")
            jobs[job_id]["errors"].append(f"{filename}: {str(e)}")
            jobs[job_id]["processed_files"] += 1  # Count as processed even if failed
    
    jobs[job_id]["status"] = "completed" if not jobs[job_id]["errors"] else "completed_with_errors"
    jobs[job_id]["current_file"] = None
    jobs[job_id]["current_phase"] = None
    logger.info(f"[{job_id}] Processing complete. Status: {jobs[job_id]['status']}")


@router.post("/{session_id}/cvs", response_model=UploadResponse)
async def upload_cvs_to_session(
    session_id: str,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    mode: Mode = Query(default=settings.default_mode)
):
    """Upload CVs to a session."""
    mgr = get_session_manager(mode)
    session = mgr.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    # Read file data before background task
    file_data = []
    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"Invalid file type: {file.filename}")
        content = await file.read()
        file_data.append((file.filename, content))
    
    # Create job with detailed progress tracking
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "processing",
        "session_id": session_id,
        "total_files": len(files),
        "processed_files": 0,
        "current_file": None,
        "current_phase": None,  # extracting, saving, chunking, embedding, indexing, done
        "errors": []
    }
    
    # Process in background
    background_tasks.add_task(process_cvs_for_session, job_id, session_id, file_data, mode)
    
    return UploadResponse(
        job_id=job_id,
        files_received=len(files),
        status="processing"
    )


@router.get("/{session_id}/cvs/status/{job_id}")
async def get_upload_status(session_id: str, job_id: str):
    """Get upload job status."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]


@router.delete("/{session_id}/cvs/{cv_id}")
async def remove_cv_from_session(
    session_id: str,
    cv_id: str,
    mode: Mode = Query(default=settings.default_mode)
):
    """Remove a CV from a session and delete from vector store."""
    mgr = get_session_manager(mode)
    session = mgr.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Check if CV exists in session
    cvs = session.get("cvs", []) if isinstance(session, dict) else session.cvs
    cv_exists = any((cv.get("id") if isinstance(cv, dict) else cv.id) == cv_id for cv in cvs)
    if not cv_exists:
        raise HTTPException(status_code=404, detail="CV not found in session")
    
    # Delete from vector store
    rag_service = ProviderFactory.get_rag_service(mode=mode)
    await rag_service.vector_store.delete_cv(cv_id)
    
    # Remove from session
    mgr.remove_cv_from_session(session_id, cv_id)
    
    return {"success": True, "message": f"CV {cv_id} removed from session"}


# ============================================
# CHAT ENDPOINTS
# ============================================

@router.post("/{session_id}/chat", response_model=ChatResponse)
async def chat_in_session(
    session_id: str,
    request: ChatRequest,
    mode: Mode = Query(default=settings.default_mode)
):
    """Send a chat message in a session context (queries only session's CVs)."""
    mgr = get_session_manager(mode)
    session = mgr.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    cvs = session.get("cvs", []) if isinstance(session, dict) else session.cvs
    if not cvs:
        raise HTTPException(status_code=400, detail="No CVs in this session. Please upload CVs first.")
    
    # Get CV IDs for this session
    cv_ids = mgr.get_cv_ids_for_session(session_id)
    total_cvs = len(cvs)
    
    # Save user message
    mgr.add_message(session_id, "user", request.message)
    
    # Query RAG with session's CVs only - pass session_id for logging
    # Use custom models if provided, otherwise use defaults
    # Import RAGServiceV3 directly to pass all pipeline parameters
    from app.services.rag_service_v3 import RAGServiceV3
    
    rag_service = RAGServiceV3(
        mode=mode,
        understanding_model=request.understanding_model,
        reranking_model=request.reranking_model,
        generation_model=request.generation_model,
        verification_model=request.verification_model,
        reranking_enabled=request.reranking_enabled if request.reranking_enabled is not None else True,
        verification_enabled=request.verification_enabled if request.verification_enabled is not None else True
    )
    result = await rag_service.query(
        question=request.message, 
        cv_ids=cv_ids,
        session_id=session_id,
        total_cvs_in_session=total_cvs
    )
    
    # Save assistant message
    mgr.add_message(session_id, "assistant", result.answer, result.sources)
    
    # Include query understanding info in response
    query_understanding_info = None
    if hasattr(result, 'query_understanding') and result.query_understanding:
        query_understanding_info = {
            "understood_query": result.query_understanding.get("understood_query"),
            "query_type": result.query_understanding.get("query_type"),
            "requirements": result.query_understanding.get("requirements", [])
        }
    
    # Include reranking info
    reranking_info = None
    if hasattr(result, 'reranking_info') and result.reranking_info:
        reranking_info = result.reranking_info
    
    # Include verification info
    verification_info = None
    if hasattr(result, 'verification_info') and result.verification_info:
        verification_info = result.verification_info
    
    return ChatResponse(
        response=result.answer,
        sources=result.sources,
        metrics=result.metrics,
        confidence_score=result.confidence_score,
        guardrail_passed=result.guardrail_passed,
        query_understanding=query_understanding_info,
        reranking_info=reranking_info,
        verification_info=verification_info
    )


@router.delete("/{session_id}/chat")
async def clear_chat_history(session_id: str, mode: Mode = Query(default=settings.default_mode)):
    """Clear chat history for a session."""
    mgr = get_session_manager(mode)
    if not mgr.clear_messages(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "message": "Chat history cleared"}


@router.get("/{session_id}/suggestions")
async def get_suggested_questions(
    session_id: str,
    mode: Mode = Query(default=settings.default_mode)
):
    """Generate suggested questions based on session's CVs."""
    import random
    import re
    
    def extract_name(filename: str) -> str:
        """Extract readable name from filename like '8b292e4e_Ethan_James_Carter_...'"""
        # Remove .pdf extension
        name = filename.replace('.pdf', '')
        # Remove leading hash/ID (8 hex chars followed by underscore)
        name = re.sub(r'^[a-f0-9]{8}_', '', name)
        # Replace underscores with spaces
        name = name.replace('_', ' ')
        # Take only first 2-3 words (the person's name, not the job title)
        parts = name.split()
        if len(parts) >= 3:
            # Check if 3rd word looks like a name (capitalized, not a job word)
            job_words = {'Senior', 'Junior', 'Lead', 'Head', 'Chief', 'Manager', 'Director', 'Specialist', 'Engineer', 'Developer', 'Designer', 'Analyst'}
            if parts[2] not in job_words and parts[2][0].isupper():
                return ' '.join(parts[:3])
            return ' '.join(parts[:2])
        return ' '.join(parts[:2]) if len(parts) >= 2 else name[:20]
    
    mgr = get_session_manager(mode)
    session = mgr.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    cvs = session.get("cvs", []) if isinstance(session, dict) else session.cvs
    if not cvs:
        return {"suggestions": []}
    
    # Extract clean names from filenames
    cv_names = [extract_name(cv.get("filename", "") if isinstance(cv, dict) else cv.filename) for cv in cvs]
    num_cvs = len(cvs)
    
    if num_cvs == 1:
        name = cv_names[0]
        suggestions = [
            f"What are {name}'s main skills?",
            f"Summarize {name}'s experience",
            f"Is {name} suitable for a senior role?",
            f"What are {name}'s qualifications?"
        ]
    else:
        # Generic strategic questions only
        generic_questions = [
            f"Rank all {num_cvs} candidates by experience",
            "Who is best for a leadership role?",
            "Who has the strongest technical skills?",
            "Compare education levels",
            "Who shows the most career growth?",
            "Who has startup experience?",
            f"Create a top 3 shortlist from {num_cvs} candidates",
            "Who has the most diverse skill set?",
            "Compare years of experience",
            "Who would fit a senior position?",
        ]
        
        random.shuffle(generic_questions)
        suggestions = generic_questions[:4]
    
    return {"suggestions": suggestions}


# ============================================
# MESSAGE MANAGEMENT ENDPOINTS
# ============================================

@router.delete("/{session_id}/messages/{message_index}")
async def delete_message(
    session_id: str,
    message_index: int,
    mode: Mode = Query(default=settings.default_mode)
):
    """Delete a specific message from a session by index."""
    mgr = get_session_manager(mode)
    session = mgr.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = session.get("messages", []) if isinstance(session, dict) else session.messages
    if message_index < 0 or message_index >= len(messages):
        raise HTTPException(status_code=404, detail="Message not found")
    
    success = mgr.delete_message(session_id, message_index)
    if success:
        return {"success": True, "message": f"Message {message_index} deleted"}
    raise HTTPException(status_code=500, detail="Failed to delete message")


@router.delete("/{session_id}/messages")
async def delete_messages_from(
    session_id: str,
    from_index: int = Query(..., description="Delete all messages from this index onwards"),
    mode: Mode = Query(default=settings.default_mode)
):
    """Delete all messages from a specific index onwards (useful for regenerating responses)."""
    mgr = get_session_manager(mode)
    session = mgr.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    count = mgr.delete_messages_from(session_id, from_index)
    return {"success": True, "deleted": count, "message": f"Deleted {count} messages"}


# ============================================
# DATABASE MANAGEMENT ENDPOINTS
# ============================================

@router.delete("/{session_id}/cvs")
async def clear_session_cvs(
    session_id: str,
    mode: Mode = Query(default=settings.default_mode)
):
    """Delete all CVs from a session and their embeddings."""
    mgr = get_session_manager(mode)
    session = mgr.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    cvs = session.get("cvs", []) if isinstance(session, dict) else session.cvs
    if not cvs:
        return {"success": True, "deleted": 0, "message": "No CVs to delete"}
    
    # Delete from vector store
    rag_service = ProviderFactory.get_rag_service(mode=mode)
    deleted = 0
    for cv in cvs:
        cv_id = cv.get("id") if isinstance(cv, dict) else cv.id
        await rag_service.vector_store.delete_cv(cv_id)
        mgr.remove_cv_from_session(session_id, cv_id)
        deleted += 1
    
    return {"success": True, "deleted": deleted, "message": f"Deleted {deleted} CVs from session"}


@router.delete("/database/all-cvs")
async def delete_all_cvs_from_database(
    mode: Mode = Query(default=settings.default_mode)
):
    """Delete ALL CVs from the entire database (use with caution)."""
    rag_service = ProviderFactory.get_rag_service(mode=mode)
    
    # Delete all embeddings
    success = await rag_service.vector_store.delete_all_cvs()
    
    # Clear all session CVs
    mgr = get_session_manager(mode)
    sessions = mgr.list_sessions()
    for s in sessions:
        session_id = s.get("id") if isinstance(s, dict) else s.id
        session = mgr.get_session(session_id)
        if session:
            cvs = session.get("cvs", []) if isinstance(session, dict) else session.cvs
            for cv in cvs:
                cv_id = cv.get("id") if isinstance(cv, dict) else cv.id
                mgr.remove_cv_from_session(session_id, cv_id)
    
    return {"success": success, "message": "All CVs deleted from database"}
