"""
Database Package for Analytics Service

This package provides database access through specialized repository classes,
each handling a specific domain of analytics operations.

Repository Classes:
    - LocationsRepository: Location/branch queries for dashboard filters
    - TasksRepository: Task-related queries (purchases, carts, searches, etc.)
    - HistoryRepository: Session and user event history queries
    - StatsRepository: Dashboard statistics and chart data queries

Shared Utilities:
    - SERVICE_NAME: Service name constant for database session routing

Example:
    ```python
    from services.analytics_service.database import (
        LocationsRepository,
        TasksRepository,
        HistoryRepository,
        StatsRepository,
    )

    locations_repo = LocationsRepository()
    locations = await locations_repo.get_locations("tenant-123")
    ```

See Also:
    - services.analytics_service.api.dependencies: Dependency injection providers
    - common.database: Shared database session management
"""

from .base import SERVICE_NAME
from .history_repository import HistoryRepository
from .locations_repository import LocationsRepository
from .stats_repository import StatsRepository
from .tasks_repository import TasksRepository

__all__ = [
    "SERVICE_NAME",
    "LocationsRepository",
    "TasksRepository",
    "HistoryRepository",
    "StatsRepository",
]
