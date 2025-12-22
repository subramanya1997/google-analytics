"""
Common database session management with async support and connection pooling.
"""
from __future__ import annotations
import os
from typing import Optional, Dict, Any
from functools import lru_cache
from contextlib import asynccontextmanager, contextmanager

from sqlalchemy import create_engine, text, event
from sqlalchemy.engine import URL, Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.exc import DisconnectionError
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# Global engine cache to avoid creating multiple engines
_engines: Dict[str, Engine] = {}
_async_engines: Dict[str, Any] = {}

def create_sqlalchemy_url(database_name: str, async_driver: bool = False) -> URL:
    """
    Create SQLAlchemy URL from environment variables.
    
    Args:
        database_name: Name of the database to connect to (required for tenant isolation)
        async_driver: Whether to use async driver (asyncpg) or sync driver (pg8000)
    
    Returns:
        SQLAlchemy URL object
    
    Note:
        For tenant isolation, use get_tenant_database_name(tenant_id) to get the database name.
        For admin operations (creating databases), use 'postgres' as the database name.
    """
    if not database_name:
        raise ValueError(
            "database_name is required for tenant-isolated architecture. "
            "Use get_tenant_database_name(tenant_id) for tenant databases, "
            "or 'postgres' for admin operations."
        )
    
    driver = "postgresql+asyncpg" if async_driver else "postgresql+pg8000"
    
    url = URL.create(
        drivername=driver,
        username=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST"),
        port=int(os.getenv("POSTGRES_PORT")),
        database=database_name,
    )
    return url


def _setup_engine_events(engine: Engine) -> None:
    """Setup engine events for connection monitoring and health checks."""
    
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Set connection-level settings."""
        # For PostgreSQL, we can set statement_timeout
        if hasattr(dbapi_connection, 'execute'):
            try:
                cursor = dbapi_connection.cursor()
                # Set statement timeout to 30 seconds
                cursor.execute("SET statement_timeout = '30s'")
                cursor.close()
            except Exception as e:
                logger.warning(f"Could not set statement timeout: {e}")
    
    @event.listens_for(engine, "engine_connect")
    def ping_connection(connection, branch):
        """Ping connection to ensure it's alive."""
        if branch:
            # "branch" refers to a sub-connection of a connection,
            # we don't want to bother pinging on these.
            return

        # turn off "close with result".  This flag is only used with
        # "connectionless" execution, otherwise will be False in any case
        save_should_close_with_result = connection.should_close_with_result
        connection.should_close_with_result = False

        try:
            # run a SELECT 1.   use a core select() so that
            # the SELECT of a scalar value without a table is
            # appropriately formatted for the backend
            connection.scalar(text("SELECT 1"))
        except Exception as err:
            # catch SQLAlchemy's DBAPIError, which is a wrapper
            # for the DBAPI's exception.  It includes a .connection_invalidated
            # attribute which specifies if this connection is a "disconnect"
            # condition, which is based on inspection of the original exception
            # by the dialect in use.
            if isinstance(err, DisconnectionError):
                # run the same SELECT again - the connection will re-validate
                # itself and establish a new connection.  The disconnect detection
                # here also causes the whole connection pool to be invalidated
                # so that all stale connections are discarded.
                connection.scalar(text("SELECT 1"))
            else:
                raise
        finally:
            # restore "close with result"
            connection.should_close_with_result = save_should_close_with_result


def database_exists(database_name: str) -> bool:
    """Check if a database exists."""
    try:
        # Connect to postgres database (default) to check if target database exists
        postgres_url = create_sqlalchemy_url("postgres")
        engine = create_engine(postgres_url)
        
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :database_name"),
                {"database_name": database_name}
            )
            return result.fetchone() is not None
    except Exception as e:
        logger.error(f"Error checking if database exists: {e}")
        return False


def create_database(database_name: str) -> bool:
    """Create a database if it doesn't exist."""
    try:
        if database_exists(database_name):
            logger.info(f"Database '{database_name}' already exists.")
            return True
            
        logger.info(f"Creating database '{database_name}'...")
        
        # Connect to postgres database (default) to create the target database
        postgres_url = create_sqlalchemy_url("postgres")
        engine = create_engine(postgres_url, isolation_level="AUTOCOMMIT")
        
        with engine.connect() as connection:
            # Use text() to properly escape the database name
            connection.execute(text(f'CREATE DATABASE "{database_name}"'))
            logger.info(f"Database '{database_name}' created successfully.")
            return True
            
    except Exception as e:
        logger.error(f"Error creating database '{database_name}': {e}")
        return False


@lru_cache(maxsize=10)
def get_engine(service_name: str = None, database_name: str = None, tenant_id: str = None) -> Engine:
    """
    Get cached database engine with optimized connection pooling.
    
    Args:
        service_name: Name of the service (for logging)
        database_name: Explicit database name
        tenant_id: Tenant ID (will be converted to database name)
    
    Returns:
        SQLAlchemy Engine instance
    
    Note:
        Either database_name or tenant_id must be provided for tenant-isolated architecture.
    """
    # If tenant_id is provided, use tenant-specific database
    if tenant_id and not database_name:
        from common.database.tenant_provisioning import get_tenant_database_name
        database_name = get_tenant_database_name(tenant_id)
    
    if not database_name:
        raise ValueError(
            "Either database_name or tenant_id must be provided. "
            "Master database concept removed for SOC2 compliance."
        )
    
    cache_key = f"{service_name or 'default'}_{database_name}"
    
    if cache_key in _engines:
        return _engines[cache_key]
    
    url = create_sqlalchemy_url(database_name)
    
    # Enhanced connection pool settings
    pool_size = int(os.getenv("DATABASE_POOL_SIZE", 20))  # Increased default
    max_overflow = int(os.getenv("DATABASE_MAX_OVERFLOW", 30))  # Increased default
    pool_timeout = int(os.getenv("DATABASE_POOL_TIMEOUT", 30))
    pool_recycle = int(os.getenv("DATABASE_POOL_RECYCLE", 3600))  # 1 hour
    
    engine = create_engine(
        url,
        # Connection pool settings
        poolclass=QueuePool,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
        pool_pre_ping=True,
        
        # Performance settings
        echo=os.getenv("DATABASE_ECHO", "false").lower() == "true",
        echo_pool=os.getenv("DATABASE_ECHO_POOL", "false").lower() == "true",
        
        # Connection settings
        connect_args={
            "connect_timeout": int(os.getenv("DATABASE_CONNECT_TIMEOUT", 10)),
            "server_settings": {
                "application_name": service_name or "analytics-service",
                "jit": "off",  # Disable JIT for faster connection times
            }
        }
    )
    
    # Setup connection monitoring
    _setup_engine_events(engine)
    
    # Cache the engine
    _engines[cache_key] = engine
    
    logger.info(f"Created database engine for {service_name or 'default'} with pool_size={pool_size}, max_overflow={max_overflow}")
    
    return engine


@lru_cache(maxsize=10)
def get_async_engine(service_name: str = None, database_name: str = None, tenant_id: str = None):
    """
    Get cached async database engine with optimized connection pooling.
    
    Args:
        service_name: Name of the service (for logging)
        database_name: Explicit database name
        tenant_id: Tenant ID (will be converted to database name)
    
    Returns:
        SQLAlchemy AsyncEngine instance
    
    Note:
        Either database_name or tenant_id must be provided for tenant-isolated architecture.
    """
    # If tenant_id is provided, use tenant-specific database
    if tenant_id and not database_name:
        from common.database.tenant_provisioning import get_tenant_database_name
        database_name = get_tenant_database_name(tenant_id)
    
    if not database_name:
        raise ValueError(
            "Either database_name or tenant_id must be provided. "
            "Master database concept removed for SOC2 compliance."
        )
    
    cache_key = f"async_{service_name or 'default'}_{database_name}"
    
    if cache_key in _async_engines:
        return _async_engines[cache_key]
    
    url = create_sqlalchemy_url(database_name, async_driver=True)
    
    # Enhanced connection pool settings for async
    pool_size = int(os.getenv("DATABASE_ASYNC_POOL_SIZE", 15))
    max_overflow = int(os.getenv("DATABASE_ASYNC_MAX_OVERFLOW", 25))
    pool_timeout = int(os.getenv("DATABASE_POOL_TIMEOUT", 30))
    pool_recycle = int(os.getenv("DATABASE_POOL_RECYCLE", 3600))
    
    async_engine = create_async_engine(
        url,
        # Connection pool settings (no poolclass needed for async engines)
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
        pool_pre_ping=True,
        
        # Performance settings
        echo=os.getenv("DATABASE_ECHO", "false").lower() == "true",
        
        # Async-specific settings
        connect_args={
            "server_settings": {
                "application_name": f"async-{service_name or 'analytics-service'}",
                "jit": "off",
            }
        }
    )
    
    # Cache the async engine
    _async_engines[cache_key] = async_engine
    
    logger.info(f"Created async database engine for {service_name or 'default'} with pool_size={pool_size}, max_overflow={max_overflow}")
    
    return async_engine


# Session makers
@lru_cache(maxsize=10)
def get_session_maker(service_name: str = None, tenant_id: str = None) -> sessionmaker:
    """Get cached session maker for sync operations."""
    engine = get_engine(service_name, tenant_id=tenant_id)
    return sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False  # Keep objects usable after commit
    )


@lru_cache(maxsize=10) 
def get_async_session_maker(service_name: str = None, tenant_id: str = None) -> async_sessionmaker:
    """Get cached async session maker for async operations."""
    async_engine = get_async_engine(service_name, tenant_id=tenant_id)
    return async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False
    )


# Context managers for database sessions
@contextmanager
def get_db_session(service_name: str = None, tenant_id: str = None):
    """Context manager for database sessions with automatic cleanup."""
    # Auto-provision tenant database if it doesn't exist
    if tenant_id:
        from common.database.tenant_provisioning import (
            tenant_database_exists,
            provision_tenant_database
        )
        if not tenant_database_exists(tenant_id):
            import asyncio
            logger.info(f"Tenant database for {tenant_id} not found, auto-provisioning...")
            success = asyncio.run(provision_tenant_database(tenant_id))
            if not success:
                raise RuntimeError(f"Failed to provision database for tenant {tenant_id}")
    
    session_maker = get_session_maker(service_name, tenant_id=tenant_id)
    session = session_maker()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()


@asynccontextmanager
async def get_async_db_session(service_name: str = None, tenant_id: str = None):
    """Async context manager for database sessions with automatic cleanup."""
    session_maker = get_async_session_maker(service_name, tenant_id=tenant_id)
    session = session_maker()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error(f"Async database session error: {e}")
        raise
    finally:
        await session.close()
