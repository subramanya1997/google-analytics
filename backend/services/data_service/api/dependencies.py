"""
Shared API Dependencies for Data Service

This module provides reusable FastAPI dependencies that are used across multiple
endpoints in the Data Ingestion Service. These dependencies handle common concerns
like tenant identification, database repository injection, and request validation.

Dependencies:
    - get_tenant_id: Extracts and validates tenant ID from HTTP headers
    - get_repository: Provides cached database repository instance

These dependencies ensure consistent behavior across all endpoints and provide
proper multi-tenant isolation and resource management.

Example:
    ```python
    from fastapi import Depends
    from services.data_service.api.dependencies import get_tenant_id, get_repository
    
    @router.get("/endpoint")
    async def my_endpoint(
        tenant_id: str = Depends(get_tenant_id),
        repo: SqlAlchemyRepository = Depends(get_repository),
    ):
        # Use tenant_id and repo here
        pass
    ```

See Also:
    - services.data_service.database.sqlalchemy_repository: Database repository implementation
"""

from functools import lru_cache

from fastapi import Header, HTTPException
from loguru import logger

from services.data_service.database.sqlalchemy_repository import SqlAlchemyRepository


def get_tenant_id(
    tenant_id_header: str | None = Header(default=None, alias="X-Tenant-Id"),
) -> str:
    """
    Extract and validate the tenant ID from the X-Tenant-Id HTTP header.

    This dependency is required for all endpoints to ensure proper multi-tenant
    data isolation. The tenant ID is used to:
    - Route database queries to tenant-specific schemas
    - Retrieve tenant-specific configuration (BigQuery, SFTP credentials)
    - Enforce data access controls

    Args:
        tenant_id_header: The value of the X-Tenant-Id header, extracted by FastAPI

    Returns:
        str: Validated tenant ID string (stripped of whitespace)

    Raises:
        HTTPException: 400 Bad Request if header is missing or empty

    Security:
        This function ensures that every request is associated with a tenant,
        preventing unauthorized access to data. The tenant ID is validated
        before any database operations occur.

    Example:
        ```python
        @router.get("/jobs")
        async def get_jobs(tenant_id: str = Depends(get_tenant_id)):
            # tenant_id is guaranteed to be non-empty
            return await repo.get_tenant_jobs(tenant_id)
        ```
    """
    if tenant_id_header is None:
        logger.warning("Missing X-Tenant-Id header")
        raise HTTPException(status_code=400, detail="X-Tenant-Id header is required")

    tenant_id_value = tenant_id_header.strip()
    if not tenant_id_value:
        logger.warning("Empty X-Tenant-Id header")
        raise HTTPException(
            status_code=400, detail="X-Tenant-Id header cannot be empty"
        )

    return tenant_id_value


@lru_cache(maxsize=1)
def get_repository() -> SqlAlchemyRepository:
    """
    Get a cached singleton instance of the SqlAlchemyRepository.

    This dependency provides a single repository instance per application lifecycle,
    ensuring efficient resource usage and consistent database connection management.
    The LRU cache ensures that only one instance is created and reused across all
    requests.

    Returns:
        SqlAlchemyRepository: Singleton repository instance for database operations

    Performance:
        Using lru_cache ensures that:
        - Only one repository instance is created per application startup
        - Database connection pooling is managed efficiently
        - Memory usage is minimized

    Thread Safety:
        The repository instance is thread-safe and can be used concurrently
        across multiple async requests. Each request gets its own database session
        through the repository's session management.

    Example:
        ```python
        @router.post("/ingest")
        async def create_job(
            repo: SqlAlchemyRepository = Depends(get_repository),
        ):
            # Use repo for database operations
            await repo.create_processing_job(job_data)
        ```
    """
    return SqlAlchemyRepository()
