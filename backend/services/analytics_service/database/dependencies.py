"""
Database Dependencies for Analytics Service.

Provides dependency injection for database clients used throughout the analytics
service, ensuring single instance management and proper connection handling.
"""

from functools import lru_cache

from services.analytics_service.database.postgres_client import AnalyticsPostgresClient


@lru_cache(maxsize=1)
def get_analytics_db_client() -> AnalyticsPostgresClient:
    """
    Get cached analytics database client instance.
    
    Uses LRU cache to ensure only one instance is created and reused across
    the application lifecycle, preventing connection overhead and ensuring
    consistent database interaction patterns.
    
    Returns:
        AnalyticsPostgresClient: Singleton database client instance
    """
    return AnalyticsPostgresClient()
