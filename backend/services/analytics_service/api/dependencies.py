"""
Shared API Dependencies for Analytics Service.

This module provides common dependency injection functions for multi-tenant
security enforcement across all analytics service API endpoints.
"""

from typing import Optional

from fastapi import Header, HTTPException
from loguru import logger


def get_tenant_id(
    tenant_id_header: Optional[str] = Header(default=None, alias="X-Tenant-Id")
) -> str:
    """
    Extract and validate tenant ID from X-Tenant-Id header for multi-tenant security.

    This dependency enforces the multi-tenant security model by requiring and
    validating the tenant identifier in all API requests for proper data isolation.

    Args:
        tenant_id_header: Raw header value from X-Tenant-Id HTTP header

    Returns:
        str: Validated tenant ID for analytics operations

    Raises:
        HTTPException: 
        - 400 BAD REQUEST: If X-Tenant-Id header is missing or empty
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
