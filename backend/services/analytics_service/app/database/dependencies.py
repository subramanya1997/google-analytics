"""
Database dependency injection for analytics service.
"""
from functools import lru_cache
from services.analytics_service.app.database.postgres_client import AnalyticsPostgresClient


@lru_cache(maxsize=1)
def get_analytics_db_client() -> AnalyticsPostgresClient:
    """
    Get cached analytics database client.
    Using lru_cache to ensure only one instance is created.
    """
    return AnalyticsPostgresClient()
