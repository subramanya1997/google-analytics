"""
Common database utilities and session management.

This module provides a unified interface for database operations across the Google
Analytics Intelligence System. It includes SQLAlchemy session management, connection
pooling, tenant configuration management, and database utilities.

Key Components:
- Base: SQLAlchemy declarative base class with automatic timestamps
- Session Management: Sync and async session factories with connection pooling
- Tenant Configuration: Multi-tenant configuration retrieval from database
- Database Utilities: Database creation, validation, and health checking

The module is designed to handle multi-service, multi-tenant database operations
with robust connection management and error handling.

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
    SessionLocal,
    AsyncSessionLocal,
    
    # Context managers
    get_db_session,
    get_async_db_session,
    
    # Database utilities
    database_exists,
    create_database,
    ensure_database_exists,
)
from .tenant_config import (
    TenantConfigManager, 
    get_tenant_config_manager,
    get_tenant_bigquery_config,
    get_tenant_postgres_config,
    get_tenant_sftp_config
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
    "SessionLocal",
    "AsyncSessionLocal",
    
    # Context managers (recommended)
    "get_db_session",
    "get_async_db_session",
    
    # Database utilities
    "database_exists",
    "create_database", 
    "ensure_database_exists",
    
    # Tenant configuration
    "TenantConfigManager",
    "get_tenant_config_manager",
    "get_tenant_bigquery_config",
    "get_tenant_postgres_config", 
    "get_tenant_sftp_config",
]
