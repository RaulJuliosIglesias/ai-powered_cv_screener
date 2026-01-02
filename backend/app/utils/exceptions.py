from typing import Optional


class CVScreenerException(Exception):
    """Base exception for CV Screener application."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class PDFExtractionError(CVScreenerException):
    """Raised when PDF text extraction fails."""
    pass


class EmbeddingError(CVScreenerException):
    """Raised when embedding generation fails."""
    pass


class VectorStoreError(CVScreenerException):
    """Raised when vector store operations fail."""
    pass


class RAGError(CVScreenerException):
    """Raised when RAG pipeline fails."""
    pass


class ValidationError(CVScreenerException):
    """Raised when input validation fails."""
    pass


class RateLimitError(CVScreenerException):
    """Raised when rate limit is exceeded."""
    pass


class FileUploadError(CVScreenerException):
    """Raised when file upload fails."""
    pass
