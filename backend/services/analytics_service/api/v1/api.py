"""
Analytics Service API Router - Version 1.

This module defines the main API router for the Analytics Service v1 API,
aggregating all analytics and reporting endpoints under a unified routing
structure with proper tagging for OpenAPI documentation.

Router Structure:
- Base path: /api/v1/ (configured in main app)
- Locations: Location-based analytics
- Statistics: Dashboard metrics and KPIs
- Tasks: Task-based analytics (purchases, cart abandonment, etc.)
- History: User and session event history
- Email: Report generation and distribution

All endpoints enforce multi-tenant security through X-Tenant-Id header.
"""

from fastapi import APIRouter

from services.analytics_service.api.v1.endpoints import email, history, locations, stats, tasks

api_router = APIRouter()

# Include all endpoint routers with proper tagging for OpenAPI documentation
api_router.include_router(locations.router, tags=["locations"])
api_router.include_router(stats.router, tags=["statistics"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
api_router.include_router(history.router, tags=["History"])
api_router.include_router(email.router, prefix="/email", tags=["Email"])
