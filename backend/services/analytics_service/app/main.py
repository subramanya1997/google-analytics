"""
Analytics Service - FastAPI application for analytics and reporting
"""
from common.fastapi import create_fastapi_app
from common.config import get_settings
from services.analytics_service.app.api.v1.api import api_router

# Get settings for this service
settings = get_settings("analytics-service")

# Create FastAPI app with reverse proxy configuration
app = create_fastapi_app(
    service_name="analytics-service",
    description="Analytics service for Google Analytics intelligence system",
    api_router=api_router,
    root_path="/analytics"  # Nginx serves this at /analytics/
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
