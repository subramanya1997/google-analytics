"""
SQLAlchemy Repository Implementation for Data Service

This module provides the database access layer for the Data Ingestion Service using
SQLAlchemy's async API and PostgreSQL-specific features. The repository pattern
encapsulates all database operations, providing a clean abstraction over the
underlying database implementation.

The repository leverages PostgreSQL functions for optimized query performance,
particularly for complex aggregations and pagination operations. All database
operations are async and use proper session management with automatic cleanup.

Key Features:
    - Async SQLAlchemy operations for non-blocking database access
    - PostgreSQL function calls for optimized queries
    - Multi-tenant data isolation via tenant_id routing
    - UUID normalization for consistent tenant identification
    - Comprehensive error handling and logging

Performance Optimizations:
    - Uses PostgreSQL functions (get_data_availability_combined, get_tenant_jobs_paginated)
      for server-side processing and reduced network overhead
    - Efficient pagination with total count calculation in single query
    - Proper use of SQLAlchemy connection pooling

Multi-Tenant Support:
    All operations automatically route to tenant-specific database schemas based
    on the tenant_id parameter. The tenant_id is normalized to UUID format for
    consistent database operations.

Example:
    ```python
    repo = SqlAlchemyRepository()
    
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
    - common.database.get_async_db_session: Database session management
    - common.models: SQLAlchemy model definitions
"""

from __future__ import annotations

from typing import Any
import uuid

from loguru import logger
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

from common.database import get_async_db_session
from common.models import (
    AddToCart,
    NoSearchResults,
    PageView,
    ProcessingJobs,
    Purchase,
    ViewItem,
    ViewSearchResults,
)


def ensure_uuid_string(tenant_id: str) -> str:
    """
    Convert tenant_id to a consistent UUID string format.

    This utility function ensures that tenant IDs are always in valid UUID format
    for database operations. If the input is already a valid UUID, it's returned
    as-is. If not, a deterministic UUID is generated using MD5 hashing to ensure
    consistent mapping for the same input string.

    Args:
        tenant_id: Tenant identifier (may be UUID string or other format)

    Returns:
        str: Valid UUID string representation of the tenant ID

    Implementation Details:
        - Valid UUIDs are validated and returned unchanged
        - Invalid UUIDs are hashed using MD5 and converted to UUID format
        - The same input always produces the same UUID (deterministic)

    Example:
        ```python
        # Valid UUID
        ensure_uuid_string("550e8400-e29b-41d4-a716-446655440000")
        # Returns: "550e8400-e29b-41d4-a716-446655440000"
        
        # Invalid UUID (converted deterministically)
        ensure_uuid_string("tenant-123")
        # Returns: "a1b2c3d4-e5f6-7890-abcd-ef1234567890" (deterministic)
        ```

    Note:
        This function is critical for multi-tenant data isolation. All tenant IDs
        must be normalized before database operations to ensure proper schema routing.
    """
    try:
        # Validate and convert to UUID string
        uuid_obj = uuid.UUID(tenant_id)
        return str(uuid_obj)
    except ValueError:
        # If not a valid UUID, generate one from the string using MD5 hash
        import hashlib

        tenant_uuid = uuid.UUID(bytes=hashlib.md5(tenant_id.encode()).digest()[:16])
        return str(tenant_uuid)


EVENT_TABLES: dict[str, Any] = {
    "purchase": Purchase.__table__,
    "add_to_cart": AddToCart.__table__,
    "page_view": PageView.__table__,
    "view_search_results": ViewSearchResults.__table__,
    "no_search_results": NoSearchResults.__table__,
    "view_item": ViewItem.__table__,
}
"""
Mapping of event type names to their corresponding SQLAlchemy table objects.

This dictionary is used for dynamic table access when processing different
event types during data ingestion. The keys match the event type identifiers
used in the ingestion pipeline.

Supported Event Types:
    - purchase: Purchase transaction events
    - add_to_cart: Add to cart events
    - page_view: Page view events
    - view_search_results: Search result view events
    - no_search_results: No search results events
    - view_item: Product view events
"""


class SqlAlchemyRepository:
    """
    Repository pattern implementation for Data Ingestion Service database operations.

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

    Error Handling:
        Database errors are logged but not caught here. They propagate to the
        calling code for proper error handling and API error formatting.

    Example:
        ```python
        repo = SqlAlchemyRepository()
        
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

    # ---------- Job operations ----------
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

        Database Operations:
            - Uses PostgreSQL INSERT ... RETURNING for atomic insert and retrieval
            - Normalizes tenant_id to UUID format for consistent storage
            - Routes to tenant-specific schema based on tenant_id
            - Commits transaction automatically on success

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
            # Returns: {
            #     "id": "uuid-here",
            #     "job_id": "job_abc123",
            #     "tenant_id": "tenant-uuid",
            #     "status": "queued",
            #     "created_at": datetime(...),
            #     ...
            # }
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

        The availability information is critical for:
        - Dashboard initialization (determining default date ranges)
        - Validating ingestion job completeness
        - Identifying data gaps that need re-ingestion
        - User-facing data availability indicators

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

        Performance:
            Uses PostgreSQL function get_data_availability_combined which:
            - Aggregates across all event tables in a single query
            - Performs server-side computation for optimal performance
            - Minimizes network overhead by returning only summary data

        Database Operations:
            - Routes to tenant-specific schema based on tenant_id
            - Calls PostgreSQL function: get_data_availability_combined(tenant_id)
            - Handles null results gracefully (no data case)

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

        The job history is useful for:
        - Monitoring ingestion job status and progress
        - Debugging failed jobs
        - Auditing data ingestion activities
        - Dashboard job status displays

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

        Performance:
            Uses PostgreSQL function get_tenant_jobs_paginated which:
            - Performs pagination server-side for optimal performance
            - Calculates total count efficiently using window functions
            - Returns results ordered by created_at DESC (most recent first)
            - Minimizes network overhead by returning only requested page

        Database Operations:
            - Routes to tenant-specific schema based on tenant_id
            - Calls PostgreSQL function: get_tenant_jobs_paginated(tenant_id, limit, offset)
            - Converts database types to Python types (UUID to str, dates to ISO strings)

        Example:
            ```python
            # Get first page
            result = await repo.get_tenant_jobs("tenant-uuid", limit=20, offset=0)
            # Returns: {
            #     "jobs": [...20 jobs...],
            #     "total": 150
            # }
            
            # Get second page
            result = await repo.get_tenant_jobs("tenant-uuid", limit=20, offset=20)
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
            # Call optimized PostgreSQL function (ULTRA FAST!)
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
