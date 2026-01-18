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
# Note: credentials=False when using wildcard origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
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
from fastapi.responses import HTMLResponse

STATIC_DIR = "/app/static"
RAILWAY_MODE = os.path.exists(STATIC_DIR) and os.path.exists(f"{STATIC_DIR}/index.html")

if RAILWAY_MODE:
    logger.info(f"Railway mode: Serving static files from {STATIC_DIR}")
    
    # Serve static assets
    if os.path.exists(f"{STATIC_DIR}/assets"):
        app.mount("/assets", StaticFiles(directory=f"{STATIC_DIR}/assets"), name="assets")
    
    # Serve root with SPA routing
    @app.get("/", response_class=HTMLResponse)
    async def serve_spa_root():
        try:
            with open(f"{STATIC_DIR}/index.html", 'r', encoding='utf-8') as f:
                return HTMLResponse(content=f.read())
        except Exception as e:
            logger.error(f"Error serving index.html: {e}")
            return HTMLResponse(content=f"<h1>Error loading app</h1>", status_code=500)
    
    # SPA fallback for all non-API routes
    @app.get("/{full_path:path}", response_class=HTMLResponse)
    async def serve_spa_fallback(full_path: str):
        # Skip API routes
        if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("redoc"):
            return {"detail": "Not Found"}
        
        # Try static file first
        file_path = f"{STATIC_DIR}/{full_path}"
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        
        # Fallback to index.html for SPA routing
        try:
            with open(f"{STATIC_DIR}/index.html", 'r', encoding='utf-8') as f:
                return HTMLResponse(content=f.read())
        except Exception as e:
            logger.error(f"Error serving SPA fallback: {e}")
            return HTMLResponse(content=f"<h1>Error loading app</h1>", status_code=500)
else:
    # Local development - API info
    @app.get("/")
    async def root():
        return {"status": "ok", "message": "CV Screener API is running"}


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
