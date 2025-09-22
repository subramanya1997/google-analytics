"""
Centralized configuration management for all backend services.

This module provides a unified interface for accessing service-specific configuration
settings across the Google Analytics Intelligence System. It includes a factory function
that returns the appropriate settings class based on the service name, enabling
consistent configuration management across all backend services.

The configuration system is built on Pydantic settings with support for:
- Environment variable loading
- Type validation and conversion
- Service-specific overrides
- Development vs. production environment handling

Example:
    ```python
    from common.config import get_settings
    
    # Get settings for analytics service
    settings = get_settings("analytics-service")
    
    # Use configuration
    app = FastAPI(title=settings.SERVICE_NAME)
    app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS)
    ```
"""

from common.config.settings import (
    AnalyticsServiceSettings,
    DataServiceSettings,
    AuthServiceSettings,
    BaseServiceSettings,
)

def get_settings(service_name: str = None) -> BaseServiceSettings:
    """
    Factory function to get appropriate settings instance for a service.
    
    Determines the correct settings class based on the service name and returns
    an instance with environment variables loaded and validated. Uses fuzzy
    matching to handle variations in service naming (e.g., "analytics" matches
    "analytics-service").
    
    Args:
        service_name: Name of the service to get settings for. Can be exact
                     service name (e.g., "analytics-service") or partial name
                     (e.g., "analytics"). If None, returns base settings.
    
    Returns:
        Settings instance with configuration loaded from environment variables
        and defaults applied. Type depends on service_name:
        - "analytics-service" or contains "analytics" -> AnalyticsServiceSettings
        - "data-ingestion-service" or contains "data" -> DataServiceSettings  
        - "auth-service" or contains "auth" -> AuthServiceSettings
        - Other/None -> BaseServiceSettings
    """
    if service_name == "analytics-service" or "analytics" in str(service_name):
        _analytics_settings = AnalyticsServiceSettings()
        return _analytics_settings
    elif service_name == "data-ingestion-service" or "data" in service_name:
        _data_settings = DataServiceSettings()
        return _data_settings
    elif service_name == "auth-service" or "auth" in service_name:
        _auth_settings = AuthServiceSettings()
        return _auth_settings
    else:
        # Default to base settings
        return BaseServiceSettings()

__all__ = [
    "get_settings",
]
