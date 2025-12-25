"""
Common utilities and shared code for Google Analytics Intelligence System backend services.

This package provides shared functionality used across all backend microservices in the
Google Analytics Intelligence System. It includes:

Modules:
    - config: Centralized configuration management with environment-based settings
    - database: Database session management, connection pooling, and tenant isolation
    - exceptions: Standardized error handling and API error responses
    - fastapi: FastAPI application factory with common middleware and configuration
    - logging: Centralized logging configuration using loguru
    - models: Shared SQLAlchemy ORM models for events and control tables
    - scheduler_client: Client for interacting with the Cronicle scheduler service

Architecture:
    The common package follows a microservices architecture pattern where each service
    (analytics-service, data-ingestion-service, auth-service) shares core functionality
    through this package. This ensures consistency, reduces code duplication, and
    simplifies maintenance.

Tenant Isolation:
    The system implements SOC2-compliant tenant isolation where each tenant has a
    dedicated PostgreSQL database. The database module provides utilities for
    provisioning, managing, and accessing tenant-specific databases.

Usage:
    Import specific modules as needed:
    
    ```python
    from common.config import get_settings
    from common.database import get_db_session
    from common.logging import setup_logging
    from common.exceptions import create_api_error
    ```

Version:
    Current version: 0.1.0
"""

__version__ = "0.1.0"
