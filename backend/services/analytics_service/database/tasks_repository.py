"""
Tasks Repository for Analytics Service

This module provides database operations for task-related queries in the
Analytics Service. Tasks represent actionable insights derived from analytics
data, including purchase follow-ups, cart abandonments, search analysis,
repeat visits, and branch performance.

Example:
    ```python
    repo = TasksRepository()
    tasks = await repo.get_purchase_tasks("tenant-123", page=1, limit=50)
    ```

See Also:
    - services.analytics_service.database.base: Shared constants
    - common.database.get_async_db_session: Database session management
"""

from typing import Any

from loguru import logger
from sqlalchemy import text

from common.database import get_async_db_session

from .base import SERVICE_NAME


class TasksRepository:
    """
    Repository for task-related database operations.

    This class provides methods for querying various task types used in the
    analytics dashboard. Tasks are derived from analytics events and represent
    actionable items for sales teams.

    Thread Safety:
        This repository is thread-safe and can be used concurrently across
        multiple async tasks. Each method creates its own database session.

    Example:
        ```python
        repo = TasksRepository()
        tasks = await repo.get_cart_abandonment_tasks(
            "tenant-123", page=1, limit=50, location_id="loc-001"
        )
        ```
    """

    async def get_purchase_tasks(
        self,
        tenant_id: str,
        page: int,
        limit: int,
        query: str | None = None,
        location_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """
        Retrieve paginated purchase analysis tasks with optional filtering.

        Purchase tasks identify customers who have made purchases and may benefit
        from follow-up engagement or cross-selling opportunities. This method
        provides paginated results with flexible filtering options.

        Args:
            tenant_id: Unique tenant identifier for data isolation.
            page: Page number (1-indexed) for pagination.
            limit: Maximum number of items per page.
            query: Optional search query to filter by customer name, email, or
                company. Performs case-insensitive partial matching.
            location_id: Optional location filter to restrict results to a
                specific branch/location.
            start_date: Optional start date filter (YYYY-MM-DD format). If provided,
                only includes purchases on or after this date.
            end_date: Optional end date filter (YYYY-MM-DD format). If provided,
                only includes purchases on or before this date.

        Returns:
            dict[str, Any]: Paginated response containing:
                - data (list[dict]): List of purchase task objects
                - total (int): Total number of matching tasks across all pages
                - page (int): Current page number
                - limit (int): Items per page
                - has_more (bool): Whether more pages are available

        Note:
            Uses the `get_purchase_tasks()` PostgreSQL function for optimized
            query execution with proper indexing.
        """
        try:
            async with get_async_db_session(
                SERVICE_NAME, tenant_id=tenant_id
            ) as session:
                # Use the existing RPC function from functions.sql
                result = await session.execute(
                    text(
                        """
                    SELECT get_purchase_tasks(:p_tenant_id, :p_page, :p_limit, :p_query, :p_location_id, :p_start_date, :p_end_date)
                """
                    ),
                    {
                        "p_tenant_id": tenant_id,
                        "p_page": page,
                        "p_limit": limit,
                        "p_query": query,
                        "p_location_id": location_id,
                        "p_start_date": start_date,
                        "p_end_date": end_date,
                    },
                )
                tasks = result.scalar()

                return tasks or {
                    "data": [],
                    "total": 0,
                    "page": page,
                    "limit": limit,
                    "has_more": False,
                }

        except Exception as e:
            logger.error(f"Error fetching purchase tasks: {e}")
            raise

    async def get_cart_abandonment_tasks(
        self,
        tenant_id: str,
        page: int,
        limit: int,
        query: str | None = None,
        location_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """
        Retrieve paginated cart abandonment tasks with optional filtering.

        Cart abandonment tasks identify sessions where users added items to their
        cart but did not complete the purchase. These represent recovery opportunities
        for sales teams to re-engage potential customers.

        Args:
            tenant_id: Unique tenant identifier for data isolation.
            page: Page number (1-indexed) for pagination.
            limit: Maximum number of items per page.
            query: Optional search query to filter by customer name, email, or
                company. Performs case-insensitive partial matching.
            location_id: Optional location filter to restrict results to a
                specific branch/location.
            start_date: Optional start date filter (YYYY-MM-DD format). If provided,
                only includes abandonments on or after this date.
            end_date: Optional end date filter (YYYY-MM-DD format). If provided,
                only includes abandonments on or before this date.

        Returns:
            dict[str, Any]: Paginated response containing:
                - data (list[dict]): List of cart abandonment task objects with
                  session details, cart contents, and customer information
                - total (int): Total number of matching tasks across all pages
                - page (int): Current page number
                - limit (int): Items per page
                - has_more (bool): Whether more pages are available

        Note:
            Uses the `get_cart_abandonment_tasks()` PostgreSQL function which
            identifies sessions with add_to_cart events but no corresponding
            purchase events.
        """
        try:
            async with get_async_db_session(
                SERVICE_NAME, tenant_id=tenant_id
            ) as session:
                result = await session.execute(
                    text(
                        """
                    SELECT get_cart_abandonment_tasks(:p_tenant_id, :p_page, :p_limit, :p_query, :p_location_id, :p_start_date, :p_end_date)
                """
                    ),
                    {
                        "p_tenant_id": tenant_id,
                        "p_page": page,
                        "p_limit": limit,
                        "p_query": query,
                        "p_location_id": location_id,
                        "p_start_date": start_date,
                        "p_end_date": end_date,
                    },
                )
                tasks = result.scalar()

                return tasks or {
                    "data": [],
                    "total": 0,
                    "page": page,
                    "limit": limit,
                    "has_more": False,
                }

        except Exception as e:
            logger.error(f"Error fetching cart abandonment tasks via RPC: {e}")
            raise

    async def get_search_analysis_tasks(
        self,
        tenant_id: str,
        page: int,
        limit: int,
        query: str | None = None,
        location_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        include_converted: bool = False,
    ) -> dict[str, Any]:
        """
        Retrieve paginated search analysis tasks with optional filtering.

        Search analysis tasks provide insights into user search behavior, including
        searches that returned no results (failed searches) and search patterns
        that led to conversions. This helps identify product gaps and optimization
        opportunities.

        Args:
            tenant_id: Unique tenant identifier for data isolation.
            page: Page number (1-indexed) for pagination.
            limit: Maximum number of items per page.
            query: Optional search query to filter by search term or customer
                information. Performs case-insensitive partial matching.
            location_id: Optional location filter to restrict results to a
                specific branch/location.
            start_date: Optional start date filter (YYYY-MM-DD format). If provided,
                only includes searches on or after this date.
            end_date: Optional end date filter (YYYY-MM-DD format). If provided,
                only includes searches on or before this date.
            include_converted: If True, includes searches that resulted in purchases.
                If False (default), only includes searches without conversions.

        Returns:
            dict[str, Any]: Paginated response containing:
                - data (list[dict]): List of search analysis task objects with
                  search terms, result counts, conversion status, and session details
                - total (int): Total number of matching tasks across all pages
                - page (int): Current page number
                - limit (int): Items per page
                - has_more (bool): Whether more pages are available

        Note:
            Uses the `get_search_analysis_tasks()` PostgreSQL function which
            analyzes view_search_results and no_search_results events.
        """
        try:
            async with get_async_db_session(
                SERVICE_NAME, tenant_id=tenant_id
            ) as session:
                result = await session.execute(
                    text(
                        """
                    SELECT get_search_analysis_tasks(:p_tenant_id, :p_page, :p_limit, :p_query, :p_location_id, :p_start_date, :p_end_date, :p_include_converted)
                """
                    ),
                    {
                        "p_tenant_id": tenant_id,
                        "p_page": page,
                        "p_limit": limit,
                        "p_query": query,
                        "p_location_id": location_id,
                        "p_start_date": start_date,
                        "p_end_date": end_date,
                        "p_include_converted": include_converted,
                    },
                )
                tasks = result.scalar()

                return tasks or {
                    "data": [],
                    "total": 0,
                    "page": page,
                    "limit": limit,
                    "has_more": False,
                }

        except Exception as e:
            logger.error(f"Error fetching search analysis tasks via RPC: {e}")
            raise

    async def get_repeat_visit_tasks(
        self,
        tenant_id: str,
        page: int,
        limit: int,
        query: str | None = None,
        location_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """
        Retrieve paginated repeat visit tasks with optional filtering.

        Repeat visit tasks identify users who have visited multiple times, indicating
        high engagement or potential for loyalty programs. These users may benefit
        from personalized offers or VIP treatment.

        Args:
            tenant_id: Unique tenant identifier for data isolation.
            page: Page number (1-indexed) for pagination.
            limit: Maximum number of items per page.
            query: Optional search query to filter by user name, email, or company.
                Performs case-insensitive partial matching.
            location_id: Optional location filter to restrict results to a
                specific branch/location.
            start_date: Optional start date filter (YYYY-MM-DD format). If provided,
                only includes repeat visits on or after this date.
            end_date: Optional end date filter (YYYY-MM-DD format). If provided,
                only includes repeat visits on or before this date.

        Returns:
            dict[str, Any]: Paginated response containing:
                - data (list[dict]): List of repeat visit task objects with
                  user information, visit counts, purchase history, and engagement
                  metrics
                - total (int): Total number of matching tasks across all pages
                - page (int): Current page number
                - limit (int): Items per page
                - has_more (bool): Whether more pages are available

        Note:
            Uses the `get_repeat_visit_tasks()` PostgreSQL function which
            identifies users with multiple sessions within the date range.
        """
        try:
            async with get_async_db_session(
                SERVICE_NAME, tenant_id=tenant_id
            ) as session:
                result = await session.execute(
                    text(
                        """
                    SELECT get_repeat_visit_tasks(:p_tenant_id, :p_page, :p_limit, :p_query, :p_location_id, :p_start_date, :p_end_date)
                """
                    ),
                    {
                        "p_tenant_id": tenant_id,
                        "p_page": page,
                        "p_limit": limit,
                        "p_query": query,
                        "p_location_id": location_id,
                        "p_start_date": start_date,
                        "p_end_date": end_date,
                    },
                )
                tasks = result.scalar()

                return tasks or {
                    "data": [],
                    "total": 0,
                    "page": page,
                    "limit": limit,
                    "has_more": False,
                }

        except Exception as e:
            logger.error(f"Error fetching repeat visit tasks via RPC: {e}")
            raise

    async def get_performance_tasks(
        self,
        tenant_id: str,
        page: int,
        limit: int,
        location_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """
        Retrieve paginated branch performance tasks with optional filtering.

        Performance tasks provide aggregated metrics for each branch/location,
        including revenue, visitor counts, conversion rates, and other KPIs.
        This helps identify top-performing locations and areas for improvement.

        Args:
            tenant_id: Unique tenant identifier for data isolation.
            page: Page number (1-indexed) for pagination.
            limit: Maximum number of items per page.
            location_id: Optional location filter to restrict results to a
                specific branch/location. If None, returns all locations.
            start_date: Optional start date filter (YYYY-MM-DD format). If provided,
                only includes performance data on or after this date.
            end_date: Optional end date filter (YYYY-MM-DD format). If provided,
                only includes performance data on or before this date.

        Returns:
            dict[str, Any]: Paginated response containing:
                - data (list[dict]): List of performance task objects with
                  location details, revenue, visitor counts, conversion rates,
                  and other performance metrics
                - total (int): Total number of matching tasks across all pages
                - page (int): Current page number
                - limit (int): Items per page
                - has_more (bool): Whether more pages are available

        Note:
            Uses the `get_performance_tasks()` PostgreSQL function which
            aggregates metrics from multiple event tables.
        """
        try:
            async with get_async_db_session(
                SERVICE_NAME, tenant_id=tenant_id
            ) as session:
                result = await session.execute(
                    text(
                        """
                    SELECT get_performance_tasks(:p_tenant_id, :p_page, :p_limit, :p_location_id, :p_start_date, :p_end_date)
                """
                    ),
                    {
                        "p_tenant_id": tenant_id,
                        "p_page": page,
                        "p_limit": limit,
                        "p_location_id": location_id,
                        "p_start_date": start_date,
                        "p_end_date": end_date,
                    },
                )
                tasks = result.scalar()

                return tasks or {
                    "data": [],
                    "total": 0,
                    "page": page,
                    "limit": limit,
                    "has_more": False,
                }

        except Exception as e:
            logger.error(f"Error fetching performance tasks via RPC: {e}")
            raise
