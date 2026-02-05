"""
Email Repository Implementation for Data Service

This module provides the database access layer for email-related operations using
SQLAlchemy's async API and PostgreSQL-specific features. The repository pattern
encapsulates all database operations related to email configuration, branch mappings,
email jobs, and email send history.

Key Features:
    - Async SQLAlchemy operations for non-blocking database access
    - PostgreSQL function calls for optimized queries
    - Multi-tenant data isolation via tenant_id routing
    - Comprehensive error handling and logging

Operations:
    - Email configuration retrieval
    - Branch email mapping CRUD operations
    - Email job management
    - Email send history with filtering and pagination

Example:
    ```python
    repo = EmailRepository()

    # Get email configuration
    config = await repo.get_email_config("tenant-uuid")

    # Get branch email mappings
    mappings = await repo.get_branch_email_mappings("tenant-uuid")

    # Get email jobs history
    jobs = await repo.get_email_jobs("tenant-uuid", page=1, limit=50)
    ```

See Also:
    - services.data_service.database.base: Shared utilities
    - services.data_service.database.ingestion_repository: Ingestion operations
    - common.database.get_async_db_session: Database session management
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger
from sqlalchemy import text

from common.database import get_async_db_session


class EmailRepository:
    """
    Repository for email-related database operations.

    This class provides a clean abstraction over database operations using SQLAlchemy's
    async API. It encapsulates all database access logic for email configuration,
    branch mappings, email jobs, and email send history.

    The repository uses PostgreSQL-specific features for optimal performance and
    leverages async/await for non-blocking database access.

    Attributes:
        service_name: Name of the service for logging and database connection routing.
                     Default: "data-service"

    Thread Safety:
        Instances are designed to be shared across async requests. Each method
        creates its own database session, ensuring thread-safe operation.

    Example:
        ```python
        repo = EmailRepository()

        # Get email config
        config = await repo.get_email_config("tenant-uuid")

        # Get branch mappings
        mappings = await repo.get_branch_email_mappings("tenant-uuid")

        # Create mapping
        result = await repo.create_branch_email_mapping("tenant-uuid", mapping_data)
        ```

    See Also:
        - common.database.get_async_db_session: Session management
    """

    def __init__(self, service_name: str = "data-service") -> None:
        """
        Initialize the repository with a service name.

        Args:
            service_name: Name of the service for database connection routing.
                         Used to determine which database connection pool to use.
                         Default: "data-service"
        """
        self.service_name = service_name

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

        Security Note:
            The password field should be masked when returning configuration
            to API clients. See the email endpoint implementation for masking logic.
        """
        try:
            async with get_async_db_session(
                self.service_name, tenant_id=tenant_id
            ) as session:
                result = await session.execute(
                    text(
                        "SELECT email_config FROM tenant_config WHERE id = :tenant_id"
                    ),
                    {"tenant_id": tenant_id},
                )
                email_config = result.scalar()

                if email_config:
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

        Note:
            Results are ordered by branch_code and sales_rep_email for consistent
            presentation in UI components.
        """
        try:
            async with get_async_db_session(
                self.service_name, tenant_id=tenant_id
            ) as session:
                query = """
                    SELECT id, branch_code, branch_name, sales_rep_email,
                           sales_rep_name, is_enabled, created_at, updated_at
                    FROM branch_email_mappings
                    WHERE tenant_id = :tenant_id
                """
                params: dict[str, Any] = {"tenant_id": tenant_id}

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

        Note:
            Supports both Pydantic model instances and plain dictionaries for
            flexibility in different usage contexts.
        """
        try:
            async with get_async_db_session(
                self.service_name, tenant_id=tenant_id
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

        Note:
            This method performs a full update of all fields. Partial updates
            should be handled at the API layer by fetching existing data first.
        """
        try:
            async with get_async_db_session(
                self.service_name, tenant_id=tenant_id
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

        Warning:
            This operation is irreversible. Consider disabling the mapping
            (is_enabled=False) instead if you may need to restore it later.
        """
        try:
            async with get_async_db_session(
                self.service_name, tenant_id=tenant_id
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

        Note:
            The job status will be updated by background workers as the job
            progresses through processing stages (queued -> processing -> completed).
        """
        try:
            tenant_id = job_data.get("tenant_id")
            async with get_async_db_session(
                self.service_name, tenant_id=tenant_id
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
                - data (list[dict]): List of job objects
                - total (int): Total number of matching jobs across all pages
                - page (int): Current page number
                - limit (int): Items per page
                - has_more (bool): Whether more pages are available

        Performance Note:
            Uses the optimized `get_email_jobs_paginated()` PostgreSQL function
            for efficient pagination and filtering.
        """
        try:
            async with get_async_db_session(
                self.service_name, tenant_id=tenant_id
            ) as session:
                # Calculate offset from page number
                offset = (page - 1) * limit

                # Call optimized PostgreSQL function
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
            branch_code: Optional branch filter.
            status: Optional status filter.
            start_date: Optional start date filter (YYYY-MM-DD format).
            end_date: Optional end date filter (YYYY-MM-DD format).

        Returns:
            dict[str, Any]: Paginated response containing:
                - data (list[dict]): List of email history objects
                - total (int): Total number of matching records across all pages
                - page (int): Current page number
                - limit (int): Items per page
                - has_more (bool): Whether more pages are available

        Performance Note:
            Uses the optimized `get_email_send_history_paginated()` PostgreSQL
            function for efficient pagination and filtering.
        """
        try:
            async with get_async_db_session(
                self.service_name, tenant_id=tenant_id
            ) as session:
                # Calculate offset from page number
                offset = (page - 1) * limit

                # Call optimized PostgreSQL function
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
