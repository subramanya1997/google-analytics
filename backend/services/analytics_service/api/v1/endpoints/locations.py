"""
Locations API Endpoints for Branch/Location Queries

This module provides RESTful API endpoints for retrieving location/branch
information. Locations represent physical branches or stores that have
analytics activity.

Use Cases:
    - Dashboard filters: Populate location dropdowns
    - Location selection: Choose locations for report generation
    - Branch management: List active branches

Data Source:
    Returns locations that have analytics activity (page views) within the
    tenant's data, ensuring only relevant locations are returned.

Multi-Tenancy:
    All endpoints require X-Tenant-Id header for proper data isolation.

Example:
    ```python
    GET /api/v1/locations
    Headers:
        X-Tenant-Id: tenant-123
    ```

See Also:
    - services.analytics_service.database.postgres_client: Database client methods
    - backend/database/functions/get_locations.sql: SQL function
"""

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from common.exceptions import handle_database_error
from services.analytics_service.api.dependencies import get_tenant_id
from services.analytics_service.api.v1.models import LocationResponse
from services.analytics_service.database.dependencies import get_analytics_db_client
from services.analytics_service.database.postgres_client import AnalyticsPostgresClient

router = APIRouter()


@router.get("/locations", response_model=list[LocationResponse])
async def get_locations(
    tenant_id: str = Depends(get_tenant_id),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client),
) -> list[LocationResponse]:
    """
    Retrieve all active locations (branches) for a tenant.

    Returns locations that have analytics activity (page views) within the
    tenant's data. This is used to populate location filters in the dashboard
    and other UI components.

    Args:
        tenant_id: Tenant identifier extracted from X-Tenant-Id header.
        db_client: Database client dependency injection.

    Returns:
        list[LocationResponse]: List of location objects, each containing:
            - locationId (str): Unique location identifier
            - locationName (str): Display name of the location
            - city (str | None): City name if available
            - state (str | None): State/province name if available

        Returns empty list if no locations found or on error.

    Raises:
        HTTPException: 400 if tenant_id is invalid.
        HTTPException: 500 if database query fails.

    Example:
        ```bash
        GET /api/v1/locations
        Headers:
            X-Tenant-Id: tenant-123
        ```

    Note:
        Only returns locations with actual analytics activity. Inactive
        locations without page view data are excluded.
    """
    try:
        # Get locations with activity
        locations = await db_client.get_locations(tenant_id)

        logger.info(
            f"Retrieved {len(locations)} active locations for tenant {tenant_id}"
        )

        return locations

    except HTTPException:
        raise
    except Exception as e:
        msg = "fetching locations"
        raise handle_database_error(msg, e)
