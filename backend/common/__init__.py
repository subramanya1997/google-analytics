"""
Common utilities and shared code for Google Analytics Intelligence System backend services.

This package provides shared functionality across all backend services including:
- Configuration management with environment-specific settings
- Database session management and connection pooling
- SQLAlchemy ORM models for multi-tenant analytics data
- FastAPI application factory with standardized middleware
- Centralized logging configuration
- Tenant configuration management

The common package ensures consistency across services while providing:
- Multi-tenant data isolation and configuration
- Robust database connection management
- Standardized error handling and logging
- Environment-aware configuration (DEV/PROD)
- Comprehensive analytics event tracking

Main Modules:
- config: Service configuration management
- database: SQLAlchemy session management and utilities  
- fastapi: Application factory and middleware
- logging: Centralized logging setup
- models: ORM models for tenants, users, locations, and events

"""

__version__ = "0.1.0"
