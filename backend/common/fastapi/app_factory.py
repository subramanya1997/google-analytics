"""
Common FastAPI application factory with standard middleware and configuration.

This module provides a factory function for creating FastAPI applications with
consistent configuration, middleware, and error handling across all backend services
in the Google Analytics Intelligence System.

Key Features:
- Standardized FastAPI application configuration
- Environment-aware CORS setup (strict in production, permissive in development)
- Request timing middleware for performance monitoring
- Global exception handling with appropriate error responses
- Health check and root endpoints
- Integrated logging setup
- Support for reverse proxy configurations

The factory ensures all services have consistent:
- API documentation endpoints (/docs, /redoc)
- Health monitoring (/health)
- Error handling and logging
- CORS policies
- Request/response timing

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
    Create a FastAPI application with standardized configuration and middleware.
    
    Factory function that creates a consistently configured FastAPI application
    with common middleware, error handling, monitoring, and documentation setup.
    Handles environment-specific configurations and provides hooks for service-
    specific customization.
    
    Args:
        service_name: Name of the service (used for settings lookup and identification)
        description: Human-readable description of the service for API documentation
        api_router: Optional APIRouter instance to include at the configured API path
        additional_setup: Optional callback function(app, settings) for custom setup
        root_path: Base path for reverse proxy deployment (auto-configured by environment)
        
    Returns:
        Configured FastAPI application instance ready for deployment
        
    Application Features:
        - Automatic logging configuration using service name
        - Environment-aware CORS policies
        - Request timing middleware with X-Process-Time header
        - Global exception handler with environment-appropriate error details
        - Standard health check endpoint at /health
        - Root endpoint at / with service information
        - API documentation at /docs and /redoc
        
    Environment Behavior:
        - DEV: Permissive CORS (allow all origins), detailed error messages
        - PROD: Strict CORS (configured origins only), generic error messages
        - Reverse proxy support automatically configured based on environment
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
        """
        Middleware to add request processing time to response headers.
        
        Measures request processing time and adds it as X-Process-Time header
        for monitoring and performance analysis.
        """
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
        """
        Health check endpoint for monitoring and load balancer probes.
        
        Returns basic service information and health status. Used by monitoring
        systems and load balancers to determine service availability.
        
        Returns:
            Dict with service name, version, status, and current timestamp
        """
        return {
            "service": settings.SERVICE_NAME,
            "version": settings.SERVICE_VERSION,
            "status": "healthy",
            "timestamp": time.time()
        }
    
    # Standard root endpoint
    @app.get("/")
    async def root():
        """
        Root endpoint providing service information and navigation.
        
        Returns basic service information and links to important endpoints
        like API documentation and health checks.
        
        Returns:
            Dict with service details and endpoint links
        """
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
        """
        Global exception handler for unhandled application errors.
        
        Catches all unhandled exceptions, logs them for debugging, and returns
        appropriate error responses. Error detail level depends on environment
        (detailed in debug mode, generic in production).
        
        Args:
            request: The FastAPI request that caused the exception
            exc: The unhandled exception
            
        Returns:
            JSONResponse with 500 status and error information
        """
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
