"""
PostgreSQL Client for Analytics Service.

This module provides a comprehensive database client for analytics service operations,
including dashboard statistics, task management, email configuration, and location data.

Utilizes RPC functions for optimized data retrieval and supports multi-tenant operations
with proper data isolation and filtering capabilities.
"""

import time
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import text

from common.database import get_async_db_session

class AnalyticsPostgresClient:
    """PostgreSQL database client for analytics service operations.
    
    Provides methods for retrieving dashboard statistics, managing analytics tasks,
    handling email configurations, and supporting location-based data access.
    
    All operations are multi-tenant aware and utilize optimized RPC functions
    for efficient data retrieval and processing.
    """

    def __init__(self):
        """Initialize PostgreSQL client for analytics operations.
        
        Sets up the client for database connections using the common database
        session management system. No persistent connections are maintained.
        """
        logger.info("Initialized Analytics PostgreSQL client")

    async def test_connection(self) -> Dict[str, Any]:
        """Test the PostgreSQL database connection.
        
        Validates database connectivity by attempting to query the tenants table
        and returns connection status with diagnostic information.
        
        Returns:
            Dict[str, Any]: Connection status dictionary containing:
                - success (bool): Whether connection succeeded
                - message (str): Status message describing the result
                - data (Dict/List): Query result data or empty list on failure
        """
        try:
            async with get_async_db_session("analytics-service") as session:
                # Try to query tenants table
                result = await session.execute(
                    text("SELECT COUNT(*) FROM tenants LIMIT 1")
                )
                count = result.scalar()
                return {
                    "success": True,
                    "message": "Connection successful",
                    "data": {"count": count},
                }
        except Exception as e:
            error_message = str(e)
            logger.error(f"PostgreSQL connection test failed: {error_message}")
            return {
                "success": False,
                "message": f"Connection failed: {error_message}",
                "data": [],
            }

    # Location operations
    async def get_locations(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Get all locations with recorded analytics activity for a tenant.
        
        Retrieves locations that have page view activity using optimized RPC function
        for efficient data access and proper performance monitoring.
        
        Args:
            tenant_id (str): Unique identifier for the tenant
            
        Returns:
            List[Dict[str, Any]]: List of location dictionaries containing:
                - locationId (str): Unique location identifier
                - locationName (str): Human-readable location name
                - city (Optional[str]): Location city
                - state (Optional[str]): Location state
            
        """
        try:
            async with get_async_db_session("analytics-service") as session:
                # Get locations that have page view activity using the optimized function
                time_start = time.time()
                result = await session.execute(
                    text(
                        """
                    SELECT * FROM get_locations_with_activity_table(:tenant_id)
                """
                    ),
                    {"tenant_id": tenant_id},
                )
                locations_with_activity = result.fetchall()
                time_end = time.time()
                logger.info(
                    f"Time taken to fetch locations: {time_end - time_start} seconds"
                )

                locations = []
                for location in locations_with_activity:
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

    # Analytics operations
    async def get_dashboard_stats(
        self,
        tenant_id: str,
        location_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get comprehensive dashboard statistics using optimized RPC function.
        
        Retrieves key metrics including revenue, purchases, visitors, cart abandonment,
        and search statistics with optional filtering by location and date range.
        
        Args:
            tenant_id (str): Unique identifier for the tenant
            location_id (Optional[str]): Location filter for statistics
            start_date (Optional[str]): Start date filter in YYYY-MM-DD format
            end_date (Optional[str]): End date filter in YYYY-MM-DD format
            
        Returns:
            Dict[str, Any]: Dashboard statistics containing:
                - totalRevenue (float): Total revenue amount
                - totalPurchases (int): Number of purchases
                - totalVisitors (int): Number of unique visitors
                - abandonedCarts (int): Number of abandoned carts
                - totalSearches (int): Total search queries
                - failedSearches (int): Number of failed searches
                - Additional metrics as returned by RPC function
        """
        try:
            if not start_date or not end_date:
                return {
                    "totalRevenue": 0,
                    "totalPurchases": 0,
                    "totalVisitors": 0,
                    "abandonedCarts": 0,
                    "totalSearches": 0,
                    "failedSearches": 0,
                }

            async with get_async_db_session("analytics-service") as session:
                result = await session.execute(
                    text(
                        """
                    SELECT get_dashboard_overview_stats(:p_tenant_id, :p_start_date, :p_end_date, :p_location_id)
                """
                    ),
                    {
                        "p_tenant_id": tenant_id,
                        "p_start_date": start_date,
                        "p_end_date": end_date,
                        "p_location_id": location_id,
                    },
                )
                stats = result.scalar()

                return stats or {}

        except Exception as e:
            logger.error(f"Error fetching dashboard stats: {e}")
            return {
                "totalRevenue": 0,
                "totalPurchases": 0,
                "totalVisitors": 0,
                "abandonedCarts": 0,
                "totalSearches": 0,
                "failedSearches": 0,
            }

    # Task list operations using RPC functions
    async def get_purchase_tasks(
        self,
        tenant_id: str,
        page: int,
        limit: int,
        query: Optional[str] = None,
        location_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get purchase analysis tasks with pagination and filtering.
        
        Retrieves purchase events for sales follow-up tasks with comprehensive
        filtering capabilities and pagination support.
        
        Args:
            tenant_id (str): Unique identifier for the tenant
            page (int): Page number for pagination (1-based)
            limit (int): Number of items per page
            query (Optional[str]): Search query for filtering results
            location_id (Optional[str]): Location filter
            start_date (Optional[str]): Start date filter in YYYY-MM-DD format
            end_date (Optional[str]): End date filter in YYYY-MM-DD format
            
        Returns:
            Dict[str, Any]: Paginated purchase tasks containing:
                - data (List[Dict]): Purchase task records
                - total (int): Total number of matching records
                - page (int): Current page number
                - limit (int): Items per page
                - has_more (bool): Whether more pages exist
        """
        try:
            async with get_async_db_session("analytics-service") as session:
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
        query: Optional[str] = None,
        location_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get cart abandonment tasks using the RPC function.
        
        Retrieves cart abandonment events for sales follow-up tasks with comprehensive
        filtering capabilities and pagination support.
        
        Args:
            tenant_id (str): Unique identifier for the tenant
            page (int): Page number for pagination (1-based)
            limit (int): Number of items per page
            query (Optional[str]): Search query for filtering results
            location_id (Optional[str]): Location filter
            start_date (Optional[str]): Start date filter in YYYY-MM-DD format
            end_date (Optional[str]): End date filter in YYYY-MM-DD format
            
        Returns:
            Dict[str, Any]: Paginated cart abandonment tasks containing:
                - data (List[Dict]): Cart abandonment task records
                - total (int): Total number of matching records
                - page (int): Current page number
                - limit (int): Items per page
                - has_more (bool): Whether more pages exist
                
        """
        try:
            async with get_async_db_session("analytics-service") as session:
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
        query: Optional[str] = None,
        location_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        include_converted: bool = False,
    ) -> Dict[str, Any]:
        """Get search analysis tasks with pagination and filtering.
        
        Retrieves search analytics events for sales follow-up tasks with comprehensive
        filtering capabilities and pagination support.
        
        Args:
            tenant_id (str): Unique identifier for the tenant
            page (int): Page number for pagination (1-based)
            limit (int): Number of items per page
            query (Optional[str]): Search query for filtering results
            location_id (Optional[str]): Location filter
            start_date (Optional[str]): Start date filter in YYYY-MM-DD format
            end_date (Optional[str]): End date filter in YYYY-MM-DD format
            include_converted (bool): Whether to include converted searches
            
        Returns:
            Dict[str, Any]: Paginated search analysis tasks containing:
                - data (List[Dict]): Search analysis task records
                - total (int): Total number of matching records
                - page (int): Current page number
                - limit (int): Items per page
                - has_more (bool): Whether more pages exist
                
        """
        try:
            async with get_async_db_session("analytics-service") as session:
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
        query: Optional[str] = None,
        location_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get repeat visit tasks with pagination and filtering.
        
        Retrieves repeat visit events for sales follow-up tasks with comprehensive
        filtering capabilities and pagination support.
        
        Args:
            tenant_id (str): Unique identifier for the tenant
            page (int): Page number for pagination (1-based)
            limit (int): Number of items per page
            query (Optional[str]): Search query for filtering results
            location_id (Optional[str]): Location filter
            start_date (Optional[str]): Start date filter in YYYY-MM-DD format
            end_date (Optional[str]): End date filter in YYYY-MM-DD format
            
        Returns:
            Dict[str, Any]: Paginated repeat visit tasks containing:
                - data (List[Dict]): Repeat visit task records
                - total (int): Total number of matching records
                - page (int): Current page number
                - limit (int): Items per page
                - has_more (bool): Whether more pages exist
                
        """
        try:
            async with get_async_db_session("analytics-service") as session:
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
        location_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get performance tasks with pagination and filtering.
        
        Retrieves performance metrics for sales follow-up tasks with comprehensive
        filtering capabilities and pagination support.
        
        Args:
            tenant_id (str): Unique identifier for the tenant
            page (int): Page number for pagination (1-based)
            limit (int): Number of items per page
            location_id (Optional[str]): Location filter
            start_date (Optional[str]): Start date filter in YYYY-MM-DD format
            end_date (Optional[str]): End date filter in YYYY-MM-DD format
            
        Returns:
            Dict[str, Any]: Paginated performance tasks containing:
                - data (List[Dict]): Performance task records
                - total (int): Total number of matching records
                - page (int): Current page number
                - limit (int): Items per page
                - has_more (bool): Whether more pages exist
                
        """
        try:
            async with get_async_db_session("analytics-service") as session:
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
    ) -> List[Dict[str, Any]]:
        """Get complete event history for a specific user session.
        
        Retrieves chronological sequence of events (page views, purchases, cart actions)
        for a specific session using optimized RPC function.
        
        Args:
            tenant_id (str): Unique identifier for the tenant
            session_id (str): Unique session identifier
            
        Returns:
            List[Dict[str, Any]]: Chronological list of session events containing
                event details, timestamps, and associated metadata
        """
        try:
            async with get_async_db_session("analytics-service") as session:
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

    async def get_user_history(self, tenant_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Get the event history for a specific user using the RPC function.
        
        Retrieves chronological sequence of events (page views, purchases, cart actions)
        for a specific user using optimized RPC function.
        
        Args:
            tenant_id (str): Unique identifier for the tenant
            user_id (str): Unique user identifier
            
        Returns:
            List[Dict[str, Any]]: Chronological list of user events containing
                event details, timestamps, and associated metadata
        """
        try:
            async with get_async_db_session("analytics-service") as session:
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

    async def get_location_stats_bulk(
        self, tenant_id: str, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """Get bulk statistics for all locations using the RPC function.
        
        Retrieves comprehensive analytics data for all locations with optional
        filtering by date range.
        
        Args:
            tenant_id (str): Unique identifier for the tenant
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            
        Returns:
            List[Dict[str, Any]]: List of location statistics containing:
                - locationId (str): Location identifier
                - locationName (str): Location name
                - totalVisitors (int): Total number of unique visitors
                - totalRevenue (float): Total revenue amount
                - abandonedCarts (int): Number of abandoned carts
                - totalSearches (int): Total number of search queries
                - failedSearches (int): Number of failed searches
                - Additional metrics as returned by RPC function
        """
        try:
            async with get_async_db_session("analytics-service") as session:
                result = await session.execute(
                    text(
                        """
                    SELECT get_location_stats_bulk(:p_tenant_id, :p_start_date, :p_end_date)
                """
                    ),
                    {
                        "p_tenant_id": tenant_id,
                        "p_start_date": start_date,
                        "p_end_date": end_date,
                    },
                )
                history = result.scalar()

                return history or []

        except Exception as e:
            logger.error(f"Error fetching bulk location stats: {e}")
            raise

    async def get_chart_data(
        self,
        tenant_id: str,
        start_date: str,
        end_date: str,
        granularity: str,
        location_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get time-series chart data using the RPC function.
        
        Retrieves time-series data for chart visualization including revenue,
        purchases, and other metrics with optional filtering by location.
        
        Args:
            tenant_id (str): Unique identifier for the tenant
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            granularity (str): Time granularity (daily, weekly, monthly, hourly, 4hours, 12hours)
            location_id (Optional[str]): Location filter
            
        Returns:
            List[Dict[str, Any]]: List of chart data containing:
                - locationId (str): Location identifier
                - locationName (str): Location name
                - totalVisitors (int): Total number of unique visitors
                - totalRevenue (float): Total revenue amount
                - abandonedCarts (int): Number of abandoned carts
                - totalSearches (int): Total number of search queries
                - failedSearches (int): Number of failed searches
                - Additional metrics as returned by RPC function
        """
        try:
            async with get_async_db_session("analytics-service") as session:
                result = await session.execute(
                    text(
                        """
                    SELECT get_chart_data(:p_tenant_id, :p_start_date, :p_end_date, :p_granularity, :p_location_id)
                """
                    ),
                    {
                        "p_tenant_id": tenant_id,
                        "p_start_date": start_date,
                        "p_end_date": end_date,
                        "p_granularity": granularity,
                        "p_location_id": location_id,
                    },
                )
                history = result.scalar()

                return history or []

        except Exception as e:
            logger.error(f"Error fetching chart data: {e}")
            raise

    async def get_complete_dashboard_data(
        self,
        tenant_id: str,
        start_date: str,
        end_date: str,
        granularity: str = "daily",
        location_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get complete dashboard data in a single optimized call.
        
        Retrieves comprehensive dashboard data including metrics, chart data,
        and location statistics with optional filtering by location and date range.
        
        Args:
            tenant_id (str): Unique identifier for the tenant
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            granularity (str): Time granularity (daily, weekly, monthly, hourly, 4hours, 12hours)
            location_id (Optional[str]): Location filter
            
        Returns:
            Dict[str, Any]: Complete dashboard data containing:
                - metrics (Dict): Dashboard metrics
                - chartData (List[Dict]): Time-series chart data
                - locationStats (List[Dict]): Location statistics
        """
        try:
            async with get_async_db_session("analytics-service") as session:
                result = await session.execute(
                    text(
                        """
                    SELECT get_complete_dashboard_data(:p_tenant_id, :p_start_date, :p_end_date, :p_granularity, :p_location_id)
                """
                    ),
                    {
                        "p_tenant_id": tenant_id,
                        "p_start_date": start_date,
                        "p_end_date": end_date,
                        "p_granularity": granularity,
                        "p_location_id": location_id,
                    },
                )
                dashboard_data = result.scalar()

                return dashboard_data or {"metrics": {}, "chartData": [], "locationStats": []}

        except Exception as e:
            logger.error(f"Error fetching complete dashboard data: {e}")
            raise

    # ======================================
    # EMAIL CONFIGURATION METHODS
    # ======================================

    async def get_email_config(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get SMTP email configuration for a tenant.
        
        Retrieves tenant-specific email configuration including SMTP server
        details, authentication credentials, and connection settings.
        
        Args:
            tenant_id (str): Unique identifier for the tenant
            
        Returns:
            Optional[Dict[str, Any]]: Email configuration dictionary containing:
                - server (str): SMTP server hostname
                - port (int): SMTP server port
                - username (str): SMTP authentication username
                - password (str): SMTP authentication password
                - use_tls (bool): Whether to use TLS encryption
                - use_ssl (bool): Whether to use SSL encryption
                - from_address (str): Default sender email address
                Returns None if no configuration found
        """
        try:
            async with get_async_db_session("analytics-service") as session:
                result = await session.execute(
                    text("SELECT email_config FROM tenants WHERE id = :tenant_id"),
                    {"tenant_id": tenant_id}
                )
                email_config = result.scalar()
                
                if email_config:
                    import json
                    return json.loads(email_config) if isinstance(email_config, str) else email_config
                return None
                
        except Exception as e:
            logger.error(f"Error fetching email config for tenant {tenant_id}: {e}")
            return None

    # ======================================
    # BRANCH EMAIL MAPPING METHODS
    # ======================================

    async def get_branch_email_mappings(
        self, tenant_id: str, branch_code: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get branch email mappings for a tenant.
        
        Retrieves mappings between branch codes and sales representative email
        addresses for automated report distribution.
        
        Args:
            tenant_id (str): Unique identifier for the tenant
            branch_code (Optional[str]): Branch filter
            
        Returns:
            List[Dict[str, Any]]: List of branch email mappings containing:
                - id (str): Unique identifier for the mapping
                - branch_code (str): Branch identifier
                - branch_name (Optional[str]): Human-readable branch name
                - sales_rep_email (str): Sales rep email address
                - sales_rep_name (Optional[str]): Sales rep name
                - is_enabled (bool): Whether mapping is active
                - created_at (datetime): Creation timestamp
                - updated_at (datetime): Last update timestamp
        """
        try:
            async with get_async_db_session("analytics-service") as session:
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
                    mappings.append({
                        "id": str(row.id),
                        "branch_code": row.branch_code,
                        "branch_name": row.branch_name,
                        "sales_rep_email": row.sales_rep_email,
                        "sales_rep_name": row.sales_rep_name,
                        "is_enabled": row.is_enabled,
                        "created_at": row.created_at,
                        "updated_at": row.updated_at
                    })
                
                return mappings
                
        except Exception as e:
            logger.error(f"Error fetching branch email mappings: {e}")
            return []

    async def create_branch_email_mapping(
        self, tenant_id: str, mapping: Any
    ) -> Dict[str, Any]:
        """Create a new branch-to-sales-rep email mapping.
        
        Creates a mapping between branch codes and sales representative email
        addresses for automated report distribution.
        
        Args:
            tenant_id (str): Unique identifier for the tenant
            mapping (Any): Branch mapping data (Pydantic model or dictionary) containing:
                - branch_code (str): Branch identifier
                - branch_name (Optional[str]): Human-readable branch name
                - sales_rep_email (str): Sales rep email address
                - sales_rep_name (Optional[str]): Sales rep name
                - is_enabled (bool): Whether mapping is active
                
        Returns:
            Dict[str, Any]: Created mapping result containing:
                - mapping_id (str): Unique identifier for the created mapping
    
        """
        try:
            async with get_async_db_session("analytics-service") as session:
                # Handle both Pydantic models and dictionaries
                if hasattr(mapping, 'branch_code'):
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
                        "is_enabled": is_enabled
                    }
                )
                row = result.fetchone()
                
                await session.commit()
                
                return {
                    "mapping_id": str(row.id)
                }
                
        except Exception as e:
            logger.error(f"Error creating branch email mapping: {e}")
            raise

    async def update_branch_email_mapping(
        self, tenant_id: str, mapping_id: str, mapping: Any
    ) -> bool:
        """Update a specific branch email mapping by ID.
        
        Updates an existing branch email mapping with new information.
        
        Args:
            tenant_id (str): Unique identifier for the tenant
            mapping_id (str): Unique identifier for the mapping
            mapping (Any): Branch mapping data (Pydantic model or dictionary) containing:
                - branch_code (str): Branch identifier
                - branch_name (Optional[str]): Human-readable branch name
                - sales_rep_email (str): Sales rep email address
                - sales_rep_name (Optional[str]): Sales rep name
                - is_enabled (bool): Whether mapping is active
                - created_at (datetime): Creation timestamp
                - updated_at (datetime): Last update timestamp
                
        Returns:
            bool: True if mapping was updated, False if not found
        """
        try:
            async with get_async_db_session("analytics-service") as session:
                # Handle both Pydantic models and dictionaries
                if hasattr(mapping, 'branch_code'):
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
                        "is_enabled": is_enabled
                    }
                )
                
                await session.commit()
                
                # Return True if a row was updated, False if mapping wasn't found
                return result.rowcount > 0
                
        except Exception as e:
            logger.error(f"Error updating branch email mapping {mapping_id}: {e}")
            raise

    async def delete_branch_email_mapping(self, tenant_id: str, mapping_id: str) -> bool:
        """Delete a specific branch email mapping by ID.
        
        Removes an existing branch email mapping from the database.
        
        Args:
            tenant_id (str): Unique identifier for the tenant
            mapping_id (str): Unique identifier for the mapping
        Returns:
            bool: True if mapping was deleted, False if not found
        """
        try:
            async with get_async_db_session("analytics-service") as session:
                result = await session.execute(
                    text("""
                        DELETE FROM branch_email_mappings
                        WHERE tenant_id = :tenant_id AND id = :mapping_id
                    """),
                    {"tenant_id": tenant_id, "mapping_id": mapping_id}
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

    async def create_email_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new email sending job record for tracking.
        
        Initializes a new email job entry in the database for progress tracking
        and audit purposes during automated report distribution.
        
        Args:
            job_data (Dict[str, Any]): Job initialization data containing:
                - tenant_id (str): Unique identifier for the tenant
                - job_id (str): Unique job identifier
                - status (str): Initial job status (typically 'queued')
                - report_date (date): Date for report generation
                - target_branches (List[str]): List of branch codes to process
                
        Returns:
            Dict[str, Any]: Created job information containing:
                - id (str): Database record ID
                - job_id (str): Unique job identifier
                - status (str): Current job status
        """
        try:
            async with get_async_db_session("analytics-service") as session:
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
                        "target_branches": job_data["target_branches"]
                    }
                )
                row = result.fetchone()
                
                await session.commit()
                
                return {
                    "id": str(row.id),
                    "job_id": row.job_id,
                    "status": row.status
                }
                
        except Exception as e:
            logger.error(f"Error creating email job: {e}")
            raise

    async def update_email_job_status(
        self, job_id: str, status: str, updates: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update email job status and progress information.
        
        Updates job status and optional additional fields like timing information,
        email counts, and error messages for comprehensive job tracking.
        
        Args:
            job_id (str): Unique job identifier
            status (str): New job status (queued, processing, completed, failed)
            updates (Optional[Dict[str, Any]]): Additional fields to update:
                - started_at (datetime): Job start timestamp
                - completed_at (datetime): Job completion timestamp
                - total_emails (int): Total number of emails to send
                - emails_sent (int): Number of successfully sent emails
                - emails_failed (int): Number of failed email deliveries
                - error_message (str): Error description if job failed
                
        Returns:
            bool: True if job record was updated, False if not found
            
        """
        try:
            async with get_async_db_session("analytics-service") as session:
                set_clause = "status = :status, updated_at = NOW()"
                params = {"job_id": job_id, "status": status}
                
                if updates:
                    for key, value in updates.items():
                        if key in ["started_at", "completed_at", "total_emails", 
                                 "emails_sent", "emails_failed", "error_message"]:
                            set_clause += f", {key} = :{key}"
                            params[key] = value
                
                result = await session.execute(
                    text(f"""
                        UPDATE email_sending_jobs 
                        SET {set_clause}
                        WHERE job_id = :job_id
                    """),
                    params
                )
                
                await session.commit()
                return result.rowcount > 0
                
        except Exception as e:
            logger.error(f"Error updating email job status: {e}")
            return False

    async def get_email_job_status(self, tenant_id: str, job_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive status information for a specific email job.
        
        Retrieves detailed job information including progress, timing, and error
        details for monitoring and troubleshooting email distribution jobs.
        
        Args:
            tenant_id (str): Unique identifier for the tenant
            job_id (str): Unique job identifier
            
        Returns:
            Optional[Dict[str, Any]]: Job status dictionary containing:
                - job_id (str): Unique job identifier
                - status (str): Current job status
                - tenant_id (str): Tenant identifier
                - report_date (date): Report generation date
                - target_branches (List[str]): Target branch codes
                - total_emails (int): Total emails to send
                - emails_sent (int): Successfully sent emails
                - emails_failed (int): Failed email deliveries
                - error_message (Optional[str]): Error description if failed
                - created_at (datetime): Job creation timestamp
                - started_at (Optional[datetime]): Job start timestamp
                - completed_at (Optional[datetime]): Job completion timestamp
                Returns None if job not found
            
        """
        try:
            async with get_async_db_session("analytics-service") as session:
                result = await session.execute(
                    text("""
                        SELECT job_id, status, report_date, target_branches,
                               total_emails, emails_sent, emails_failed, error_message,
                               created_at, started_at, completed_at
                        FROM email_sending_jobs 
                        WHERE tenant_id = :tenant_id AND job_id = :job_id
                    """),
                    {"tenant_id": tenant_id, "job_id": job_id}
                )
                row = result.fetchone()
                
                if row:
                    return {
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
                        "completed_at": row.completed_at
                    }
                return None
                
        except Exception as e:
            logger.error(f"Error fetching email job status: {e}")
            return None

    async def get_email_jobs(
        self, 
        tenant_id: str, 
        page: int = 1, 
        limit: int = 50,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get email job history with pagination.
        
        Retrieves email job history with pagination and filtering capabilities.
        
        Args:
            tenant_id (str): Unique identifier for the tenant
            page (int): Page number for pagination (1-based)
            limit (int): Number of items per page
            status (Optional[str]): Filter by job status
            
        Returns:
            Dict[str, Any]: Email job history containing:
                - data (List[Dict]): List of email job records
                - total (int): Total number of matching records
                - page (int): Current page number
                - limit (int): Items per page
                - has_more (bool): Whether more pages exist
                
        """
        try:
            async with get_async_db_session("analytics-service") as session:
                # Build query
                where_clause = "WHERE tenant_id = :tenant_id"
                params = {"tenant_id": tenant_id}
                
                if status:
                    where_clause += " AND status = :status"
                    params["status"] = status
                
                # Get total count
                count_result = await session.execute(
                    text(f"SELECT COUNT(*) FROM email_sending_jobs {where_clause}"),
                    params
                )
                count = count_result.scalar()
                
                # Get paginated data
                offset = (page - 1) * limit
                params.update({"limit": limit, "offset": offset})
                
                result = await session.execute(
                    text(f"""
                        SELECT job_id, status, report_date, target_branches,
                               total_emails, emails_sent, emails_failed, error_message,
                               created_at, started_at, completed_at
                        FROM email_sending_jobs 
                        {where_clause}
                        ORDER BY created_at DESC
                        LIMIT :limit OFFSET :offset
                    """),
                    params
                )
                results = result.fetchall()
                
                jobs = []
                for row in results:
                    jobs.append({
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
                        "completed_at": row.completed_at
                    })
                
                return {
                    "data": jobs,
                    "total": count,
                    "page": page,
                    "limit": limit,
                    "has_more": (page * limit) < count
                }
                
        except Exception as e:
            logger.error(f"Error fetching email jobs: {e}")
            return {"data": [], "total": 0, "page": page, "limit": limit, "has_more": False}

    # ======================================
    # EMAIL HISTORY METHODS
    # ======================================

    async def log_email_send_history(self, history_data: Dict[str, Any]) -> None:
        """Log email send history record.
        
        Logs a new email send history record for tracking email delivery metrics.
        
        Args:
            history_data (Dict[str, Any]): Email send history data containing:
                - tenant_id (str): Unique identifier for the tenant
                - job_id (str): Unique identifier for the email job
                - branch_code (str): Branch identifier
                - sales_rep_email (str): Sales rep email address
                - sales_rep_name (Optional[str]): Sales rep name
                - subject (str): Email subject
                - report_date (str): Date of the report
                - status (str): Email delivery status
                - smtp_response (Optional[str]): SMTP server response
                - error_message (Optional[str]): Error message if delivery failed
                - sent_at (datetime): Timestamp of email send
        """
        try:
            async with get_async_db_session("analytics-service") as session:
                # Ensure all required fields are present
                data = {
                    "tenant_id": history_data["tenant_id"],
                    "job_id": history_data.get("job_id"),
                    "branch_code": history_data["branch_code"],
                    "sales_rep_email": history_data["sales_rep_email"],
                    "sales_rep_name": history_data.get("sales_rep_name"),
                    "subject": history_data["subject"],
                    "report_date": history_data["report_date"],
                    "status": history_data["status"],
                    "smtp_response": history_data.get("smtp_response"),
                    "error_message": history_data.get("error_message")  # Can be None
                }
                
                await session.execute(
                    text("""
                        INSERT INTO email_send_history (
                            tenant_id, job_id, branch_code, sales_rep_email,
                            sales_rep_name, subject, report_date, status,
                            smtp_response, error_message
                        ) VALUES (
                            :tenant_id, :job_id, :branch_code, :sales_rep_email,
                            :sales_rep_name, :subject, :report_date, :status,
                            :smtp_response, :error_message
                        )
                    """),
                    data
                )
                await session.commit()
                
        except Exception as e:
            logger.error(f"Error logging email send history: {e}")

    async def get_email_send_history(
        self,
        tenant_id: str,
        page: int = 1,
        limit: int = 50,
        branch_code: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get email send history with pagination and filtering.
        
        Retrieves email send history with pagination and filtering capabilities.
        
        Args:
            tenant_id (str): Unique identifier for the tenant
            page (int): Page number for pagination (1-based)
            limit (int): Number of items per page
            branch_code (Optional[str]): Filter by branch
            status (Optional[str]): Filter by status
            start_date (Optional[str]): Filter from date (YYYY-MM-DD)
            end_date (Optional[str]): Filter to date (YYYY-MM-DD)
        Returns:
            Dict[str, Any]: Email send history containing:
                - data (List[Dict]): List of email send history records
                - total (int): Total number of matching records
                - page (int): Current page number
                - limit (int): Items per page
                - has_more (bool): Whether more pages exist
                
        Raises:
            Exception: Database errors are propagated to caller
        """
        try:
            async with get_async_db_session("analytics-service") as session:
                # Build WHERE clause
                where_conditions = ["tenant_id = :tenant_id"]
                params = {"tenant_id": tenant_id}
                
                if branch_code:
                    where_conditions.append("branch_code = :branch_code")
                    params["branch_code"] = branch_code
                    
                if status:
                    where_conditions.append("status = :status")
                    params["status"] = status
                    
                if start_date:
                    where_conditions.append("report_date >= :start_date")
                    params["start_date"] = start_date
                    
                if end_date:
                    where_conditions.append("report_date <= :end_date") 
                    params["end_date"] = end_date
                
                where_clause = "WHERE " + " AND ".join(where_conditions)
                
                # Get total count
                count_result = await session.execute(
                    text(f"SELECT COUNT(*) FROM email_send_history {where_clause}"),
                    params
                )
                count = count_result.scalar()
                
                # Get paginated data
                offset = (page - 1) * limit
                params.update({"limit": limit, "offset": offset})
                
                result = await session.execute(
                    text(f"""
                        SELECT id, job_id, branch_code, sales_rep_email, sales_rep_name,
                               subject, report_date, status, smtp_response, error_message, sent_at
                        FROM email_send_history
                        {where_clause}
                        ORDER BY sent_at DESC
                        LIMIT :limit OFFSET :offset
                    """),
                    params
                )
                results = result.fetchall()
                
                history = []
                for row in results:
                    history.append({
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
                        "sent_at": row.sent_at
                    })
                
                return {
                    "data": history,
                    "total": count,
                    "page": page,
                    "limit": limit,
                    "has_more": (page * limit) < count
                }
                
        except Exception as e:
            logger.error(f"Error fetching email send history: {e}")
            return {"data": [], "total": 0, "page": page, "limit": limit, "has_more": False}