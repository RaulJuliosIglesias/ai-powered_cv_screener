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
from app.services.rag_service_v2 import RAGService
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


class ChatResponse(BaseModel):
    response: str
    sources: List[dict] = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)


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
    rag_service = RAGService(mode)
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
        rag_service = RAGService(mode)
    except Exception as e:
        logger.error(f"[{job_id}] Service init failed: {e}")
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["errors"].append(str(e))
        return
    
    for filename, content in file_data:
        try:
            # Extract text
            text = extract_text_from_pdf(content, filename)
            logger.info(f"[{job_id}] Extracted {len(text)} chars from {filename}")
            
            # Create CV ID
            cv_id = f"cv_{uuid.uuid4().hex[:8]}"
            
            # Save PDF to disk for later viewing
            pdf_path = PDF_STORAGE_DIR / f"{cv_id}.pdf"
            with open(pdf_path, "wb") as f:
                f.write(content)
            logger.info(f"[{job_id}] Saved PDF to {pdf_path}")
            
            # Chunk the document
            chunks = chunking_service.chunk_cv(text=text, cv_id=cv_id, filename=filename)
            logger.info(f"[{job_id}] Created {len(chunks)} chunks for {filename}")
            
            # Index chunks
            await rag_service.index_documents(chunks)
            
            # Add CV to session (use mode-based manager)
            mgr = get_session_manager(mode)
            mgr.add_cv_to_session(session_id, cv_id, filename, len(chunks))
            
            jobs[job_id]["processed_files"] += 1
            logger.info(f"[{job_id}] Added {filename} to session {session_id}")
            
        except Exception as e:
            logger.error(f"[{job_id}] Error processing {filename}: {e}")
            jobs[job_id]["errors"].append(f"{filename}: {str(e)}")
    
    jobs[job_id]["status"] = "completed" if not jobs[job_id]["errors"] else "completed_with_errors"
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
    
    # Create job
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "processing",
        "session_id": session_id,
        "total_files": len(files),
        "processed_files": 0,
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
    rag_service = RAGService(mode)
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
    
    # Query RAG with session's CVs only - pass total CVs for accurate context
    rag_service = RAGService(mode)
    result = await rag_service.query(request.message, cv_ids=cv_ids, total_cvs_in_session=total_cvs)
    
    # Save assistant message
    mgr.add_message(session_id, "assistant", result.answer, result.sources)
    
    return ChatResponse(
        response=result.answer,
        sources=result.sources,
        metrics=result.metrics
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
    
    mgr = get_session_manager(mode)
    session = mgr.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    cvs = session.get("cvs", []) if isinstance(session, dict) else session.cvs
    if not cvs:
        return {"suggestions": []}
    
    cv_names = [(cv.get("filename", "") if isinstance(cv, dict) else cv.filename).replace('.pdf', '').replace('_', ' ') for cv in cvs]
    num_cvs = len(cvs)
    
    if num_cvs == 1:
        name = cv_names[0]
        suggestions = [
            f"What are {name}'s main technical skills?",
            f"Summarize {name}'s work experience",
            f"Is {name} suitable for a senior position?",
            f"What are {name}'s strongest qualifications?"
        ]
    else:
        # Generic strategic questions (always include 2-3)
        generic_questions = [
            f"Rank all {num_cvs} candidates by years of experience",
            "Who would be the best fit for a leadership/management role?",
            "Which candidates have the strongest technical background?",
            "Compare the education levels of all candidates",
            "Who has experience working in startups vs large companies?",
            "Which candidates show the most career progression?",
            "Who has the best combination of technical and soft skills?",
            f"Create a shortlist of top 3 candidates from the {num_cvs} CVs",
            "Which candidates have remote work experience?",
            "Who has the most diverse skill set?",
        ]
        
        # Pick 2-3 random candidates for specific questions
        sample_names = random.sample(cv_names, min(3, len(cv_names)))
        specific_questions = [
            f"Compare {sample_names[0]} vs {sample_names[1] if len(sample_names) > 1 else sample_names[0]}: who is more experienced?",
        ]
        if len(sample_names) >= 2:
            specific_questions.append(f"Would {sample_names[0]} or {sample_names[1]} be better for a senior role?")
        
        # Combine: 3 generic + 1 specific
        random.shuffle(generic_questions)
        suggestions = generic_questions[:3] + specific_questions[:1]
    
    return {"suggestions": suggestions[:4]}


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
    rag_service = RAGService(mode)
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
    rag_service = RAGService(mode)
    
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
