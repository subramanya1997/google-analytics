"""
PostgreSQL client for analytics service operations
"""

from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import text

from common.database import get_async_db_session

class AnalyticsPostgresClient:
    """PostgreSQL client for analytics operations."""

    def __init__(self):
        """Initialize PostgreSQL client."""
        logger.info("Initialized Analytics PostgreSQL client")

    # Location operations
    async def get_locations(self, tenant_id: str) -> List[Dict[str, Any]]:
        """Get all active locations for tenant."""
        try:
            async with get_async_db_session("analytics-service", tenant_id=tenant_id) as session:
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
        query: Optional[str] = None,
        location_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get purchase analysis tasks with pagination and filtering."""
        try:
            async with get_async_db_session("analytics-service", tenant_id=tenant_id) as session:
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
        """Get cart abandonment tasks using the RPC function."""
        try:
            async with get_async_db_session("analytics-service", tenant_id=tenant_id) as session:
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
        """Get search analysis tasks using the RPC function."""
        try:
            async with get_async_db_session("analytics-service", tenant_id=tenant_id) as session:
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
        """Get repeat visit tasks using the RPC function."""
        try:
            async with get_async_db_session("analytics-service", tenant_id=tenant_id) as session:
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
        """Get performance tasks using the RPC function."""
        try:
            async with get_async_db_session("analytics-service", tenant_id=tenant_id) as session:
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
        """Get the event history for a specific session using the RPC function."""
        try:
            async with get_async_db_session("analytics-service", tenant_id=tenant_id) as session:
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
        """Get the event history for a specific user using the RPC function."""
        try:
            async with get_async_db_session("analytics-service", tenant_id=tenant_id) as session:
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
        location_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get dashboard overview stats."""
        async with get_async_db_session("analytics-service", tenant_id=tenant_id) as session:
            result = await session.execute(
                text("SELECT get_dashboard_overview_stats(:p_tenant_id, :p_start_date, :p_end_date, :p_location_id)"),
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
        location_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get chart data for dashboard."""
        async with get_async_db_session("analytics-service", tenant_id=tenant_id) as session:
            result = await session.execute(
                text("SELECT get_chart_data(:p_tenant_id, :p_start_date, :p_end_date, :p_granularity, :p_location_id)"),
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
    ) -> List[Dict[str, Any]]:
        """Get location stats for dashboard."""
        async with get_async_db_session("analytics-service", tenant_id=tenant_id) as session:
            result = await session.execute(
                text("SELECT get_location_stats_bulk(:p_tenant_id, :p_start_date, :p_end_date)"),
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

    async def get_email_config(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get email configuration for a tenant."""
        try:
            async with get_async_db_session("analytics-service", tenant_id=tenant_id) as session:
                result = await session.execute(
                    text("SELECT email_config FROM tenant_config WHERE id = :tenant_id"),
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
        """Get branch email mappings for a tenant."""
        try:
            async with get_async_db_session("analytics-service", tenant_id=tenant_id) as session:
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
        """Create a new branch email mapping."""
        try:
            async with get_async_db_session("analytics-service", tenant_id=tenant_id) as session:
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
        """Update a specific branch email mapping by ID."""
        try:
            async with get_async_db_session("analytics-service", tenant_id=tenant_id) as session:
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
        """Delete a specific branch email mapping by ID."""
        try:
            async with get_async_db_session("analytics-service", tenant_id=tenant_id) as session:
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
        """Create a new email sending job."""
        try:
            tenant_id = job_data.get("tenant_id")
            async with get_async_db_session("analytics-service", tenant_id=tenant_id) as session:
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

    async def get_email_jobs(
        self, 
        tenant_id: str, 
        page: int = 1, 
        limit: int = 50,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get email job history with pagination - ULTRA-FAST PostgreSQL function only."""
        try:
            async with get_async_db_session("analytics-service", tenant_id=tenant_id) as session:
                # Calculate offset from page number
                offset = (page - 1) * limit
                
                # Call optimized PostgreSQL function (ULTRA FAST!)
                jobs_query = text("SELECT * FROM get_email_jobs_paginated(:tenant_id, :limit, :offset, :status)")
                
                result = await session.execute(
                    jobs_query,
                    {
                        "tenant_id": tenant_id,
                        "limit": limit,
                        "offset": offset,
                        "status": status
                    }
                )
                results = result.mappings().all()
                
                jobs = []
                total = 0
                
                for row in results:
                    if total == 0:  # Get total from first row
                        total = int(row.total_count)
                    
                    # Build job data with proper type conversion
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
                    "total": total,
                    "page": page,
                    "limit": limit,
                    "has_more": (page * limit) < total
                }
                
        except Exception as e:
            logger.error(f"Error fetching email jobs: {e}")
            return {"data": [], "total": 0, "page": page, "limit": limit, "has_more": False}

    # ======================================
    # EMAIL HISTORY METHODS
    # ======================================

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
        """Get email send history with pagination - ULTRA-FAST PostgreSQL function."""
        try:
            async with get_async_db_session("analytics-service", tenant_id=tenant_id) as session:
                # Calculate offset from page number
                offset = (page - 1) * limit
                
                # Call optimized PostgreSQL function (ULTRA FAST!)
                result = await session.execute(
                    text("SELECT * FROM get_email_send_history_paginated(:tenant_id, :limit, :offset, :branch_code, :status, :start_date, :end_date)"),
                    {
                        "tenant_id": tenant_id,
                        "limit": limit,
                        "offset": offset,
                        "branch_code": branch_code,
                        "status": status,
                        "start_date": start_date,
                        "end_date": end_date
                    }
                )
                results = result.mappings().all()
                
                history = []
                total = 0
                
                for row in results:
                    if total == 0:  # Get total from first row
                        total = int(row.total_count)
                    
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
                    "total": total,
                    "page": page,
                    "limit": limit,
                    "has_more": (page * limit) < total
                }
                
        except Exception as e:
            logger.error(f"Error fetching email send history: {e}")
            return {"data": [], "total": 0, "page": page, "limit": limit, "has_more": False}