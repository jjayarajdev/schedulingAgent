"""
FastAPI application for Scheduling Agent backend.

Provides:
- Chat API endpoints
- Health checks
- CORS support
- Error handling
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.api.chat import router as chat_router
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.database import engine

settings = get_settings()
logger = get_logger(__name__)


# ============================================================================
# Lifespan Events
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.

    Handles:
    - Database initialization
    - Resource cleanup
    """
    # Startup
    logger.info(
        "application_starting",
        app_name=settings.app_name,
        environment=settings.environment,
    )

    # Initialize database (tables should already be created via Alembic)
    try:
        from sqlalchemy import text
        async with engine.begin() as conn:
            # Test connection
            await conn.execute(text("SELECT 1"))
            logger.info("database_connection_established")
    except Exception as e:
        logger.error("database_connection_failed", error=str(e))
        # Don't fail startup - let health check report unhealthy

    yield

    # Shutdown
    logger.info("application_shutting_down")

    # Close database connections
    await engine.dispose()
    logger.info("database_connections_closed")


# ============================================================================
# Create FastAPI Application
# ============================================================================


app = FastAPI(
    title="Scheduling Agent API",
    description="Multi-agent scheduling system powered by AWS Bedrock",
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================================
# CORS Middleware
# ============================================================================


# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
        "*",  # Allow all origins for now (restrict in production)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Exception Handlers
# ============================================================================


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors."""
    logger.warning(
        "validation_error",
        path=request.url.path,
        errors=exc.errors(),
    )

    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "body": exc.body,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        error=str(exc),
        error_type=type(exc).__name__,
    )

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc) if settings.debug else "An error occurred",
        },
    )


# ============================================================================
# Include Routers
# ============================================================================


# Include chat API routes
app.include_router(
    chat_router,
    prefix="/api",
    tags=["chat"],
)


# ============================================================================
# Root Endpoint
# ============================================================================


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "environment": settings.environment,
        "status": "running",
    }


@app.get("/api")
async def api_root():
    """API root endpoint."""
    return {
        "name": "Scheduling Agent API",
        "version": "1.0.0",
        "endpoints": {
            "chat": "/api/chat",
            "health": "/api/health",
            "sessions": "/api/sessions/{session_id}",
            "messages": "/api/sessions/{session_id}/messages",
        },
    }


# ============================================================================
# Run Application
# ============================================================================


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level.lower(),
    )
