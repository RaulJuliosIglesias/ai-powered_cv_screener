from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import sys

from app.config import get_settings
from app.api.routes_v2 import router
from app.api.routes_sessions import router as sessions_router
from app.api.routes_sessions_stream import router as sessions_stream_router
from app.api.export_routes import router as export_router
from app.api.v8_routes import router as v8_router
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

# Configure CORS - allow all origins for Railway
# Frontend and backend are on same domain in Railway
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


# Include routers FIRST (before catch-all)
app.include_router(router)
app.include_router(sessions_router)
app.include_router(sessions_stream_router)
app.include_router(export_router)
app.include_router(v8_router)

# Serve static files for Railway deployment
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Check if running in Railway (static dir exists)
STATIC_DIR = "/app/static"
RAILWAY_MODE = os.path.exists(STATIC_DIR) and os.path.exists(f"{STATIC_DIR}/index.html")

if RAILWAY_MODE:
    logger.info(f"Railway mode: Serving static files from {STATIC_DIR}")
    
    # Serve static assets (js, css, etc.)
    if os.path.exists(f"{STATIC_DIR}/assets"):
        app.mount("/assets", StaticFiles(directory=f"{STATIC_DIR}/assets"), name="assets")
    
    # Serve vite.svg and other root static files
    @app.get("/vite.svg")
    async def serve_vite_svg():
        return FileResponse(f"{STATIC_DIR}/vite.svg")
    
    # Serve root index.html for SPA
    @app.get("/", response_class=FileResponse)
    async def serve_spa_root():
        return FileResponse(f"{STATIC_DIR}/index.html", media_type="text/html")

else:
    # Local development - just API info
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
    logger.info(f"Default mode: {settings.default_mode}")
    logger.info(f"CORS origins: {settings.cors_origins_list}")
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
