"""
Auth Service - FastAPI application for authentication and authorization
"""
from common.fastapi import create_fastapi_app
from common.config import get_settings
from services.auth_service.app.api.v1.api import api_router

# Get settings for this service
settings = get_settings("auth-service")

# Create FastAPI app with reverse proxy configuration
app = create_fastapi_app(
    service_name="auth-service",
    description="Authentication service for Google Analytics intelligence system",
    api_router=api_router,
    root_path="/auth"  # Nginx serves this at /auth/
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
