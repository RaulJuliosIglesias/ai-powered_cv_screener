from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from typing import List
import uuid
import os
import asyncio
from datetime import datetime
from pathlib import Path
import time

from app.config import get_settings
from app.models.schemas import (
    UploadResponse,
    ProcessingStatusResponse,
    FileStatus,
    CVListResponse,
    CVInfo,
    CVMetadata,
    DeleteCVResponse,
    ChatRequest,
    ChatResponse,
    SourceInfo,
    UsageInfo,
    StatsResponse,
    JobStatus,
    ErrorResponse,
)
from app.api.dependencies import (
    get_pdf_service,
    get_embedding_service,
    get_vector_store,
    get_rag_service,
    get_guardrails_service,
    get_usage_tracker,
    get_query_logger,
    get_rate_limiter,
)
from app.utils.exceptions import CVScreenerException, RateLimitError


router = APIRouter(prefix="/api", tags=["CV Screener"])

# In-memory job storage (use Redis in production)
processing_jobs = {}

settings = get_settings()

# Ensure uploads directory exists
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@router.post("/upload", response_model=UploadResponse)
async def upload_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
):
    """Upload PDF files for processing."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    # Validate files
    valid_files = []
    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file.filename}. Only PDF files are accepted."
            )
        
        # Check file size
        content = await file.read()
        if len(content) > settings.max_file_size_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"File too large: {file.filename}. Maximum size is {settings.max_file_size_mb}MB."
            )
        
        await file.seek(0)
        valid_files.append((file, content))
    
    if len(valid_files) > settings.max_files_per_upload:
        raise HTTPException(
            status_code=400,
            detail=f"Too many files. Maximum is {settings.max_files_per_upload} files per upload."
        )
    
    # Create job
    job_id = str(uuid.uuid4())
    processing_jobs[job_id] = {
        "status": JobStatus.PROCESSING,
        "total_files": len(valid_files),
        "processed_files": 0,
        "failed_files": [],
        "files": [
            {"filename": f[0].filename, "status": JobStatus.PENDING, "error": None}
            for f in valid_files
        ],
        "error_message": None,
    }
    
    # Save files and start processing
    saved_files = []
    for file, content in valid_files:
        file_path = UPLOAD_DIR / f"{job_id}_{file.filename}"
        with open(file_path, "wb") as f:
            f.write(content)
        saved_files.append((file.filename, str(file_path)))
    
    # Start background processing
    background_tasks.add_task(process_files, job_id, saved_files)
    
    return UploadResponse(
        job_id=job_id,
        files_received=len(valid_files),
        status=JobStatus.PROCESSING,
    )


async def process_files(job_id: str, files: List[tuple]):
    """Process uploaded PDF files in the background."""
    pdf_service = get_pdf_service()
    embedding_service = get_embedding_service()
    vector_store = get_vector_store()
    
    job = processing_jobs[job_id]
    
    for i, (filename, file_path) in enumerate(files):
        try:
            # Update file status
            job["files"][i]["status"] = JobStatus.PROCESSING
            
            # Generate CV ID
            cv_id = f"cv_{uuid.uuid4().hex[:8]}"
            
            # Extract and chunk PDF
            extracted_cv = pdf_service.process_cv(file_path, cv_id)
            
            # Generate embeddings
            chunk_texts = [chunk.content for chunk in extracted_cv.chunks]
            embeddings = embedding_service.generate_embeddings_batch(chunk_texts)
            
            # Store in vector database
            vector_store.add_chunks(extracted_cv.chunks, embeddings)
            
            # Update status
            job["files"][i]["status"] = JobStatus.COMPLETED
            job["processed_files"] += 1
            
        except Exception as e:
            job["files"][i]["status"] = JobStatus.FAILED
            job["files"][i]["error"] = str(e)
            job["failed_files"].append(filename)
        
        finally:
            # Clean up uploaded file
            try:
                os.remove(file_path)
            except:
                pass
    
    # Update job status
    if job["failed_files"]:
        if job["processed_files"] == 0:
            job["status"] = JobStatus.FAILED
            job["error_message"] = "All files failed to process"
        else:
            job["status"] = JobStatus.COMPLETED
    else:
        job["status"] = JobStatus.COMPLETED


@router.get("/status/{job_id}", response_model=ProcessingStatusResponse)
async def get_processing_status(job_id: str):
    """Get the status of a processing job."""
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = processing_jobs[job_id]
    
    progress = (job["processed_files"] / job["total_files"] * 100) if job["total_files"] > 0 else 0
    
    return ProcessingStatusResponse(
        job_id=job_id,
        status=job["status"],
        total_files=job["total_files"],
        processed_files=job["processed_files"],
        failed_files=job["failed_files"],
        progress_percent=progress,
        error_message=job["error_message"],
        files=[
            FileStatus(
                filename=f["filename"],
                status=f["status"],
                error=f["error"],
            )
            for f in job["files"]
        ],
    )


@router.get("/cvs", response_model=CVListResponse)
async def list_cvs():
    """List all indexed CVs."""
    vector_store = get_vector_store()
    
    cvs = vector_store.get_all_cvs()
    
    cv_list = [
        CVInfo(
            id=cv["id"],
            filename=cv["filename"],
            indexed_at=datetime.fromisoformat(cv["indexed_at"]) if cv.get("indexed_at") else datetime.now(),
            chunk_count=cv["chunk_count"],
            metadata=CVMetadata(
                name=cv.get("candidate_name"),
                extracted_skills=[],
            ),
        )
        for cv in cvs
    ]
    
    return CVListResponse(total=len(cv_list), cvs=cv_list)


@router.delete("/cvs/{cv_id}", response_model=DeleteCVResponse)
async def delete_cv(cv_id: str):
    """Remove a CV from the index."""
    vector_store = get_vector_store()
    
    # Check if CV exists
    cv = vector_store.get_cv_by_id(cv_id)
    if not cv:
        raise HTTPException(status_code=404, detail="CV not found")
    
    # Delete CV
    deleted_count = vector_store.delete_cv(cv_id)
    
    return DeleteCVResponse(
        success=True,
        message=f"CV removed from index ({deleted_count} chunks deleted)",
    )


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a question and get RAG-powered response."""
    rag_service = get_rag_service()
    guardrails = get_guardrails_service()
    usage_tracker = get_usage_tracker()
    query_logger = get_query_logger()
    rate_limiter = get_rate_limiter()
    vector_store = get_vector_store()
    
    # Check if any CVs are indexed
    stats = vector_store.get_collection_stats()
    if stats["total_cvs"] == 0:
        raise HTTPException(
            status_code=404,
            detail="No CVs indexed. Please upload CVs first."
        )
    
    # Check rate limit
    allowed, wait_time = rate_limiter.check_limit()
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Please wait {wait_time:.1f} seconds."
        )
    
    # Sanitize input
    sanitized_message = guardrails.sanitize_input(request.message)
    
    if not sanitized_message.strip():
        raise HTTPException(status_code=400, detail="Empty message")
    
    try:
        start_time = time.time()
        
        # Query RAG service
        result = await rag_service.query_async(
            sanitized_message,
            request.conversation_id,
        )
        
        latency_ms = (time.time() - start_time) * 1000
        
        # Record usage
        usage_tracker.record(
            operation="query",
            model=settings.llm_model,
            prompt_tokens=result["usage"]["prompt_tokens"],
            completion_tokens=result["usage"]["completion_tokens"],
            latency_ms=latency_ms,
        )
        rate_limiter.record_request(result["usage"]["total_tokens"])
        
        # Log query
        query_logger.log_query(
            query=sanitized_message,
            retrieved_chunks=[],
            response=result["response"],
            sources=[s["filename"] for s in result["sources"]],
            latency_ms=latency_ms,
            usage=result["usage"],
        )
        
        return ChatResponse(
            response=result["response"],
            sources=[
                SourceInfo(
                    cv_id=s["cv_id"],
                    filename=s["filename"],
                    relevance_score=s["relevance_score"],
                    matched_chunk=s["matched_chunk"],
                )
                for s in result["sources"]
            ],
            conversation_id=result["conversation_id"],
            usage=UsageInfo(
                prompt_tokens=result["usage"]["prompt_tokens"],
                completion_tokens=result["usage"]["completion_tokens"],
                total_tokens=result["usage"]["total_tokens"],
                estimated_cost_usd=result["usage"]["estimated_cost_usd"],
            ),
        )
        
    except CVScreenerException as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get usage statistics and monitoring data."""
    usage_tracker = get_usage_tracker()
    vector_store = get_vector_store()
    
    usage_stats = usage_tracker.get_total_stats()
    vector_stats = vector_store.get_collection_stats()
    
    # Estimate vector store size (rough approximation)
    # Each embedding is ~1536 floats * 4 bytes = ~6KB
    size_mb = (vector_stats["total_chunks"] * 6) / 1024
    
    return StatsResponse(
        total_queries=usage_stats["total_requests"],
        total_tokens_used=usage_stats["total_tokens"],
        estimated_total_cost_usd=usage_stats["total_cost_usd"],
        average_response_time_ms=usage_stats["average_latency_ms"],
        cvs_indexed=vector_stats["total_cvs"],
        vector_store_size_mb=size_mb,
    )


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@router.get("/v7/status")
async def get_v7_status():
    """Get status of v7 services (HuggingFace-based enhancements)."""
    try:
        from app.services.v7_integration import get_v7_services
        v7 = get_v7_services()
        return {
            "status": "ok",
            "v7_services": v7.get_status(),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/v7/metrics/ragas")
async def get_ragas_metrics(days: int = 7):
    """
    Get aggregate RAGAS evaluation metrics.
    
    Args:
        days: Number of days to aggregate (default: 7)
        
    Returns:
        Aggregate statistics from RAGAS evaluations
    """
    try:
        from app.services.ragas_evaluation_service import get_ragas_evaluation_service
        evaluator = get_ragas_evaluation_service()
        metrics = await evaluator.get_aggregate_metrics(days=days)
        return {
            "status": "ok",
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/welcome")
async def get_welcome_message():
    """Get the welcome message for new users."""
    rag_service = get_rag_service()
    vector_store = get_vector_store()
    
    stats = vector_store.get_collection_stats()
    
    return {
        "message": rag_service.get_welcome_message(),
        "cvs_indexed": stats["total_cvs"],
    }
