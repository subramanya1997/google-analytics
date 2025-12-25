"""
Data Service Database Module

This module contains the database access layer for the Data Ingestion Service.
It provides abstractions for database operations using SQLAlchemy and PostgreSQL
functions for efficient data querying and manipulation.

Module Structure:
    - sqlalchemy_repository: Repository pattern implementation for database operations

The database layer handles:
    - Ingestion job CRUD operations
    - Data availability queries
    - Job history retrieval with pagination
    - Multi-tenant data isolation

All database operations use async SQLAlchemy sessions and leverage PostgreSQL
functions for optimized query performance.

See Also:
    - services.data_service.database.sqlalchemy_repository: Repository implementation
    - common.database: Shared database utilities and session management
"""
