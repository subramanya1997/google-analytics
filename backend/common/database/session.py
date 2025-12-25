"""
Common database session management with async support and connection pooling.

This module provides comprehensive database connection and session management for both
synchronous and asynchronous operations. It includes connection pooling, automatic
reconnection, health checks, and tenant-aware database access.

Key Features:
    - Connection pooling with configurable pool sizes
    - Automatic connection health checks and reconnection
    - Support for both sync and async operations
    - Tenant-aware database connections
    - Engine caching to avoid duplicate connections
    - Context managers for automatic session cleanup

Connection Pooling:
    - Sync pools: Default 20 connections, max overflow 30
    - Async pools: Default 15 connections, max overflow 25
    - Automatic connection recycling (1 hour)
    - Pre-ping enabled for connection validation

Tenant Isolation:
    Each tenant has a dedicated database. Database names follow the pattern:
    google-analytics-{tenant_id}

Usage:
    ```python
    # Sync context manager (recommended)
    from common.database import get_db_session
    
    with get_db_session(tenant_id="tenant-123") as session:
        users = session.query(User).all()
    
    # Async context manager
    from common.database import get_async_db_session
    
    async with get_async_db_session(tenant_id="tenant-123") as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
    ```
"""

from __future__ import annotations

from contextlib import asynccontextmanager, contextmanager
from functools import lru_cache
import os
from typing import Any

from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import URL, Engine
from sqlalchemy.exc import DisconnectionError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

load_dotenv()

# Global engine cache to avoid creating multiple engines
_engines: dict[str, Engine] = {}
_async_engines: dict[str, Any] = {}


def create_sqlalchemy_url(database_name: str, async_driver: bool = False) -> URL:
    """
    Create SQLAlchemy database URL from environment variables.

    This function constructs a SQLAlchemy URL object using database connection
    parameters from environment variables. It supports both synchronous and
    asynchronous database drivers.

    Args:
        database_name: Name of the database to connect to. Required for tenant isolation.
            For tenant databases, use get_tenant_database_name(tenant_id).
            For admin operations (creating databases), use 'postgres'.
        async_driver: Whether to use async driver. If True, uses 'postgresql+asyncpg'.
            If False, uses 'postgresql+pg8000' (synchronous).

    Returns:
        SQLAlchemy URL object configured with:
        - Driver: postgresql+asyncpg (async) or postgresql+pg8000 (sync)
        - Username: From POSTGRES_USER environment variable
        - Password: From POSTGRES_PASSWORD environment variable
        - Host: From POSTGRES_HOST environment variable
        - Port: From POSTGRES_PORT environment variable
        - Database: The provided database_name

    Raises:
        ValueError: If database_name is empty or None.

    Environment Variables:
        - POSTGRES_USER: Database username
        - POSTGRES_PASSWORD: Database password
        - POSTGRES_HOST: Database hostname or IP address
        - POSTGRES_PORT: Database port (default: 5432)

    Example:
        ```python
        # Create URL for tenant database
        from common.database.tenant_provisioning import get_tenant_database_name
        
        tenant_db = get_tenant_database_name("tenant-123")
        url = create_sqlalchemy_url(tenant_db)
        
        # Create URL for admin operations
        admin_url = create_sqlalchemy_url("postgres")
        
        # Create async URL
        async_url = create_sqlalchemy_url(tenant_db, async_driver=True)
        ```

    Note:
        - Database credentials should be stored securely (env vars, secrets manager)
        - For tenant isolation, always use tenant-specific database names
        - Use 'postgres' database only for administrative operations
    """
    if not database_name:
        msg = (
            "database_name is required for tenant-isolated architecture. "
            "Use get_tenant_database_name(tenant_id) for tenant databases, "
            "or 'postgres' for admin operations."
        )
        raise ValueError(
            msg
        )

    driver = "postgresql+asyncpg" if async_driver else "postgresql+pg8000"

    return URL.create(
        drivername=driver,
        username=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST"),
        port=int(os.getenv("POSTGRES_PORT")),
        database=database_name,
    )


def _setup_engine_events(engine: Engine) -> None:
    """Setup engine events for connection monitoring and health checks."""

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
        """Set connection-level settings."""
        # For PostgreSQL, we can set statement_timeout
        if hasattr(dbapi_connection, "execute"):
            try:
                cursor = dbapi_connection.cursor()
                # Set statement timeout to 30 seconds
                cursor.execute("SET statement_timeout = '30s'")
                cursor.close()
            except Exception as e:
                logger.warning(f"Could not set statement timeout: {e}")

    @event.listens_for(engine, "engine_connect")
    def ping_connection(connection: Any, branch: Any) -> None:
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
                {"database_name": database_name},
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
def get_engine(
    service_name: str | None = None, database_name: str | None = None, tenant_id: str | None = None
) -> Engine:
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
        msg = (
            "Either database_name or tenant_id must be provided. "
            "Master database concept removed for SOC2 compliance."
        )
        raise ValueError(
            msg
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
            },
        },
    )

    # Setup connection monitoring
    _setup_engine_events(engine)

    # Cache the engine
    _engines[cache_key] = engine

    logger.info(
        f"Created database engine for {service_name or 'default'} with pool_size={pool_size}, max_overflow={max_overflow}"
    )

    return engine


@lru_cache(maxsize=10)
def get_async_engine(
    service_name: str | None = None, database_name: str | None = None, tenant_id: str | None = None
) -> Any:
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
        msg = (
            "Either database_name or tenant_id must be provided. "
            "Master database concept removed for SOC2 compliance."
        )
        raise ValueError(
            msg
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
        },
    )

    # Cache the async engine
    _async_engines[cache_key] = async_engine

    logger.info(
        f"Created async database engine for {service_name or 'default'} with pool_size={pool_size}, max_overflow={max_overflow}"
    )

    return async_engine


# Session makers
@lru_cache(maxsize=10)
def get_session_maker(service_name: str | None = None, tenant_id: str | None = None) -> sessionmaker:
    """Get cached session maker for sync operations."""
    engine = get_engine(service_name, tenant_id=tenant_id)
    return sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,  # Keep objects usable after commit
    )


@lru_cache(maxsize=10)
def get_async_session_maker(
    service_name: str | None = None, tenant_id: str | None = None
) -> async_sessionmaker:
    """Get cached async session maker for async operations."""
    async_engine = get_async_engine(service_name, tenant_id=tenant_id)
    return async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


# Context managers for database sessions
@contextmanager
def get_db_session(service_name: str | None = None, tenant_id: str | None = None) -> Any:
    """
    Context manager for synchronous database sessions with automatic cleanup.

    This is the recommended way to obtain database sessions for synchronous operations.
    It handles session creation, transaction management, and cleanup automatically.
    If a tenant database doesn't exist, it will be automatically provisioned.

    Args:
        service_name: Optional name of the service (for logging and connection naming).
            Used to identify the service in connection pool metrics.
        tenant_id: Optional tenant ID. If provided, connects to the tenant-specific
            database. If the database doesn't exist, it will be automatically created
            and initialized.

    Yields:
        SQLAlchemy Session object ready for database operations.

    Raises:
        RuntimeError: If tenant database provisioning fails.
        ValueError: If neither tenant_id nor database_name is provided.

    Example:
        ```python
        from common.database import get_db_session
        from common.models import User
        
        # Using with tenant_id (recommended)
        with get_db_session(tenant_id="tenant-123") as session:
            users = session.query(User).all()
            new_user = User(name="John Doe")
            session.add(new_user)
            # Session automatically commits on successful exit
        
        # Using with service name
        with get_db_session(service_name="analytics-service", tenant_id="tenant-123") as session:
            result = session.execute(text("SELECT COUNT(*) FROM users"))
            count = result.scalar()
        ```

    Note:
        - Sessions automatically commit on successful exit
        - Sessions automatically rollback on exceptions
        - Sessions are automatically closed when exiting the context
        - Tenant databases are auto-provisioned if they don't exist
        - This is a synchronous operation - use get_async_db_session for async code
    """
    # Auto-provision tenant database if it doesn't exist
    if tenant_id:
        from common.database.tenant_provisioning import (
            provision_tenant_database,
            tenant_database_exists,
        )

        if not tenant_database_exists(tenant_id):
            import asyncio

            logger.info(
                f"Tenant database for {tenant_id} not found, auto-provisioning..."
            )
            success = asyncio.run(provision_tenant_database(tenant_id))
            if not success:
                msg = f"Failed to provision database for tenant {tenant_id}"
                raise RuntimeError(
                    msg
                )

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
async def get_async_db_session(service_name: str | None = None, tenant_id: str | None = None) -> Any:
    """
    Async context manager for asynchronous database sessions with automatic cleanup.

    This is the recommended way to obtain database sessions for asynchronous operations.
    It handles session creation, transaction management, and cleanup automatically.
    If a tenant database doesn't exist, it will be automatically provisioned.

    Args:
        service_name: Optional name of the service (for logging and connection naming).
            Used to identify the service in connection pool metrics.
        tenant_id: Optional tenant ID. If provided, connects to the tenant-specific
            database. If the database doesn't exist, it will be automatically created
            and initialized.

    Yields:
        SQLAlchemy AsyncSession object ready for async database operations.

    Raises:
        RuntimeError: If tenant database provisioning fails.
        ValueError: If neither tenant_id nor database_name is provided.

    Example:
        ```python
        from common.database import get_async_db_session
        from common.models import User
        from sqlalchemy import select
        
        # Using with tenant_id (recommended)
        async with get_async_db_session(tenant_id="tenant-123") as session:
            result = await session.execute(select(User))
            users = result.scalars().all()
            
            new_user = User(name="Jane Doe")
            session.add(new_user)
            # Session automatically commits on successful exit
        
        # Using with service name
        async with get_async_db_session(
            service_name="analytics-service",
            tenant_id="tenant-123"
        ) as session:
            result = await session.execute(text("SELECT COUNT(*) FROM users"))
            count = result.scalar()
        ```

    Note:
        - Sessions automatically commit on successful exit
        - Sessions automatically rollback on exceptions
        - Sessions are automatically closed when exiting the context
        - Tenant databases are auto-provisioned if they don't exist
        - This is an asynchronous operation - use get_db_session for sync code
        - All database operations must be awaited
    """
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
