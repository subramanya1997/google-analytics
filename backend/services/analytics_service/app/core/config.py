import json
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Service Configuration
    SERVICE_NAME: str = "analytics-service"
    SERVICE_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8002
    
    # Configuration Files
    POSTGRES_CONFIG_FILE: str = "config/postgres.json"
    
    # Database Configuration
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 0
    
    # CORS Configuration - Use string instead of List[AnyHttpUrl] to avoid parsing issues
    CORS_ORIGINS: Any = "" 
    
    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        elif isinstance(v, list):
            return v
        return []
    
    # Analytics Configuration
    DEFAULT_TENANT_ID: str = "default"
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 1000
    CACHE_TTL_SECONDS: int = 300  # 5 minutes
    
    # Security
    SECRET_KEY: str = "default-secret-key-for-development"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # External Service URLs
    AUTH_SERVICE_URL: str = "http://localhost:8000"
    DATA_SERVICE_URL: str = "http://localhost:8001"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from environment
    
    def get_postgres_config(self) -> Dict[str, Any]:
        """Get Postgres configuration from JSON file."""
        config_path = Path(self.POSTGRES_CONFIG_FILE)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Postgres config file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            return json.load(f)


settings = Settings()
