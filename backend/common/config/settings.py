"""
Centralized configuration management for all backend services.

This module defines Pydantic Settings classes for managing configuration across
all microservices. It provides a hierarchical settings system with base settings
shared by all services and service-specific overrides.

Configuration Loading:
    Settings are loaded in the following priority order (highest to lowest):
    1. Environment variables
    2. .env file in the project root
    3. Default values defined in the classes

Validation:
    All settings are validated using Pydantic validators to ensure:
    - Type correctness
    - Value constraints (e.g., positive integers, valid page sizes)
    - Format requirements (e.g., CORS origins parsing)

Service Settings Hierarchy:
    BaseServiceSettings (base class)
    ├── AnalyticsServiceSettings
    ├── DataServiceSettings
    └── AuthServiceSettings

Example:
    ```python
    from common.config.settings import AnalyticsServiceSettings
    
    settings = AnalyticsServiceSettings()
    print(settings.SERVICE_NAME)  # "analytics-service"
    print(settings.PORT)  # 8001
    print(settings.DATABASE_POOL_SIZE)  # 10 (from base)
    ```

Environment Variables:
    All settings can be overridden via environment variables. For example:
    - SERVICE_NAME=analytics-service
    - PORT=8001
    - LOG_LEVEL=DEBUG
    - CORS_ORIGINS=http://localhost:3000,https://example.com
"""

from typing import Any

from pydantic import ValidationInfo, field_validator
from pydantic_settings import BaseSettings

# Constants
MAX_PAGE_SIZE_LIMIT = 10000  # Maximum allowed page size for pagination
MIN_REQUIRED_ARGS = 2  # Minimum required arguments for certain operations


class BaseServiceSettings(BaseSettings):
    """
    Base settings class providing common configuration for all services.

    This class defines all shared configuration options used across microservices,
    including service metadata, API configuration, database settings, and logging.
    Service-specific settings classes inherit from this base class and override
    or extend these settings as needed.

    Attributes:
        SERVICE_NAME (str): Name identifier for the service. Default: "base-service"
        SERVICE_VERSION (str): Version string for the service. Default: "0.0.1"
        PORT (int): Port number the service listens on. Default: 8000
        
        ENVIRONMENT (str): Deployment environment. Values: "DEV" or "PROD". Default: "DEV"
        DEBUG (bool): Enable debug mode. Default: False
        LOG_LEVEL (str): Logging level. Values: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL". Default: "INFO"
        
        API_V1_STR (str): API version prefix for routes. Default: "/api/v1"
        CORS_ORIGINS (list[str]): List of allowed CORS origins. Can be set via comma-separated string or list.
        SCHEDULER_API_URL (str): Base URL for the Cronicle scheduler API.
        
        DATABASE_POOL_SIZE (int): Number of connections to maintain in the pool. Default: 10
        DATABASE_MAX_OVERFLOW (int): Maximum overflow connections beyond pool_size. Default: 5
        
        DEFAULT_PAGE_SIZE (int): Default number of items per page for pagination. Default: 50
        MAX_PAGE_SIZE (int): Maximum allowed page size for pagination. Default: 1000

    Configuration:
        Settings are loaded from:
        - Environment variables (case-sensitive, uppercase)
        - .env file in the project root
        - Default values defined here

    Example:
        ```python
        settings = BaseServiceSettings()
        
        # Access settings
        print(settings.SERVICE_NAME)
        print(settings.PORT)
        print(settings.LOG_LEVEL)
        
        # Override via environment variable
        # export PORT=9000
        settings = BaseServiceSettings()
        print(settings.PORT)  # 9000
        ```

    Note:
        - PostgreSQL database configuration is retrieved dynamically from the database
          via the tenant configuration system (see common.database.tenant_config)
        - CORS_ORIGINS can be set as a comma-separated string or a list
        - All integer fields are validated to be positive
        - Page sizes are validated to be between 1 and MAX_PAGE_SIZE_LIMIT
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
    SCHEDULER_API_URL: str = "https://dev-fusionx.extremeb2b.com/scheduler/"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> list[str]:
        """
        Assemble CORS origins from string or list format.

        This validator normalizes CORS origins input, accepting either:
        - A comma-separated string: "http://localhost:3000,https://example.com"
        - A list of strings: ["http://localhost:3000", "https://example.com"]
        - An empty string or empty list: returns []

        Args:
            v: Input value that can be a string, list, or other type.

        Returns:
            List of CORS origin strings with whitespace stripped. Empty list if
            input is empty or invalid.

        Example:
            ```python
            # Comma-separated string
            origins = "http://localhost:3000, https://example.com"
            # Returns: ["http://localhost:3000", "https://example.com"]
            
            # List
            origins = ["http://localhost:3000", "https://example.com"]
            # Returns: ["http://localhost:3000", "https://example.com"]
            
            # Empty
            origins = ""
            # Returns: []
            ```

        Note:
            - Whitespace around origins is automatically stripped
            - Empty strings in comma-separated input are filtered out
            - Invalid types return an empty list
        """
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        if isinstance(v, list):
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
    def validate_positive_int(cls, v: Any, info: ValidationInfo) -> int | None:
        """
        Validate that database pool configuration fields are positive integers.

        This validator ensures that database connection pool settings are valid
        positive integers. It handles type conversion from strings (common when
        loading from environment variables) and validates the value range.

        Args:
            v: Input value to validate. Can be int, str, or None.
            info: Pydantic ValidationInfo object containing field metadata.

        Returns:
            Validated integer value, or None if input is None.

        Raises:
            ValueError: If the value cannot be converted to an integer or is negative.

        Example:
            ```python
            # Valid inputs
            validate_positive_int(10, info)  # Returns: 10
            validate_positive_int("20", info)  # Returns: 20
            
            # Invalid inputs
            validate_positive_int(-5, info)  # Raises ValueError
            validate_positive_int("abc", info)  # Raises ValueError
            ```

        Note:
            - Accepts string input and converts to int (useful for env vars)
            - None values are allowed and returned as-is
            - Zero is considered valid (though not recommended for pool sizes)
        """
        if v is None:
            return None
        try:
            int_val = int(v)
            if int_val < 0:
                msg = f"{info.field_name} must be a positive integer"
                raise ValueError(msg)
            return int_val
        except (ValueError, TypeError) as e:
            msg = f"{info.field_name} must be a valid positive integer, got: {v}"
            raise ValueError(
                msg
            ) from e

    @field_validator("DEFAULT_PAGE_SIZE", "MAX_PAGE_SIZE")
    @classmethod
    def validate_page_sizes(cls, v: int, info: ValidationInfo) -> int:
        """
        Validate pagination page size configuration values.

        This validator ensures that pagination settings are within acceptable bounds:
        - Must be at least 1 (cannot have zero or negative page sizes)
        - Cannot exceed MAX_PAGE_SIZE_LIMIT (10000) to prevent performance issues

        Args:
            v: Integer value to validate.
            info: Pydantic ValidationInfo object containing field metadata.

        Returns:
            Validated integer value if within acceptable range.

        Raises:
            ValueError: If the value is less than 1 or exceeds MAX_PAGE_SIZE_LIMIT.

        Example:
            ```python
            # Valid values
            validate_page_sizes(50, info)  # Returns: 50
            validate_page_sizes(1000, info)  # Returns: 1000
            
            # Invalid values
            validate_page_sizes(0, info)  # Raises ValueError
            validate_page_sizes(15000, info)  # Raises ValueError
            ```

        Note:
            - DEFAULT_PAGE_SIZE should be reasonable for typical use cases (50-100)
            - MAX_PAGE_SIZE should balance usability with performance (1000-5000)
            - Values exceeding MAX_PAGE_SIZE_LIMIT are rejected to prevent
              database performance degradation
        """
        if v < 1:
            msg = f"{info.field_name} must be at least 1"
            raise ValueError(msg)
        if v > MAX_PAGE_SIZE_LIMIT:
            msg = f"{info.field_name} cannot exceed {MAX_PAGE_SIZE_LIMIT}"
            raise ValueError(msg)
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

    # Note: PostgreSQL configuration is now retrieved dynamically from the database
    # via the tenant configuration system. See common.database.tenant_config module.


class AnalyticsServiceSettings(BaseServiceSettings):
    """
    Settings configuration for the analytics service.

    This class extends BaseServiceSettings with analytics-service-specific
    configuration options, including scheduler settings and Azure Storage integration.

    Inherited Attributes:
        All attributes from BaseServiceSettings are available with these overrides:
        - SERVICE_NAME: "analytics-service"
        - SERVICE_VERSION: "0.0.1"
        - PORT: 8001

    Additional Attributes:
        EMAIL_NOTIFICATION_CRON (str): Cron expression for scheduled email notifications.
            Default: "0 8 * * *" (Daily at 8:00 AM UTC).
        ANALYTICS_SERVICE_URL (str): Public URL of the analytics service endpoint.
            Used for generating callback URLs in scheduled jobs.
        AZURE_STORAGE_CONNECTION_STRING (str): Azure Storage account connection string
            for queue operations. Should be set via environment variable for security.

    Example:
        ```python
        from common.config.settings import AnalyticsServiceSettings
        
        settings = AnalyticsServiceSettings()
        print(settings.SERVICE_NAME)  # "analytics-service"
        print(settings.PORT)  # 8001
        print(settings.EMAIL_NOTIFICATION_CRON)  # "0 8 * * *"
        ```

    Note:
        - Azure Storage connection string should be stored securely (env vars, secrets manager)
        - Cron expressions use UTC timezone
        - Service URL should match the deployed service endpoint
    """

    SERVICE_NAME: str = "analytics-service"
    SERVICE_VERSION: str = "0.0.1"
    PORT: int = 8001

    # Scheduler Configuration
    EMAIL_NOTIFICATION_CRON: str = "0 8 * * *"  # Daily at 8 AM
    ANALYTICS_SERVICE_URL: str = (
        "https://devenv-ai-tech-assistant.extremeb2b.com/analytics"
    )

    # Azure Storage Queue Configuration
    AZURE_STORAGE_CONNECTION_STRING: str = ""


class DataServiceSettings(BaseServiceSettings):
    """
    Settings configuration for the data ingestion service.

    This class extends BaseServiceSettings with data-ingestion-service-specific
    configuration options, including scheduler settings for automated data ingestion
    and Azure Storage integration.

    Inherited Attributes:
        All attributes from BaseServiceSettings are available with these overrides:
        - SERVICE_NAME: "data-ingestion-service"
        - SERVICE_VERSION: "0.0.1"
        - PORT: 8002

    Additional Attributes:
        DATA_INGESTION_CRON (str): Cron expression for scheduled data ingestion jobs.
            Default: "0 2 * * *" (Daily at 2:00 AM UTC). This time is chosen to
            minimize impact on production traffic.
        DATA_SERVICE_URL (str): Public URL of the data ingestion service endpoint.
            Used for generating callback URLs in scheduled jobs.
        AZURE_STORAGE_CONNECTION_STRING (str): Azure Storage account connection string
            for queue operations. Should be set via environment variable for security.

    Example:
        ```python
        from common.config.settings import DataServiceSettings
        
        settings = DataServiceSettings()
        print(settings.SERVICE_NAME)  # "data-ingestion-service"
        print(settings.PORT)  # 8002
        print(settings.DATA_INGESTION_CRON)  # "0 2 * * *"
        ```

    Note:
        - Data ingestion typically runs during off-peak hours (2 AM UTC)
        - Azure Storage connection string should be stored securely
        - Cron expressions use UTC timezone
        - Service URL should match the deployed service endpoint
    """

    SERVICE_NAME: str = "data-ingestion-service"
    SERVICE_VERSION: str = "0.0.1"
    PORT: int = 8002

    # Scheduler Configuration
    DATA_INGESTION_CRON: str = "0 2 * * *"  # Daily at 2 AM
    DATA_SERVICE_URL: str = "https://devenv-ai-tech-assistant.extremeb2b.com/data"

    # Azure Storage Queue Configuration
    AZURE_STORAGE_CONNECTION_STRING: str = ""


class AuthServiceSettings(BaseServiceSettings):
    """
    Settings configuration for the authentication service.

    This class extends BaseServiceSettings with auth-service-specific configuration
    options, including external API endpoints for authentication operations.

    Inherited Attributes:
        All attributes from BaseServiceSettings are available with these overrides:
        - SERVICE_NAME: "auth-service"
        - SERVICE_VERSION: "0.0.1"
        - PORT: 8003

    Additional Attributes:
        BASE_URL (str): Base URL of the external authentication API endpoint.
            This is used for making authentication and authorization requests to
            the external identity provider or authentication service.

    Example:
        ```python
        from common.config.settings import AuthServiceSettings
        
        settings = AuthServiceSettings()
        print(settings.SERVICE_NAME)  # "auth-service"
        print(settings.PORT)  # 8003
        print(settings.BASE_URL)  # "https://devenv-mturmyvlly.extremeb2b.com"
        ```

    Note:
        - BASE_URL should point to the production authentication service in production
        - This URL is used for OAuth callbacks and token validation
        - Should be configured via environment variable for different environments
    """

    SERVICE_NAME: str = "auth-service"
    SERVICE_VERSION: str = "0.0.1"
    PORT: int = 8003

    # External API Configuration
    BASE_URL: str = "https://devenv-mturmyvlly.extremeb2b.com"
