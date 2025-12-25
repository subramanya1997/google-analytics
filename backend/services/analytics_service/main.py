"""
Analytics Service - FastAPI Application Entry Point

This module serves as the main entry point for the Analytics Service, a microservice
responsible for providing analytics dashboard APIs, task management, and automated
email reporting capabilities for the Google Analytics Intelligence System.

The service is built on FastAPI and provides RESTful APIs for:
    - Dashboard statistics and metrics aggregation
    - Task management (purchases, cart abandonment, search analysis, etc.)
    - Email report generation and distribution
    - Historical event tracking (sessions and users)
    - Location-based analytics

Architecture:
    The service follows a multi-tenant architecture where each tenant's data is
    isolated at the database level. All API requests require an X-Tenant-Id header
    for proper tenant identification and data isolation.

Deployment:
    The service runs on port 8001 and is typically served behind an Nginx reverse
    proxy at the /analytics path. The root_path parameter ensures proper URL
    generation in OpenAPI documentation.

Example:
    To run the service locally:
        ```bash
        uv run uvicorn services.analytics_service:app --port 8001 --reload
        ```

    To access API documentation:
        - Swagger UI: http://localhost:8001/docs
        - ReDoc: http://localhost:8001/redoc

Attributes:
    app (FastAPI): The FastAPI application instance configured with:
        - Service name: "analytics-service"
        - API router: Includes all v1 endpoints
        - Root path: "/analytics" for reverse proxy compatibility
        - CORS, logging, and error handling middleware

See Also:
    - services.analytics_service.api.v1.api: API router configuration
    - common.fastapi.create_fastapi_app: FastAPI app factory
    - backend/docs/ARCHITECTURE.md: System architecture documentation
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
