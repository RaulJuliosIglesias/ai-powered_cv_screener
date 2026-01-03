import uuid
import io
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Query, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
import pdfplumber

from app.config import Mode, settings

# Directory to store uploaded PDFs
PDF_STORAGE_DIR = Path("pdf_storage")
PDF_STORAGE_DIR.mkdir(exist_ok=True)

# Mapping of cv_id to PDF file path (in production, use database)
cv_pdf_mapping = {}
from app.services.rag_service_v2 import RAGService
from app.services.chunking_service import ChunkingService
from app.models.sessions import LocalSessionManager
from app.providers.cloud.sessions import SupabaseSessionManager

def get_session_manager(mode: Mode):
    """Get session manager based on mode."""
    if mode == Mode.cloud:
        return SupabaseSessionManager()
    return LocalSessionManager()


router = APIRouter(prefix="/api", tags=["CV Screener"])


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class SourceInfo(BaseModel):
    cv_id: str
    filename: str
    relevance: float


class ChatResponse(BaseModel):
    response: str
    sources: List[SourceInfo]
    conversation_id: str
    metrics: dict
    mode: str


class UploadResponse(BaseModel):
    job_id: str
    files_received: int
    status: str


class StatusResponse(BaseModel):
    job_id: str
    status: str
    total_files: int
    processed_files: int
    errors: List[str]


class CVInfo(BaseModel):
    id: str
    filename: str
    chunk_count: int


class CVListResponse(BaseModel):
    total: int
    cvs: List[CVInfo]


class StatsResponse(BaseModel):
    mode: str
    total_chunks: int
    total_cvs: int
    storage_type: str


# ============================================
# IN-MEMORY JOB TRACKING (use Redis in production)
# ============================================

jobs = {}


# ============================================
# PDF EXTRACTION
# ============================================

def extract_text_from_pdf(content: bytes, filename: str) -> str:
    """Extract text from PDF bytes."""
    text_parts = []
    
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    
    full_text = "\n\n".join(text_parts)
    
    if not full_text.strip():
        raise ValueError(f"Could not extract text from {filename}")
    
    # Clean text
    import re
    full_text = re.sub(r'\n{3,}', '\n\n', full_text)
    full_text = re.sub(r' {2,}', ' ', full_text)
    
    return full_text.strip()


# ============================================
# BACKGROUND TASK
# ============================================

import logging
logger = logging.getLogger(__name__)

async def process_cvs(job_id: str, file_data: List[tuple], mode: Mode):
    """Background task to process uploaded CVs.
    
    Args:
        job_id: The job ID for tracking
        file_data: List of tuples (filename, content_bytes)
        mode: Processing mode (local/cloud)
    """
    logger.info(f"[{job_id}] Starting processing of {len(file_data)} files")
    
    try:
        chunking_service = ChunkingService()
        logger.info(f"[{job_id}] ChunkingService created")
        
        rag_service = RAGService(mode)
        logger.info(f"[{job_id}] RAGService created for mode {mode}")
    except Exception as e:
        logger.error(f"[{job_id}] Failed to initialize services: {e}")
        jobs[job_id]["errors"].append(f"Service init failed: {str(e)}")
        jobs[job_id]["status"] = "failed"
        return
    
    for filename, content in file_data:
        logger.info(f"[{job_id}] Processing file: {filename} ({len(content)} bytes)")
        try:
            # Extract text
            text = extract_text_from_pdf(content, filename)
            logger.info(f"[{job_id}] Extracted {len(text)} chars from {filename}")
            
            # Create chunks
            cv_id = f"cv_{uuid.uuid4().hex[:8]}"
            chunks = chunking_service.chunk_cv(
                text=text,
                cv_id=cv_id,
                filename=filename
            )
            logger.info(f"[{job_id}] Created {len(chunks)} chunks for {filename}")
            
            # Save PDF to disk
            pdf_path = PDF_STORAGE_DIR / f"{cv_id}.pdf"
            with open(pdf_path, "wb") as f:
                f.write(content)
            cv_pdf_mapping[cv_id] = str(pdf_path)
            logger.info(f"[{job_id}] Saved PDF to {pdf_path}")
            
            # Index chunks
            await rag_service.index_documents(chunks)
            logger.info(f"[{job_id}] Indexed chunks for {filename}")
            
            jobs[job_id]["processed_files"] += 1
            
        except Exception as e:
            logger.error(f"[{job_id}] Error processing {filename}: {e}")
            jobs[job_id]["errors"].append(f"{filename}: {str(e)}")
    
    jobs[job_id]["status"] = "completed" if not jobs[job_id]["errors"] else "completed_with_errors"
    logger.info(f"[{job_id}] Processing complete. Status: {jobs[job_id]['status']}")


# ============================================
# ENDPOINTS
# ============================================

@router.post("/upload", response_model=UploadResponse)
async def upload_cvs(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    mode: Mode = Query(default=settings.default_mode)
):
    """Upload CV PDFs for processing."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    # Validate files and read content BEFORE sending response
    file_data = []
    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file.filename}. Only PDF files are accepted."
            )
        # Read file content now (before background task)
        content = await file.read()
        file_data.append((file.filename, content))
    
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "processing",
        "total_files": len(files),
        "processed_files": 0,
        "errors": []
    }
    
    # Process in background with pre-read file data
    background_tasks.add_task(process_cvs, job_id, file_data, mode)
    
    return UploadResponse(
        job_id=job_id,
        files_received=len(files),
        status="processing"
    )


@router.get("/status/{job_id}", response_model=StatusResponse)
async def get_status(job_id: str):
    """Check processing status."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    return StatusResponse(
        job_id=job_id,
        status=job["status"],
        total_files=job["total_files"],
        processed_files=job["processed_files"],
        errors=job["errors"]
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    mode: Mode = Query(default=settings.default_mode)
):
    """Send a question and get RAG-powered response."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    rag_service = RAGService(mode)
    
    # Check if there are any CVs indexed
    stats = await rag_service.get_stats()
    if stats.get("total_cvs", 0) == 0:
        raise HTTPException(
            status_code=404,
            detail="No CVs indexed. Please upload CVs first."
        )
    
    result = await rag_service.query(request.message)
    
    return ChatResponse(
        response=result.answer,
        sources=[SourceInfo(**s) for s in result.sources],
        conversation_id=request.conversation_id or str(uuid.uuid4()),
        metrics=result.metrics,
        mode=result.mode
    )


@router.get("/cvs", response_model=CVListResponse)
async def list_cvs(mode: Mode = Query(default=settings.default_mode)):
    """List all indexed CVs."""
    rag_service = RAGService(mode)
    cvs = await rag_service.vector_store.list_cvs()
    return CVListResponse(
        total=len(cvs),
        cvs=[CVInfo(**cv) for cv in cvs]
    )


@router.delete("/cvs/{cv_id}")
async def delete_cv(
    cv_id: str,
    mode: Mode = Query(default=settings.default_mode)
):
    """Delete a CV from the index and remove from all sessions."""
    rag_service = RAGService(mode)
    success = await rag_service.vector_store.delete_cv(cv_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="CV not found")
    
    # Also remove CV from all sessions that reference it
    mgr = get_session_manager(mode)
    sessions = mgr.list_sessions()
    sessions_updated = 0
    for s in sessions:
        session_id = s.get("id") if isinstance(s, dict) else s.id
        session = mgr.get_session(session_id)
        if session:
            cvs = session.get("cvs", []) if isinstance(session, dict) else session.cvs
            if any((cv.get("id") if isinstance(cv, dict) else cv.id) == cv_id for cv in cvs):
                mgr.remove_cv_from_session(session_id, cv_id)
                sessions_updated += 1
    
    # Delete PDF file if exists
    if cv_id in cv_pdf_mapping:
        try:
            Path(cv_pdf_mapping[cv_id]).unlink(missing_ok=True)
            del cv_pdf_mapping[cv_id]
        except Exception:
            pass
    
    return {"success": True, "message": f"CV {cv_id} deleted", "sessions_updated": sessions_updated}


@router.get("/stats", response_model=StatsResponse)
async def get_stats(mode: Mode = Query(default=settings.default_mode)):
    """Get system statistics."""
    rag_service = RAGService(mode)
    stats = await rag_service.get_stats()
    return StatsResponse(**stats)


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "default_mode": settings.default_mode.value
    }


# ============================================
# MODEL SELECTION ENDPOINTS
# ============================================

@router.get("/models")
async def get_models():
    """Get available LLM models from OpenRouter."""
    from app.providers.cloud.llm import fetch_openrouter_models, get_current_model
    models = await fetch_openrouter_models()
    return {
        "models": models,
        "current": get_current_model()
    }


@router.post("/models/{model_id:path}")
async def set_model(model_id: str):
    """Set the current LLM model."""
    from app.providers.cloud.llm import set_current_model, get_current_model
    
    success = set_current_model(model_id)
    if not success:
        raise HTTPException(status_code=400, detail=f"Invalid model: {model_id}")
    
    return {"success": True, "current": get_current_model()}


@router.delete("/cvs")
async def delete_all_cvs(mode: Mode = Query(default=settings.default_mode)):
    """Delete all CVs from the index."""
    rag_service = RAGService(mode)
    
    # Get all CVs and delete them
    cvs = await rag_service.vector_store.list_cvs()
    deleted = 0
    for cv in cvs:
        cv_id = cv["id"]
        if await rag_service.vector_store.delete_cv(cv_id):
            # Also delete PDF file
            if cv_id in cv_pdf_mapping:
                try:
                    Path(cv_pdf_mapping[cv_id]).unlink(missing_ok=True)
                    del cv_pdf_mapping[cv_id]
                except Exception:
                    pass
            deleted += 1
    
    return {"success": True, "deleted": deleted}


@router.get("/cvs/{cv_id}/pdf")
async def get_cv_pdf(cv_id: str):
    """Get the PDF file for a CV."""
    # First check mapping
    if cv_id in cv_pdf_mapping:
        pdf_path = Path(cv_pdf_mapping[cv_id])
        if pdf_path.exists():
            return FileResponse(
                path=str(pdf_path),
                media_type="application/pdf",
                filename=pdf_path.name
            )
    
    # Try to find by cv_id in storage directory
    pdf_path = PDF_STORAGE_DIR / f"{cv_id}.pdf"
    if pdf_path.exists():
        cv_pdf_mapping[cv_id] = str(pdf_path)
        return FileResponse(
            path=str(pdf_path),
            media_type="application/pdf",
            filename=pdf_path.name
        )
    
    raise HTTPException(status_code=404, detail=f"PDF not found for CV {cv_id}")
