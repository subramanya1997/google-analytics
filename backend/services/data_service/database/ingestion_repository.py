"""
Ingestion Repository Implementation for Data Service

This module provides the database access layer for data ingestion operations using
SQLAlchemy's async API and PostgreSQL-specific features. The repository pattern
encapsulates all database operations related to ingestion job management, data
availability queries, and job history retrieval.

Key Features:
    - Async SQLAlchemy operations for non-blocking database access
    - PostgreSQL function calls for optimized queries
    - Multi-tenant data isolation via tenant_id routing
    - Comprehensive error handling and logging

Performance Optimizations:
    - Uses PostgreSQL functions (get_data_availability_combined, get_tenant_jobs_paginated)
      for server-side processing and reduced network overhead
    - Efficient pagination with total count calculation in single query
    - Proper use of SQLAlchemy connection pooling

Example:
    ```python
    repo = IngestionRepository()

    # Create a new ingestion job
    job = await repo.create_processing_job({
        "job_id": "job_123",
        "tenant_id": "tenant-uuid",
        "status": "queued",
        ...
    })

    # Query data availability
    availability = await repo.get_data_availability_with_breakdown("tenant-uuid")

    # Get paginated job history
    jobs = await repo.get_tenant_jobs("tenant-uuid", limit=20, offset=0)
    ```

See Also:
    - services.data_service.database.base: Shared utilities
    - services.data_service.database.email_repository: Email operations
    - common.database.get_async_db_session: Database session management
"""

from __future__ import annotations

from typing import Any

from loguru import logger
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

from common.database import get_async_db_session
from common.models import ProcessingJobs

from .base import ensure_uuid_string


class IngestionRepository:
    """
    Repository for data ingestion database operations.

    This class provides a clean abstraction over database operations using SQLAlchemy's
    async API. It encapsulates all database access logic for ingestion jobs, data
    availability queries, and job history retrieval.

    The repository uses PostgreSQL-specific features (functions, INSERT ... RETURNING)
    for optimal performance and leverages async/await for non-blocking database access.

    Attributes:
        service_name: Name of the service for logging and database connection routing.
                     Default: "data-service"

    Thread Safety:
        Instances are designed to be shared across async requests. Each method
        creates its own database session, ensuring thread-safe operation.

    Example:
        ```python
        repo = IngestionRepository()

        # Create job
        job = await repo.create_processing_job({
            "job_id": "job_abc123",
            "tenant_id": "tenant-uuid",
            "status": "queued",
            "data_types": ["events"],
            "start_date": date(2024, 1, 1),
            "end_date": date(2024, 1, 31),
        })

        # Query availability
        availability = await repo.get_data_availability_with_breakdown("tenant-uuid")

        # Get jobs
        result = await repo.get_tenant_jobs("tenant-uuid", limit=10, offset=0)
        ```

    See Also:
        - common.database.get_async_db_session: Session management
        - common.models.ProcessingJobs: Job model definition
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

    async def create_processing_job(self, job_data: dict[str, Any]) -> dict[str, Any]:
        """
        Create a new processing job record in the database.

        This method inserts a new job record into the processing_jobs table and
        returns the complete record including database-generated fields (id,
        timestamps, etc.). The job is created with status "queued" and will be
        picked up by background workers for processing.

        Args:
            job_data: Dictionary containing job information with keys:
                - job_id: Unique job identifier (str)
                - tenant_id: Tenant identifier (str, will be normalized to UUID)
                - status: Job status, typically "queued" (str)
                - data_types: List of data types to process (list[str])
                - start_date: Start date for data ingestion (date)
                - end_date: End date for data ingestion (date)
                - progress: Optional progress information (dict, optional)
                - records_processed: Optional record counts (dict, optional)
                - error_message: Optional error message (str, optional)

        Returns:
            dict[str, Any]: Complete job record as dictionary, including all
                           database columns (id, created_at, etc.). Returns
                           empty dict if insertion fails.

        Example:
            ```python
            job = await repo.create_processing_job({
                "job_id": "job_abc123",
                "tenant_id": "tenant-uuid",
                "status": "queued",
                "data_types": ["events", "users"],
                "start_date": date(2024, 1, 1),
                "end_date": date(2024, 1, 31),
            })
            ```

        Raises:
            DatabaseError: If database insertion fails
        """
        # Extract tenant_id for database routing
        tenant_id = job_data.get("tenant_id")

        async with get_async_db_session(
            self.service_name, tenant_id=tenant_id
        ) as session:
            # Ensure tenant_id is properly formatted for UUID column
            if "tenant_id" in job_data:
                job_data["tenant_id"] = ensure_uuid_string(job_data["tenant_id"])

            stmt = (
                insert(ProcessingJobs.__table__)
                .values(job_data)
                .returning(*ProcessingJobs.__table__.columns)
            )
            result = await session.execute(stmt)
            await session.commit()
            row = result.mappings().first()
            return dict(row) if row else {}

    async def get_data_availability_with_breakdown(
        self, tenant_id: str
    ) -> dict[str, Any]:
        """
        Get data availability summary for a tenant using optimized PostgreSQL function.

        This method queries the database to determine what date ranges have been
        successfully ingested and are available for analytics queries. It uses a
        PostgreSQL function (get_data_availability_combined) that efficiently
        aggregates data across all event tables in a single query.

        Args:
            tenant_id: Tenant identifier for data isolation

        Returns:
            dict[str, Any]: Data availability information with structure:
                {
                    "summary": {
                        "earliest_date": "YYYY-MM-DD" | None,
                        "latest_date": "YYYY-MM-DD" | None,
                        "total_events": int
                    }
                }
            If no data exists, returns summary with None dates and 0 total_events.

        Example:
            ```python
            availability = await repo.get_data_availability_with_breakdown("tenant-uuid")
            # Returns: {
            #     "summary": {
            #         "earliest_date": "2024-01-01",
            #         "latest_date": "2024-01-31",
            #         "total_events": 125000
            #     }
            # }
            ```

        Raises:
            DatabaseError: If database query fails
        """
        tenant_uuid_str = ensure_uuid_string(tenant_id)

        async with get_async_db_session(
            self.service_name, tenant_id=tenant_id
        ) as session:
            # Call simplified function that only returns summary data
            combined_query = text(
                "SELECT * FROM get_data_availability_combined(:tenant_id)"
            )
            result_obj = await session.execute(
                combined_query, {"tenant_id": tenant_uuid_str}
            )
            result = result_obj.mappings().first()

            if result:
                summary_data = {
                    "earliest_date": result.earliest_date.isoformat()
                    if result.earliest_date
                    else None,
                    "latest_date": result.latest_date.isoformat()
                    if result.latest_date
                    else None,
                    "total_events": int(result.event_count),
                }
                logger.info(
                    f"Data availability: {summary_data['total_events']} total events"
                )
            else:
                summary_data = {
                    "earliest_date": None,
                    "latest_date": None,
                    "total_events": 0,
                }
                logger.info("Data availability: No data found")

            return {
                "summary": summary_data,
            }

    async def get_tenant_jobs(
        self, tenant_id: str, limit: int = 50, offset: int = 0
    ) -> dict[str, Any]:
        """
        Get paginated ingestion job history for a tenant using optimized PostgreSQL function.

        This method retrieves a paginated list of ingestion jobs for the specified
        tenant, ordered by creation time (most recent first). It uses a PostgreSQL
        function (get_tenant_jobs_paginated) that efficiently handles pagination
        and total count calculation in a single query.

        Args:
            tenant_id: Tenant identifier for data isolation
            limit: Maximum number of jobs to return (default: 50)
            offset: Number of jobs to skip for pagination (default: 0)

        Returns:
            dict[str, Any]: Paginated job list with structure:
                {
                    "jobs": [
                        {
                            "id": str,
                            "tenant_id": str,
                            "job_id": str,
                            "status": str,
                            "data_types": list[str],
                            "start_date": "YYYY-MM-DD" | None,
                            "end_date": "YYYY-MM-DD" | None,
                            "progress": dict | None,
                            "records_processed": dict | None,
                            "error_message": str | None,
                            "created_at": "ISO datetime" | None,
                            "started_at": "ISO datetime" | None,
                            "completed_at": "ISO datetime" | None
                        },
                        ...
                    ],
                    "total": int
                }

        Example:
            ```python
            # Get first page
            result = await repo.get_tenant_jobs("tenant-uuid", limit=20, offset=0)
            # Returns: {
            #     "jobs": [...20 jobs...],
            #     "total": 150
            # }
            ```

        Raises:
            DatabaseError: If database query fails
        """
        tenant_uuid_str = ensure_uuid_string(tenant_id)

        async with get_async_db_session(
            self.service_name, tenant_id=tenant_id
        ) as session:
            # Call optimized PostgreSQL function
            jobs_query = text(
                "SELECT * FROM get_tenant_jobs_paginated(:tenant_id, :limit, :offset)"
            )

            result = await session.execute(
                jobs_query,
                {"tenant_id": tenant_uuid_str, "limit": limit, "offset": offset},
            )
            results = result.mappings().all()

            jobs = []
            total = 0

            for row in results:
                if total == 0:  # Get total from first row
                    total = int(row.total_count)

                # Build job data with proper type conversion
                job_data = {
                    "id": str(row.id),
                    "tenant_id": str(row.tenant_id),
                    "job_id": row.job_id,
                    "status": row.status,
                    "data_types": row.data_types,
                    "start_date": row.start_date.isoformat()
                    if row.start_date
                    else None,
                    "end_date": row.end_date.isoformat() if row.end_date else None,
                    "progress": row.progress,
                    "records_processed": row.records_processed,
                    "error_message": row.error_message,
                    "created_at": row.created_at.isoformat()
                    if row.created_at
                    else None,
                    "started_at": row.started_at.isoformat()
                    if row.started_at
                    else None,
                    "completed_at": row.completed_at.isoformat()
                    if row.completed_at
                    else None,
                }
                jobs.append(job_data)

            logger.info(f"Job history: {len(jobs)} jobs returned, {total} total")

            return {"jobs": jobs, "total": total}
