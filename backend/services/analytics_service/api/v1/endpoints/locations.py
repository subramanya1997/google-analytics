"""
Locations API endpoints
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
    Get all locations that have analytics activity.

    Returns locations that have page view data, indicating active branches.
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
