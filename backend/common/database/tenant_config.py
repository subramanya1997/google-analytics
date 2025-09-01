"""
Tenant configuration utilities for retrieving configurations from the database.
"""
import json
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from loguru import logger

from common.database.session import get_engine


def _safe_json_parse(data: Any) -> Dict[str, Any]:
    """Safely parse JSON data that might already be a dictionary."""
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
    """Manager for tenant-specific configurations stored in the database."""
    
    def __init__(self, service_name: str = None):
        """Initialize the tenant config manager."""
        self.engine = get_engine(service_name)
    
    def get_tenant_config(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get all configurations for a tenant.
        
        Args:
            tenant_id: The tenant ID
            
        Returns:
            Dict containing all tenant configurations or None if not found
        """
        try:
            with Session(self.engine) as session:
                result = session.execute(
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
                ).fetchone()
                
                if not result:
                    logger.warning(f"Tenant not found or inactive: {tenant_id}")
                    return None
                
                # Parse JSON fields safely
                bigquery_credentials = _safe_json_parse(result.bigquery_credentials)
                postgres_config = _safe_json_parse(result.postgres_config)
                sftp_config = _safe_json_parse(result.sftp_config)
                
                return {
                    "tenant_id": result.id,
                    "name": result.name,
                    "domain": result.domain,
                    "bigquery_config": {
                        "project_id": result.bigquery_project_id,
                        "dataset_id": result.bigquery_dataset_id,
                        "service_account": bigquery_credentials
                    },
                    "postgres_config": postgres_config,
                    "sftp_config": sftp_config,
                    "is_active": result.is_active,
                    "created_at": result.created_at,
                    "updated_at": result.updated_at
                }
                
        except Exception as e:
            logger.error(f"Failed to get tenant config for {tenant_id}: {e}")
            return None
    
    def get_bigquery_config(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get BigQuery configuration for a tenant.
        
        Args:
            tenant_id: The tenant ID
            
        Returns:
            Dict containing BigQuery configuration or None if not found
        """
        tenant_config = self.get_tenant_config(tenant_id)
        return tenant_config.get("bigquery_config") if tenant_config else None
    
    def get_postgres_config(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get PostgreSQL configuration for a tenant.
        
        Args:
            tenant_id: The tenant ID
            
        Returns:
            Dict containing PostgreSQL configuration or None if not found
        """
        tenant_config = self.get_tenant_config(tenant_id)
        return tenant_config.get("postgres_config") if tenant_config else None
    
    def get_sftp_config(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get SFTP configuration for a tenant.
        
        Args:
            tenant_id: The tenant ID
            
        Returns:
            Dict containing SFTP configuration or None if not found
        """
        tenant_config = self.get_tenant_config(tenant_id)
        return tenant_config.get("sftp_config") if tenant_config else None
    
    def validate_tenant_exists(self, tenant_id: str) -> bool:
        """
        Check if a tenant exists and is active.
        
        Args:
            tenant_id: The tenant ID
            
        Returns:
            True if tenant exists and is active, False otherwise
        """
        try:
            with Session(self.engine) as session:
                result = session.execute(
                    text("SELECT COUNT(*) FROM tenants WHERE id = :tenant_id AND is_active = true"),
                    {"tenant_id": tenant_id}
                ).scalar()
                
                return result > 0
                
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


def get_tenant_bigquery_config(tenant_id: str, service_name: str = None) -> Optional[Dict[str, Any]]:
    """Convenience function to get BigQuery config for a tenant."""
    manager = get_tenant_config_manager(service_name)
    return manager.get_bigquery_config(tenant_id)


def get_tenant_postgres_config(tenant_id: str, service_name: str = None) -> Optional[Dict[str, Any]]:
    """Convenience function to get PostgreSQL config for a tenant."""
    manager = get_tenant_config_manager(service_name)
    return manager.get_postgres_config(tenant_id)


def get_tenant_sftp_config(tenant_id: str, service_name: str = None) -> Optional[Dict[str, Any]]:
    """Convenience function to get SFTP config for a tenant."""
    manager = get_tenant_config_manager(service_name)
    return manager.get_sftp_config(tenant_id)
