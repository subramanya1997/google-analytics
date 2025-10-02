"""
Data Ingestion Service API Models Package.

This package contains all Pydantic models used for API request and response
serialization in the data ingestion service. The models provide comprehensive
type safety, validation, and documentation for the complete data pipeline API.

Available Models:
- CreateIngestionJobRequest: Job creation and configuration
- IngestionJobResponse: Job status and information responses

Model Features:
- Comprehensive validation with business logic enforcement
- ISO date/datetime serialization for API consistency
- OpenAPI schema generation for interactive documentation
- Multi-tenant job tracking and status management
- Type safety for all API operations

The models support the complete data ingestion workflow from job creation
through status monitoring and completion tracking.
"""

from .ingestion import CreateIngestionJobRequest, IngestionJobResponse

__all__ = ["CreateIngestionJobRequest", "IngestionJobResponse"]
