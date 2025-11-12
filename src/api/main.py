"""
KMS 2.5 FastAPI Application

Main FastAPI application for semantic search and case retrieval.

Task Reference: Phase 3, Task 3.1
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import time
import uuid

# TODO: Import routes
# from .routes import search, cases, health

# TODO: Import middleware
# from .middleware import auth, logging, rate_limiting


# Initialize FastAPI app
app = FastAPI(
    title="KMS 2.5 Vector Search API",
    description="Semantic search API for HPE support cases",
    version="2.5.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID to each request for tracing"""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id

    return response


# Logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing"""
    logger = logging.getLogger(__name__)

    start_time = time.time()
    logger.info(f"Request: {request.method} {request.url.path}")

    response = await call_next(request)

    duration = time.time() - start_time
    logger.info(
        f"Response: {response.status_code} "
        f"Duration: {duration:.3f}s "
        f"RequestID: {request.state.request_id}"
    )

    return response


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger = logging.getLogger(__name__)
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "request_id": getattr(request.state, "request_id", None)
        }
    )


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize connections and resources on startup"""
    logger = logging.getLogger(__name__)
    logger.info("Starting KMS 2.5 API server")

    # TODO: Initialize Weaviate connection
    # TODO: Load configuration
    # TODO: Initialize metrics collection


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger = logging.getLogger(__name__)
    logger.info("Shutting down KMS 2.5 API server")

    # TODO: Close Weaviate connection
    # TODO: Flush metrics


# Include routers
# Import routes
from .routes import auth

# Add routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["authentication"])

# TODO: Add additional routers when implemented
# app.include_router(health.router, prefix="/api", tags=["health"])
# app.include_router(search.router, prefix="/api/v1", tags=["search"])
# app.include_router(cases.router, prefix="/api/v1", tags=["cases"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "KMS 2.5 Vector Search API",
        "version": "2.5.0",
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Disable in production
        log_level="info"
    )
