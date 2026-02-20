"""
Shared API Dependencies for Analytics Service

This module provides FastAPI dependency functions that are shared across multiple
endpoints in the analytics service. These dependencies handle common concerns
like tenant identification, authentication, request validation, and repository
access.

Dependencies:
    - get_tenant_id: Extracts and validates tenant ID from HTTP headers
    - get_locations_repository: Returns LocationsRepository instance
    - get_tasks_repository: Returns TasksRepository instance
    - get_history_repository: Returns HistoryRepository instance
    - get_stats_repository: Returns StatsRepository instance

Multi-Tenancy:
    The analytics service implements multi-tenant data isolation where each
    tenant's data is completely isolated at the database level. All API endpoints
    require a valid tenant ID to ensure proper data access control.

Repository Pattern:
    The service uses specialized repository classes for database operations.
    Each repository handles a specific domain of analytics data, improving
    code organization, testability, and maintainability.

Security:
    Tenant ID validation is critical for data isolation. This module ensures
    that no request can proceed without a valid tenant identifier, preventing
    unauthorized data access across tenant boundaries.

Example:
    ```python
    from fastapi import Depends
    from services.analytics_service.api.dependencies import (
        get_tenant_id,
        get_locations_repository,
    )
    from services.analytics_service.database import LocationsRepository

    @router.get("/endpoint")
    async def my_endpoint(
        tenant_id: str = Depends(get_tenant_id),
        repo: LocationsRepository = Depends(get_locations_repository),
    ):
        return await repo.get_locations(tenant_id)
    ```

See Also:
    - common.database.session: Database session management with tenant isolation
    - services.analytics_service.database: Repository classes for database operations
"""

import re
from functools import lru_cache

from fastapi import Header, HTTPException
from loguru import logger

from common.database.tenant_provisioning import tenant_database_exists
from services.analytics_service.database import (
    HistoryRepository,
    LocationsRepository,
    StatsRepository,
    TasksRepository,
)

UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)


@lru_cache
def get_locations_repository() -> LocationsRepository:
    """
    Get a singleton instance of the LocationsRepository.

    This dependency provides access to location/branch database operations.
    The repository instance is cached and reused across requests for efficiency.

    Returns:
        LocationsRepository: Singleton repository instance for location queries.

    Example:
        ```python
        @router.get("/locations")
        async def get_locations(
            tenant_id: str = Depends(get_tenant_id),
            repo: LocationsRepository = Depends(get_locations_repository),
        ):
            return await repo.get_locations(tenant_id)
        ```
    """
    return LocationsRepository()


@lru_cache
def get_tasks_repository() -> TasksRepository:
    """
    Get a singleton instance of the TasksRepository.

    This dependency provides access to task-related database operations,
    including purchases, cart abandonments, search analysis, repeat visits,
    and performance tasks.

    Returns:
        TasksRepository: Singleton repository instance for task queries.

    Example:
        ```python
        @router.get("/tasks/purchases")
        async def get_purchases(
            tenant_id: str = Depends(get_tenant_id),
            repo: TasksRepository = Depends(get_tasks_repository),
        ):
            return await repo.get_purchase_tasks(tenant_id, page=1, limit=50)
        ```
    """
    return TasksRepository()


@lru_cache
def get_history_repository() -> HistoryRepository:
    """
    Get a singleton instance of the HistoryRepository.

    This dependency provides access to session and user history database
    operations, enabling detailed analysis of user journeys and session
    activities.

    Returns:
        HistoryRepository: Singleton repository instance for history queries.

    Example:
        ```python
        @router.get("/history/session/{session_id}")
        async def get_session_history(
            session_id: str,
            tenant_id: str = Depends(get_tenant_id),
            repo: HistoryRepository = Depends(get_history_repository),
        ):
            return await repo.get_session_history(tenant_id, session_id)
        ```
    """
    return HistoryRepository()


@lru_cache
def get_stats_repository() -> StatsRepository:
    """
    Get a singleton instance of the StatsRepository.

    This dependency provides access to dashboard statistics and chart data
    database operations, including overview metrics, time-series data,
    and location comparisons.

    Returns:
        StatsRepository: Singleton repository instance for statistics queries.

    Example:
        ```python
        @router.get("/stats/overview")
        async def get_overview(
            tenant_id: str = Depends(get_tenant_id),
            repo: StatsRepository = Depends(get_stats_repository),
        ):
            return await repo.get_overview_stats(tenant_id, "2024-01-01", "2024-01-31")
        ```
    """
    return StatsRepository()


def get_tenant_id(
    tenant_id_header: str | None = Header(default=None, alias="X-Tenant-Id"),
) -> str:
    """
    Extract and validate the tenant ID from the X-Tenant-Id HTTP header.

    This dependency function is used across all analytics service endpoints to
    ensure proper tenant identification and data isolation. It validates that
    the header is present and contains a non-empty value.

    Args:
        tenant_id_header: The value of the X-Tenant-Id header, automatically
            extracted by FastAPI. Can be None if header is missing.

    Returns:
        str: The validated tenant ID string (stripped of whitespace).

    Raises:
        HTTPException: 400 Bad Request if:
            - The X-Tenant-Id header is missing (None)
            - The header value is empty or contains only whitespace

    Example:
        ```python
        @router.get("/stats")
        async def get_stats(tenant_id: str = Depends(get_tenant_id)):
            # tenant_id is guaranteed to be a valid non-empty string
            return await fetch_stats(tenant_id)
        ```

    Security Note:
        This function does not validate the format or existence of the tenant ID
        in the database. It only ensures that a tenant ID is provided. Database-level
        validation and access control should be handled by the database client.

    See Also:
        - services.analytics_service.database: Repository classes
            that use tenant_id for data isolation
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

    if not UUID_RE.match(tenant_id_value):
        logger.warning(f"Invalid tenant ID format: {tenant_id_value}")
        raise HTTPException(status_code=400, detail="Invalid tenant ID format")

    if not tenant_database_exists(tenant_id_value):
        logger.warning(f"Tenant database not found for: {tenant_id_value}")
        raise HTTPException(
            status_code=404,
            detail="Tenant not found. Please ensure your account is properly configured.",
        )

    return tenant_id_value
