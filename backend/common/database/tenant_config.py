"""
Tenant configuration utilities for retrieving configurations from the database.

This module provides functionality to retrieve and manage tenant-specific configurations
stored in the database. It enables multi-tenant applications to have different
configurations for BigQuery, PostgreSQL, SFTP, and other services on a per-tenant basis.

Key Features:
- Tenant configuration retrieval with caching
- Safe JSON parsing for configuration fields
- Service-specific configuration extraction
- Tenant validation and existence checking
- Error handling and logging

The tenant configuration system supports:
- BigQuery connection settings (project, dataset, service account)
- PostgreSQL database configurations
- SFTP connection parameters
- Custom configuration extensions

Example:
    ```python
    from common.database.tenant_config import get_tenant_bigquery_config
    
    # Get BigQuery config for a tenant
    config = await get_tenant_bigquery_config("tenant-123")
    if config:
        project_id = config["project_id"]
        dataset_id = config["dataset_id"]
    ```
"""
import json
from typing import Dict, Any, Optional
from sqlalchemy import text
from loguru import logger

from common.database.session import get_async_db_session


def _safe_json_parse(data: Any) -> Dict[str, Any]:
    """
    Safely parse JSON data that might already be a dictionary.
    
    Handles various input types and gracefully fails on invalid JSON,
    providing consistent dict output for configuration processing.
    
    Args:
        data: Input data that might be JSON string, dict, or None
        
    Returns:
        Parsed dictionary or empty dict if parsing fails
        
    """
    if data is None:
        return {}
    if isinstance(data, dict):
        return data
    if isinstance(data, str):
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON string: {data}")
            return {}
    return {}


class TenantConfigManager:
    """
    Manager for tenant-specific configurations stored in the database.
    
    Provides methods to retrieve and validate tenant configurations for various
    services including BigQuery, PostgreSQL, and SFTP. Handles JSON parsing,
    error handling, and provides convenience methods for service-specific configs.
    
    Attributes:
        service_name: Name of the service using this manager (for database connections)
        
    Example:
        ```python
        manager = TenantConfigManager("analytics-service")
        config = await manager.get_tenant_config("tenant-123")
        
        if config and config["is_active"]:
            bigquery_config = config["bigquery_config"]
            # Use configuration
        ```
    """
    
    def __init__(self, service_name: str = None):
        """
        Initialize the tenant config manager.
        
        Args:
            service_name: Name of the service using this manager for database connections
        """
        self.service_name = service_name
    
    async def get_tenant_config(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get all configurations for a tenant from the database.
        
        Retrieves complete tenant configuration including BigQuery, PostgreSQL,
        and SFTP settings. Only returns configurations for active tenants.
        
        Args:
            tenant_id: The tenant ID to retrieve configuration for
            
        Returns:
            Dictionary containing all tenant configurations with parsed JSON fields,
            or None if tenant not found or inactive
            
        Configuration Structure:
            {
                "tenant_id": str,
                "name": str,
                "domain": str,
                "bigquery_config": {
                    "project_id": str,
                    "dataset_id": str, 
                    "service_account": dict
                },
                "postgres_config": dict,
                "sftp_config": dict,
                "is_active": bool,
                "created_at": datetime,
                "updated_at": datetime
            }
        """
        try:
            async with get_async_db_session(self.service_name) as session:
                result = await session.execute(
                    text("""
                        SELECT 
                            id, name, domain,
                            bigquery_project_id, bigquery_dataset_id, bigquery_credentials,
                            postgres_config, sftp_config,
                            is_active, created_at, updated_at
                        FROM tenants 
                        WHERE id = :tenant_id AND is_active = true
                    """),
                    {"tenant_id": tenant_id}
                )
                row = result.fetchone()
                
                if not row:
                    logger.warning(f"Tenant not found or inactive: {tenant_id}")
                    return None
                
                # Parse JSON fields safely
                bigquery_credentials = _safe_json_parse(row.bigquery_credentials)
                postgres_config = _safe_json_parse(row.postgres_config)
                sftp_config = _safe_json_parse(row.sftp_config)
                
                return {
                    "tenant_id": row.id,
                    "name": row.name,
                    "domain": row.domain,
                    "bigquery_config": {
                        "project_id": row.bigquery_project_id,
                        "dataset_id": row.bigquery_dataset_id,
                        "service_account": bigquery_credentials
                    },
                    "postgres_config": postgres_config,
                    "sftp_config": sftp_config,
                    "is_active": row.is_active,
                    "created_at": row.created_at,
                    "updated_at": row.updated_at
                }
                
        except Exception as e:
            logger.error(f"Failed to get tenant config for {tenant_id}: {e}")
            return None
    
    async def get_bigquery_config(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get BigQuery configuration for a tenant.
        
        Args:
            tenant_id: The tenant ID
            
        Returns:
            Dict containing BigQuery configuration or None if not found
        """
        tenant_config = await self.get_tenant_config(tenant_id)
        return tenant_config.get("bigquery_config") if tenant_config else None
    
    async def get_postgres_config(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get PostgreSQL configuration for a tenant.
        
        Args:
            tenant_id: The tenant ID
            
        Returns:
            Dict containing PostgreSQL configuration or None if not found
        """
        tenant_config = await self.get_tenant_config(tenant_id)
        return tenant_config.get("postgres_config") if tenant_config else None
    
    async def get_sftp_config(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get SFTP configuration for a tenant.
        
        Args:
            tenant_id: The tenant ID
            
        Returns:
            Dict containing SFTP configuration or None if not found
        """
        tenant_config = await self.get_tenant_config(tenant_id)
        return tenant_config.get("sftp_config") if tenant_config else None
    
    async def validate_tenant_exists(self, tenant_id: str) -> bool:
        """
        Check if a tenant exists and is active.
        
        Args:
            tenant_id: The tenant ID
            
        Returns:
            True if tenant exists and is active, False otherwise
        """
        try:
            async with get_async_db_session(self.service_name) as session:
                result = await session.execute(
                    text("SELECT COUNT(*) FROM tenants WHERE id = :tenant_id AND is_active = true"),
                    {"tenant_id": tenant_id}
                )
                count = result.scalar()
                
                return count > 0
                
        except Exception as e:
            logger.error(f"Failed to validate tenant {tenant_id}: {e}")
            return False


# Global instance for easy access
_tenant_config_manager: Optional[TenantConfigManager] = None


def get_tenant_config_manager(service_name: str = None) -> TenantConfigManager:
    """Get a cached tenant config manager instance."""
    global _tenant_config_manager
    if _tenant_config_manager is None:
        _tenant_config_manager = TenantConfigManager(service_name)
    return _tenant_config_manager


async def get_tenant_bigquery_config(tenant_id: str, service_name: str = None) -> Optional[Dict[str, Any]]:
    """Convenience function to get BigQuery config for a tenant."""
    manager = get_tenant_config_manager(service_name)
    return await manager.get_bigquery_config(tenant_id)


async def get_tenant_postgres_config(tenant_id: str, service_name: str = None) -> Optional[Dict[str, Any]]:
    """Convenience function to get PostgreSQL config for a tenant."""
    manager = get_tenant_config_manager(service_name)
    return await manager.get_postgres_config(tenant_id)


async def get_tenant_sftp_config(tenant_id: str, service_name: str = None) -> Optional[Dict[str, Any]]:
    """Convenience function to get SFTP config for a tenant."""
    manager = get_tenant_config_manager(service_name)
    return await manager.get_sftp_config(tenant_id)
