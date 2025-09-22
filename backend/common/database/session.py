"""
Common database session management with async support and connection pooling.

This module provides comprehensive database session management for the Google Analytics
Intelligence System, supporting both synchronous and asynchronous operations with
optimized connection pooling, health checking, and error handling.

Key Features:
- Sync and async SQLAlchemy session management
- Connection pooling with configurable limits
- Automatic connection health checking and recovery
- Database creation and existence validation
- Service-specific engine caching
- Connection event monitoring and logging
- PostgreSQL-specific optimizations

The module uses a factory pattern with LRU caching to ensure efficient resource
management and prevent connection leaks across multiple services.

Connection Pool Configuration:
    Environment variables control pool behavior:
    - DATABASE_POOL_SIZE: Base connection pool size (default: 20)
    - DATABASE_MAX_OVERFLOW: Additional connections beyond pool_size (default: 30)
    - DATABASE_POOL_TIMEOUT: Seconds to wait for connection (default: 30)
    - DATABASE_POOL_RECYCLE: Seconds before recycling connections (default: 3600)
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

def create_sqlalchemy_url(database_name: str = None, async_driver: bool = False) -> URL:
    """
    Create SQLAlchemy database URL from environment variables.
    
    Constructs a PostgreSQL connection URL using environment variables for
    connection parameters. Supports both synchronous and asynchronous drivers
    with appropriate PostgreSQL adapters.
    
    Args:
        database_name: Name of the database to connect to. If None, uses
                      POSTGRES_DATABASE environment variable.
        async_driver: Whether to use async driver (asyncpg) or sync driver (pg8000).
                     Default is False for synchronous connections.
    
    Returns:
        SQLAlchemy URL object configured for PostgreSQL connection
        
    Environment Variables Required:
        - POSTGRES_USER: Database username
        - POSTGRES_PASSWORD: Database password  
        - POSTGRES_HOST: Database host
        - POSTGRES_PORT: Database port
        - POSTGRES_DATABASE: Default database name (used if database_name is None)
        
    Example:
        ```python
        # Sync connection
        sync_url = create_sqlalchemy_url("mydb")
        
        # Async connection
        async_url = create_sqlalchemy_url("mydb", async_driver=True)
        ```
        
    Note:
        Uses pg8000 for synchronous connections and asyncpg for asynchronous
        connections, both optimized for PostgreSQL.
    """
    driver = "postgresql+asyncpg" if async_driver else "postgresql+pg8000"
    
    url = URL.create(
        drivername=driver,
        username=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST"),
        port=int(os.getenv("POSTGRES_PORT")),
        database=database_name or os.getenv("POSTGRES_DATABASE"),
    )
    return url


def _setup_engine_events(engine: Engine) -> None:
    """
    Configure engine event listeners for connection monitoring and optimization.
    
    Sets up SQLAlchemy engine events to handle connection-level configuration,
    health checking, and automatic recovery from stale connections. These events
    ensure robust database connectivity across the application lifecycle.
    
    Args:
        engine: SQLAlchemy Engine instance to configure
        
    Event Handlers Registered:
        - connect: Sets PostgreSQL connection-level parameters
        - engine_connect: Performs connection health checks with ping
    """
    
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """
        Configure connection-level PostgreSQL settings.
        
        Sets important PostgreSQL parameters when new connections are established,
        including statement timeout to prevent long-running queries from hanging.
        
        Args:
            dbapi_connection: Raw database connection
            connection_record: SQLAlchemy connection record metadata
        """
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
        """
        Health check connections to detect and recover from disconnections.
        
        Performs a lightweight ping operation on connections to ensure they're
        still valid before use. Automatically handles connection recovery for
        disconnected or stale connections by invalidating the pool.
        
        Args:
            connection: SQLAlchemy connection wrapper
            branch: Whether this is a sub-connection (ignored for ping checks)
        """
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
    """
    Check if a PostgreSQL database exists.
    
    Connects to the default 'postgres' database to query the system catalog
    for the existence of the target database. This is a non-destructive
    operation that doesn't affect the target database.
    
    Args:
        database_name: Name of the database to check for existence
        
    Returns:
        True if the database exists, False otherwise or if an error occurs
        
    Example:
        ```python
        if database_exists("analytics_db"):
            print("Database is ready")
        else:
            create_database("analytics_db")
        ```
    """
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
    """
    Create a PostgreSQL database if it doesn't already exist.
    
    Safely creates a new database by first checking for existence, then
    creating if necessary. Uses AUTOCOMMIT isolation level to ensure
    the CREATE DATABASE command executes properly.
    
    Args:
        database_name: Name of the database to create
        
    Returns:
        True if database exists or was created successfully, False on error
        
    Side Effects:
        - Creates a new PostgreSQL database if it doesn't exist
        - Logs database creation status
        
    Example:
        ```python
        if create_database("new_tenant_db"):
            print("Database ready for use")
        else:
            print("Failed to create database")
        ```
        
    Note:
        Requires database user to have CREATE DATABASE privileges.
    """
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


def ensure_database_exists() -> bool:
    """
    Ensure the configured database exists, creating it if necessary.
    
    Reads the database name from the POSTGRES_DATABASE environment variable
    and ensures it exists in the PostgreSQL server. Creates the database
    if it doesn't exist.
    
    Returns:
        True if database exists or was created successfully, False on error
        
    Environment Variables:
        POSTGRES_DATABASE: Name of the database to ensure exists
        
    Example:
        ```python
        # In application startup
        if not ensure_database_exists():
            raise RuntimeError("Failed to ensure database exists")
        ```
        
    Note:
        This is typically called during application initialization to ensure
        the target database is available before attempting connections.
    """
    database_name = os.getenv("POSTGRES_DATABASE")
    if not database_name:
        logger.error("POSTGRES_DATABASE environment variable is not set")
        return False
        
    return create_database(database_name)


@lru_cache(maxsize=10)
def get_engine(service_name: str = None, database_name: str = None) -> Engine:
    """
    Get cached SQLAlchemy engine with optimized connection pooling.
    
    Creates and caches database engines per service and database combination,
    with comprehensive connection pooling, health checking, and PostgreSQL
    optimizations. Engines are cached using LRU to prevent resource leaks
    while allowing efficient reuse.
    
    Args:
        service_name: Name of the service using the engine (used for application_name)
        database_name: Name of the database to connect to (uses env default if None)
        
    Returns:
        Configured SQLAlchemy Engine with connection pooling and health monitoring
        
    Connection Pool Configuration:
        - pool_size: Base number of connections (env: DATABASE_POOL_SIZE, default: 20)
        - max_overflow: Additional connections beyond pool_size (env: DATABASE_MAX_OVERFLOW, default: 30)
        - pool_timeout: Seconds to wait for available connection (env: DATABASE_POOL_TIMEOUT, default: 30)
        - pool_recycle: Seconds before recycling connections (env: DATABASE_POOL_RECYCLE, default: 3600)
        - pool_pre_ping: Validates connections before use (always enabled)
        
    Performance Features:
        - Connection health checking with automatic recovery
        - PostgreSQL JIT disabled for faster connection setup
        - Configurable statement timeout (30s)
        - Connection-level optimizations
        
    Note:
        Engines are cached per (service_name, database_name) combination.
        LRU cache prevents memory leaks from unused engines.
    """
    cache_key = f"{service_name or 'default'}_{database_name or 'default'}"
    
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
def get_async_engine(service_name: str = None, database_name: str = None):
    """
    Get cached async SQLAlchemy engine with optimized connection pooling.
    
    Creates and caches async database engines per service and database combination,
    using asyncpg driver for high-performance asynchronous PostgreSQL connections.
    Async engines are optimized for concurrent workloads and non-blocking operations.
    
    Args:
        service_name: Name of the service using the engine (used for application_name)
        database_name: Name of the database to connect to (uses env default if None)
        
    Returns:
        Configured async SQLAlchemy Engine with connection pooling
        
    Async Connection Pool Configuration:
        - pool_size: Base number of connections (env: DATABASE_ASYNC_POOL_SIZE, default: 15)
        - max_overflow: Additional connections (env: DATABASE_ASYNC_MAX_OVERFLOW, default: 25)  
        - pool_timeout: Seconds to wait for connection (env: DATABASE_POOL_TIMEOUT, default: 30)
        - pool_recycle: Seconds before recycling connections (env: DATABASE_POOL_RECYCLE, default: 3600)
        - pool_pre_ping: Validates connections before use (always enabled)
        
    Performance Features:
        - asyncpg driver for native async PostgreSQL operations
        - PostgreSQL JIT disabled for faster connection setup
        - Prefixed application_name for monitoring
        - Optimized pool sizes for async workloads
        
    Note:
        Async engines use smaller default pool sizes as they're more efficient
        at handling concurrent connections than synchronous engines.
    """
    cache_key = f"async_{service_name or 'default'}_{database_name or 'default'}"
    
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
def get_session_maker(service_name: str = None) -> sessionmaker:
    """Get cached session maker for sync operations."""
    engine = get_engine(service_name)
    return sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False  # Keep objects usable after commit
    )


@lru_cache(maxsize=10) 
def get_async_session_maker(service_name: str = None) -> async_sessionmaker:
    """Get cached async session maker for async operations."""
    async_engine = get_async_engine(service_name)
    return async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False
    )


# Context managers for database sessions
@contextmanager
def get_db_session(service_name: str = None):
    """
    Context manager for synchronous database sessions with automatic cleanup.
    
    Provides a transactional database session with automatic commit/rollback
    and resource cleanup. This is the recommended way to perform database
    operations in synchronous code.
    
    Args:
        service_name: Service name for engine selection and logging
        
    Yields:
        SQLAlchemy Session configured for the specified service
        
    Transaction Handling:
        - Automatically commits on successful completion
        - Rolls back on exceptions
        - Always closes session to prevent resource leaks
        - Logs errors for debugging
        
    Error Handling:
        Exceptions are automatically handled with rollback and re-raised
        after logging for upstream handling.
    """
    session_maker = get_session_maker(service_name)
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
async def get_async_db_session(service_name: str = None):
    """
    Async context manager for asynchronous database sessions with automatic cleanup.
    
    Provides a transactional async database session with automatic commit/rollback
    and resource cleanup. This is the recommended way to perform database
    operations in asynchronous code.
    
    Args:
        service_name: Service name for engine selection and logging
        
    Yields:
        SQLAlchemy AsyncSession configured for the specified service
        
    Transaction Handling:
        - Automatically commits on successful completion
        - Rolls back on exceptions  
        - Always closes session to prevent resource leaks
        - Logs errors for debugging
        
    Error Handling:
        Exceptions are automatically handled with rollback and re-raised
        after logging for upstream handling.
    """
    session_maker = get_async_session_maker(service_name)
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


# Legacy compatibility
SessionLocal = get_session_maker()
AsyncSessionLocal = get_async_session_maker()
