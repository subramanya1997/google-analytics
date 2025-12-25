"""
Data Service Module - Multi-Source Analytics Data Ingestion Service

This module provides the FastAPI application entrypoint for the Data Ingestion Service,
which handles the extraction, transformation, and loading (ETL) of analytics data from
multiple external sources into the PostgreSQL database.

The Data Service is a critical component of the Google Analytics Intelligence System,
responsible for:
- Extracting Google Analytics 4 (GA4) event data from BigQuery
- Downloading user and location data from SFTP servers
- Managing ingestion job lifecycle and status tracking
- Providing data availability information for analytics dashboards

Architecture:
    The service follows a microservices architecture pattern with:
    - RESTful API endpoints for job management and scheduling
    - Asynchronous background processing via Azure Queue Storage
    - Multi-tenant data isolation and configuration management
    - Comprehensive error handling and logging

Key Features:
    - Parallel BigQuery extraction (6 event types processed concurrently)
    - SFTP file download and parsing
    - Job status tracking with detailed progress information
    - Data availability reporting with breakdown by event type
    - Scheduled ingestion via external scheduler integration

Service Configuration:
    - Port: 8002
    - Base Path: /data/api/v1
    - Service Name: data-ingestion-service

Example:
    ```python
    from services.data_service import app
    
    # Run with uvicorn
    # uvicorn services.data_service:app --port 8002
    ```

See Also:
    - services.data_service.api: API endpoint definitions
    - services.data_service.database: Database repository layer
    - services.data_service_functions: Azure Functions for background processing
"""

from services.data_service.main import app

__all__ = ["app"]
