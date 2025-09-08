"""
Centralized configuration management for all backend services.
"""
import os
from typing import List, Any
from pydantic import validator
from pydantic_settings import BaseSettings


class BaseServiceSettings(BaseSettings):
    """Base settings class for all services."""
    
    # Service Information (defaults)
    SERVICE_NAME: str = "base-service"
    SERVICE_VERSION: str = "0.0.1"
    PORT: int = 8000
    
    # Global Configuration
    ENVIRONMENT: str = "DEV"  # Can be "DEV" or "PROD"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    
    # CORS Configuration
    CORS_ORIGINS: Any = ""
    
    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        elif isinstance(v, list):
            return v
        return []
    
    # Database Configuration
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 5
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"
    
    # Note: PostgreSQL configuration is now retrieved dynamically from the database
    # via the tenant configuration system. See common.database.tenant_config module.


class AnalyticsServiceSettings(BaseServiceSettings):
    """Settings for analytics service."""
    
    SERVICE_NAME: str = "analytics-service"
    SERVICE_VERSION: str = "0.0.1"
    PORT: int = 8001


class DataServiceSettings(BaseServiceSettings):
    """Settings for data ingestion service."""
    
    SERVICE_NAME: str = "data-ingestion-service"
    SERVICE_VERSION: str = "0.0.1"
    PORT: int = 8002


class AuthServiceSettings(BaseServiceSettings):
    """Settings for authentication service."""
    
    SERVICE_NAME: str = "auth-service"
    SERVICE_VERSION: str = "0.0.1"
    PORT: int = 8003
    
    # External API Configuration
    BASE_URL: str = "https://devenv-mturmyvlly.extremeb2b.com"