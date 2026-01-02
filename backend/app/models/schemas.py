from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Upload Schemas
class UploadResponse(BaseModel):
    job_id: str
    files_received: int
    status: JobStatus


class FileStatus(BaseModel):
    filename: str
    status: JobStatus
    error: Optional[str] = None


class ProcessingStatusResponse(BaseModel):
    job_id: str
    status: JobStatus
    total_files: int
    processed_files: int
    failed_files: List[str] = []
    progress_percent: float
    error_message: Optional[str] = None
    files: List[FileStatus] = []


# CV Schemas
class CVMetadata(BaseModel):
    name: Optional[str] = None
    extracted_skills: List[str] = []


class CVInfo(BaseModel):
    id: str
    filename: str
    indexed_at: datetime
    chunk_count: int
    metadata: CVMetadata


class CVListResponse(BaseModel):
    total: int
    cvs: List[CVInfo]


class DeleteCVResponse(BaseModel):
    success: bool
    message: str


# Chat Schemas
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_id: Optional[str] = None


class SourceInfo(BaseModel):
    cv_id: str
    filename: str
    relevance_score: float
    matched_chunk: str


class UsageInfo(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float


class ChatResponse(BaseModel):
    response: str
    sources: List[SourceInfo]
    conversation_id: str
    usage: UsageInfo


# Stats Schemas
class StatsResponse(BaseModel):
    total_queries: int
    total_tokens_used: int
    estimated_total_cost_usd: float
    average_response_time_ms: float
    cvs_indexed: int
    vector_store_size_mb: float


# Error Schemas
class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
