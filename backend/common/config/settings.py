"""
Centralized configuration management for all backend services.
"""
import os
from typing import List, Any
from pydantic import field_validator, ValidationInfo
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
    SCHEDULER_API_URL: str = "https://dev-fusionx.extremeb2b.com/scheduler/"
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        elif isinstance(v, list):
            return v
        return []
    
    # Database Configuration
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 5
    
    # API Pagination Configuration
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 1000
    
    @field_validator("DATABASE_POOL_SIZE", "DATABASE_MAX_OVERFLOW", mode="before")
    @classmethod
    def validate_positive_int(cls, v, info: ValidationInfo):
        """Validate that integer fields are positive."""
        if v is None:
            return None
        try:
            int_val = int(v)
            if int_val < 0:
                raise ValueError(f"{info.field_name} must be a positive integer")
            return int_val
        except (ValueError, TypeError) as e:
            raise ValueError(f"{info.field_name} must be a valid positive integer, got: {v}") from e
    
    @field_validator("DEFAULT_PAGE_SIZE", "MAX_PAGE_SIZE")
    @classmethod
    def validate_page_sizes(cls, v, info: ValidationInfo):
        """Validate page size configuration."""
        if v < 1:
            raise ValueError(f"{info.field_name} must be at least 1")
        if v > 10000:
            raise ValueError(f"{info.field_name} cannot exceed 10000")
        return v
    
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
    
    # Scheduler Configuration
    EMAIL_NOTIFICATION_CRON: str = "0 8 * * *"  # Daily at 8 AM
    ANALYTICS_SERVICE_URL: str = "https://devenv-ai-tech-assistant.extremeb2b.com/analytics"
    
    # Azure Storage Queue Configuration
    AZURE_STORAGE_CONNECTION_STRING: str = ""


class DataServiceSettings(BaseServiceSettings):
    """Settings for data ingestion service."""
    
    SERVICE_NAME: str = "data-ingestion-service"
    SERVICE_VERSION: str = "0.0.1"
    PORT: int = 8002
    
    # Scheduler Configuration
    DATA_INGESTION_CRON: str = "0 2 * * *"  # Daily at 2 AM
    DATA_SERVICE_URL: str = "https://devenv-ai-tech-assistant.extremeb2b.com/data"
    
    # Azure Storage Queue Configuration
    AZURE_STORAGE_CONNECTION_STRING: str = ""


class AuthServiceSettings(BaseServiceSettings):
    """Settings for authentication service."""
    
    SERVICE_NAME: str = "auth-service"
    SERVICE_VERSION: str = "0.0.1"
    PORT: int = 8003
    
    # External API Configuration
    BASE_URL: str = "https://devenv-mturmyvlly.extremeb2b.com"