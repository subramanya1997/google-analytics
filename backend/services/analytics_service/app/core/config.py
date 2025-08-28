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
    SUPABASE_CONFIG_FILE: str = "config/supabase.json"
    
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
    
    def get_supabase_config(self) -> Dict[str, Any]:
        """Load Supabase configuration from JSON file."""
        config_path = Path(self.SUPABASE_CONFIG_FILE)
        if not config_path.exists():
            raise FileNotFoundError(f"Supabase config file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def get_database_url(self) -> str:
        """Get database URL from Supabase config."""
        try:
            supabase_config = self.get_supabase_config()
            return supabase_config.get('connection_string', '')
        except FileNotFoundError:
            # Fallback to environment variable if config file doesn't exist
            return os.getenv('DATABASE_URL', '')
    
    def get_supabase_client_config(self) -> Dict[str, Any]:
        """Get Supabase client configuration."""
        try:
            return self.get_supabase_config()
        except FileNotFoundError:
            raise FileNotFoundError("Supabase configuration not found. Please set up config/supabase.json")


settings = Settings()
