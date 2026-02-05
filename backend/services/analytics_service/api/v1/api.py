"""
API Router Configuration for Analytics Service v1

This module aggregates all API endpoint routers into a single FastAPI router
that is mounted to the main application. It organizes endpoints by functional
area and applies appropriate tags for OpenAPI documentation.

Router Organization:
    - Locations: Branch/location queries
    - Statistics: Dashboard metrics and aggregated data
    - Tasks: Task management endpoints (purchases, cart abandonment, etc.)
    - History: Session and user event history

Note:
    Email endpoints (email configuration, mappings, report distribution, scheduling)
    have been moved to the Data Service for consolidation with data ingestion
    scheduling functionality.

API Versioning:
    This is the v1 API router. Future breaking changes should be introduced
    in a v2 router while maintaining backward compatibility in v1.

Example:
    The router is included in the main FastAPI app:
    ```python
    from services.analytics_service.api.v1.api import api_router

    app.include_router(api_router, prefix="/api/v1")
    ```

See Also:
    - services.analytics_service.main: Main application that includes this router
    - services.analytics_service.api.v1.endpoints: Individual endpoint modules
    - services.data_service.api.v1.endpoints.email: Email endpoints (now in Data Service)
"""

from fastapi import APIRouter

from services.analytics_service.api.v1.endpoints import (
    history,
    locations,
    stats,
    tasks,
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(locations.router, tags=["locations"])
api_router.include_router(stats.router, tags=["statistics"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
api_router.include_router(history.router, tags=["History"])
