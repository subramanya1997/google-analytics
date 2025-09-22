"""
Data Ingestion Service - FastAPI Application Entry Point.

This module provides the main FastAPI application for the Data Ingestion Service,
which handles analytics data ingestion, processing, and storage for the Google
Analytics Intelligence System. The service manages the complete data pipeline
from multiple sources to the analytics database.

The Data Ingestion Service is responsible for:
- Google Analytics 4 event data extraction from BigQuery
- User and location data ingestion from SFTP sources
- Multi-tenant data processing and storage
- Background job management and status tracking
- Data availability monitoring and reporting
- Comprehensive analytics data pipeline orchestration

Key Features:
- **Multi-Source Data Ingestion**: BigQuery (GA4 events) + SFTP (user/location data)
- **Asynchronous Processing**: Background job execution with real-time status tracking
- **Multi-Tenant Architecture**: Isolated data processing per tenant
- **Comprehensive Event Coverage**: 6 GA4 event types (purchase, add_to_cart, page_view, etc.)
- **Data Quality Management**: Validation, transformation, and error handling
- **Performance Optimization**: Batch processing, connection pooling, thread pools

Data Sources and Types:
1. **BigQuery (Google Analytics 4)**:
   - Purchase events: E-commerce transaction data
   - Add to cart events: Shopping behavior tracking
   - Page view events: Website navigation analytics
   - Search events: Search interaction and failure analysis
   - View item events: Product engagement tracking

2. **SFTP (Azure Blob Storage)**:
   - User data: Customer profiles and demographics
   - Location data: Warehouse and branch information

Architecture Components:
1. **API Layer**: REST endpoints for job management and data queries
2. **Service Layer**: Business logic for data processing orchestration
3. **Client Layer**: External service integrations (BigQuery, SFTP)
4. **Database Layer**: Multi-tenant data storage and retrieval
5. **Background Processing**: Asynchronous job execution system

API Endpoints:
- POST /api/v1/ingest: Create and start data ingestion jobs
- GET /api/v1/data-availability: Query available data date ranges
- GET /api/v1/jobs: List ingestion job history with pagination
- GET /api/v1/jobs/{job_id}: Get specific job details and status

Production Configuration:
- Reverse proxy path: /data/ (configured for Nginx deployment)
- Service name: data-ingestion-service
- Default port: 8001 (configurable via environment)
- Health check: /health
- API documentation: /data/docs

Multi-Tenant Security:
- X-Tenant-Id header validation for all operations
- Tenant-specific configuration isolation
- Data segregation at database level
- Secure credential management per tenant

Background Processing:
- Thread pool executor for heavy synchronous operations
- Async/await patterns for I/O-bound operations
- Comprehensive error handling with job failure recovery
- Real-time progress tracking and status updates

Performance Optimizations:
- Batch database operations (1000 records per batch)
- Connection pooling for database and external services
- Parallel processing of multiple data types
- Efficient memory management for large datasets

Environment Variables:
- POSTGRES_*: Database connection parameters for analytics storage
- X-Tenant-Id: Required header for all API operations
- Various timeout and pooling configurations

Data Flow Architecture:
1. **Job Creation**: API receives ingestion request with date range and data types
2. **Background Execution**: Job queued for async processing
3. **Data Extraction**: Parallel fetching from BigQuery and SFTP sources
4. **Data Transformation**: Normalization, validation, and type conversion
5. **Database Storage**: Batch insertion with upsert logic for dimensions
6. **Status Reporting**: Real-time job progress and completion tracking

Security Considerations:
- Tenant isolation for all data operations
- Secure service account credentials for BigQuery
- SFTP authentication with timeout management
- Input validation and SQL injection prevention
- Comprehensive audit logging for all operations

Monitoring and Observability:
- Structured logging with correlation IDs
- Job execution metrics and timing
- Error rate tracking and alerting
- Data quality metrics and validation reports
"""

from common.fastapi import create_fastapi_app
from services.data_service.api.v1.api import api_router

# Create FastAPI app with reverse proxy configuration
app = create_fastapi_app(
    service_name="data-ingestion-service",
    description="Data ingestion service for Google Analytics intelligence system",
    api_router=api_router,
    root_path="/data",  # Nginx serves this at /data/
)
