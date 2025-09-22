"""
Centralized configuration management for all backend services.

This module provides Pydantic-based configuration classes that handle environment
variable loading and validation for all backend services in the Google Analytics
Intelligence System. Each service extends the base configuration with service-specific
settings while maintaining consistent defaults and validation patterns.

The configuration system supports:
- Environment variable loading with .env file support
- Type validation and conversion
- Service-specific configuration overrides
- CORS origin parsing and validation
- Database connection pooling configuration
- API pagination settings

Example:
    ```python
    from common.config import get_settings
    
    settings = get_settings("analytics-service")
    print(f"Service running on port: {settings.PORT}")
    ```
"""
import os
from typing import List, Any
from pydantic import validator
from pydantic_settings import BaseSettings


class BaseServiceSettings(BaseSettings):
    """
    Base configuration settings class for all backend services.
    
    Provides common configuration options that are shared across all services
    including database settings, API configuration, CORS settings, and pagination
    defaults. Service-specific settings classes should inherit from this base class.
    
    Attributes:
        SERVICE_NAME: Name identifier for the service (used in logging and monitoring)
        SERVICE_VERSION: Version string for the service
        PORT: Port number the service will bind to
        ENVIRONMENT: Environment identifier ("DEV" or "PROD")
        DEBUG: Enable debug mode for additional logging and error details
        LOG_LEVEL: Logging level for the service
        API_V1_STR: Base path for API v1 endpoints
        CORS_ORIGINS: Comma-separated list of allowed CORS origins
        DATABASE_POOL_SIZE: Maximum number of database connections in the pool
        DATABASE_MAX_OVERFLOW: Maximum overflow connections beyond pool_size
        DEFAULT_PAGE_SIZE: Default number of items per page for paginated responses
        MAX_PAGE_SIZE: Maximum allowed page size to prevent resource exhaustion
        
    Configuration:
        Loads from .env file and environment variables with case-sensitive matching.
        Extra fields are ignored to prevent configuration pollution.
    """
    
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
        """
        Parse and validate CORS origins from environment variable or list.
        
        Converts comma-separated string of origins into a list, stripping whitespace
        and filtering empty strings. Also handles cases where the value is already
        a list or None.
        
        Args:
            v: CORS origins value from environment (string, list, or None)
            
        Returns:
            List of valid CORS origin strings
            
        Example:
            "http://localhost:3000,https://app.example.com" -> 
            ["http://localhost:3000", "https://app.example.com"]
        """
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
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"
    
    # Note: PostgreSQL configuration is now retrieved dynamically from the database
    # via the tenant configuration system. See common.database.tenant_config module.


class AnalyticsServiceSettings(BaseServiceSettings):
    """
    Configuration settings for the Analytics Service.
    
    Handles analytics data processing, dashboard data generation, and reporting
    functionality. Runs on port 8001 by default and processes analytical queries
    from the frontend dashboard.
    
    Inherits all base configuration options and overrides service-specific defaults.
    """
    
    SERVICE_NAME: str = "analytics-service"
    SERVICE_VERSION: str = "0.0.1"
    PORT: int = 8001


class DataServiceSettings(BaseServiceSettings):
    """
    Configuration settings for the Data Ingestion Service.
    
    Handles ingestion of data from BigQuery, SFTP sources, and other external
    data sources. Runs on port 8002 by default and manages ETL processes for
    loading analytics data into the PostgreSQL database.
    
    Inherits all base configuration options and overrides service-specific defaults.
    """
    
    SERVICE_NAME: str = "data-ingestion-service"
    SERVICE_VERSION: str = "0.0.1"
    PORT: int = 8002


class AuthServiceSettings(BaseServiceSettings):
    """
    Configuration settings for the Authentication Service.
    
    Handles user authentication, authorization, and session management.
    Runs on port 8003 by default and integrates with external authentication
    systems for user verification and access control.
    
    Attributes:
        BASE_URL: Base URL for external API integrations and callbacks
        
    Inherits all base configuration options and overrides service-specific defaults.
    """
    
    SERVICE_NAME: str = "auth-service"
    SERVICE_VERSION: str = "0.0.1"
    PORT: int = 8003
    
    # External API Configuration
    BASE_URL: str = "https://devenv-mturmyvlly.extremeb2b.com"