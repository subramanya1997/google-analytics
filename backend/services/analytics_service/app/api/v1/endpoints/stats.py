"""
Statistics API endpoints
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from loguru import logger

from fastapi import Depends
from services.analytics_service.app.models import (
    DashboardStatsResponse, 
    ChartDataPoint, 
    LocationStatsResponse
)
from services.analytics_service.app.database.postgres_client import AnalyticsPostgresClient
from services.analytics_service.app.database.dependencies import get_analytics_db_client
from services.analytics_service.app.core.config import settings

router = APIRouter()


@router.get("/dashboard", response_model=Dict[str, Any])
async def get_dashboard_stats(
    tenant_id: str = Query(default=settings.DEFAULT_TENANT_ID, description="Tenant ID"),
    location_id: Optional[str] = Query(default=None, description="Location ID filter"),
    start_date: Optional[str] = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(default=None, description="End date (YYYY-MM-DD)"),
    granularity: str = Query(default="daily", description="Time granularity (daily, weekly, monthly)"),
    timezone_offset: int = Query(default=0, description="Timezone offset in minutes"),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client)
):
    """
    Get comprehensive dashboard statistics.
    
    Returns:
    - Overall metrics (revenue, purchases, abandonment, etc.)
    - Chart data for trends
    - Location-based statistics
    """
    try:
        # Database client injected via dependency
        
        # Use single optimized call if we have date range
        if start_date and end_date:
            response = db_client.get_complete_dashboard_data(
                tenant_id=tenant_id,
                start_date=start_date,
                end_date=end_date,
                granularity=granularity,
                location_id=location_id
            )
        else:
            # Fallback for no date range
            response = {
                "metrics": {
                    'totalRevenue': 0,
                    'totalPurchases': 0,
                    'totalVisitors': 0,
                    'uniqueUsers': 0,
                    'abandonedCarts': 0,
                    'totalSearches': 0,
                    'failedSearches': 0,
                    'conversionRate': 0
                },
                "chartData": [],
                "locationStats": []
            }
        
        logger.info(f"Retrieved dashboard stats for tenant {tenant_id}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch dashboard statistics: {str(e)}")


@router.get("/", response_model=Dict[str, Any])
async def get_stats(
    tenant_id: str = Query(default=settings.DEFAULT_TENANT_ID, description="Tenant ID"),
    location_id: Optional[str] = Query(default=None, description="Location ID filter"),
    start_date: Optional[str] = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(default=None, description="End date (YYYY-MM-DD)"),
    granularity: str = Query(default="daily", description="Time granularity"),
    timezone_offset: int = Query(default=0, description="Timezone offset in minutes"),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client)
):
    """
    DEPRECATED: Use /dashboard instead.
    Get statistics - comprehensive endpoint that matches frontend expectations.
    
    This endpoint replicates the functionality of the frontend /api/stats route.
    """
    # This endpoint is deprecated and will be removed.
    # For now, it can just call the new dashboard endpoint.
    return await get_dashboard_stats(
        tenant_id=tenant_id,
        location_id=location_id,
        start_date=start_date,
        end_date=end_date,
        granularity=granularity,
        timezone_offset=timezone_offset,
        db_client=db_client
    )
