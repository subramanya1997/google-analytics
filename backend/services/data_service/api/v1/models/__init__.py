"""
Data Service API v1 Models Module

This module exports all Pydantic models used for request/response validation
in the v1 API. Models are organized by functional area and provide comprehensive
validation, serialization, and API documentation generation.

Exported Models:
    Ingestion Models:
    - CreateIngestionJobRequest: Request model for creating ingestion jobs
    - IngestionJobResponse: Response model for ingestion job information

    Schedule Models:
    - ScheduleRequest: Request model for schedule configuration

    Email Models:
    - BranchEmailMappingRequest: Request model for creating/updating branch email mappings
    - BranchEmailMappingResponse: Response model for branch email mapping data
    - SendReportsRequest: Request model for triggering email report distribution
    - EmailJobResponse: Response model for email job status

These models ensure:
    - Type safety across the API layer
    - Automatic request validation
    - Consistent response serialization
    - OpenAPI/Swagger documentation generation

See Also:
    - services.data_service.api.v1.models.ingestion: Ingestion job models
    - services.data_service.api.v1.models.schedule: Schedule configuration models
    - services.data_service.api.v1.models.email: Email management models
"""

from .email import (
    BranchEmailMappingRequest,
    BranchEmailMappingResponse,
    EmailJobResponse,
    SendReportsRequest,
)
from .ingestion import CreateIngestionJobRequest, IngestionJobResponse
from .schedule import ScheduleRequest

__all__ = [
    "CreateIngestionJobRequest",
    "IngestionJobResponse",
    "ScheduleRequest",
    "BranchEmailMappingRequest",
    "BranchEmailMappingResponse",
    "SendReportsRequest",
    "EmailJobResponse",
]
