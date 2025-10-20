"""
Main FastAPI Application - Lightweight but Production-Ready
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time
import sys

from app.config import settings
from app.data_loader import data_manager
from app.routes import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle - startup and shutdown
    """
    # Startup
    logger.info(f"Starting {settings.api_title} v{settings.api_version}")

    # Load CSV data into memory
    try:
        data_manager.initialize()
        logger.info("Data loaded successfully")
    except Exception as e:
        logger.error(f"Failed to initialize data: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down application")


# Create FastAPI application
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="Mini Project: LLM Observability Platform",
    lifespan=lifespan,
    docs_url=f"{settings.api_prefix}/docs",
    redoc_url=f"{settings.api_prefix}/redoc",
    openapi_url=f"{settings.api_prefix}/openapi.json",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Custom middleware for logging and performance monitoring
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests and add performance headers"""
    start_time = time.time()

    # Log request
    logger.info(f"{request.method} {request.url.path}")

    # Process request
    response = await call_next(request)

    # Add performance header
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)

    # Log response
    logger.info(
        f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s"
    )

    return response


# Exception handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Custom 404 handler"""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "The requested resource was not found",
            "path": str(request.url.path),
        },
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Custom 500 handler"""
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
        },
    )


# Include API routes
app.include_router(router, prefix=settings.api_prefix)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "status": "running",
        "docs": f"{settings.api_prefix}/docs",
        "endpoints": {
            "dashboard": f"{settings.api_prefix}/dashboard/stats",
            "experiments": f"{settings.api_prefix}/experiments",
            "search": f"{settings.api_prefix}/search",
            "health": f"{settings.api_prefix}/health",
        },
    }


# Additional monitoring endpoint
@app.get("/api/v1/status")
async def status():
    """System status endpoint"""
    return {
        "status": "operational",
        "data_loaded": data_manager._initialized,
        "experiments_count": (
            len(data_manager.experiments_df) if data_manager._initialized else 0
        ),
        "trials_count": len(data_manager.trials_df) if data_manager._initialized else 0,
        "runs_count": len(data_manager.runs_df) if data_manager._initialized else 0,
        "version": settings.api_version,
    }


if __name__ == "__main__":
    import uvicorn

    # Run with uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level="info",
    )
