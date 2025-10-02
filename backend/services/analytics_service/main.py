"""
Analytics Service - FastAPI Application Entry Point.

This module provides the main FastAPI application for the Analytics Service,
which handles analytics data querying, reporting, and email distribution for
the Google Analytics Intelligence System. The service provides business
intelligence capabilities including dashboard statistics, task management,
and automated report generation.

Key Responsibilities:
- Dashboard statistics and metrics aggregation
- Task-based analytics (purchases, cart abandonment, search analysis, etc.)
- Location-based analytics and reporting
- Email report generation and distribution
- User session and event history tracking

API Endpoints:
- GET /api/v1/stats: Dashboard statistics and metrics
- GET /api/v1/locations: Location analytics data
- GET /api/v1/tasks/*: Task-based analytics endpoints
- GET /api/v1/history/*: User and session history
- POST /api/v1/email/*: Email management and reporting

Production Configuration:
- Reverse proxy path: /analytics/ (configured for Nginx deployment)
- Service name: analytics-service
- Default port: 8002 (configurable via environment)
- Health check: /health
- API documentation: /analytics/docs

Multi-Tenant Security:
All operations require X-Tenant-Id header for proper data isolation.
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
