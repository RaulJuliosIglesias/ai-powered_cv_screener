from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import sys

from app.config import get_settings
from app.api.routes import router
from app.utils.exceptions import CVScreenerException


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger("cv_screener")

# Get settings
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title="CV Screener RAG API",
    description="AI-powered CV screening application using RAG",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(CVScreenerException)
async def cv_screener_exception_handler(request: Request, exc: CVScreenerException):
    """Handle custom CV Screener exceptions."""
    logger.error(f"CVScreenerException: {exc.message}", extra=exc.details)
    return JSONResponse(
        status_code=500,
        content={"detail": exc.message, "error_code": type(exc).__name__},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger.exception(f"Unexpected error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."},
    )


# Include routers
app.include_router(router)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "CV Screener RAG API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting CV Screener API...")
    logger.info(f"CORS origins: {settings.cors_origins_list}")
    logger.info(f"ChromaDB path: {settings.chroma_persist_dir}")
    logger.info("API ready to receive requests")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down CV Screener API...")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )
