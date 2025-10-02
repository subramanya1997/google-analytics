"""
Locations API Endpoints.

This module implements REST API endpoints for location-based analytics,
providing access to location data for branches with analytics activity.

Key Features:
- Active locations with analytics activity filtering
- Location metadata including city and state information
- Multi-tenant location data isolation

All endpoints require X-Tenant-Id header for proper data isolation.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger

from services.analytics_service.api.dependencies import get_tenant_id
from services.analytics_service.api.v1.models import LocationResponse
from services.analytics_service.database.dependencies import get_analytics_db_client
from services.analytics_service.database.postgres_client import AnalyticsPostgresClient

router = APIRouter()


@router.get("/locations", response_model=List[LocationResponse])
async def get_locations(
    tenant_id: str = Depends(get_tenant_id),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client),
):
    """
    Get all active locations with recorded analytics activity.

    Retrieves locations/branches that have analytics data recorded, providing
    basic location information for filtering and reporting purposes.

    Args:
        tenant_id (str): Unique tenant identifier (from X-Tenant-Id header)
        db_client (AnalyticsPostgresClient): Database client dependency

    Returns:
        List[LocationResponse]: List of active locations containing:
            - locationId (str): Unique location identifier
            - locationName (str): Human-readable location name
            - city (Optional[str]): Location city
            - state (Optional[str]): Location state

    Raises:
        HTTPException: 500 error for database failures or processing errors
    """
    try:
        # Get locations with activity
        locations = await db_client.get_locations(tenant_id)

        logger.info(
            f"Retrieved {len(locations)} active locations for tenant {tenant_id}"
        )

        return locations

    except Exception as e:
        logger.error(f"Error fetching locations: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch locations: {str(e)}"
        )
