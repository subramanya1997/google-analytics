"""
Analytics Service - FastAPI application for analytics and reporting
"""

from common.fastapi import create_fastapi_app
from services.analytics_service.api.v1.api import api_router

# Create FastAPI app with reverse proxy configuration
app = create_fastapi_app(
    service_name="analytics-service",
    description="Analytics service for Google Analytics intelligence system",
    api_router=api_router,
    root_path="/analytics",  # Nginx serves this at /analytics/
)
