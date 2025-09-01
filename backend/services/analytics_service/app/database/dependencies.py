"""
Database dependency injection for analytics service.
"""
from functools import lru_cache
from typing import Dict
from services.analytics_service.app.database.postgres_client import AnalyticsPostgresClient
from services.analytics_service.app.database.tenant_postgres_client import TenantAnalyticsPostgresClient


@lru_cache(maxsize=1)
def get_analytics_db_client() -> AnalyticsPostgresClient:
    """
    Get cached analytics database client.
    Using lru_cache to ensure only one instance is created.
    """
    return AnalyticsPostgresClient()


# Cache for tenant-specific clients
_tenant_clients: Dict[str, TenantAnalyticsPostgresClient] = {}


def get_tenant_analytics_db_client(tenant_id: str) -> TenantAnalyticsPostgresClient:
    """
    Get cached tenant-specific analytics database client.
    
    Args:
        tenant_id: The tenant ID
        
    Returns:
        TenantAnalyticsPostgresClient instance for the tenant
    """
    if tenant_id not in _tenant_clients:
        _tenant_clients[tenant_id] = TenantAnalyticsPostgresClient(tenant_id)
    
    return _tenant_clients[tenant_id]
