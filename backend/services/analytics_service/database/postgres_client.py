"""
PostgreSQL client for analytics service operations
"""

import time
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import text
from sqlalchemy.orm import Session

from common.database import SessionLocal

class AnalyticsPostgresClient:
    """PostgreSQL client for analytics operations."""

    def __init__(self):
        """Initialize PostgreSQL client."""
        logger.info("Initialized Analytics PostgreSQL client")

    def get_db_session(self) -> Session:
        """Get a database session."""
        return SessionLocal()

    def test_connection(self) -> Dict[str, Any]:
        """Test the PostgreSQL connection."""
        try:
            with self.get_db_session() as session:
                # Try to query tenants table
                result = session.execute(
                    text("SELECT COUNT(*) FROM tenants LIMIT 1")
                ).scalar()
                return {
                    "success": True,
                    "message": "Connection successful",
                    "data": {"count": result},
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
    def get_locations(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Get all locations with activity."""
        try:
            with self.get_db_session() as session:
                # Get locations that have page view activity using the optimized function
                time_start = time.time()
                locations_with_activity = session.execute(
                    text(
                        """
                    SELECT * FROM get_locations_with_activity_table(:tenant_id)
                """
                    ),
                    {"tenant_id": tenant_id},
                ).fetchall()
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
    def get_dashboard_stats(
        self,
        tenant_id: str,
        location_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get dashboard statistics using RPC function."""
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

            with self.get_db_session() as session:
                result = session.execute(
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
                ).scalar()

                return result or {}

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
    def get_purchase_tasks(
        self,
        tenant_id: str,
        page: int,
        limit: int,
        query: Optional[str] = None,
        location_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get purchase analysis tasks with pagination and filtering."""
        try:
            with self.get_db_session() as session:
                # Use the existing RPC function from functions.sql
                result = session.execute(
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
                ).scalar()

                return result or {
                    "data": [],
                    "total": 0,
                    "page": page,
                    "limit": limit,
                    "has_more": False,
                }

        except Exception as e:
            logger.error(f"Error fetching purchase tasks: {e}")
            raise

    def get_cart_abandonment_tasks(
        self,
        tenant_id: str,
        page: int,
        limit: int,
        query: Optional[str] = None,
        location_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get cart abandonment tasks using the RPC function."""
        try:
            with self.get_db_session() as session:
                result = session.execute(
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
                ).scalar()

                return result or {
                    "data": [],
                    "total": 0,
                    "page": page,
                    "limit": limit,
                    "has_more": False,
                }

        except Exception as e:
            logger.error(f"Error fetching cart abandonment tasks via RPC: {e}")
            raise

    def get_search_analysis_tasks(
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
        """Get search analysis tasks using the RPC function."""
        try:
            with self.get_db_session() as session:
                result = session.execute(
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
                ).scalar()

                return result or {
                    "data": [],
                    "total": 0,
                    "page": page,
                    "limit": limit,
                    "has_more": False,
                }

        except Exception as e:
            logger.error(f"Error fetching search analysis tasks via RPC: {e}")
            raise

    def get_repeat_visit_tasks(
        self,
        tenant_id: str,
        page: int,
        limit: int,
        query: Optional[str] = None,
        location_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get repeat visit tasks using the RPC function."""
        try:
            with self.get_db_session() as session:
                result = session.execute(
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
                ).scalar()

                return result or {
                    "data": [],
                    "total": 0,
                    "page": page,
                    "limit": limit,
                    "has_more": False,
                }

        except Exception as e:
            logger.error(f"Error fetching repeat visit tasks via RPC: {e}")
            raise

    def get_performance_tasks(
        self,
        tenant_id: str,
        page: int,
        limit: int,
        location_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get performance tasks using the RPC function."""
        try:
            with self.get_db_session() as session:
                result = session.execute(
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
                ).scalar()

                return result or {
                    "data": [],
                    "total": 0,
                    "page": page,
                    "limit": limit,
                    "has_more": False,
                }

        except Exception as e:
            logger.error(f"Error fetching performance tasks via RPC: {e}")
            raise

    def get_session_history(
        self, tenant_id: str, session_id: str
    ) -> List[Dict[str, Any]]:
        """Get the event history for a specific session using the RPC function."""
        try:
            with self.get_db_session() as session:
                result = session.execute(
                    text(
                        """
                    SELECT get_session_history(:p_tenant_id, :p_session_id)
                """
                    ),
                    {"p_tenant_id": tenant_id, "p_session_id": session_id},
                ).scalar()

                return result or []

        except Exception as e:
            logger.error(
                f"Error fetching session history for session {session_id}: {e}"
            )
            raise

    def get_user_history(self, tenant_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Get the event history for a specific user using the RPC function."""
        try:
            with self.get_db_session() as session:
                result = session.execute(
                    text(
                        """
                    SELECT get_user_history(:p_tenant_id, :p_user_id)
                """
                    ),
                    {"p_tenant_id": tenant_id, "p_user_id": user_id},
                ).scalar()

                return result or []

        except Exception as e:
            logger.error(f"Error fetching user history for user {user_id}: {e}")
            raise

    def get_location_stats_bulk(
        self, tenant_id: str, start_date: str, end_date: str
    ) -> List[Dict[str, Any]]:
        """Get bulk statistics for all locations using the RPC function."""
        try:
            with self.get_db_session() as session:
                result = session.execute(
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
                ).scalar()

                return result or []

        except Exception as e:
            logger.error(f"Error fetching bulk location stats: {e}")
            raise

    def get_chart_data(
        self,
        tenant_id: str,
        start_date: str,
        end_date: str,
        granularity: str,
        location_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get time-series chart data using the RPC function."""
        try:
            with self.get_db_session() as session:
                result = session.execute(
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
                ).scalar()

                return result or []

        except Exception as e:
            logger.error(f"Error fetching chart data: {e}")
            raise

    def get_complete_dashboard_data(
        self,
        tenant_id: str,
        start_date: str,
        end_date: str,
        granularity: str = "daily",
        location_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get complete dashboard data in a single optimized call."""
        try:
            with self.get_db_session() as session:
                result = session.execute(
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
                ).scalar()

                return result or {"metrics": {}, "chartData": [], "locationStats": []}

        except Exception as e:
            logger.error(f"Error fetching complete dashboard data: {e}")
            raise
