"""
Tenant configuration utilities for retrieving configurations from the database.

This module provides functions for querying tenant-specific service configurations
stored in the tenant_config table. It handles service enable/disable status and
validation errors for external service integrations.

Key Features:
    - Retrieve service status (enabled/disabled) for tenants
    - Get validation errors for service configurations
    - Graceful error handling with safe defaults
    - Support for BigQuery, SFTP, and SMTP services

Service Status:
    Each tenant can have services enabled or disabled independently. Services include:
    - BigQuery: Google BigQuery data extraction
    - SFTP: File transfer operations
    - SMTP: Email sending capabilities

Usage:
    ```python
    from common.database.tenant_config import get_tenant_service_status
    
    status = await get_tenant_service_status("tenant-123")
    
    if status["bigquery"]["enabled"]:
        # BigQuery is enabled for this tenant
        pass
    else:
        error = status["bigquery"]["error"]
        # Handle disabled service or validation error
    ```
"""

from typing import Any

from loguru import logger
from sqlalchemy import text

from common.database.session import get_async_db_session


async def get_tenant_service_status(
    tenant_id: str, service_name: str | None = None
) -> dict[str, dict[str, Any]]:
    """
    Get service enable/disable status and validation errors for a tenant.

    This function queries the tenant_config table to retrieve the status of external
    service integrations (BigQuery, SFTP, SMTP) for a specific tenant. It returns
    both the enabled/disabled status and any validation errors.

    Args:
        tenant_id: The tenant ID to query service status for. Must be a valid UUID
            string matching an existing tenant.
        service_name: Optional service name for database connection context. Used
            for logging and connection pool identification. If None, default
            connection settings are used.

    Returns:
        Dictionary containing service status for each service:
        {
            "bigquery": {
                "enabled": bool,  # True if BigQuery is enabled, False otherwise
                "error": str | None  # Validation error message if any, None if valid
            },
            "sftp": {
                "enabled": bool,  # True if SFTP is enabled, False otherwise
                "error": str | None  # Validation error message if any, None if valid
            },
            "smtp": {
                "enabled": bool,  # True if SMTP is enabled, False otherwise
                "error": str | None  # Validation error message if any, None if valid
            }
        }

        If the tenant is not found or inactive, all services are returned as disabled
        with an appropriate error message.

    Example:
        ```python
        from common.database.tenant_config import get_tenant_service_status
        
        status = await get_tenant_service_status("tenant-123")
        
        # Check BigQuery status
        if status["bigquery"]["enabled"]:
            # Proceed with BigQuery operations
            pass
        else:
            error = status["bigquery"]["error"]
            logger.warning(f"BigQuery disabled: {error}")
        
        # Check all services
        for service_name, service_status in status.items():
            if service_status["enabled"]:
                print(f"{service_name} is enabled")
            else:
                print(f"{service_name} is disabled: {service_status['error']}")
        ```

    Note:
        - Returns all services as disabled if tenant is not found or inactive
        - Validation errors indicate configuration issues that need to be resolved
        - Services default to enabled (True) if the status field is None
        - This function handles errors gracefully and never raises exceptions
    """
    try:
        async with get_async_db_session(service_name, tenant_id=tenant_id) as session:
            result = await session.execute(
                text("""
                    SELECT
                        bigquery_enabled, bigquery_validation_error,
                        sftp_enabled, sftp_validation_error,
                        smtp_enabled, smtp_validation_error
                    FROM tenant_config
                    WHERE id = :tenant_id AND is_active = true
                """),
                {"tenant_id": tenant_id},
            )
            row = result.fetchone()

            if not row:
                logger.warning(f"Tenant not found or inactive: {tenant_id}")
                # Return all services disabled if tenant not found
                return {
                    "bigquery": {
                        "enabled": False,
                        "error": "Tenant not found or inactive",
                    },
                    "sftp": {"enabled": False, "error": "Tenant not found or inactive"},
                    "smtp": {"enabled": False, "error": "Tenant not found or inactive"},
                }

            return {
                "bigquery": {
                    "enabled": row.bigquery_enabled
                    if row.bigquery_enabled is not None
                    else True,
                    "error": row.bigquery_validation_error,
                },
                "sftp": {
                    "enabled": row.sftp_enabled
                    if row.sftp_enabled is not None
                    else True,
                    "error": row.sftp_validation_error,
                },
                "smtp": {
                    "enabled": row.smtp_enabled
                    if row.smtp_enabled is not None
                    else True,
                    "error": row.smtp_validation_error,
                },
            }

    except Exception as e:
        logger.error(f"Failed to get service status for tenant {tenant_id}: {e}")
        # Return all services disabled on error
        return {
            "bigquery": {
                "enabled": False,
                "error": f"Failed to retrieve status: {e!s}",
            },
            "sftp": {"enabled": False, "error": f"Failed to retrieve status: {e!s}"},
            "smtp": {"enabled": False, "error": f"Failed to retrieve status: {e!s}"},
        }
