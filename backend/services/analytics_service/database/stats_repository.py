"""
Stats Repository for Analytics Service

This module provides database operations for analytics statistics and metrics
in the Analytics Service. It handles retrieval of dashboard overview stats,
time-series chart data, and location-based statistics.

Example:
    ```python
    repo = StatsRepository()
    overview = await repo.get_overview_stats("tenant-123", "2024-01-01", "2024-01-31")
    chart_data = await repo.get_chart_data("tenant-123", "2024-01-01", "2024-01-31", "daily")
    ```

See Also:
    - services.analytics_service.database.base: Shared constants
    - common.database.get_async_db_session: Database session management
"""

from typing import Any

from sqlalchemy import text

from common.database import get_async_db_session

from .base import SERVICE_NAME


class StatsRepository:
    """
    Repository for analytics statistics database operations.

    This class provides methods for querying aggregated analytics data used
    in dashboard visualizations, including overview metrics, time-series charts,
    and location comparisons.

    Thread Safety:
        This repository is thread-safe and can be used concurrently across
        multiple async tasks. Each method creates its own database session.

    Example:
        ```python
        repo = StatsRepository()
        stats = await repo.get_overview_stats(
            "tenant-123", "2024-01-01", "2024-01-31"
        )
        ```
    """

    async def get_overview_stats(
        self,
        tenant_id: str,
        start_date: str,
        end_date: str,
        location_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Retrieve aggregated dashboard overview statistics for a date range.

        Provides high-level metrics for the analytics dashboard including revenue,
        purchase counts, visitor statistics, and conversion rates. This is the
        primary endpoint for dashboard summary cards.

        Args:
            tenant_id: Unique tenant identifier for data isolation.
            start_date: Start date for statistics (YYYY-MM-DD format).
            end_date: End date for statistics (YYYY-MM-DD format).
            location_id: Optional location filter. If provided, statistics are
                limited to the specified location. If None, includes all locations.

        Returns:
            dict[str, Any]: Dictionary containing aggregated statistics:
                - totalRevenue (str): Total revenue formatted as currency string
                - purchases (int): Total number of purchases
                - totalVisitors (int): Total number of unique visitors
                - uniqueUsers (int): Total number of unique users
                - abandonedCarts (int): Number of abandoned cart sessions
                - totalSearches (int): Total number of search queries
                - failedSearches (int): Number of searches with no results
                - repeatVisits (int): Number of repeat visitor sessions
                - conversionRate (float): Purchase conversion rate (0.0-1.0)

            Returns empty dict if no data found or on error.

        Example:
            ```python
            stats = await repo.get_overview_stats(
                tenant_id="tenant-123",
                start_date="2024-01-01",
                end_date="2024-01-31",
                location_id="loc-001",
            )
            # {
            #     "totalRevenue": "$125,430.50",
            #     "purchases": 342,
            #     "totalVisitors": 1250,
            #     "uniqueUsers": 890,
            #     "abandonedCarts": 156,
            #     "totalSearches": 2340,
            #     "failedSearches": 89,
            #     "repeatVisits": 234,
            #     "conversionRate": 0.2736
            # }
            ```

        Note:
            Uses the `get_dashboard_overview_stats()` PostgreSQL function which
            efficiently aggregates data from multiple event tables.
        """
        async with get_async_db_session(
            SERVICE_NAME, tenant_id=tenant_id
        ) as session:
            result = await session.execute(
                text(
                    "SELECT get_dashboard_overview_stats(:p_tenant_id, :p_start_date, :p_end_date, :p_location_id)"
                ),
                {
                    "p_tenant_id": tenant_id,
                    "p_start_date": start_date,
                    "p_end_date": end_date,
                    "p_location_id": location_id,
                },
            )
            return result.scalar() or {}

    async def get_chart_data(
        self,
        tenant_id: str,
        start_date: str,
        end_date: str,
        granularity: str,
        location_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve time-series chart data for dashboard visualization.

        Returns aggregated metrics grouped by time periods (daily, weekly, monthly)
        suitable for rendering line charts, bar charts, and other time-series
        visualizations in the dashboard.

        Args:
            tenant_id: Unique tenant identifier for data isolation.
            start_date: Start date for chart data (YYYY-MM-DD format).
            end_date: End date for chart data (YYYY-MM-DD format).
            granularity: Time granularity for grouping. Valid values:
                - "daily": Group by day
                - "weekly": Group by week
                - "monthly": Group by month
            location_id: Optional location filter. If provided, data is limited
                to the specified location. If None, includes all locations.

        Returns:
            list[dict[str, Any]]: List of time-series data points, each containing:
                - date (str): Date/time period identifier
                - revenue (float): Revenue for this period
                - purchases (int): Number of purchases
                - visitors (int): Number of visitors
                - conversions (int): Number of conversions
                - Other period-specific metrics

            Returns empty list if no data found or on error.

        Example:
            ```python
            chart_data = await repo.get_chart_data(
                tenant_id="tenant-123",
                start_date="2024-01-01",
                end_date="2024-01-31",
                granularity="daily",
                location_id="loc-001",
            )
            # [
            #     {
            #         "date": "2024-01-01",
            #         "revenue": 4500.00,
            #         "purchases": 12,
            #         "visitors": 45,
            #         ...
            #     },
            #     ...
            # ]
            ```

        Note:
            Uses the `get_chart_data()` PostgreSQL function which efficiently
            groups and aggregates time-series data.
        """
        async with get_async_db_session(
            SERVICE_NAME, tenant_id=tenant_id
        ) as session:
            result = await session.execute(
                text(
                    "SELECT get_chart_data(:p_tenant_id, :p_start_date, :p_end_date, :p_granularity, :p_location_id)"
                ),
                {
                    "p_tenant_id": tenant_id,
                    "p_start_date": start_date,
                    "p_end_date": end_date,
                    "p_granularity": granularity,
                    "p_location_id": location_id,
                },
            )
            return result.scalar() or []

    async def get_location_stats(
        self,
        tenant_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        """
        Retrieve aggregated statistics grouped by location/branch.

        Returns performance metrics for each location, enabling comparison across
        branches and identification of top-performing locations. Used for location
        comparison charts and tables in the dashboard.

        Args:
            tenant_id: Unique tenant identifier for data isolation.
            start_date: Start date for statistics (YYYY-MM-DD format).
            end_date: End date for statistics (YYYY-MM-DD format).

        Returns:
            list[dict[str, Any]]: List of location statistics, each containing:
                - locationId (str): Unique location identifier
                - locationName (str): Display name of the location
                - revenue (float): Total revenue for this location
                - purchases (int): Number of purchases
                - visitors (int): Number of visitors
                - conversionRate (float): Conversion rate for this location
                - Other location-specific metrics

            Returns empty list if no data found or on error.

        Example:
            ```python
            location_stats = await repo.get_location_stats(
                tenant_id="tenant-123",
                start_date="2024-01-01",
                end_date="2024-01-31"
            )
            # [
            #     {
            #         "locationId": "loc-001",
            #         "locationName": "Downtown Branch",
            #         "revenue": 45000.00,
            #         "purchases": 120,
            #         "visitors": 450,
            #         "conversionRate": 0.2667,
            #         ...
            #     },
            #     ...
            # ]
            ```

        Note:
            Uses the `get_location_stats_bulk()` PostgreSQL function which
            efficiently aggregates metrics per location.
        """
        async with get_async_db_session(
            SERVICE_NAME, tenant_id=tenant_id
        ) as session:
            result = await session.execute(
                text(
                    "SELECT get_location_stats_bulk(:p_tenant_id, :p_start_date, :p_end_date)"
                ),
                {
                    "p_tenant_id": tenant_id,
                    "p_start_date": start_date,
                    "p_end_date": end_date,
                },
            )
            return result.scalar() or []
