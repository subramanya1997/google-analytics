"""
Shared API dependencies for the analytics service.
"""

from typing import Optional

from fastapi import Header, HTTPException
from loguru import logger


def get_tenant_id(
    tenant_id_header: Optional[str] = Header(default=None, alias="X-Tenant-Id")
) -> str:
    """
    Extract and validate the tenant id from the X-Tenant-Id header.

    Raises 400 if the header is missing or empty.
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
