"""
Database Dependency Injection for Analytics Service

This module provides FastAPI dependency functions for injecting database clients
into API endpoints. It uses caching to ensure a single instance of the database
client is reused across all requests, improving performance and resource usage.

Dependencies:
    - get_analytics_db_client: Provides a singleton AnalyticsPostgresClient instance

Design Pattern:
    Uses the dependency injection pattern with LRU caching to ensure:
    1. Single instance of database client (singleton pattern)
    2. Efficient resource usage (connection pooling handled by SQLAlchemy)
    3. Thread-safe concurrent access (async-safe)

Example:
    ```python
    from fastapi import Depends
    from services.analytics_service.database.dependencies import (
        get_analytics_db_client
    )
    from services.analytics_service.database.postgres_client import (
        AnalyticsPostgresClient
    )
    
    @router.get("/stats")
    async def get_stats(
        tenant_id: str = Depends(get_tenant_id),
        db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client)
    ):
        return await db_client.get_overview_stats(tenant_id, ...)
    ```

See Also:
    - services.analytics_service.database.postgres_client: Database client implementation
    - fastapi.Depends: FastAPI dependency injection mechanism
"""

from functools import lru_cache

from services.analytics_service.database.postgres_client import AnalyticsPostgresClient


@lru_cache(maxsize=1)
def get_analytics_db_client() -> AnalyticsPostgresClient:
    """
    Get a cached singleton instance of the Analytics PostgreSQL client.

    This dependency function ensures that only one instance of AnalyticsPostgresClient
    is created and reused across all requests. The client is stateless and uses
    connection pooling, making it safe for concurrent use.

    Returns:
        AnalyticsPostgresClient: A singleton instance of the database client.

    Caching:
        Uses functools.lru_cache with maxsize=1 to ensure only one instance exists.
        The cache persists for the lifetime of the application process.

    Thread Safety:
        The returned client is safe for concurrent use across multiple async tasks.
        Each method call creates its own database session from the connection pool.

    Example:
        ```python
        # In an endpoint
        @router.get("/endpoint")
        async def my_endpoint(
            db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client)
        ):
            # db_client is the same instance across all requests
            result = await db_client.get_overview_stats(...)
        ```

    See Also:
        - services.analytics_service.database.postgres_client.AnalyticsPostgresClient:
            The client class being instantiated
    """
    return AnalyticsPostgresClient()
