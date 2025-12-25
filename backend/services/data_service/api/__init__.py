"""
Data Service API Module

This module contains all API-related components for the Data Ingestion Service,
including endpoint definitions, request/response models, and shared dependencies.

The API module is organized into versioned submodules (v1) to support future API
evolution while maintaining backward compatibility.

Module Structure:
    - dependencies: Shared FastAPI dependencies (tenant ID extraction, repository injection)
    - v1: Version 1 API implementation
        - endpoints: HTTP endpoint handlers (ingestion, schedule)
        - models: Pydantic request/response models

Key Components:
    - Tenant ID extraction from HTTP headers
    - Repository dependency injection for database access
    - Request validation and response serialization
    - Error handling and API error formatting

See Also:
    - services.data_service.api.dependencies: Shared API dependencies
    - services.data_service.api.v1: Version 1 API implementation
"""
