"""
Factory for creating tenant-aware clients that use configurations from the database.
"""
from typing import Optional, Dict, Any
from loguru import logger

from common.database import get_tenant_bigquery_config, get_tenant_sftp_config
from .bigquery_client import BigQueryClient
from .enhanced_bigquery_client import EnhancedBigQueryClient
from .sftp_client import SFTPClient
from .azure_sftp_client import AzureSFTPClient


class TenantClientFactory:
    """Factory for creating tenant-specific clients using database configurations."""
    
    @staticmethod
    def create_bigquery_client(tenant_id: str) -> Optional[BigQueryClient]:
        """
        Create a BigQuery client for a specific tenant using database configuration.
        
        Args:
            tenant_id: The tenant ID
            
        Returns:
            BigQueryClient instance or None if configuration not found
        """
        try:
            bigquery_config = get_tenant_bigquery_config(tenant_id, "data-ingestion-service")
            
            if not bigquery_config:
                logger.error(f"BigQuery configuration not found for tenant {tenant_id}")
                return None
            
            # Prepare config in the format expected by BigQueryClient
            client_config = {
                "tenant_id": tenant_id,
                "project_id": bigquery_config["project_id"],
                "dataset_id": bigquery_config["dataset_id"],
                "service_account": bigquery_config["service_account"]
            }
            
            return BigQueryClient(client_config)
            
        except Exception as e:
            logger.error(f"Failed to create BigQuery client for tenant {tenant_id}: {e}")
            return None
    
    @staticmethod
    def create_enhanced_bigquery_client(tenant_id: str) -> Optional[EnhancedBigQueryClient]:
        """
        Create an Enhanced BigQuery client for a specific tenant using database configuration.
        
        Args:
            tenant_id: The tenant ID
            
        Returns:
            EnhancedBigQueryClient instance or None if configuration not found
        """
        try:
            bigquery_config = get_tenant_bigquery_config(tenant_id, "data-ingestion-service")
            
            if not bigquery_config:
                logger.error(f"BigQuery configuration not found for tenant {tenant_id}")
                return None
            
            return EnhancedBigQueryClient(bigquery_config)
            
        except Exception as e:
            logger.error(f"Failed to create Enhanced BigQuery client for tenant {tenant_id}: {e}")
            return None
    
    @staticmethod
    def create_sftp_client(tenant_id: str) -> Optional[SFTPClient]:
        """
        Create an SFTP client for a specific tenant using database configuration.
        
        Args:
            tenant_id: The tenant ID
            
        Returns:
            SFTPClient instance or None if configuration not found
        """
        try:
            sftp_config = get_tenant_sftp_config(tenant_id, "data-ingestion-service")
            
            if not sftp_config:
                logger.error(f"SFTP configuration not found for tenant {tenant_id}")
                return None
            
            return SFTPClient(sftp_config)
            
        except Exception as e:
            logger.error(f"Failed to create SFTP client for tenant {tenant_id}: {e}")
            return None
    
    @staticmethod
    def create_azure_sftp_client(tenant_id: str) -> Optional[AzureSFTPClient]:
        """
        Create an Azure SFTP client for a specific tenant using database configuration.
        
        Args:
            tenant_id: The tenant ID
            
        Returns:
            AzureSFTPClient instance or None if configuration not found
        """
        try:
            sftp_config = get_tenant_sftp_config(tenant_id, "data-ingestion-service")
            
            if not sftp_config:
                logger.error(f"SFTP configuration not found for tenant {tenant_id}")
                return None
            
            return AzureSFTPClient(sftp_config)
            
        except Exception as e:
            logger.error(f"Failed to create Azure SFTP client for tenant {tenant_id}: {e}")
            return None


# Convenience functions for easy access
def get_tenant_bigquery_client(tenant_id: str) -> Optional[BigQueryClient]:
    """Convenience function to get BigQuery client for tenant."""
    return TenantClientFactory.create_bigquery_client(tenant_id)


def get_tenant_enhanced_bigquery_client(tenant_id: str) -> Optional[EnhancedBigQueryClient]:
    """Convenience function to get Enhanced BigQuery client for tenant."""
    return TenantClientFactory.create_enhanced_bigquery_client(tenant_id)


def get_tenant_sftp_client(tenant_id: str) -> Optional[SFTPClient]:
    """Convenience function to get SFTP client for tenant."""
    return TenantClientFactory.create_sftp_client(tenant_id)


def get_tenant_azure_sftp_client(tenant_id: str) -> Optional[AzureSFTPClient]:
    """Convenience function to get Azure SFTP client for tenant."""
    return TenantClientFactory.create_azure_sftp_client(tenant_id)
