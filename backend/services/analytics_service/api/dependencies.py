"""
Shared API Dependencies for Analytics Service

This module provides FastAPI dependency functions that are shared across multiple
endpoints in the analytics service. These dependencies handle common concerns
like tenant identification, authentication, and request validation.

Dependencies:
    - get_tenant_id: Extracts and validates tenant ID from HTTP headers

Multi-Tenancy:
    The analytics service implements multi-tenant data isolation where each
    tenant's data is completely isolated at the database level. All API endpoints
    require a valid tenant ID to ensure proper data access control.

Security:
    Tenant ID validation is critical for data isolation. This module ensures
    that no request can proceed without a valid tenant identifier, preventing
    unauthorized data access across tenant boundaries.

Example:
    ```python
    from fastapi import Depends
    from services.analytics_service.api.dependencies import get_tenant_id
    
    @router.get("/endpoint")
    async def my_endpoint(tenant_id: str = Depends(get_tenant_id)):
        # tenant_id is guaranteed to be a non-empty string
        pass
    ```

See Also:
    - common.database.session: Database session management with tenant isolation
    - services.analytics_service.database.postgres_client: Database client using tenant ID
"""

from fastapi import Header, HTTPException
from loguru import logger


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
        - services.analytics_service.database.postgres_client: Database client
            that uses tenant_id for data isolation
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
