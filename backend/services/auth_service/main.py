"""
Auth Service - FastAPI application for authentication and authorization
"""

from common.fastapi import create_fastapi_app
from services.auth_service.api.v1.api import api_router

# Create FastAPI app with reverse proxy configuration
app = create_fastapi_app(
    service_name="auth-service",
    description="Authentication service for Google Analytics intelligence system",
    api_router=api_router,
    root_path="/auth",  # Nginx serves this at /auth/
)
