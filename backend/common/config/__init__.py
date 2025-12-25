"""
Centralized configuration management for all backend services.

This module provides a unified interface for accessing service-specific configuration
settings. It automatically selects the appropriate settings class based on the service
name, ensuring each service gets its correct configuration.

The configuration system uses Pydantic Settings, which automatically loads values from:
    1. Environment variables (highest priority)
    2. .env file in the project root
    3. Default values defined in the settings classes

Service-Specific Settings:
    - AnalyticsServiceSettings: Configuration for analytics-service
    - DataServiceSettings: Configuration for data-ingestion-service
    - AuthServiceSettings: Configuration for auth-service
    - BaseServiceSettings: Base configuration shared by all services

Example:
    ```python
    from common.config import get_settings
    
    # Get settings for a specific service
    settings = get_settings("analytics-service")
    print(settings.SERVICE_NAME)  # "analytics-service"
    print(settings.PORT)  # 8001
    
    # Use settings in your application
    app.run(host="0.0.0.0", port=settings.PORT)
    ```
"""

from common.config.settings import (
    AnalyticsServiceSettings,
    AuthServiceSettings,
    BaseServiceSettings,
    DataServiceSettings,
)


def get_settings(service_name: str | None = None) -> BaseServiceSettings:
    """
    Get settings instance for the specified service.

    This function returns the appropriate settings class based on the service name.
    It performs fuzzy matching to handle variations in service naming (e.g., "analytics"
    matches "analytics-service").

    Args:
        service_name: Name of the service to get settings for. Can be:
            - "analytics-service" or any string containing "analytics"
            - "data-ingestion-service" or any string containing "data"
            - "auth-service" or any string containing "auth"
            - None or any other value returns BaseServiceSettings

    Returns:
        Instance of the appropriate settings class:
            - AnalyticsServiceSettings if service_name contains "analytics"
            - DataServiceSettings if service_name contains "data"
            - AuthServiceSettings if service_name contains "auth"
            - BaseServiceSettings otherwise (default)

    Example:
        ```python
        # Explicit service name
        settings = get_settings("analytics-service")
        
        # Fuzzy matching
        settings = get_settings("analytics")  # Returns AnalyticsServiceSettings
        
        # Default
        settings = get_settings()  # Returns BaseServiceSettings
        settings = get_settings("unknown-service")  # Returns BaseServiceSettings
        ```

    Note:
        - Settings are loaded from environment variables and .env file
        - Each call returns a new instance (settings are not cached)
        - Service name matching is case-insensitive
    """
    if service_name:
        service_lower = service_name.lower()
        if service_lower == "analytics-service" or "analytics" in service_lower:
            return AnalyticsServiceSettings()
        if service_lower == "data-ingestion-service" or "data" in service_lower:
            return DataServiceSettings()
        if service_lower == "auth-service" or "auth" in service_lower:
            return AuthServiceSettings()
    # Default to base settings
    return BaseServiceSettings()


__all__ = [
    "get_settings",
]
