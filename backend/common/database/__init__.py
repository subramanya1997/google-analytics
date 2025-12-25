"""
Common database utilities and session management.

This module provides a comprehensive database abstraction layer for all backend services,
including connection pooling, session management, tenant isolation, and database
provisioning utilities.

Key Features:
    - Multi-tenant database isolation (SOC2 compliant)
    - Async and sync database session support
    - Connection pooling with automatic reconnection
    - Database provisioning and schema initialization
    - Tenant configuration management

Architecture:
    The module implements a tenant-isolated architecture where each tenant has a
    dedicated PostgreSQL database. This ensures complete data isolation and SOC2
    compliance. Database names follow the pattern: google-analytics-{tenant_id}

Main Components:
    - Base: SQLAlchemy declarative base class for all ORM models
    - session: Database connection and session management
    - tenant_config: Tenant service configuration retrieval
    - tenant_provisioning: Database creation and schema initialization

Usage:
    ```python
    from common.database import get_db_session, get_tenant_database_name
    
    # Using context manager (recommended)
    with get_db_session(tenant_id="tenant-123") as session:
        result = session.query(User).all()
    
    # Get tenant database name
    db_name = get_tenant_database_name("tenant-123")
    # Returns: "google-analytics-tenant-123"
    ```
"""

from .base import Base
from .session import (
    create_database,
    create_sqlalchemy_url,
    # Database utilities
    database_exists,
    get_async_db_session,
    get_async_engine,
    get_async_session_maker,
    # Context managers
    get_db_session,
    # Core functions
    get_engine,
    # Session makers
    get_session_maker,
)
from .tenant_config import get_tenant_service_status
from .tenant_provisioning import (
    drop_tenant_database,
    get_tenant_database_name,
    provision_tenant_database,
    tenant_database_exists,
)

__all__ = [
    # Base
    "Base",
    "create_database",
    "create_sqlalchemy_url",
    # Database utilities
    "database_exists",
    "drop_tenant_database",
    "get_async_db_session",
    "get_async_engine",
    "get_async_session_maker",
    # Context managers (recommended)
    "get_db_session",
    # Core engine functions
    "get_engine",
    # Session makers
    "get_session_maker",
    # Tenant provisioning
    "get_tenant_database_name",
    # Tenant configuration
    "get_tenant_service_status",
    "provision_tenant_database",
    "tenant_database_exists",
]
