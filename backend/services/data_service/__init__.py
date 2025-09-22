"""
Data Ingestion Service Package.

This package provides the complete data ingestion service for the Google Analytics
Intelligence System. It handles multi-source analytics data processing including
Google Analytics 4 events from BigQuery and user/location data from SFTP sources
with comprehensive job management, real-time status tracking, and multi-tenant security.

The package is structured as a FastAPI microservice with the following components:

Package Structure:
- main.py: FastAPI application entry point with reverse proxy configuration
- api/: REST API endpoints and routing
  - dependencies.py: Multi-tenant security and shared dependencies
  - v1/: API version 1 implementation
    - api.py: Main API router aggregating all endpoints
    - endpoints/: Individual endpoint implementations
      - ingestion.py: Data ingestion workflow endpoints
    - models/: Pydantic request/response models with validation
- clients/: External service integration
  - bigquery_client.py: Google Analytics 4 data extraction from BigQuery
  - sftp_client.py: Azure SFTP file processing for user/location data
  - tenant_client_factory.py: Multi-tenant client creation and management
- database/: Data persistence layer
  - sqlalchemy_repository.py: Comprehensive database operations with Repository pattern
- services/: Business logic layer
  - ingestion_service.py: Multi-source data processing orchestration

Key Features:
- **Multi-Source Integration**: BigQuery (GA4 events) + SFTP (user/location data)
- **Asynchronous Processing**: Background job execution with real-time status tracking
- **Multi-Tenant Architecture**: Isolated data processing and configuration per tenant
- **Comprehensive Event Coverage**: 6 GA4 event types with full attribution
- **Performance Optimization**: Batch processing, thread pools, connection pooling
- **Data Quality Management**: Validation, transformation, and error handling
- **Job Management**: Complete lifecycle tracking with progress monitoring

Service Architecture:
The data ingestion service follows a layered architecture:
1. **API Layer**: FastAPI endpoints with multi-tenant security and validation
2. **Business Logic**: Data processing orchestration and job management
3. **Client Layer**: External service integrations (BigQuery, SFTP)
4. **Database Layer**: Repository pattern with async operations and batch processing

Production Deployment:
- Reverse proxy support with /data/ path prefix
- Environment-aware configuration management
- Comprehensive logging and monitoring
- Health checks and service discovery endpoints
- Docker containerization support

Multi-Tenant Security:
- X-Tenant-Id header enforcement for all operations
- Tenant-specific configuration isolation (BigQuery projects, SFTP credentials)
- Data segregation at database level with UUID-based tenant identification
- Secure credential management per tenant

Data Pipeline:
1. **Job Creation**: API receives ingestion request with date range and data types
2. **Background Execution**: Job queued for async processing with status tracking
3. **Multi-Source Extraction**: Parallel processing of BigQuery events and SFTP files
4. **Data Transformation**: Normalization, validation, and type conversion
5. **Database Storage**: Batch operations with upsert logic and transaction management
6. **Status Reporting**: Real-time progress updates and completion notification

Environment Configuration:
- POSTGRES_*: Database connection parameters for analytics storage
- X-Tenant-Id: Required header for all API operations
- BigQuery service account configurations per tenant
- SFTP connection parameters per tenant
- Various timeout and pooling configurations

The service provides endpoints at:
- POST /api/v1/ingest: Create and start data ingestion jobs
- GET /api/v1/data-availability: Query available data ranges and statistics
- GET /api/v1/jobs: List ingestion job history with pagination
- GET /api/v1/jobs/{job_id}: Get specific job details and status
- GET /health: Service health check
"""

from services.data_service.main import app

__all__ = ["app"]
