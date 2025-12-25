"""
Common database utilities and session management.
"""

from .base import Base
from .session import (
    # Core functions
    get_engine,
    get_async_engine,
    create_sqlalchemy_url,
    
    # Session makers
    get_session_maker,
    get_async_session_maker,
    
    # Context managers
    get_db_session,
    get_async_db_session,
    
    # Database utilities
    database_exists,
    create_database
)
from .tenant_config import (
    get_tenant_service_status
)
from .tenant_provisioning import (
    get_tenant_database_name,
    tenant_database_exists,
    provision_tenant_database,
    drop_tenant_database,
)

__all__ = [
    # Base
    "Base",
    
    # Core engine functions
    "get_engine",
    "get_async_engine", 
    "create_sqlalchemy_url",
    
    # Session makers
    "get_session_maker",
    "get_async_session_maker",
    
    # Context managers (recommended)
    "get_db_session",
    "get_async_db_session",
    
    # Database utilities
    "database_exists",
    "create_database",
    
    # Tenant configuration
    "get_tenant_service_status",
    
    # Tenant provisioning
    "get_tenant_database_name",
    "tenant_database_exists",
    "provision_tenant_database",
    "drop_tenant_database",
]
