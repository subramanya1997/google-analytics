"""
Statistics API endpoints
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from services.analytics_service.api.dependencies import get_tenant_id
from services.analytics_service.database.dependencies import get_analytics_db_client
from services.analytics_service.database.postgres_client import AnalyticsPostgresClient

router = APIRouter()


@router.get("/stats", response_model=Dict[str, Any])
async def get_dashboard_stats(
    tenant_id: str = Depends(get_tenant_id),
    location_id: Optional[str] = Query(default=None, description="Location ID filter"),
    start_date: Optional[str] = Query(
        default=None, description="Start date (YYYY-MM-DD)"
    ),
    end_date: Optional[str] = Query(default=None, description="End date (YYYY-MM-DD)"),
    granularity: str = Query(
        default="daily", description="Time granularity (daily, weekly, monthly)"
    ),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client),
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
                location_id=location_id,
            )
        else:
            # Fallback for no date range
            response = {
                "metrics": {
                    "totalRevenue": 0,
                    "totalPurchases": 0,
                    "totalVisitors": 0,
                    "uniqueUsers": 0,
                    "abandonedCarts": 0,
                    "totalSearches": 0,
                    "failedSearches": 0,
                    "conversionRate": 0,
                },
                "chartData": [],
                "locationStats": [],
            }

        logger.info(f"Retrieved dashboard stats for tenant {tenant_id}")

        return response

    except Exception as e:
        logger.error(f"Error fetching dashboard stats: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch dashboard statistics: {str(e)}"
        )
