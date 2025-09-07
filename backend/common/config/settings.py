"""
Centralized configuration management for all backend services.
"""
import json
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import validator
from pydantic_settings import BaseSettings


class BaseServiceSettings(BaseSettings):
    """Base settings class for all services."""
    
    # Service Information (defaults)
    SERVICE_NAME: str = "base-service"
    SERVICE_VERSION: str = "0.1.0"
    PORT: int = 8000
    
    # Global Configuration
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    HOST: str = "0.0.0.0"
    
    # CORS Configuration
    CORS_ORIGINS: Any = ""
    
    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        elif isinstance(v, list):
            return v
        return []
    
    # Configuration Files Directory
    CONFIG_DIR: str = "config"
    
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
    SERVICE_VERSION: str = "0.1.0"
    PORT: int = 8001


class DataServiceSettings(BaseServiceSettings):
    """Settings for data ingestion service."""
    
    SERVICE_NAME: str = "data-ingestion-service"
    SERVICE_VERSION: str = "0.1.0"
    PORT: int = 8002
    
    # Configuration Files
    BIGQUERY_CONFIG_FILE: str = "config/bigquery.json"
    SFTP_CONFIG_FILE: str = "config/sftp.json"
    
    # BigQuery Configuration
    GOOGLE_CLOUD_PROJECT_ID: str = "learned-maker-366218"
    BIGQUERY_DATASET_ID: str = "analytics_349447920"
    
    # SFTP Configuration (optional defaults)
    SFTP_HOST: Optional[str] = None
    SFTP_PORT: int = 22
    SFTP_USERNAME: Optional[str] = None
    SFTP_PASSWORD: Optional[str] = None
    SFTP_REMOTE_PATH: str = "/data"
    
    # Job Processing Configuration
    MAX_CONCURRENT_JOBS: int = 5
    JOB_TIMEOUT_MINUTES: int = 60
    CLEANUP_COMPLETED_JOBS_AFTER_DAYS: int = 30
    
    def get_bigquery_config(self) -> Dict[str, Any]:
        """Load BigQuery configuration from JSON file."""
        config_path = Path(self.BIGQUERY_CONFIG_FILE)
        if not config_path.exists():
            raise FileNotFoundError(f"BigQuery config file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def get_sftp_config(self) -> Dict[str, Any]:
        """Get SFTP configuration from JSON file."""
        config_path = Path(self.SFTP_CONFIG_FILE)
        
        if not config_path.exists():
            raise FileNotFoundError(f"SFTP config file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            return json.load(f)


class AuthServiceSettings(BaseServiceSettings):
    """Settings for authentication service."""
    
    SERVICE_NAME: str = "auth-service"
    SERVICE_VERSION: str = "0.1.0"
    PORT: int = 8003
    
    # External API Configuration
    BASE_URL: str = "https://devenv-mturmyvlly.extremeb2b.com"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Service setting instances - will be created when imported
_analytics_settings: Optional[AnalyticsServiceSettings] = None
_data_settings: Optional[DataServiceSettings] = None
_auth_settings: Optional[AuthServiceSettings] = None


def get_settings(service_name: str = None) -> BaseServiceSettings:
    """Get settings instance for the specified service."""
    global _analytics_settings, _data_settings, _auth_settings
    
    # Auto-detect service from environment variable if not provided
    if not service_name:
        service_name = os.getenv("SERVICE_NAME", "")
    
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