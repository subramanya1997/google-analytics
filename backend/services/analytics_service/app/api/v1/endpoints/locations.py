"""
Locations API endpoints
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List
from loguru import logger

from fastapi import Depends
from services.analytics_service.app.models import LocationResponse
from services.analytics_service.app.database.postgres_client import AnalyticsPostgresClient
from services.analytics_service.app.database.dependencies import get_analytics_db_client
from services.analytics_service.app.core.config import settings

router = APIRouter()


@router.get("", response_model=List[LocationResponse])
async def get_locations(
    tenant_id: str = Query(default=settings.DEFAULT_TENANT_ID, description="Tenant ID"),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client)
):
    """
    Get all locations that have analytics activity.
    
    Returns locations that have page view data, indicating active branches.
    """
    try:
        # Get locations with activity
        locations = db_client.get_locations(tenant_id)
        
        logger.info(f"Retrieved {len(locations)} active locations for tenant {tenant_id}")
        
        return locations
        
    except Exception as e:
        logger.error(f"Error fetching locations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch locations: {str(e)}")
