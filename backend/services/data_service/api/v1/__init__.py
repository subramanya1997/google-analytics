"""
Data Service API v1 Module

This module contains the version 1 implementation of the Data Ingestion Service API.
Versioning allows for future API evolution while maintaining backward compatibility
with existing clients.

The v1 API provides endpoints for:
- Data ingestion job management (create, list, status)
- Data availability queries
- Scheduled ingestion configuration

Module Structure:
    - api: Router aggregation and endpoint registration
    - endpoints: HTTP endpoint handlers
        - ingestion: Job creation and management endpoints
        - schedule: Scheduled ingestion configuration endpoints
    - models: Pydantic request/response schemas
        - ingestion: Job request/response models
        - schedule: Schedule configuration models

API Versioning:
    The API is versioned via URL path (/api/v1/) to support:
    - Multiple API versions running simultaneously
    - Gradual migration of clients to new versions
    - Deprecation of old endpoints without breaking changes

See Also:
    - services.data_service.api.v1.api: Main API router
    - services.data_service.api.v1.endpoints: Endpoint implementations
    - services.data_service.api.v1.models: Request/response models
"""
