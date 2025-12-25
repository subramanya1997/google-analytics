"""
Data Service API v1 Router Configuration

This module aggregates all v1 API endpoints into a single FastAPI router instance.
The router is registered with the main FastAPI application and serves as the
entry point for all v1 API requests.

Router Structure:
    - /ingest: Ingestion job management endpoints
    - /data-availability: Data availability query endpoints
    - /jobs: Job history and status endpoints
    - /data/schedule: Scheduled ingestion configuration endpoints

All endpoints are prefixed with /api/v1 when registered with the main application.

Example:
    ```python
    from services.data_service.api.v1.api import api_router
    
    app.include_router(api_router, prefix="/api/v1")
    ```

See Also:
    - services.data_service.api.v1.endpoints.ingestion: Ingestion endpoints
    - services.data_service.api.v1.endpoints.schedule: Schedule endpoints
"""

from fastapi import APIRouter

from services.data_service.api.v1.endpoints import ingestion, schedule

api_router = APIRouter()

api_router.include_router(ingestion.router, tags=["Ingestion"])
api_router.include_router(schedule.router, prefix="/data", tags=["Schedule"])
