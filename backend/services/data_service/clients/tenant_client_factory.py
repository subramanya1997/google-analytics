"""
Tenant-Aware Client Factory for Multi-Tenant Data Source Integration.

This module provides a factory pattern for creating tenant-specific data source
clients (BigQuery and SFTP) using configurations stored in the database. It
enables secure, isolated access to tenant-specific data sources while providing
a consistent interface for client instantiation across the application.

Key Features:
- **Multi-Tenant Security**: Each tenant gets isolated client instances
- **Configuration Management**: Retrieves tenant configs from database
- **Error Handling**: Graceful degradation when configurations are missing
- **Client Lifecycle**: Proper instantiation and error recovery
- **Logging Integration**: Comprehensive logging for troubleshooting

Factory Pattern Benefits:
- Centralizes client creation logic
- Ensures consistent configuration retrieval
- Provides error handling and logging
- Enables easy testing and mocking
- Supports graceful degradation

Supported Client Types:
1. **BigQueryClient**: For GA4 analytics data extraction
2. **SFTPClient**: For user and location data processing

The factory retrieves tenant-specific configurations from the database
and instantiates properly configured client instances for secure,
isolated data access.
"""

from typing import Optional

from loguru import logger

from common.database import get_tenant_bigquery_config, get_tenant_sftp_config

from .sftp_client import SFTPClient
from .bigquery_client import BigQueryClient


class TenantClientFactory:
    """
    Factory for creating tenant-specific data source clients with database configuration.
    
    This factory handles the complexities of multi-tenant client instantiation by
    retrieving tenant-specific configurations from the database and creating
    properly authenticated client instances. It provides consistent error handling
    and logging across all client types.
    
    Key Responsibilities:
    - Retrieve tenant configurations from database
    - Instantiate authenticated client instances
    - Handle configuration validation and errors
    - Provide consistent logging and error reporting
    - Enable graceful degradation for missing configurations
    
    The factory pattern ensures that client creation logic is centralized and
    consistent across the application, making it easier to maintain and test
    multi-tenant data access patterns.
    """

    @staticmethod
    async def create_enhanced_bigquery_client(
        tenant_id: str,
    ) -> Optional[BigQueryClient]:
        """
        Create authenticated BigQuery client for tenant using database configuration.
        
        Retrieves tenant-specific BigQuery configuration from the database and
        instantiates a properly authenticated BigQuery client for GA4 data extraction.
        Handles configuration validation and provides detailed error logging.
        
        **Configuration Retrieval:**
        Fetches BigQuery configuration including:
        - Google Cloud project ID
        - BigQuery dataset ID  
        - Service account credentials (JSON)
        
        **Authentication:**
        Uses service account-based authentication for secure access to
        tenant-specific BigQuery datasets with minimal required permissions.
        
        Args:
            tenant_id: Unique tenant identifier for configuration lookup
            
        Returns:
            Optional[BigQueryClient]: Authenticated client instance or None if:
            - Configuration not found in database
            - Invalid service account credentials
            - Client instantiation failure
        """
        try:
            bigquery_config = await get_tenant_bigquery_config(
                tenant_id, "data-ingestion-service"
            )

            if not bigquery_config:
                logger.error(f"BigQuery configuration not found for tenant {tenant_id}")
                return None

            return BigQueryClient(bigquery_config)

        except Exception as e:
            logger.error(
                f"Failed to create Enhanced BigQuery client for tenant {tenant_id}: {e}"
            )
            return None

    @staticmethod
    async def create_azure_sftp_client(tenant_id: str) -> Optional[SFTPClient]:
        """
        Create authenticated Azure SFTP client for tenant using database configuration.
        
        Retrieves tenant-specific SFTP configuration from the database and
        instantiates a properly configured SFTP client for Azure Blob Storage
        endpoints. Handles connection validation and error recovery.
        
        **Configuration Retrieval:**
        Fetches SFTP configuration including:
        - Azure SFTP endpoint hostname
        - Authentication credentials (username/password)
        - File paths and naming conventions
        - Connection parameters and timeouts
        
        **Azure Integration:**
        Configured specifically for Azure Blob Storage SFTP endpoints with
        appropriate timeout settings and authentication patterns.
        
        Args:
            tenant_id: Unique tenant identifier for configuration lookup
            
        Returns:
            Optional[SFTPClient]: Configured client instance or None if:
            - Configuration not found in database
            - Invalid SFTP credentials or endpoint
            - Client instantiation failure
    
        """
        try:
            sftp_config = await get_tenant_sftp_config(tenant_id, "data-ingestion-service")

            if not sftp_config:
                logger.error(f"SFTP configuration not found for tenant {tenant_id}")
                return None

            return SFTPClient(sftp_config)

        except Exception as e:
            logger.error(
                f"Failed to create Azure SFTP client for tenant {tenant_id}: {e}"
            )
            return None


async def get_tenant_bigquery_client(
    tenant_id: str,
) -> Optional[BigQueryClient]:
    """
    Convenience function to create authenticated BigQuery client for tenant.
    
    This is a simplified interface for the most common use case of creating
    a BigQuery client for a specific tenant. It wraps the factory method
    with a more concise function signature.
    
    Args:
        tenant_id: Unique tenant identifier for configuration lookup
        
    Returns:
        Optional[BigQueryClient]: Authenticated client or None if unavailable
        
    """
    return await TenantClientFactory.create_enhanced_bigquery_client(tenant_id)


async def get_tenant_sftp_client(tenant_id: str) -> Optional[SFTPClient]:
    """
    Convenience function to create authenticated Azure SFTP client for tenant.
    
    This is a simplified interface for the most common use case of creating
    an SFTP client for a specific tenant. It wraps the factory method with
    a more concise function signature for improved developer experience.
    
    Args:
        tenant_id: Unique tenant identifier for configuration lookup
        
    Returns:
        Optional[SFTPClient]: Configured client or None if unavailable
        
    """
    return await TenantClientFactory.create_azure_sftp_client(tenant_id)
