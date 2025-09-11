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

    # ======================================
    # EMAIL CONFIGURATION METHODS
    # ======================================

    def get_email_config(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get email configuration for a tenant."""
        try:
            with self.get_db_session() as session:
                result = session.execute(
                    text("SELECT email_config FROM tenants WHERE id = :tenant_id"),
                    {"tenant_id": tenant_id}
                ).scalar()
                
                if result:
                    import json
                    return json.loads(result) if isinstance(result, str) else result
                return None
                
        except Exception as e:
            logger.error(f"Error fetching email config for tenant {tenant_id}: {e}")
            return None

    # ======================================
    # BRANCH EMAIL MAPPING METHODS
    # ======================================

    def get_branch_email_mappings(
        self, tenant_id: str, branch_code: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get branch email mappings for a tenant."""
        try:
            with self.get_db_session() as session:
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
                
                query += "ORDER BY branch_code, sales_rep_email"
                
                results = session.execute(text(query), params).fetchall()
                
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

    def create_branch_email_mapping(
        self, tenant_id: str, mapping: Any
    ) -> Dict[str, Any]:
        """Create a new branch email mapping."""
        try:
            with self.get_db_session() as session:
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
                
                result = session.execute(
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
                ).fetchone()
                
                session.commit()
                
                return {
                    "mapping_id": str(result.id)
                }
                
        except Exception as e:
            logger.error(f"Error creating branch email mapping: {e}")
            raise

    def update_branch_email_mapping(
        self, tenant_id: str, mapping_id: str, mapping: Any
    ) -> bool:
        """Update a specific branch email mapping by ID."""
        try:
            with self.get_db_session() as session:
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
                
                result = session.execute(
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
                
                session.commit()
                
                # Return True if a row was updated, False if mapping wasn't found
                return result.rowcount > 0
                
        except Exception as e:
            logger.error(f"Error updating branch email mapping {mapping_id}: {e}")
            raise

    def delete_branch_email_mapping(self, tenant_id: str, mapping_id: str) -> bool:
        """Delete a specific branch email mapping by ID."""
        try:
            with self.get_db_session() as session:
                result = session.execute(
                    text("""
                        DELETE FROM branch_email_mappings
                        WHERE tenant_id = :tenant_id AND id = :mapping_id
                    """),
                    {"tenant_id": tenant_id, "mapping_id": mapping_id}
                )
                
                session.commit()
                
                # Return True if a row was deleted, False if mapping wasn't found
                return result.rowcount > 0
                
        except Exception as e:
            logger.error(f"Error deleting branch email mapping {mapping_id}: {e}")
            raise

    # ======================================
    # EMAIL JOB METHODS
    # ======================================

    def create_email_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new email sending job."""
        try:
            with self.get_db_session() as session:
                result = session.execute(
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
                ).fetchone()
                
                session.commit()
                
                return {
                    "id": str(result.id),
                    "job_id": result.job_id,
                    "status": result.status
                }
                
        except Exception as e:
            logger.error(f"Error creating email job: {e}")
            raise

    def update_email_job_status(
        self, job_id: str, status: str, updates: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update email job status and other fields."""
        try:
            with self.get_db_session() as session:
                set_clause = "status = :status, updated_at = NOW()"
                params = {"job_id": job_id, "status": status}
                
                if updates:
                    for key, value in updates.items():
                        if key in ["started_at", "completed_at", "total_emails", 
                                 "emails_sent", "emails_failed", "error_message"]:
                            set_clause += f", {key} = :{key}"
                            params[key] = value
                
                result = session.execute(
                    text(f"""
                        UPDATE email_sending_jobs 
                        SET {set_clause}
                        WHERE job_id = :job_id
                    """),
                    params
                )
                
                session.commit()
                return result.rowcount > 0
                
        except Exception as e:
            logger.error(f"Error updating email job status: {e}")
            return False

    def get_email_job_status(self, tenant_id: str, job_id: str) -> Optional[Dict[str, Any]]:
        """Get email job status."""
        try:
            with self.get_db_session() as session:
                result = session.execute(
                    text("""
                        SELECT job_id, status, report_date, target_branches,
                               total_emails, emails_sent, emails_failed, error_message,
                               created_at, started_at, completed_at
                        FROM email_sending_jobs 
                        WHERE tenant_id = :tenant_id AND job_id = :job_id
                    """),
                    {"tenant_id": tenant_id, "job_id": job_id}
                ).fetchone()
                
                if result:
                    return {
                        "job_id": result.job_id,
                        "status": result.status,
                        "tenant_id": tenant_id,
                        "report_date": result.report_date,
                        "target_branches": result.target_branches or [],
                        "total_emails": result.total_emails or 0,
                        "emails_sent": result.emails_sent or 0,
                        "emails_failed": result.emails_failed or 0,
                        "error_message": result.error_message,
                        "created_at": result.created_at,
                        "started_at": result.started_at,
                        "completed_at": result.completed_at
                    }
                return None
                
        except Exception as e:
            logger.error(f"Error fetching email job status: {e}")
            return None

    def get_email_jobs(
        self, 
        tenant_id: str, 
        page: int = 1, 
        limit: int = 50,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get email job history with pagination."""
        try:
            with self.get_db_session() as session:
                # Build query
                where_clause = "WHERE tenant_id = :tenant_id"
                params = {"tenant_id": tenant_id}
                
                if status:
                    where_clause += " AND status = :status"
                    params["status"] = status
                
                # Get total count
                count_result = session.execute(
                    text(f"SELECT COUNT(*) FROM email_sending_jobs {where_clause}"),
                    params
                ).scalar()
                
                # Get paginated data
                offset = (page - 1) * limit
                params.update({"limit": limit, "offset": offset})
                
                results = session.execute(
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
                ).fetchall()
                
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
                    "total": count_result,
                    "page": page,
                    "limit": limit,
                    "has_more": (page * limit) < count_result
                }
                
        except Exception as e:
            logger.error(f"Error fetching email jobs: {e}")
            return {"data": [], "total": 0, "page": page, "limit": limit, "has_more": False}

    # ======================================
    # EMAIL HISTORY METHODS
    # ======================================

    def log_email_send_history(self, history_data: Dict[str, Any]) -> None:
        """Log email send history record."""
        try:
            with self.get_db_session() as session:
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
                
                session.execute(
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
                session.commit()
                
        except Exception as e:
            logger.error(f"Error logging email send history: {e}")

    def get_email_send_history(
        self,
        tenant_id: str,
        page: int = 1,
        limit: int = 50,
        branch_code: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get email send history with pagination and filtering."""
        try:
            with self.get_db_session() as session:
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
                count_result = session.execute(
                    text(f"SELECT COUNT(*) FROM email_send_history {where_clause}"),
                    params
                ).scalar()
                
                # Get paginated data
                offset = (page - 1) * limit
                params.update({"limit": limit, "offset": offset})
                
                results = session.execute(
                    text(f"""
                        SELECT id, job_id, branch_code, sales_rep_email, sales_rep_name,
                               subject, report_date, status, smtp_response, error_message, sent_at
                        FROM email_send_history
                        {where_clause}
                        ORDER BY sent_at DESC
                        LIMIT :limit OFFSET :offset
                    """),
                    params
                ).fetchall()
                
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
                    "total": count_result,
                    "page": page,
                    "limit": limit,
                    "has_more": (page * limit) < count_result
                }
                
        except Exception as e:
            logger.error(f"Error fetching email send history: {e}")
            return {"data": [], "total": 0, "page": page, "limit": limit, "has_more": False}