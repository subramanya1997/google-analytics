"""
Tenant configuration utilities for retrieving configurations from the database.
"""
import json
from typing import Dict, Any
from sqlalchemy import text
from loguru import logger

from common.database.session import get_async_db_session

async def get_tenant_service_status(tenant_id: str, service_name: str = None) -> Dict[str, Dict[str, Any]]:
    """
    Get service enable/disable status for a tenant.
    
    Args:
        tenant_id: The tenant ID
        service_name: Service name for DB connection (optional)
    
    Returns:
        Dict containing service status for each service:
        {
            "bigquery": {"enabled": bool, "error": str|None},
            "sftp": {"enabled": bool, "error": str|None},
            "smtp": {"enabled": bool, "error": str|None}
        }
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
                {"tenant_id": tenant_id}
            )
            row = result.fetchone()
            
            if not row:
                logger.warning(f"Tenant not found or inactive: {tenant_id}")
                # Return all services disabled if tenant not found
                return {
                    "bigquery": {"enabled": False, "error": "Tenant not found or inactive"},
                    "sftp": {"enabled": False, "error": "Tenant not found or inactive"},
                    "smtp": {"enabled": False, "error": "Tenant not found or inactive"}
                }
            
            return {
                "bigquery": {
                    "enabled": row.bigquery_enabled if row.bigquery_enabled is not None else True,
                    "error": row.bigquery_validation_error
                },
                "sftp": {
                    "enabled": row.sftp_enabled if row.sftp_enabled is not None else True,
                    "error": row.sftp_validation_error
                },
                "smtp": {
                    "enabled": row.smtp_enabled if row.smtp_enabled is not None else True,
                    "error": row.smtp_validation_error
                }
            }
            
    except Exception as e:
        logger.error(f"Failed to get service status for tenant {tenant_id}: {e}")
        # Return all services disabled on error
        return {
            "bigquery": {"enabled": False, "error": f"Failed to retrieve status: {str(e)}"},
            "sftp": {"enabled": False, "error": f"Failed to retrieve status: {str(e)}"},
            "smtp": {"enabled": False, "error": f"Failed to retrieve status: {str(e)}"}
        }
