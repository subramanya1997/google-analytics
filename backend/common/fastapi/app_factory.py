"""
Common FastAPI application factory with standard middleware and configuration.

This module provides a factory function for creating FastAPI applications with
consistent configuration, middleware, and error handling across all services.

Features:
    - Automatic logging setup
    - CORS configuration (environment-aware)
    - Request timing middleware
    - Global exception handling
    - Health check endpoints
    - OpenAPI documentation

Middleware:
    - CORS: Configured based on environment (dev vs production)
    - Request Timing: Adds X-Process-Time header to all responses
    - Logging: Automatic request/response logging

Endpoints:
    - GET /: Root endpoint with service information
    - GET /health: Health check endpoint
    - GET /docs: Swagger UI documentation
    - GET /redoc: ReDoc documentation

Usage:
    ```python
    from common.fastapi import create_fastapi_app
    from fastapi import APIRouter
    
    # Define your API routes
    api_router = APIRouter()
    
    @api_router.get("/users")
    async def get_users():
        return {"users": []}
    
    # Create app
    app = create_fastapi_app(
        service_name="analytics-service",
        description="Analytics service API",
        api_router=api_router
    )
    ```
"""

from collections.abc import Callable
import time
from typing import Any

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from loguru import logger

from common.config import BaseServiceSettings, get_settings
from common.logging import setup_logging


def create_fastapi_app(
    service_name: str,
    description: str,
    api_router: APIRouter | None = None,
    additional_setup: Callable[[FastAPI, BaseServiceSettings], None] | None = None,
    root_path: str = "",
) -> FastAPI:
    """
    Create a FastAPI application with standardized configuration and middleware.

    This factory function creates a fully configured FastAPI application with:
    - Service-specific settings loaded from configuration
    - Logging configured for the service
    - CORS middleware (environment-aware)
    - Request timing middleware
    - Global exception handling
    - Health check and root endpoints
    - Optional API router inclusion

    Args:
        service_name: Name of the service (e.g., "analytics-service", "data-ingestion-service").
            Used to load service-specific settings and configure logging.
        description: Human-readable description of the service. Used in OpenAPI documentation
            and API metadata.
        api_router: Optional FastAPI APIRouter instance containing route definitions.
            If provided, routes are included with the API_V1_STR prefix (default: "/api/v1").
        additional_setup: Optional callback function for additional application setup.
            Called after all standard configuration is complete. Signature:
            `(app: FastAPI, settings: BaseServiceSettings) -> None`
            Useful for adding custom middleware, startup/shutdown handlers, etc.
        root_path: Optional root path for reverse proxy scenarios. In DEV environment,
            this is automatically set to empty string. In production, should match
            the reverse proxy path (e.g., "/api/analytics").

    Returns:
        Fully configured FastAPI application instance ready to run.

    Side Effects:
        - Configures logging for the service (via setup_logging)
        - Adds middleware to the application
        - Registers exception handlers
        - Creates health check and root endpoints

    Example:
        ```python
        from common.fastapi import create_fastapi_app
        from fastapi import APIRouter
        
        # Create API router with routes
        api_router = APIRouter(prefix="/users", tags=["users"])
        
        @api_router.get("")
        async def list_users():
            return {"users": []}
        
        # Create app with router
        app = create_fastapi_app(
            service_name="analytics-service",
            description="Analytics service for Google Analytics Intelligence",
            api_router=api_router
        )
        
        # Run with uvicorn
        # uvicorn.run(app, host="0.0.0.0", port=8001)
        ```

    Example with additional setup:
        ```python
        def setup_database(app: FastAPI, settings: BaseServiceSettings):
            @app.on_event("startup")
            async def init_db():
                # Initialize database connections
                pass
        
        app = create_fastapi_app(
            service_name="analytics-service",
            description="Analytics service",
            additional_setup=setup_database
        )
        ```

    Note:
        - Logging is configured automatically based on service name
        - CORS is configured differently for DEV vs production environments
        - Root path is automatically adjusted for DEV environment
        - All unhandled exceptions are caught and return generic error messages
        - Health check endpoint is available at /health
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
        root_path=effective_root_path,
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
        # Allow common development origins
        # Note: allow_credentials=True is incompatible with allow_origins=["*"]
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[
                "http://localhost:3000",
                "http://localhost:3001",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:3001",
            ],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Add request timing middleware
    @app.middleware("http")
    async def add_process_time_header(
        request: Request, call_next: Callable[[Request], Any]
    ) -> Response:
        """Add process time header to responses."""
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        # Log request with timing
        logger.info(
            f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s"
        )
        return response

    # Include API router if provided
    if api_router:
        app.include_router(api_router, prefix=settings.API_V1_STR)

    # Standard health check endpoint
    @app.get("/health")
    async def health_check() -> dict[str, Any]:
        """Health check endpoint."""
        return {
            "service": settings.SERVICE_NAME,
            "version": settings.SERVICE_VERSION,
            "status": "healthy",
            "timestamp": time.time(),
        }

    # Standard root endpoint
    @app.get("/")
    async def root() -> dict[str, Any]:
        """Root endpoint."""
        return {
            "service": settings.SERVICE_NAME,
            "version": settings.SERVICE_VERSION,
            "message": f"{settings.SERVICE_NAME} is running",
            "docs": "/docs",
            "health": "/health",
        }

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error(
            f"Unhandled exception in {request.method} {request.url.path}: {exc}",
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "An error occurred while processing your request. Please try again later."
            },
        )

    # Run additional setup if provided
    if additional_setup:
        additional_setup(app, settings)

    return app
