import uuid
import io
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Query, HTTPException, BackgroundTasks
from pydantic import BaseModel
import pdfplumber

from app.config import Mode, settings
from app.services.rag_service_v2 import RAGService
from app.services.chunking_service import ChunkingService


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

async def process_cvs(job_id: str, files: List[UploadFile], mode: Mode):
    """Background task to process uploaded CVs."""
    chunking_service = ChunkingService()
    rag_service = RAGService(mode)
    
    for file in files:
        try:
            # Read PDF content
            content = await file.read()
            
            # Extract text
            text = extract_text_from_pdf(content, file.filename)
            
            # Create chunks
            cv_id = f"cv_{uuid.uuid4().hex[:8]}"
            chunks = chunking_service.chunk_cv(
                text=text,
                cv_id=cv_id,
                filename=file.filename
            )
            
            # Index chunks
            await rag_service.index_documents(chunks)
            
            jobs[job_id]["processed_files"] += 1
            
        except Exception as e:
            jobs[job_id]["errors"].append(f"{file.filename}: {str(e)}")
    
    jobs[job_id]["status"] = "completed" if not jobs[job_id]["errors"] else "completed_with_errors"


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
    
    # Validate files
    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file.filename}. Only PDF files are accepted."
            )
    
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status": "processing",
        "total_files": len(files),
        "processed_files": 0,
        "errors": []
    }
    
    # Process in background
    background_tasks.add_task(process_cvs, job_id, files, mode)
    
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
    """Delete a CV from the index."""
    rag_service = RAGService(mode)
    success = await rag_service.vector_store.delete_cv(cv_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="CV not found")
    
    return {"success": True, "message": f"CV {cv_id} deleted"}


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
