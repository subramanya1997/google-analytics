"""
Tenant-aware database session management.
"""
from typing import Optional, Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker, Session
from loguru import logger

from .tenant_config import get_tenant_postgres_config


class TenantSessionManager:
    """Manager for tenant-specific database sessions."""
    
    def __init__(self):
        """Initialize the session manager."""
        self._engines: Dict[str, Any] = {}
        self._session_makers: Dict[str, Any] = {}
    
    def get_tenant_engine(self, tenant_id: str, service_name: str = None):
        """
        Get or create a database engine for a specific tenant.
        
        Args:
            tenant_id: The tenant ID
            service_name: Optional service name for logging
            
        Returns:
            SQLAlchemy engine for the tenant
        """
        if tenant_id not in self._engines:
            postgres_config = get_tenant_postgres_config(tenant_id, service_name)
            
            if not postgres_config:
                raise ValueError(f"PostgreSQL configuration not found for tenant {tenant_id}")
            
            # Create SQLAlchemy URL from tenant config
            url = URL.create(
                drivername="postgresql+pg8000",
                username=postgres_config.get("user"),
                password=postgres_config.get("password"),
                host=postgres_config.get("host"),
                port=int(postgres_config.get("port", 5432)),
                database=postgres_config.get("database", "postgres"),
            )
            
            # Create engine with connection pooling
            engine = create_engine(
                url,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=5,
            )
            
            self._engines[tenant_id] = engine
            logger.info(f"Created database engine for tenant {tenant_id}")
        
        return self._engines[tenant_id]
    
    def get_tenant_session_maker(self, tenant_id: str, service_name: str = None):
        """
        Get or create a session maker for a specific tenant.
        
        Args:
            tenant_id: The tenant ID
            service_name: Optional service name for logging
            
        Returns:
            SQLAlchemy session maker for the tenant
        """
        if tenant_id not in self._session_makers:
            engine = self.get_tenant_engine(tenant_id, service_name)
            session_maker = sessionmaker(bind=engine, autoflush=False, autocommit=False)
            self._session_makers[tenant_id] = session_maker
            logger.info(f"Created session maker for tenant {tenant_id}")
        
        return self._session_makers[tenant_id]
    
    def get_tenant_session(self, tenant_id: str, service_name: str = None) -> Session:
        """
        Get a database session for a specific tenant.
        
        Args:
            tenant_id: The tenant ID
            service_name: Optional service name for logging
            
        Returns:
            SQLAlchemy session for the tenant
        """
        session_maker = self.get_tenant_session_maker(tenant_id, service_name)
        return session_maker()
    
    def close_tenant_connections(self, tenant_id: str):
        """
        Close all connections for a specific tenant.
        
        Args:
            tenant_id: The tenant ID
        """
        if tenant_id in self._engines:
            self._engines[tenant_id].dispose()
            del self._engines[tenant_id]
            logger.info(f"Closed database connections for tenant {tenant_id}")
        
        if tenant_id in self._session_makers:
            del self._session_makers[tenant_id]
    
    def close_all_connections(self):
        """Close all tenant database connections."""
        for tenant_id in list(self._engines.keys()):
            self.close_tenant_connections(tenant_id)


# Global instance for easy access
_tenant_session_manager: Optional[TenantSessionManager] = None


def get_tenant_session_manager() -> TenantSessionManager:
    """Get a cached tenant session manager instance."""
    global _tenant_session_manager
    if _tenant_session_manager is None:
        _tenant_session_manager = TenantSessionManager()
    return _tenant_session_manager


def get_tenant_session(tenant_id: str, service_name: str = None) -> Session:
    """
    Convenience function to get a database session for a tenant.
    
    Args:
        tenant_id: The tenant ID
        service_name: Optional service name for logging
        
    Returns:
        SQLAlchemy session for the tenant
    """
    manager = get_tenant_session_manager()
    return manager.get_tenant_session(tenant_id, service_name)


def get_tenant_engine(tenant_id: str, service_name: str = None):
    """
    Convenience function to get a database engine for a tenant.
    
    Args:
        tenant_id: The tenant ID
        service_name: Optional service name for logging
        
    Returns:
        SQLAlchemy engine for the tenant
    """
    manager = get_tenant_session_manager()
    return manager.get_tenant_engine(tenant_id, service_name)
