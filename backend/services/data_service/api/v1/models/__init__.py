"""
Data Service API v1 Models Module

This module exports all Pydantic models used for request/response validation
in the v1 API. Models are organized by functional area and provide comprehensive
validation, serialization, and API documentation generation.

Exported Models:
    - CreateIngestionJobRequest: Request model for creating ingestion jobs
    - IngestionJobResponse: Response model for ingestion job information
    - ScheduleRequest: Request model for schedule configuration

These models ensure:
    - Type safety across the API layer
    - Automatic request validation
    - Consistent response serialization
    - OpenAPI/Swagger documentation generation

See Also:
    - services.data_service.api.v1.models.ingestion: Ingestion job models
    - services.data_service.api.v1.models.schedule: Schedule configuration models
"""

from .ingestion import CreateIngestionJobRequest, IngestionJobResponse
from .schedule import ScheduleRequest

__all__ = ["CreateIngestionJobRequest", "IngestionJobResponse", "ScheduleRequest"]
