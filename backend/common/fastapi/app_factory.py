"""
Common FastAPI application factory with standard middleware and configuration.
"""
import time
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from common.config import get_settings
from common.logging import setup_logging
from loguru import logger


def create_fastapi_app(
    service_name: str,
    description: str,
    api_router = None,
    additional_setup: Optional[callable] = None,
    root_path: str = ""
) -> FastAPI:
    """
    Create a FastAPI app with common configuration and middleware.
    
    Args:
        service_name: Name of the service (used for settings)
        description: Service description
        api_router: Optional API router to include
        additional_setup: Optional function for additional app setup
    """
    
    # Setup logging first
    setup_logging(service_name)
    
    # Get service settings
    settings = get_settings(service_name)
    
    # Conditionally set the root_path based on the environment
    # In development, root_path should be empty as we are not behind a reverse proxy
    effective_root_path = root_path if settings.ENVIRONMENT != "DEV" else ""
    
    # Create FastAPI app with proper reverse proxy support
    openapi_url = "/openapi.json"
    
    app = FastAPI(
        title=settings.SERVICE_NAME,
        version=settings.SERVICE_VERSION,
        description=description,
        openapi_url=openapi_url,
        docs_url="/docs",
        redoc_url="/redoc",
        root_path=effective_root_path
    )
    
    # Configure CORS
    if settings.ENVIRONMENT == "production":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        # Allow all origins in development
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    # Add request timing middleware
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
    
    # Include API router if provided
    if api_router:
        app.include_router(api_router, prefix=settings.API_V1_STR)
    
    # Standard health check endpoint
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "service": settings.SERVICE_NAME,
            "version": settings.SERVICE_VERSION,
            "status": "healthy",
            "timestamp": time.time()
        }
    
    # Standard root endpoint
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "service": settings.SERVICE_NAME,
            "version": settings.SERVICE_VERSION,
            "message": f"{settings.SERVICE_NAME} is running",
            "docs": "/docs",
            "health": "/health"
        }
    
    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Global exception handler caught: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": str(exc) if settings.DEBUG else "An error occurred"
            }
        )
    
    # Run additional setup if provided
    if additional_setup:
        additional_setup(app, settings)
    
    return app
