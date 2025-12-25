"""
Statistics API endpoints - Split into 3 separate endpoints for parallel frontend loading
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from common.exceptions import handle_database_error
from services.analytics_service.api.dependencies import get_tenant_id
from services.analytics_service.database.dependencies import get_analytics_db_client
from services.analytics_service.database.postgres_client import AnalyticsPostgresClient

router = APIRouter()


# ============================================================
# Individual endpoints for parallel frontend loading
# ============================================================

@router.get("/stats/overview", response_model=Dict[str, Any])
async def get_overview_stats(
    tenant_id: str = Depends(get_tenant_id),
    location_id: Optional[str] = Query(default=None, description="Location ID filter"),
    start_date: Optional[str] = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(default=None, description="End date (YYYY-MM-DD)"),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client),
):
    """Get dashboard overview metrics (revenue, purchases, visitors, etc.)"""
    try:
        if start_date and end_date:
            metrics = await db_client.get_overview_stats(
                tenant_id=tenant_id,
                start_date=start_date,
                end_date=end_date,
                location_id=location_id,
            )
        else:
            metrics = {
                "totalRevenue": "$0",
                "purchases": 0,
                "totalVisitors": 0,
                "uniqueUsers": 0,
                "abandonedCarts": 0,
                "totalSearches": 0,
                "failedSearches": 0,
                "repeatVisits": 0,
                "conversionRate": 0,
            }
        return metrics
    except HTTPException:
        raise
    except Exception as e:
        raise handle_database_error("fetching overview stats", e)


@router.get("/stats/chart", response_model=List[Dict[str, Any]])
async def get_chart_stats(
    tenant_id: str = Depends(get_tenant_id),
    location_id: Optional[str] = Query(default=None, description="Location ID filter"),
    start_date: Optional[str] = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(default=None, description="End date (YYYY-MM-DD)"),
    granularity: str = Query(default="daily", description="Time granularity"),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client),
):
    """Get chart data for dashboard trends."""
    try:
        if start_date and end_date:
            chart_data = await db_client.get_chart_data(
                tenant_id=tenant_id,
                start_date=start_date,
                end_date=end_date,
                granularity=granularity,
                location_id=location_id,
            )
        else:
            chart_data = []
        return chart_data
    except HTTPException:
        raise
    except Exception as e:
        raise handle_database_error("fetching chart stats", e)


@router.get("/stats/locations", response_model=List[Dict[str, Any]])
async def get_location_stats(
    tenant_id: str = Depends(get_tenant_id),
    start_date: Optional[str] = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(default=None, description="End date (YYYY-MM-DD)"),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client),
):
    """Get location-based statistics."""
    try:
        if start_date and end_date:
            location_stats = await db_client.get_location_stats(
                tenant_id=tenant_id,
                start_date=start_date,
                end_date=end_date,
            )
        else:
            location_stats = []
        return location_stats
    except HTTPException:
        raise
    except Exception as e:
        raise handle_database_error("fetching location stats", e)


