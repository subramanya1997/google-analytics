"""
Centralized configuration management for all backend services.
"""

from .settings import get_settings, BaseServiceSettings

__all__ = ["get_settings", "BaseServiceSettings"]
