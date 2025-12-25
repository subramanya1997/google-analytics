"""
Data Service API v1 Endpoints Module

This module contains all HTTP endpoint handlers for the v1 API. Endpoints are
organized by functional area (ingestion, schedule) and handle HTTP request/response
cycles, validation, error handling, and business logic orchestration.

Endpoint Responsibilities:
    - Request validation using Pydantic models
    - Business logic orchestration
    - Database operations via repository pattern
    - Error handling and API error formatting
    - Response serialization

Module Structure:
    - ingestion: Data ingestion job management endpoints
    - schedule: Scheduled ingestion configuration endpoints

Each endpoint module defines its own FastAPI router with route handlers that
are aggregated in the main API router.

See Also:
    - services.data_service.api.v1.endpoints.ingestion: Ingestion endpoints
    - services.data_service.api.v1.endpoints.schedule: Schedule endpoints
"""
