"""
Factory for creating tenant-aware clients using configurations from the database.
"""

from loguru import logger

from .bigquery_client import BigQueryClient
from .sftp_client import SFTPClient
from typing import Any


async def get_tenant_bigquery_config(tenant_id: str) -> dict[str, Any] | None:
    """
    Retrieve BigQuery configuration for a specific tenant from the database.

    Fetches BigQuery credentials and settings from the tenant's isolated
    database configuration table. Used internally by client factory functions.

    Args:
        tenant_id: Tenant ID (UUID string) for database routing.

    Returns:
        dict[str, Any] | None: BigQuery configuration dictionary containing
                              project_id, dataset_id, and credentials, or None
                              if configuration not found or disabled.

    Note:
        - Uses tenant-specific database connection
        - Returns None if BigQuery is disabled for tenant
        - Configuration is stored encrypted in database
    """
    from shared.database import create_repository

    repo = create_repository(tenant_id)
    return await repo.get_tenant_bigquery_config(tenant_id)


async def get_tenant_sftp_config(tenant_id: str) -> dict[str, Any] | None:
    """
    Retrieve SFTP configuration for a specific tenant from the database.

    Fetches SFTP connection settings from the tenant's isolated database
    configuration table. Used internally by client factory functions.

    Args:
        tenant_id: Tenant ID (UUID string) for database routing.

    Returns:
        dict[str, Any] | None: SFTP configuration dictionary containing
                             host, port, username, password, remote_path, etc.,
                             or None if configuration not found or disabled.

    Note:
        - Uses tenant-specific database connection
        - Returns None if SFTP is disabled for tenant
        - Configuration is stored encrypted in database
    """
    from shared.database import create_repository

    repo = create_repository(tenant_id)
    return await repo.get_tenant_sftp_config(tenant_id)


async def get_tenant_bigquery_client(tenant_id: str) -> BigQueryClient | None:
    """
    Create a BigQuery client instance for a specific tenant.

    This factory function retrieves the tenant's BigQuery configuration from
    the database and creates an authenticated BigQueryClient instance ready
    for querying GA4 event data.

    Args:
        tenant_id: Tenant ID (UUID string) for configuration lookup and client creation.

    Returns:
        BigQueryClient | None: Authenticated BigQueryClient instance configured
                              for the tenant's project and dataset, or None if
                              configuration is not found or BigQuery is disabled.

    Raises:
        Exception: If client creation fails (logged but returns None).

    Note:
        - Configuration is fetched from tenant-specific database
        - Returns None gracefully if BigQuery not configured for tenant
        - Errors are logged but don't raise exceptions
        - Client is ready for immediate use after creation

    Example:
        >>> client = await get_tenant_bigquery_client(tenant_id)
        >>> if client:
        ...     events = client.get_date_range_events("2024-01-01", "2024-01-07")
    """
    try:
        bigquery_config = await get_tenant_bigquery_config(tenant_id)

        if not bigquery_config:
            logger.error(f"BigQuery configuration not found for tenant {tenant_id}")
            return None

        return BigQueryClient(bigquery_config)

    except Exception as e:
        logger.error(f"Failed to create BigQuery client for tenant {tenant_id}: {e}")
        return None


async def get_tenant_sftp_client(tenant_id: str) -> SFTPClient | None:
    """
    Create an SFTP client instance for a specific tenant.

    This factory function retrieves the tenant's SFTP configuration from
    the database and creates an SFTPClient instance ready for file downloads.

    Args:
        tenant_id: Tenant ID (UUID string) for configuration lookup and client creation.

    Returns:
        SFTPClient | None: Configured SFTPClient instance ready for file operations,
                          or None if configuration is not found or SFTP is disabled.

    Raises:
        Exception: If client creation fails (logged but returns None).

    Note:
        - Configuration is fetched from tenant-specific database
        - Returns None gracefully if SFTP not configured for tenant
        - Errors are logged but don't raise exceptions
        - Client is ready for immediate use after creation

    Example:
        >>> client = await get_tenant_sftp_client(tenant_id)
        >>> if client:
        ...     users_df = client._get_users_data_sync()
    """
    try:
        sftp_config = await get_tenant_sftp_config(tenant_id)

        if not sftp_config:
            logger.error(f"SFTP configuration not found for tenant {tenant_id}")
            return None

        return SFTPClient(sftp_config)

    except Exception as e:
        logger.error(f"Failed to create SFTP client for tenant {tenant_id}: {e}")
        return None
