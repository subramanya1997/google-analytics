"""
Data Service Database Module

This module contains the database access layer for the Data Service.
It provides abstractions for database operations using SQLAlchemy and PostgreSQL
functions for efficient data querying and manipulation.

Module Structure:
    - base: Shared utilities (ensure_uuid_string, EVENT_TABLES)
    - ingestion_repository: Repository for data ingestion operations
    - email_repository: Repository for email-related operations

The database layer handles:
    - Ingestion job CRUD operations
    - Data availability queries
    - Job history retrieval with pagination
    - Email configuration management
    - Branch email mapping CRUD
    - Email job tracking
    - Email send history
    - Multi-tenant data isolation

All database operations use async SQLAlchemy sessions and leverage PostgreSQL
functions for optimized query performance.

Example:
    ```python
    from services.data_service.database import IngestionRepository, EmailRepository

    # Ingestion operations
    ingestion_repo = IngestionRepository()
    job = await ingestion_repo.create_processing_job(job_data)

    # Email operations
    email_repo = EmailRepository()
    config = await email_repo.get_email_config("tenant-uuid")
    ```

See Also:
    - services.data_service.database.ingestion_repository: Ingestion operations
    - services.data_service.database.email_repository: Email operations
    - services.data_service.database.base: Shared utilities
    - common.database: Shared database utilities and session management
"""

from .base import EVENT_TABLES, ensure_uuid_string
from .email_repository import EmailRepository
from .ingestion_repository import IngestionRepository

__all__ = [
    "EVENT_TABLES",
    "EmailRepository",
    "IngestionRepository",
    "ensure_uuid_string",
]
