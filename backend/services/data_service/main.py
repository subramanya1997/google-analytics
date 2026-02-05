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

Background Tasks:
    - Job Status Monitor: Periodically checks for stuck jobs and marks them as failed

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
    - common.job_monitor: Job status monitoring
"""

from typing import Any

from fastapi import FastAPI
from loguru import logger

from common.config import BaseServiceSettings
from common.fastapi import create_fastapi_app
from common.job_monitor import JobStatusMonitor
from services.data_service.api.v1.api import api_router

# Global job monitor instance
_job_monitor: JobStatusMonitor | None = None


def setup_job_monitor(app: FastAPI, settings: BaseServiceSettings) -> None:
    """
    Setup job status monitor with startup/shutdown event handlers.
    
    This function configures a background task that monitors job statuses
    across all tenants and marks stuck jobs as failed.
    
    Args:
        app: FastAPI application instance.
        settings: Service settings containing configuration.
    """
    global _job_monitor
    
    # Get job monitor settings with defaults
    monitor_enabled = getattr(settings, "JOB_MONITOR_ENABLED", True)
    interval_seconds = getattr(settings, "JOB_MONITOR_INTERVAL_SECONDS", 300)
    stuck_timeout_minutes = getattr(settings, "JOB_STUCK_TIMEOUT_MINUTES", 10)
    azure_connection_string = getattr(settings, "AZURE_STORAGE_CONNECTION_STRING", "")
    
    if not monitor_enabled:
        logger.info("Job status monitor is disabled")
        return
    
    @app.on_event("startup")
    async def start_job_monitor() -> None:
        """Start the job status monitor on application startup."""
        global _job_monitor
        
        logger.info("Initializing job status monitor...")
        _job_monitor = JobStatusMonitor(
            azure_connection_string=azure_connection_string,
            interval_seconds=interval_seconds,
            stuck_timeout_minutes=stuck_timeout_minutes,
        )
        await _job_monitor.start()
    
    @app.on_event("shutdown")
    async def stop_job_monitor() -> None:
        """Stop the job status monitor on application shutdown."""
        global _job_monitor
        
        if _job_monitor:
            logger.info("Stopping job status monitor...")
            await _job_monitor.stop()
            _job_monitor = None


# Create FastAPI app with reverse proxy configuration and job monitor
app = create_fastapi_app(
    service_name="data-ingestion-service",
    description="Data ingestion service for Google Analytics intelligence system",
    api_router=api_router,
    root_path="/data",  # Nginx serves this at /data/
    additional_setup=setup_job_monitor,
)
