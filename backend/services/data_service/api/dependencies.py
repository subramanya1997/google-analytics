"""
Shared API Dependencies for Data Ingestion Service.

This module provides common dependency injection functions used across all
data service API endpoints. These dependencies handle cross-cutting concerns
like tenant identification, validation, and security enforcement.

The dependencies ensure consistent multi-tenant security patterns and provide
reusable validation logic that can be injected into any endpoint that requires
tenant-aware operations.

Key Dependencies:
- Tenant ID extraction and validation from HTTP headers
- Multi-tenant security enforcement
- Request context validation

Security Model:
All data ingestion operations require explicit tenant identification through
the X-Tenant-Id header to ensure proper data isolation and prevent cross-tenant
data access. This is enforced at the API layer before any business logic execution.
"""

from typing import Optional

from fastapi import Header, HTTPException
from loguru import logger


def get_tenant_id(
    tenant_id_header: Optional[str] = Header(default=None, alias="X-Tenant-Id")
) -> str:
    """
    Extract and validate tenant ID from X-Tenant-Id header for multi-tenant security.

    This dependency function enforces the multi-tenant security model by requiring
    and validating the tenant identifier in all API requests. It ensures that all
    data operations are properly scoped to the requesting tenant.

    Args:
        tenant_id_header: Raw header value from X-Tenant-Id HTTP header
                         (automatically extracted by FastAPI dependency injection)

    Returns:
        str: Validated tenant ID string for use in business logic

    Raises:
        HTTPException: 
        - 400 BAD REQUEST: If X-Tenant-Id header is missing
        - 400 BAD REQUEST: If X-Tenant-Id header is empty or whitespace-only

    Multi-Tenant Security:
        This function is the primary security gate for tenant isolation:
        - Validates presence of tenant identification
        - Ensures non-empty tenant values
        - Logs security violations for monitoring
        - Prevents accidental cross-tenant operations


    Header Format:
        X-Tenant-Id: {tenant-uuid}
        
        Example:
        X-Tenant-Id: 550e8400-e29b-41d4-a716-446655440000

    
    Logging:
        Security violations are logged at WARNING level for monitoring
        and alerting purposes, enabling detection of misconfigured clients
        or potential security issues.

    Performance:
        This function performs minimal string validation and is designed
        for high-throughput API operations without significant overhead.
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
