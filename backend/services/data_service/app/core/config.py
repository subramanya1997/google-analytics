import json
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from pydantic import AnyHttpUrl, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Service Configuration
    SERVICE_NAME: str = "data-ingestion-service"
    SERVICE_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # API Configuration
    API_V1_STR: str = "/api/v1"
    HOST: str = "0.0.0.0"
    PORT: int = 8001
    
    # Configuration Files
    BIGQUERY_CONFIG_FILE: str = "config/bigquery.json"
    SFTP_CONFIG_FILE: str = "config/sftp.json"
    POSTGRES_CONFIG_FILE: str = "config/postgres.json"
    
    # Database Configuration
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 0
    
    # CORS Configuration
    CORS_ORIGINS: List[AnyHttpUrl] = []
    
    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str] | str:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
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
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
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
    
    def get_postgres_config(self) -> Dict[str, Any]:
        """Get Postgres configuration from JSON file."""
        config_path = Path(self.POSTGRES_CONFIG_FILE)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Postgres config file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            return json.load(f)


settings = Settings()
