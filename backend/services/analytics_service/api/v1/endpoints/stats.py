"""
Statistics API Endpoints for Dashboard Metrics

This module provides RESTful API endpoints for retrieving aggregated analytics
statistics used in the dashboard. The endpoints are split into three separate
routes to enable parallel loading in the frontend, improving perceived performance.

Endpoint Design:
    The statistics endpoints are intentionally split into:
    1. /stats/overview - High-level summary metrics (revenue, purchases, visitors)
    2. /stats/chart - Time-series data for chart visualizations
    3. /stats/locations - Location-based aggregated statistics

    This separation allows the frontend to:
    - Load critical overview data first
    - Fetch chart data in parallel
    - Load location stats independently

Performance Considerations:
    - All endpoints use optimized PostgreSQL functions for fast aggregation
    - Date range filtering is applied at the database level
    - Results are cached where appropriate by the database layer

Multi-Tenancy:
    All endpoints require X-Tenant-Id header for proper data isolation.

Example:
    ```python
    # Get overview stats
    GET /api/v1/stats/overview?start_date=2024-01-01&end_date=2024-01-31
    Headers: X-Tenant-Id: tenant-123
    
    # Get chart data
    GET /api/v1/stats/chart?start_date=2024-01-01&end_date=2024-01-31&granularity=daily
    Headers: X-Tenant-Id: tenant-123
    ```

See Also:
    - services.analytics_service.database.stats_repository: StatsRepository
    - backend/database/functions/get_dashboard_overview_stats.sql: SQL function
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from common.exceptions import handle_database_error
from services.analytics_service.api.dependencies import get_stats_repository, get_tenant_id
from services.analytics_service.database import StatsRepository

router = APIRouter()


# ============================================================
# Individual endpoints for parallel frontend loading
# ============================================================


@router.get("/stats/overview", response_model=dict[str, Any])
async def get_overview_stats(
    tenant_id: str = Depends(get_tenant_id),
    location_id: str | None = Query(default=None, description="Location ID filter"),
    start_date: str | None = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(default=None, description="End date (YYYY-MM-DD)"),
    repo: StatsRepository = Depends(get_stats_repository),
) -> dict[str, Any]:
    """
    Retrieve dashboard overview statistics for a date range.

    Returns high-level aggregated metrics including revenue, purchase counts,
    visitor statistics, and conversion rates. This is the primary endpoint
    for dashboard summary cards and KPIs.

    Args:
        tenant_id: Tenant identifier extracted from X-Tenant-Id header.
        location_id: Optional location filter. If provided, statistics are
            limited to the specified location.
        start_date: Optional start date filter (YYYY-MM-DD format). If not
            provided, returns default empty metrics.
        end_date: Optional end date filter (YYYY-MM-DD format). If not
            provided, returns default empty metrics.
        repo: StatsRepository dependency injection.

    Returns:
        dict[str, Any]: Dictionary containing:
            - totalRevenue (str): Total revenue formatted as currency
            - purchases (int): Total number of purchases
            - totalVisitors (int): Total unique visitors
            - uniqueUsers (int): Total unique users
            - abandonedCarts (int): Number of abandoned cart sessions
            - totalSearches (int): Total search queries
            - failedSearches (int): Searches with no results
            - repeatVisits (int): Repeat visitor sessions
            - conversionRate (float): Purchase conversion rate (0.0-1.0)

        Returns default empty metrics if dates are not provided.

    Raises:
        HTTPException: 400 if tenant_id is invalid.
        HTTPException: 500 if database query fails.

    Example:
        ```bash
        GET /api/v1/stats/overview?start_date=2024-01-01&end_date=2024-01-31&location_id=loc-001
        Headers:
            X-Tenant-Id: tenant-123
        ```

    Note:
        Both start_date and end_date must be provided for actual statistics.
        If either is missing, returns default empty metrics structure.
    """
    try:
        if start_date and end_date:
            metrics = await repo.get_overview_stats(
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
        msg = "fetching overview stats"
        raise handle_database_error(msg, e)


@router.get("/stats/chart", response_model=list[dict[str, Any]])
async def get_chart_stats(
    tenant_id: str = Depends(get_tenant_id),
    location_id: str | None = Query(default=None, description="Location ID filter"),
    start_date: str | None = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(default=None, description="End date (YYYY-MM-DD)"),
    granularity: str = Query(default="daily", description="Time granularity"),
    repo: StatsRepository = Depends(get_stats_repository),
) -> list[dict[str, Any]]:
    """
    Retrieve time-series chart data for dashboard visualizations.

    Returns aggregated metrics grouped by time periods (daily, weekly, monthly)
    suitable for rendering line charts, bar charts, and other time-series
    visualizations.

    Args:
        tenant_id: Tenant identifier extracted from X-Tenant-Id header.
        location_id: Optional location filter. If provided, data is limited
            to the specified location.
        start_date: Optional start date filter (YYYY-MM-DD format). If not
            provided, returns empty list.
        end_date: Optional end date filter (YYYY-MM-DD format). If not
            provided, returns empty list.
        granularity: Time granularity for grouping. Valid values:
            - "daily": Group by day (default)
            - "weekly": Group by week
            - "monthly": Group by month
        repo: StatsRepository dependency injection.

    Returns:
        list[dict[str, Any]]: List of time-series data points, each containing:
            - date (str): Date/time period identifier
            - revenue (float): Revenue for this period
            - purchases (int): Number of purchases
            - visitors (int): Number of visitors
            - conversions (int): Number of conversions
            - Other period-specific metrics

        Returns empty list if dates are not provided or no data found.

    Raises:
        HTTPException: 400 if tenant_id is invalid.
        HTTPException: 500 if database query fails.

    Example:
        ```bash
        GET /api/v1/stats/chart?start_date=2024-01-01&end_date=2024-01-31&granularity=daily
        Headers:
            X-Tenant-Id: tenant-123
        ```

    Note:
        Both start_date and end_date must be provided for actual data.
        If either is missing, returns empty list.
    """
    try:
        if start_date and end_date:
            chart_data = await repo.get_chart_data(
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
        msg = "fetching chart stats"
        raise handle_database_error(msg, e)


@router.get("/stats/locations", response_model=list[dict[str, Any]])
async def get_location_stats(
    tenant_id: str = Depends(get_tenant_id),
    start_date: str | None = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(default=None, description="End date (YYYY-MM-DD)"),
    repo: StatsRepository = Depends(get_stats_repository),
) -> list[dict[str, Any]]:
    """
    Retrieve aggregated statistics grouped by location/branch.

    Returns performance metrics for each location, enabling comparison across
    branches and identification of top-performing locations. Used for location
    comparison charts and tables in the dashboard.

    Args:
        tenant_id: Tenant identifier extracted from X-Tenant-Id header.
        start_date: Optional start date filter (YYYY-MM-DD format). If not
            provided, returns empty list.
        end_date: Optional end date filter (YYYY-MM-DD format). If not
            provided, returns empty list.
        repo: StatsRepository dependency injection.

    Returns:
        list[dict[str, Any]]: List of location statistics, each containing:
            - locationId (str): Unique location identifier
            - locationName (str): Display name of the location
            - revenue (float): Total revenue for this location
            - purchases (int): Number of purchases
            - visitors (int): Number of visitors
            - conversionRate (float): Conversion rate for this location
            - Other location-specific metrics

        Returns empty list if dates are not provided or no data found.

    Raises:
        HTTPException: 400 if tenant_id is invalid.
        HTTPException: 500 if database query fails.

    Example:
        ```bash
        GET /api/v1/stats/locations?start_date=2024-01-01&end_date=2024-01-31
        Headers:
            X-Tenant-Id: tenant-123
        ```

    Note:
        Both start_date and end_date must be provided for actual data.
        If either is missing, returns empty list.
    """
    try:
        if start_date and end_date:
            location_stats = await repo.get_location_stats(
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
        msg = "fetching location stats"
        raise handle_database_error(msg, e)
