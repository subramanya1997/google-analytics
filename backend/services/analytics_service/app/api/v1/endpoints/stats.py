"""
Statistics API endpoints
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from loguru import logger

from app.models.analytics import (
    DashboardStatsResponse, 
    ChartDataPoint, 
    LocationStatsResponse
)
from app.database.supabase_client import AnalyticsSupabaseClient
from app.core.config import settings

router = APIRouter()


@router.get("/dashboard", response_model=Dict[str, Any])
async def get_dashboard_stats(
    tenant_id: str = Query(default=settings.DEFAULT_TENANT_ID, description="Tenant ID"),
    location_id: Optional[str] = Query(default=None, description="Location ID filter"),
    start_date: Optional[str] = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(default=None, description="End date (YYYY-MM-DD)"),
    granularity: str = Query(default="daily", description="Time granularity (daily, weekly, monthly)"),
    timezone_offset: int = Query(default=0, description="Timezone offset in minutes")
):
    """
    Get comprehensive dashboard statistics.
    
    Returns:
    - Overall metrics (revenue, purchases, abandonment, etc.)
    - Chart data for trends
    - Location-based statistics
    """
    try:
        # Initialize database client
        supabase_config = settings.get_supabase_client_config()
        db_client = AnalyticsSupabaseClient(supabase_config)
        
        # Get dashboard statistics
        stats = db_client.get_dashboard_stats(
            tenant_id=tenant_id,
            location_id=location_id,
            start_date=start_date,
            end_date=end_date,
            granularity=granularity
        )
        
        # For now, return basic structure - we'll enhance this with chart data
        response = {
            "metrics": stats,
            "chartData": [],  # Will implement time-series data
            "locationStats": []  # Will implement location breakdown
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
    timezone_offset: int = Query(default=0, description="Timezone offset in minutes")
):
    """
    Get statistics - comprehensive endpoint that matches frontend expectations.
    
    This endpoint replicates the functionality of the frontend /api/stats route.
    """
    try:
        # Initialize database client
        supabase_config = settings.get_supabase_client_config()
        db_client = AnalyticsSupabaseClient(supabase_config)
        
        # Get basic dashboard statistics
        stats = db_client.get_dashboard_stats(
            tenant_id=tenant_id,
            location_id=location_id,
            start_date=start_date,
            end_date=end_date,
            granularity=granularity
        )
        
        # Get location-based statistics
        locations = db_client.get_locations(tenant_id)
        location_stats = []
        
        for location in locations:
            loc_stats = db_client.get_dashboard_stats(
                tenant_id=tenant_id,
                location_id=location['locationId'],
                start_date=start_date,
                end_date=end_date,
                granularity=granularity
            )
            
            # Extract revenue value (remove $ and commas)
            revenue_str = loc_stats.get('totalRevenue', '$0.00')
            revenue = float(revenue_str.replace('$', '').replace(',', ''))
            
            location_stats.append({
                'locationId': location['locationId'],
                'locationName': location['locationName'],
                'revenue': revenue,
                'purchases': loc_stats.get('purchases', 0),
                'visitors': loc_stats.get('totalVisitors', 0),
                'abandonedCarts': loc_stats.get('abandonedCarts', 0),
                'repeatVisits': loc_stats.get('repeatVisits', 0)
            })
        
        # Sort by revenue descending
        location_stats.sort(key=lambda x: x['revenue'], reverse=True)
        
        # Create chart data (simplified for now)
        chart_data = []
        if start_date and end_date:
            # For now, create a simple data point
            revenue_str = stats.get('totalRevenue', '$0.00')
            revenue = float(revenue_str.replace('$', '').replace(',', ''))
            
            chart_data.append({
                'date': end_date,
                'revenue': revenue,
                'purchases': stats.get('purchases', 0),
                'visitors': stats.get('totalVisitors', 0)
            })
        
        response = {
            'metrics': stats,
            'locationStats': location_stats,
            'chartData': chart_data
        }
        
        logger.info(f"Retrieved comprehensive stats for tenant {tenant_id}")
        
        return response
        
    except Exception as e:
        logger.error(f"Error fetching comprehensive stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch statistics: {str(e)}")
