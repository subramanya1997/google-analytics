"""
PostgreSQL Client for Analytics Service Database Operations

This module provides a high-level database client interface for all analytics
service database operations. It encapsulates PostgreSQL function calls and
provides a clean API for querying analytics data, managing email configurations,
and handling task-related queries.

Architecture:
    The client uses PostgreSQL stored functions (RPC functions) for all complex
    queries to ensure optimal performance and maintainability. These functions
    are defined in backend/database/functions/ and handle:
    - Aggregated statistics and metrics
    - Paginated task queries with filtering
    - Historical event tracking
    - Email job and history management

Multi-Tenancy:
    All methods accept a tenant_id parameter which is used to ensure complete
    data isolation at the database level. The database session is configured
    with tenant-specific connection parameters.

Performance:
    - Uses async database sessions for non-blocking I/O
    - Leverages PostgreSQL functions for optimized query execution
    - Implements pagination for large result sets
    - Uses connection pooling via SQLAlchemy

Error Handling:
    Database errors are logged and re-raised to be handled by the API layer.
    The client does not suppress exceptions to ensure proper error propagation.

Example:
    ```python
    client = AnalyticsPostgresClient()
    
    # Get dashboard statistics
    stats = await client.get_overview_stats(
        tenant_id="tenant-123",
        start_date="2024-01-01",
        end_date="2024-01-31"
    )
    
    # Get paginated purchase tasks
    tasks = await client.get_purchase_tasks(
        tenant_id="tenant-123",
        page=1,
        limit=50,
        location_id="loc-456"
    )
    ```

See Also:
    - backend/database/functions/: PostgreSQL function definitions
    - common.database.session: Database session management
    - services.analytics_service.database.dependencies: Dependency injection
"""

from typing import Any

from loguru import logger
from sqlalchemy import text

from common.database import get_async_db_session


class AnalyticsPostgresClient:
    """
    PostgreSQL Client for Analytics Service Database Operations.

    This class provides a comprehensive interface for all database operations
    required by the analytics service. It encapsulates PostgreSQL function calls
    and provides type-safe methods for querying analytics data.

    The client is designed to be used as a singleton via dependency injection.
    All methods are async and use connection pooling for optimal performance.

    Attributes:
        None (stateless client, uses connection pool)

    Thread Safety:
        This client is thread-safe and can be used concurrently across multiple
        async tasks. Each method creates its own database session.

    Example:
        ```python
        # Via dependency injection (recommended)
        @router.get("/stats")
        async def get_stats(
            tenant_id: str = Depends(get_tenant_id),
            db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client)
        ):
            return await db_client.get_overview_stats(tenant_id, ...)
        ```

    See Also:
        - services.analytics_service.database.dependencies.get_analytics_db_client:
            Dependency injection function
    """

    def __init__(self) -> None:
        """
        Initialize the Analytics PostgreSQL client.

        This is a lightweight initialization that only logs the client creation.
        Actual database connections are created on-demand when methods are called.
        """
        logger.info("Initialized Analytics PostgreSQL client")

    # Location operations
    async def get_locations(self, tenant_id: str) -> list[dict[str, Any]]:
        """
        Retrieve all active locations (branches) for a tenant.

        Returns locations that have analytics activity (page views) within the
        tenant's data. This is used to populate location filters in the dashboard
        and other UI components.

        Args:
            tenant_id: Unique tenant identifier for data isolation.

        Returns:
            list[dict[str, Any]]: List of location dictionaries, each containing:
                - locationId (str): Unique location identifier
                - locationName (str): Display name of the location
                - city (str | None): City name if available
                - state (str | None): State/province name if available

            Returns empty list if no locations found or on error.

        Raises:
            Exception: Database connection or query errors are logged and
                re-raised. Returns empty list on error to prevent API failures.

        Example:
            ```python
            locations = await client.get_locations("tenant-123")
            # [
            #     {
            #         "locationId": "loc-001",
            #         "locationName": "Downtown Branch",
            #         "city": "San Francisco",
            #         "state": "CA"
            #     },
            #     ...
            # ]
            ```

        Note:
            Uses the `get_locations()` PostgreSQL function which optimizes
            the query by filtering only locations with activity.
        """
        try:
            async with get_async_db_session(
                "analytics-service", tenant_id=tenant_id
            ) as session:
                # Get all active locations using the optimized function
                result = await session.execute(
                    text(
                        """
                    SELECT * FROM get_locations(:tenant_id)
                """
                    ),
                    {"tenant_id": tenant_id},
                )
                locations_data = result.fetchall()

                locations = []
                for location in locations_data:
                    locations.append(
                        {
                            "locationId": location.location_id,
                            "locationName": location.location_name,
                            "city": location.city,
                            "state": location.state,
                        }
                    )

                return locations

        except Exception as e:
            logger.error(f"Error fetching locations: {e}")
            return []

    # Task list operations using RPC functions
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

            Returns default empty structure if no tasks found or on error.

        Raises:
            Exception: Database errors are logged and re-raised. Callers should
                handle exceptions appropriately.

        Example:
            ```python
            result = await client.get_purchase_tasks(
                tenant_id="tenant-123",
                page=1,
                limit=50,
                location_id="loc-001",
                start_date="2024-01-01",
                end_date="2024-01-31"
            )
            # {
            #     "data": [...],
            #     "total": 150,
            #     "page": 1,
            #     "limit": 50,
            #     "has_more": True
            # }
            ```

        Note:
            Uses the `get_purchase_tasks()` PostgreSQL function for optimized
            query execution with proper indexing.
        """
        try:
            async with get_async_db_session(
                "analytics-service", tenant_id=tenant_id
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

            Returns default empty structure if no tasks found or on error.

        Raises:
            Exception: Database errors are logged and re-raised.

        Example:
            ```python
            result = await client.get_cart_abandonment_tasks(
                tenant_id="tenant-123",
                page=1,
                limit=50,
                start_date="2024-01-01"
            )
            ```

        Note:
            Uses the `get_cart_abandonment_tasks()` PostgreSQL function which
            identifies sessions with add_to_cart events but no corresponding
            purchase events.
        """
        try:
            async with get_async_db_session(
                "analytics-service", tenant_id=tenant_id
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

            Returns default empty structure if no tasks found or on error.

        Raises:
            Exception: Database errors are logged and re-raised.

        Example:
            ```python
            # Get failed searches only
            result = await client.get_search_analysis_tasks(
                tenant_id="tenant-123",
                page=1,
                limit=50,
                include_converted=False
            )
            
            # Get all searches including converted ones
            result = await client.get_search_analysis_tasks(
                tenant_id="tenant-123",
                include_converted=True
            )
            ```

        Note:
            Uses the `get_search_analysis_tasks()` PostgreSQL function which
            analyzes view_search_results and no_search_results events.
        """
        try:
            async with get_async_db_session(
                "analytics-service", tenant_id=tenant_id
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

            Returns default empty structure if no tasks found or on error.

        Raises:
            Exception: Database errors are logged and re-raised.

        Example:
            ```python
            result = await client.get_repeat_visit_tasks(
                tenant_id="tenant-123",
                page=1,
                limit=50,
                query="Acme Corp"
            )
            ```

        Note:
            Uses the `get_repeat_visit_tasks()` PostgreSQL function which
            identifies users with multiple sessions within the date range.
        """
        try:
            async with get_async_db_session(
                "analytics-service", tenant_id=tenant_id
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

            Returns default empty structure if no tasks found or on error.

        Raises:
            Exception: Database errors are logged and re-raised.

        Example:
            ```python
            # Get all branch performance
            result = await client.get_performance_tasks(
                tenant_id="tenant-123",
                page=1,
                limit=50,
                start_date="2024-01-01",
                end_date="2024-01-31"
            )
            
            # Get specific branch performance
            result = await client.get_performance_tasks(
                tenant_id="tenant-123",
                location_id="loc-001"
            )
            ```

        Note:
            Uses the `get_performance_tasks()` PostgreSQL function which
            aggregates metrics from multiple event tables.
        """
        try:
            async with get_async_db_session(
                "analytics-service", tenant_id=tenant_id
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

    async def get_session_history(
        self, tenant_id: str, session_id: str
    ) -> list[dict[str, Any]]:
        """
        Retrieve the complete event history for a specific session.

        Returns a chronological timeline of all events (page views, searches,
        cart additions, purchases, etc.) that occurred during a single user
        session. This is useful for debugging, customer support, and understanding
        user behavior patterns.

        Args:
            tenant_id: Unique tenant identifier for data isolation.
            session_id: Unique session identifier to retrieve history for.

        Returns:
            list[dict[str, Any]]: Chronologically ordered list of event objects,
            each containing:
                - event_type (str): Type of event (page_view, purchase, etc.)
                - timestamp (datetime): When the event occurred
                - event_data (dict): Event-specific data (page URL, product info, etc.)
                - user_id (str): User identifier associated with the session

            Returns empty list if session not found or on error.

        Raises:
            Exception: Database errors are logged and re-raised.

        Example:
            ```python
            events = await client.get_session_history(
                tenant_id="tenant-123",
                session_id="session-abc-123"
            )
            # [
            #     {
            #         "event_type": "page_view",
            #         "timestamp": "2024-01-15T10:30:00Z",
            #         "page_url": "/products/widget",
            #         ...
            #     },
            #     {
            #         "event_type": "add_to_cart",
            #         "timestamp": "2024-01-15T10:35:00Z",
            #         "product_id": "prod-123",
            #         ...
            #     },
            #     ...
            # ]
            ```

        Note:
            Uses the `get_session_history()` PostgreSQL function which
            efficiently queries multiple event tables and orders by timestamp.
        """
        try:
            async with get_async_db_session(
                "analytics-service", tenant_id=tenant_id
            ) as session:
                result = await session.execute(
                    text(
                        """
                    SELECT get_session_history(:p_tenant_id, :p_session_id)
                """
                    ),
                    {"p_tenant_id": tenant_id, "p_session_id": session_id},
                )
                history = result.scalar()

                return history or []

        except Exception as e:
            logger.error(
                f"Error fetching session history for session {session_id}: {e}"
            )
            raise

    async def get_user_history(
        self, tenant_id: str, user_id: str
    ) -> list[dict[str, Any]]:
        """
        Retrieve the complete event history for a specific user across all sessions.

        Returns a chronological timeline of all events associated with a user
        across all their sessions. This provides a comprehensive view of a user's
        entire journey and engagement history with the platform.

        Args:
            tenant_id: Unique tenant identifier for data isolation.
            user_id: Unique user identifier to retrieve history for.

        Returns:
            list[dict[str, Any]]: Chronologically ordered list of event objects
            across all sessions, each containing:
                - event_type (str): Type of event (page_view, purchase, etc.)
                - timestamp (datetime): When the event occurred
                - session_id (str): Session identifier for the event
                - event_data (dict): Event-specific data
                - location_id (str): Location where the event occurred

            Returns empty list if user not found or on error.

        Raises:
            Exception: Database errors are logged and re-raised.

        Example:
            ```python
            events = await client.get_user_history(
                tenant_id="tenant-123",
                user_id="user-xyz-789"
            )
            # Returns all events across all sessions for this user
            ```

        Note:
            Uses the `get_user_history()` PostgreSQL function which queries
            multiple event tables and orders by timestamp across all sessions.
            This can return large result sets for highly active users.
        """
        try:
            async with get_async_db_session(
                "analytics-service", tenant_id=tenant_id
            ) as session:
                result = await session.execute(
                    text(
                        """
                    SELECT get_user_history(:p_tenant_id, :p_user_id)
                """
                    ),
                    {"p_tenant_id": tenant_id, "p_user_id": user_id},
                )
                history = result.scalar()

                return history or []

        except Exception as e:
            logger.error(f"Error fetching user history for user {user_id}: {e}")
            raise

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

        Raises:
            Exception: Database errors are logged and re-raised.

        Example:
            ```python
            stats = await client.get_overview_stats(
                tenant_id="tenant-123",
                start_date="2024-01-01",
                end_date="2024-01-31",
                location_id="loc-001"
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
            "analytics-service", tenant_id=tenant_id
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

        Raises:
            Exception: Database errors are logged and re-raised.

        Example:
            ```python
            chart_data = await client.get_chart_data(
                tenant_id="tenant-123",
                start_date="2024-01-01",
                end_date="2024-01-31",
                granularity="daily",
                location_id="loc-001"
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
            "analytics-service", tenant_id=tenant_id
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

        Raises:
            Exception: Database errors are logged and re-raised.

        Example:
            ```python
            location_stats = await client.get_location_stats(
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
            "analytics-service", tenant_id=tenant_id
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

    # ======================================
    # EMAIL CONFIGURATION METHODS
    # ======================================

    async def get_email_config(self, tenant_id: str) -> dict[str, Any] | None:
        """
        Retrieve SMTP email configuration for a tenant.

        Returns the email/SMTP configuration stored in the tenant_config table,
        which is used for sending automated analytics reports to sales representatives.

        Args:
            tenant_id: Unique tenant identifier for data isolation.

        Returns:
            dict[str, Any] | None: Email configuration dictionary containing:
                - server (str): SMTP server hostname
                - port (int): SMTP server port (typically 587 for TLS)
                - from_address (str): Sender email address
                - username (str): SMTP authentication username
                - password (str): SMTP authentication password (should be masked
                  when returned to API clients)
                - use_tls (bool): Whether to use TLS encryption

            Returns None if no configuration found or on error.

        Raises:
            Exception: Database errors are logged. Returns None on error to
                prevent API failures.

        Example:
            ```python
            config = await client.get_email_config("tenant-123")
            # {
            #     "server": "smtp.example.com",
            #     "port": 587,
            #     "from_address": "reports@company.com",
            #     "username": "smtp_user",
            #     "password": "***",
            #     "use_tls": True
            # }
            ```

        Security Note:
            The password field should be masked when returning configuration
            to API clients. See the email endpoint implementation for masking logic.
        """
        try:
            async with get_async_db_session(
                "analytics-service", tenant_id=tenant_id
            ) as session:
                result = await session.execute(
                    text(
                        "SELECT email_config FROM tenant_config WHERE id = :tenant_id"
                    ),
                    {"tenant_id": tenant_id},
                )
                email_config = result.scalar()

                if email_config:
                    import json

                    return (
                        json.loads(email_config)
                        if isinstance(email_config, str)
                        else email_config
                    )
                return None

        except Exception as e:
            logger.error(f"Error fetching email config for tenant {tenant_id}: {e}")
            return None

    # ======================================
    # BRANCH EMAIL MAPPING METHODS
    # ======================================

    async def get_branch_email_mappings(
        self, tenant_id: str, branch_code: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Retrieve branch-to-email mappings for a tenant.

        Branch email mappings define which sales representatives should receive
        automated analytics reports for which branches. This enables targeted
        report distribution based on branch assignments.

        Args:
            tenant_id: Unique tenant identifier for data isolation.
            branch_code: Optional branch code filter. If provided, only returns
                mappings for the specified branch. If None, returns all mappings.

        Returns:
            list[dict[str, Any]]: List of mapping dictionaries, each containing:
                - id (str): Unique mapping identifier
                - branch_code (str): Branch/location code
                - branch_name (str | None): Display name of the branch
                - sales_rep_email (str): Email address of the sales representative
                - sales_rep_name (str | None): Name of the sales representative
                - is_enabled (bool): Whether this mapping is active
                - created_at (datetime): When the mapping was created
                - updated_at (datetime): When the mapping was last updated

            Returns empty list if no mappings found or on error.

        Raises:
            Exception: Database errors are logged. Returns empty list on error.

        Example:
            ```python
            # Get all mappings
            mappings = await client.get_branch_email_mappings("tenant-123")
            
            # Get mappings for specific branch
            mappings = await client.get_branch_email_mappings(
                "tenant-123",
                branch_code="BRANCH-001"
            )
            ```

        Note:
            Results are ordered by branch_code and sales_rep_email for consistent
            presentation in UI components.
        """
        try:
            async with get_async_db_session(
                "analytics-service", tenant_id=tenant_id
            ) as session:
                query = """
                    SELECT id, branch_code, branch_name, sales_rep_email,
                           sales_rep_name, is_enabled, created_at, updated_at
                    FROM branch_email_mappings
                    WHERE tenant_id = :tenant_id
                """
                params = {"tenant_id": tenant_id}

                if branch_code:
                    query += " AND branch_code = :branch_code"
                    params["branch_code"] = branch_code

                query += " ORDER BY branch_code, sales_rep_email"

                result = await session.execute(text(query), params)
                results = result.fetchall()

                mappings = []
                for row in results:
                    mappings.append(
                        {
                            "id": str(row.id),
                            "branch_code": row.branch_code,
                            "branch_name": row.branch_name,
                            "sales_rep_email": row.sales_rep_email,
                            "sales_rep_name": row.sales_rep_name,
                            "is_enabled": row.is_enabled,
                            "created_at": row.created_at,
                            "updated_at": row.updated_at,
                        }
                    )

                return mappings

        except Exception as e:
            logger.error(f"Error fetching branch email mappings: {e}")
            return []

    async def create_branch_email_mapping(
        self, tenant_id: str, mapping: Any
    ) -> dict[str, Any]:
        """
        Create a new branch-to-email mapping for a tenant.

        Creates a mapping that associates a branch/location with a sales
        representative's email address for automated report distribution.

        Args:
            tenant_id: Unique tenant identifier for data isolation.
            mapping: Mapping data, either a Pydantic model instance or dictionary
                containing:
                - branch_code (str): Branch/location code (required)
                - branch_name (str | None): Display name of the branch
                - sales_rep_email (str): Email address of sales rep (required)
                - sales_rep_name (str | None): Name of the sales representative
                - is_enabled (bool): Whether mapping is active (defaults to True)

        Returns:
            dict[str, Any]: Dictionary containing:
                - mapping_id (str): Unique identifier of the created mapping

        Raises:
            Exception: Database errors (including constraint violations) are logged
                and re-raised. Callers should handle exceptions appropriately.

        Example:
            ```python
            # Using dictionary
            result = await client.create_branch_email_mapping(
                "tenant-123",
                {
                    "branch_code": "BRANCH-001",
                    "branch_name": "Downtown Branch",
                    "sales_rep_email": "rep@company.com",
                    "sales_rep_name": "John Doe",
                    "is_enabled": True
                }
            )
            # {"mapping_id": "uuid-here"}
            ```

        Note:
            Supports both Pydantic model instances and plain dictionaries for
            flexibility in different usage contexts.
        """
        try:
            async with get_async_db_session(
                "analytics-service", tenant_id=tenant_id
            ) as session:
                # Handle both Pydantic models and dictionaries
                if hasattr(mapping, "branch_code"):
                    # Pydantic model
                    branch_code = mapping.branch_code
                    branch_name = mapping.branch_name
                    sales_rep_email = mapping.sales_rep_email
                    sales_rep_name = mapping.sales_rep_name
                    is_enabled = mapping.is_enabled
                else:
                    # Dictionary
                    branch_code = mapping["branch_code"]
                    branch_name = mapping.get("branch_name")
                    sales_rep_email = mapping["sales_rep_email"]
                    sales_rep_name = mapping.get("sales_rep_name")
                    is_enabled = mapping.get("is_enabled", True)

                result = await session.execute(
                    text("""
                        INSERT INTO branch_email_mappings (
                            tenant_id, branch_code, branch_name,
                            sales_rep_email, sales_rep_name, is_enabled
                        ) VALUES (
                            :tenant_id, :branch_code, :branch_name,
                            :sales_rep_email, :sales_rep_name, :is_enabled
                        )
                        RETURNING id
                    """),
                    {
                        "tenant_id": tenant_id,
                        "branch_code": branch_code,
                        "branch_name": branch_name,
                        "sales_rep_email": sales_rep_email,
                        "sales_rep_name": sales_rep_name,
                        "is_enabled": is_enabled,
                    },
                )
                row = result.fetchone()

                await session.commit()

                return {"mapping_id": str(row.id)}

        except Exception as e:
            logger.error(f"Error creating branch email mapping: {e}")
            raise

    async def update_branch_email_mapping(
        self, tenant_id: str, mapping_id: str, mapping: Any
    ) -> bool:
        """
        Update an existing branch-to-email mapping.

        Updates all fields of a branch email mapping identified by its unique ID.
        The updated_at timestamp is automatically set to the current time.

        Args:
            tenant_id: Unique tenant identifier for data isolation.
            mapping_id: Unique identifier of the mapping to update.
            mapping: Updated mapping data, either a Pydantic model instance or
                dictionary containing:
                - branch_code (str): Updated branch code
                - branch_name (str | None): Updated branch name
                - sales_rep_email (str): Updated sales rep email
                - sales_rep_name (str | None): Updated sales rep name
                - is_enabled (bool): Updated enabled status

        Returns:
            bool: True if the mapping was found and updated, False if the mapping
                with the given ID does not exist for this tenant.

        Raises:
            Exception: Database errors are logged and re-raised.

        Example:
            ```python
            success = await client.update_branch_email_mapping(
                "tenant-123",
                "mapping-uuid",
                {
                    "branch_code": "BRANCH-001",
                    "sales_rep_email": "newemail@company.com",
                    "is_enabled": False
                }
            )
            if not success:
                # Handle mapping not found
                pass
            ```

        Note:
            This method performs a full update of all fields. Partial updates
            should be handled at the API layer by fetching existing data first.
        """
        try:
            async with get_async_db_session(
                "analytics-service", tenant_id=tenant_id
            ) as session:
                # Handle both Pydantic models and dictionaries
                if hasattr(mapping, "branch_code"):
                    # Pydantic model
                    branch_code = mapping.branch_code
                    branch_name = mapping.branch_name
                    sales_rep_email = mapping.sales_rep_email
                    sales_rep_name = mapping.sales_rep_name
                    is_enabled = mapping.is_enabled
                else:
                    # Dictionary
                    branch_code = mapping["branch_code"]
                    branch_name = mapping.get("branch_name")
                    sales_rep_email = mapping["sales_rep_email"]
                    sales_rep_name = mapping.get("sales_rep_name")
                    is_enabled = mapping.get("is_enabled", True)

                result = await session.execute(
                    text("""
                        UPDATE branch_email_mappings SET
                            branch_code = :branch_code,
                            branch_name = :branch_name,
                            sales_rep_email = :sales_rep_email,
                            sales_rep_name = :sales_rep_name,
                            is_enabled = :is_enabled,
                            updated_at = NOW()
                        WHERE tenant_id = :tenant_id AND id = :mapping_id
                    """),
                    {
                        "tenant_id": tenant_id,
                        "mapping_id": mapping_id,
                        "branch_code": branch_code,
                        "branch_name": branch_name,
                        "sales_rep_email": sales_rep_email,
                        "sales_rep_name": sales_rep_name,
                        "is_enabled": is_enabled,
                    },
                )

                await session.commit()

                # Return True if a row was updated, False if mapping wasn't found
                return result.rowcount > 0

        except Exception as e:
            logger.error(f"Error updating branch email mapping {mapping_id}: {e}")
            raise

    async def delete_branch_email_mapping(
        self, tenant_id: str, mapping_id: str
    ) -> bool:
        """
        Delete a branch-to-email mapping by ID.

        Permanently removes a branch email mapping. This will prevent automated
        reports from being sent to the associated sales representative for the
        specified branch.

        Args:
            tenant_id: Unique tenant identifier for data isolation.
            mapping_id: Unique identifier of the mapping to delete.

        Returns:
            bool: True if the mapping was found and deleted, False if the mapping
                with the given ID does not exist for this tenant.

        Raises:
            Exception: Database errors are logged and re-raised.

        Example:
            ```python
            success = await client.delete_branch_email_mapping(
                "tenant-123",
                "mapping-uuid"
            )
            if not success:
                # Handle mapping not found
                pass
            ```

        Warning:
            This operation is irreversible. Consider disabling the mapping
            (is_enabled=False) instead if you may need to restore it later.
        """
        try:
            async with get_async_db_session(
                "analytics-service", tenant_id=tenant_id
            ) as session:
                result = await session.execute(
                    text("""
                        DELETE FROM branch_email_mappings
                        WHERE tenant_id = :tenant_id AND id = :mapping_id
                    """),
                    {"tenant_id": tenant_id, "mapping_id": mapping_id},
                )

                await session.commit()

                # Return True if a row was deleted, False if mapping wasn't found
                return result.rowcount > 0

        except Exception as e:
            logger.error(f"Error deleting branch email mapping {mapping_id}: {e}")
            raise

    # ======================================
    # EMAIL JOB METHODS
    # ======================================

    async def create_email_job(self, job_data: dict[str, Any]) -> dict[str, Any]:
        """
        Create a new email sending job record in the database.

        Email jobs track the lifecycle of automated report distribution operations.
        This method creates the initial job record with status "queued" before
        the job is processed by background workers.

        Args:
            job_data: Dictionary containing job information:
                - tenant_id (str): Tenant identifier (required)
                - job_id (str): Unique job identifier (required)
                - status (str): Initial job status, typically "queued" (required)
                - report_date (date): Date for the report being generated (required)
                - target_branches (list[str] | None): List of branch codes to
                  target, or None for all branches

        Returns:
            dict[str, Any]: Dictionary containing:
                - id (str): Database record ID
                - job_id (str): Job identifier
                - status (str): Job status

        Raises:
            Exception: Database errors are logged and re-raised.

        Example:
            ```python
            job = await client.create_email_job({
                "tenant_id": "tenant-123",
                "job_id": "email_job_abc123",
                "status": "queued",
                "report_date": date(2024, 1, 15),
                "target_branches": ["BRANCH-001", "BRANCH-002"]
            })
            ```

        Note:
            The job status will be updated by background workers as the job
            progresses through processing stages (queued -> processing -> completed).
        """
        try:
            tenant_id = job_data.get("tenant_id")
            async with get_async_db_session(
                "analytics-service", tenant_id=tenant_id
            ) as session:
                result = await session.execute(
                    text("""
                        INSERT INTO email_sending_jobs (
                            tenant_id, job_id, status, report_date,
                            target_branches
                        ) VALUES (
                            :tenant_id, :job_id, :status, :report_date,
                            :target_branches
                        )
                        RETURNING id, job_id, status
                    """),
                    {
                        "tenant_id": job_data["tenant_id"],
                        "job_id": job_data["job_id"],
                        "status": job_data["status"],
                        "report_date": job_data["report_date"],
                        "target_branches": job_data["target_branches"],
                    },
                )
                row = result.fetchone()

                await session.commit()

                return {"id": str(row.id), "job_id": row.job_id, "status": row.status}

        except Exception as e:
            logger.error(f"Error creating email job: {e}")
            raise

    async def get_email_jobs(
        self, tenant_id: str, page: int = 1, limit: int = 50, status: str | None = None
    ) -> dict[str, Any]:
        """
        Retrieve paginated email job history with optional status filtering.

        Returns a paginated list of email sending jobs, including their status,
        progress metrics, and timestamps. This is used for job monitoring and
        audit purposes.

        Args:
            tenant_id: Unique tenant identifier for data isolation.
            page: Page number (1-indexed) for pagination. Defaults to 1.
            limit: Maximum number of items per page. Defaults to 50.
            status: Optional status filter. If provided, only returns jobs with
                this status (e.g., "queued", "processing", "completed", "failed").
                If None, returns jobs with any status.

        Returns:
            dict[str, Any]: Paginated response containing:
                - data (list[dict]): List of job objects, each containing:
                    - job_id (str): Unique job identifier
                    - status (str): Current job status
                    - tenant_id (str): Tenant identifier
                    - report_date (date): Report date for this job
                    - target_branches (list[str]): Branch codes targeted
                    - total_emails (int): Total emails to send
                    - emails_sent (int): Successfully sent emails
                    - emails_failed (int): Failed email attempts
                    - error_message (str | None): Error message if job failed
                    - created_at (datetime): When job was created
                    - started_at (datetime | None): When processing started
                    - completed_at (datetime | None): When processing completed
                - total (int): Total number of matching jobs across all pages
                - page (int): Current page number
                - limit (int): Items per page
                - has_more (bool): Whether more pages are available

            Returns default empty structure if no jobs found or on error.

        Raises:
            Exception: Database errors are logged. Returns empty structure on error.

        Example:
            ```python
            # Get all jobs
            jobs = await client.get_email_jobs("tenant-123", page=1, limit=50)
            
            # Get only completed jobs
            jobs = await client.get_email_jobs(
                "tenant-123",
                page=1,
                limit=50,
                status="completed"
            )
            ```

        Performance Note:
            Uses the optimized `get_email_jobs_paginated()` PostgreSQL function
            for efficient pagination and filtering.
        """
        try:
            async with get_async_db_session(
                "analytics-service", tenant_id=tenant_id
            ) as session:
                # Calculate offset from page number
                offset = (page - 1) * limit

                # Call optimized PostgreSQL function (ULTRA FAST!)
                jobs_query = text(
                    "SELECT * FROM get_email_jobs_paginated(:tenant_id, :limit, :offset, :status)"
                )

                result = await session.execute(
                    jobs_query,
                    {
                        "tenant_id": tenant_id,
                        "limit": limit,
                        "offset": offset,
                        "status": status,
                    },
                )
                results = result.mappings().all()

                jobs = []
                total = 0

                for row in results:
                    if total == 0:  # Get total from first row
                        total = int(row.total_count)

                    # Build job data with proper type conversion
                    jobs.append(
                        {
                            "job_id": row.job_id,
                            "status": row.status,
                            "tenant_id": tenant_id,
                            "report_date": row.report_date,
                            "target_branches": row.target_branches or [],
                            "total_emails": row.total_emails or 0,
                            "emails_sent": row.emails_sent or 0,
                            "emails_failed": row.emails_failed or 0,
                            "error_message": row.error_message,
                            "created_at": row.created_at,
                            "started_at": row.started_at,
                            "completed_at": row.completed_at,
                        }
                    )

                return {
                    "data": jobs,
                    "total": total,
                    "page": page,
                    "limit": limit,
                    "has_more": (page * limit) < total,
                }

        except Exception as e:
            logger.error(f"Error fetching email jobs: {e}")
            return {
                "data": [],
                "total": 0,
                "page": page,
                "limit": limit,
                "has_more": False,
            }

    # ======================================
    # EMAIL HISTORY METHODS
    # ======================================

    async def get_email_send_history(
        self,
        tenant_id: str,
        page: int = 1,
        limit: int = 50,
        branch_code: str | None = None,
        status: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """
        Retrieve paginated email send history with comprehensive filtering.

        Returns a detailed history of individual email sends, including success/failure
        status, SMTP responses, and error messages. This provides granular visibility
        into email delivery operations for troubleshooting and auditing.

        Args:
            tenant_id: Unique tenant identifier for data isolation.
            page: Page number (1-indexed) for pagination. Defaults to 1.
            limit: Maximum number of items per page. Defaults to 50.
            branch_code: Optional branch filter. If provided, only returns emails
                sent for the specified branch.
            status: Optional status filter. If provided, only returns emails with
                this status (e.g., "sent", "failed"). If None, returns all statuses.
            start_date: Optional start date filter (YYYY-MM-DD format). If provided,
                only includes emails sent on or after this date.
            end_date: Optional end date filter (YYYY-MM-DD format). If provided,
                only includes emails sent on or before this date.

        Returns:
            dict[str, Any]: Paginated response containing:
                - data (list[dict]): List of email history objects, each containing:
                    - id (str): Unique history record ID
                    - job_id (str): Associated job identifier
                    - branch_code (str): Branch code for this email
                    - sales_rep_email (str): Recipient email address
                    - sales_rep_name (str | None): Recipient name
                    - subject (str): Email subject line
                    - report_date (date): Report date
                    - status (str): Send status ("sent", "failed", etc.)
                    - smtp_response (str | None): SMTP server response message
                    - error_message (str | None): Error message if send failed
                    - sent_at (datetime | None): When email was sent
                - total (int): Total number of matching records across all pages
                - page (int): Current page number
                - limit (int): Items per page
                - has_more (bool): Whether more pages are available

            Returns default empty structure if no history found or on error.

        Raises:
            Exception: Database errors are logged. Returns empty structure on error.

        Example:
            ```python
            # Get all email history
            history = await client.get_email_send_history("tenant-123")
            
            # Get failed emails for a specific branch
            history = await client.get_email_send_history(
                "tenant-123",
                branch_code="BRANCH-001",
                status="failed",
                start_date="2024-01-01"
            )
            ```

        Performance Note:
            Uses the optimized `get_email_send_history_paginated()` PostgreSQL
            function for efficient pagination and filtering.
        """
        try:
            async with get_async_db_session(
                "analytics-service", tenant_id=tenant_id
            ) as session:
                # Calculate offset from page number
                offset = (page - 1) * limit

                # Call optimized PostgreSQL function (ULTRA FAST!)
                result = await session.execute(
                    text(
                        "SELECT * FROM get_email_send_history_paginated(:tenant_id, :limit, :offset, :branch_code, :status, :start_date, :end_date)"
                    ),
                    {
                        "tenant_id": tenant_id,
                        "limit": limit,
                        "offset": offset,
                        "branch_code": branch_code,
                        "status": status,
                        "start_date": start_date,
                        "end_date": end_date,
                    },
                )
                results = result.mappings().all()

                history = []
                total = 0

                for row in results:
                    if total == 0:  # Get total from first row
                        total = int(row.total_count)

                    history.append(
                        {
                            "id": str(row.id),
                            "job_id": row.job_id,
                            "branch_code": row.branch_code,
                            "sales_rep_email": row.sales_rep_email,
                            "sales_rep_name": row.sales_rep_name,
                            "subject": row.subject,
                            "report_date": row.report_date,
                            "status": row.status,
                            "smtp_response": row.smtp_response,
                            "error_message": row.error_message,
                            "sent_at": row.sent_at,
                        }
                    )

                return {
                    "data": history,
                    "total": total,
                    "page": page,
                    "limit": limit,
                    "has_more": (page * limit) < total,
                }

        except Exception as e:
            logger.error(f"Error fetching email send history: {e}")
            return {
                "data": [],
                "total": 0,
                "page": page,
                "limit": limit,
                "has_more": False,
            }
