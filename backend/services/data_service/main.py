"""
Data Service FastAPI Application Entrypoint

This module creates and configures the FastAPI application instance for the Data
Ingestion Service. The application is configured with reverse proxy support for
deployment behind Nginx and includes comprehensive API documentation, CORS, and
logging middleware.

The application serves as the primary interface for:
- Creating and managing data ingestion jobs
- Querying data availability information
- Configuring scheduled ingestion workflows
- Monitoring job status and history

Application Configuration:
    - Service Name: data-ingestion-service
    - Root Path: /data (for Nginx reverse proxy)
    - API Router: /api/v1 (includes ingestion and schedule endpoints)
    - Documentation: Available at /docs (Swagger) and /redoc (ReDoc)

Middleware Stack:
    - Request logging with structured loguru logger
    - CORS configuration for cross-origin requests
    - Error handling with standardized API error responses
    - Multi-tenant request context management

Example:
    ```bash
    # Run locally
    uvicorn services.data_service:app --port 8002 --reload
    
    # Run in production
    uvicorn services.data_service:app --host 0.0.0.0 --port 8002
    ```

See Also:
    - common.fastapi.create_fastapi_app: Application factory function
    - services.data_service.api.v1.api: API router configuration
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
