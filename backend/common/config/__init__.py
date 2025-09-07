"""
Centralized configuration management for all backend services.
"""

from common.config.settings import (
    AnalyticsServiceSettings,
    DataServiceSettings,
    AuthServiceSettings,
    BaseServiceSettings,
)

def get_settings(service_name: str = None) -> BaseServiceSettings:
    """Get settings instance for the specified service."""
    if service_name == "analytics-service" or "analytics" in service_name:
        if _analytics_settings is None:
            _analytics_settings = AnalyticsServiceSettings()
        return _analytics_settings
    elif service_name == "data-ingestion-service" or "data" in service_name:
        if _data_settings is None:
            _data_settings = DataServiceSettings()
        return _data_settings
    elif service_name == "auth-service" or "auth" in service_name:
        if _auth_settings is None:
            _auth_settings = AuthServiceSettings()
        return _auth_settings
    else:
        # Default to base settings
        return BaseServiceSettings()

__all__ = [
    "get_settings",
]
