"""
Common FastAPI utilities and middleware.

This module provides shared FastAPI functionality used across all backend services,
including application factory, middleware, and common route handlers.

Main Components:
    - app_factory: FastAPI application factory with standard configuration

Usage:
    ```python
    from common.fastapi import create_fastapi_app
    from fastapi import APIRouter
    
    # Create API router
    api_router = APIRouter()
    
    # Create FastAPI app with common configuration
    app = create_fastapi_app(
        service_name="analytics-service",
        description="Analytics service for Google Analytics Intelligence",
        api_router=api_router
    )
    ```
"""
from .app_factory import create_fastapi_app

__all__ = ["create_fastapi_app"]