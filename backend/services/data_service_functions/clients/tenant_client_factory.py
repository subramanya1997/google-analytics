"""
Factory for creating tenant-aware clients using configurations from the database.
"""

from typing import Optional

from loguru import logger

from .sftp_client import SFTPClient
from .bigquery_client import BigQueryClient


async def get_tenant_bigquery_config(tenant_id: str) -> Optional[dict]:
    """Get BigQuery configuration for a tenant from the database."""
    from shared.database import create_repository
    
    repo = create_repository()
    return await repo.get_tenant_bigquery_config(tenant_id)


async def get_tenant_sftp_config(tenant_id: str) -> Optional[dict]:
    """Get SFTP configuration for a tenant from the database."""
    from shared.database import create_repository
    
    repo = create_repository()
    return await repo.get_tenant_sftp_config(tenant_id)


async def get_tenant_bigquery_client(tenant_id: str) -> Optional[BigQueryClient]:
    """
    Create a BigQuery client for a specific tenant using database configuration.

    Args:
        tenant_id: The tenant ID

    Returns:
        BigQueryClient instance or None if configuration not found
    """
    try:
        bigquery_config = await get_tenant_bigquery_config(tenant_id)

        if not bigquery_config:
            logger.error(f"BigQuery configuration not found for tenant {tenant_id}")
            return None

        return BigQueryClient(bigquery_config)

    except Exception as e:
        logger.error(
            f"Failed to create BigQuery client for tenant {tenant_id}: {e}"
        )
        return None


async def get_tenant_sftp_client(tenant_id: str) -> Optional[SFTPClient]:
    """
    Create an SFTP client for a specific tenant using database configuration.

    Args:
        tenant_id: The tenant ID

    Returns:
        SFTPClient instance or None if configuration not found
    """
    try:
        sftp_config = await get_tenant_sftp_config(tenant_id)

        if not sftp_config:
            logger.error(f"SFTP configuration not found for tenant {tenant_id}")
            return None

        return SFTPClient(sftp_config)

    except Exception as e:
        logger.error(
            f"Failed to create SFTP client for tenant {tenant_id}: {e}"
        )
        return None

