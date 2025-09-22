"""
Data Ingestion Service API Router - Version 1.

This module defines the main API router for the Data Ingestion Service v1 API,
aggregating all data ingestion and management endpoints under a unified routing
structure with proper tagging for OpenAPI documentation.

The API router organizes all data ingestion endpoints including job management,
data availability queries, and status monitoring under a coherent structure
that supports the complete data pipeline workflow.

Router Structure:
- Base path: /api/v1/ (configured in main app)
- Ingestion endpoints: /api/v1/* (data processing and job management)
- Tags: ["Ingestion"] (for OpenAPI grouping and documentation)

Endpoint Categories:
- **Job Management**: Create, monitor, and track data ingestion jobs
- **Data Availability**: Query available data ranges and statistics
- **Status Monitoring**: Real-time job status and progress tracking
- **Data Quality**: Validation and error reporting

OpenAPI Integration:
All endpoints are automatically included in the OpenAPI schema generation
with proper tagging, categorization, and comprehensive documentation for
easy API discovery and testing through the interactive docs interface.

Multi-Tenant Architecture:
All endpoints enforce tenant isolation through the X-Tenant-Id header
dependency, ensuring secure multi-tenant operations and proper data
segregation across all API operations.

"""

from fastapi import APIRouter

from services.data_service.api.v1.endpoints import ingestion

api_router = APIRouter()

# Include all endpoint routers with proper tagging for OpenAPI documentation
api_router.include_router(ingestion.router, tags=["Ingestion"])
