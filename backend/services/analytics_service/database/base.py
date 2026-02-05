"""
Base Utilities for Analytics Service Database Layer

This module provides shared constants and utilities used across all repository
implementations in the Analytics Service.

Constants:
    SERVICE_NAME: The service name used for database session routing

See Also:
    - services.analytics_service.database.locations_repository: Location operations
    - services.analytics_service.database.tasks_repository: Task operations
    - services.analytics_service.database.history_repository: History operations
    - services.analytics_service.database.stats_repository: Statistics operations
    - common.database: Shared database session management
"""

# Service name constant for database session routing
SERVICE_NAME = "analytics-service"
