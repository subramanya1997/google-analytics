"""
PostgreSQL client for analytics service operations
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import and_, text
from sqlalchemy.orm import Session

from common.models import (
    AddToCart,
    NoSearchResults,
    PageView,
    Purchase,
    TaskTracking
)
from services.analytics_service.database.postgres_session import SessionLocal


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
        granularity: str = "daily",
    ) -> Dict[str, Any]:
        """Get dashboard statistics using RPC function."""
        try:
            if not start_date or not end_date:
                return {
                    "totalRevenue": 0,
                    "totalPurchases": 0,
                    "totalVisitors": 0,
                    "uniqueUsers": 0,
                    "abandonedCarts": 0,
                    "totalSearches": 0,
                    "failedSearches": 0,
                    "conversionRate": 0,
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
            return self._calculate_dashboard_stats_fallback(
                tenant_id, location_id, start_date, end_date
            )

    def _calculate_dashboard_stats_fallback(
        self,
        tenant_id: str,
        location_id: Optional[str],
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> Dict[str, Any]:
        """Fallback method to calculate dashboard stats."""
        try:
            with self.get_db_session() as session:
                # Base filters
                filters = [Purchase.tenant_id == tenant_id]
                if location_id:
                    filters.append(Purchase.user_prop_default_branch_id == location_id)
                if start_date and end_date:
                    start_formatted = start_date.replace("-", "")
                    end_formatted = end_date.replace("-", "")
                    filters.append(
                        Purchase.event_date
                        >= datetime.strptime(start_formatted, "%Y%m%d").date()
                    )
                    filters.append(
                        Purchase.event_date
                        <= datetime.strptime(end_formatted, "%Y%m%d").date()
                    )

                # Purchase data
                purchases = session.query(Purchase).filter(and_(*filters)).all()
                total_revenue = sum(
                    float(p.ecommerce_purchase_revenue or 0) for p in purchases
                )
                total_purchases = len(purchases)
                purchase_sessions = set(
                    p.param_ga_session_id for p in purchases if p.param_ga_session_id
                )

                # Cart data with same filters
                cart_filters = [AddToCart.tenant_id == tenant_id]
                if location_id:
                    cart_filters.append(
                        AddToCart.user_prop_default_branch_id == location_id
                    )
                if start_date and end_date:
                    cart_filters.append(
                        AddToCart.event_date
                        >= datetime.strptime(start_formatted, "%Y%m%d").date()
                    )
                    cart_filters.append(
                        AddToCart.event_date
                        <= datetime.strptime(end_formatted, "%Y%m%d").date()
                    )

                carts = session.query(AddToCart).filter(and_(*cart_filters)).all()
                cart_sessions = set(
                    c.param_ga_session_id for c in carts if c.param_ga_session_id
                )
                abandoned_carts = len(cart_sessions - purchase_sessions)

                # Failed searches
                search_filters = [NoSearchResults.tenant_id == tenant_id]
                if location_id:
                    search_filters.append(
                        NoSearchResults.user_prop_default_branch_id == location_id
                    )
                if start_date and end_date:
                    search_filters.append(
                        NoSearchResults.event_date
                        >= datetime.strptime(start_formatted, "%Y%m%d").date()
                    )
                    search_filters.append(
                        NoSearchResults.event_date
                        <= datetime.strptime(end_formatted, "%Y%m%d").date()
                    )

                failed_searches = (
                    session.query(NoSearchResults).filter(and_(*search_filters)).count()
                )

                # Page view data for visitors and repeat visits
                pv_filters = [PageView.tenant_id == tenant_id]
                if location_id:
                    pv_filters.append(
                        PageView.user_prop_default_branch_id == location_id
                    )
                if start_date and end_date:
                    pv_filters.append(
                        PageView.event_date
                        >= datetime.strptime(start_formatted, "%Y%m%d").date()
                    )
                    pv_filters.append(
                        PageView.event_date
                        <= datetime.strptime(end_formatted, "%Y%m%d").date()
                    )

                pageviews = session.query(PageView).filter(and_(*pv_filters)).all()

                # Total Visitors (unique sessions)
                total_visitors = len(
                    set(
                        pv.param_ga_session_id
                        for pv in pageviews
                        if pv.param_ga_session_id
                    )
                )

                # Repeat Visits (users with more than one session)
                user_sessions = {}
                for pv in pageviews:
                    user_id = pv.user_prop_webuserid
                    session_id = pv.param_ga_session_id
                    if user_id and session_id:
                        if user_id not in user_sessions:
                            user_sessions[user_id] = set()
                        user_sessions[user_id].add(session_id)

                repeat_visits = sum(
                    1 for sessions in user_sessions.values() if len(sessions) > 1
                )

                return {
                    "totalRevenue": f"${total_revenue:,.2f}",
                    "purchases": total_purchases,
                    "abandonedCarts": abandoned_carts,
                    "failedSearches": failed_searches,
                    "totalVisitors": total_visitors,
                    "repeatVisits": repeat_visits,
                }

        except Exception as e:
            logger.error(f"Error in fallback stats calculation: {e}")
            return {
                "totalRevenue": "$0.00",
                "purchases": 0,
                "abandonedCarts": 0,
                "failedSearches": 0,
                "totalVisitors": 0,
                "repeatVisits": 0,
            }

    # Task operations
    def get_task_status(
        self, tenant_id: str, task_id: str, task_type: str
    ) -> Dict[str, Any]:
        """Get task completion status."""
        try:
            with self.get_db_session() as session:
                task = (
                    session.query(TaskTracking)
                    .filter(
                        TaskTracking.tenant_id == tenant_id,
                        TaskTracking.task_id == task_id,
                        TaskTracking.task_type == task_type,
                    )
                    .first()
                )

                if task:
                    return {
                        "taskId": task_id,
                        "taskType": task_type,
                        "completed": task.completed,
                        "notes": task.notes or "",
                        "completedAt": (
                            task.completed_at.isoformat() if task.completed_at else None
                        ),
                        "completedBy": task.completed_by or "",
                    }
                else:
                    return {
                        "taskId": task_id,
                        "taskType": task_type,
                        "completed": False,
                        "notes": "",
                        "completedAt": None,
                        "completedBy": None,
                    }

        except Exception as e:
            logger.error(f"Error fetching task status: {e}")
            raise

    def update_task_status(
        self,
        tenant_id: str,
        task_id: str,
        task_type: str,
        completed: bool,
        notes: str = "",
        completed_by: str = "",
    ) -> Dict[str, Any]:
        """Update task completion status."""
        try:
            with self.get_db_session() as session:
                # Try to find existing task
                task = (
                    session.query(TaskTracking)
                    .filter(
                        TaskTracking.tenant_id == tenant_id,
                        TaskTracking.task_id == task_id,
                        TaskTracking.task_type == task_type,
                    )
                    .first()
                )

                if task:
                    # Update existing task
                    task.completed = completed
                    task.notes = notes
                    task.completed_by = completed_by
                    task.updated_at = datetime.now()
                    if completed:
                        task.completed_at = datetime.now()
                else:
                    # Create new task
                    task = TaskTracking(
                        tenant_id=tenant_id,
                        task_id=task_id,
                        task_type=task_type,
                        completed=completed,
                        notes=notes,
                        completed_by=completed_by,
                        completed_at=datetime.now() if completed else None,
                    )
                    session.add(task)

                session.commit()

                return {
                    "success": True,
                    "taskId": task_id,
                    "taskType": task_type,
                    "completed": completed,
                }

        except Exception as e:
            logger.error(f"Error updating task status: {e}")
            raise

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
