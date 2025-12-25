"""
Data Ingestion Endpoints

This module provides HTTP endpoints for managing data ingestion jobs in the
Google Analytics Intelligence System. It handles the creation, monitoring, and
querying of ingestion jobs that process analytics data from multiple sources.

Endpoints:
    - POST /ingest: Create and queue a new ingestion job
    - GET /data-availability: Query available data date ranges
    - GET /jobs: Retrieve paginated job history for a tenant

Job Processing Flow:
    1. Client creates job via POST /ingest
    2. Job record created in database with status "queued"
    3. Job message sent to Azure Queue Storage
    4. Background worker (Azure Function) processes job
    5. Job status updated throughout processing lifecycle
    6. Client can query job status via GET /jobs

Multi-Tenant Support:
    All endpoints require X-Tenant-Id header for proper data isolation.
    Tenant ID is used for:
    - Database schema routing
    - Tenant-specific configuration retrieval
    - Service availability checks (BigQuery, SFTP)

Error Handling:
    - Service availability validation before job creation
    - Comprehensive error messages for debugging
    - Standardized API error responses

See Also:
    - services.data_service_functions: Background job processing
    - services.data_service.database.sqlalchemy_repository: Database operations
"""

from datetime import datetime
import json
import os
from typing import Any
from uuid import uuid4

from azure.storage.queue.aio import QueueClient
from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from common.config import get_settings
from common.database import get_tenant_service_status
from common.exceptions import create_api_error, handle_database_error
from services.data_service.api.dependencies import get_repository, get_tenant_id
from services.data_service.api.v1.models import (
    CreateIngestionJobRequest,
    IngestionJobResponse,
)
from services.data_service.database.sqlalchemy_repository import SqlAlchemyRepository

router = APIRouter()

# Get settings for Azure Functions URL
_settings = get_settings("data-service")


@router.post("/ingest", response_model=IngestionJobResponse)
async def create_ingestion_job(
    request: CreateIngestionJobRequest,
    tenant_id: str = Depends(get_tenant_id),
    repo: SqlAlchemyRepository = Depends(get_repository),
) -> IngestionJobResponse:
    """
    Create and start a new data ingestion job for multi-source analytics data processing.

    This endpoint initiates a comprehensive data ingestion job that processes analytics
    data from multiple sources based on the specified date range and data types. The job
    executes asynchronously in the background while returning immediate job information
    to the client.

    **Supported Data Types:**
    - `events`: Google Analytics 4 event data from BigQuery (6 event types)
    - `users`: Customer profile data from SFTP sources
    - `locations`: Warehouse/branch data from SFTP sources

    **Multi-Tenant Security:**
    Requires X-Tenant-Id header for proper data isolation and tenant-specific
    configuration retrieval (BigQuery project, SFTP credentials, etc.)

    **Job Status Workflow:**
    1. `queued` → Job created, waiting for background processing
    2. `processing` → Job actively running data extraction/transformation
    3. `completed` → All data types processed successfully
    4. `failed` → Job encountered unrecoverable error
    """
    try:
        # Check which services are needed based on data_types
        needs_bigquery = "events" in request.data_types
        needs_sftp = "users" in request.data_types or "locations" in request.data_types

        # Validate services are enabled
        service_status = await get_tenant_service_status(
            tenant_id, "data-ingestion-service"
        )

        # Check if required services are enabled
        disabled_services = []

        if needs_bigquery and not service_status["bigquery"]["enabled"]:
            error_msg = (
                service_status["bigquery"]["error"] or "BigQuery service is disabled"
            )
            disabled_services.append(f"BigQuery: {error_msg}")

        if needs_sftp and not service_status["sftp"]["enabled"]:
            error_msg = service_status["sftp"]["error"] or "SFTP service is disabled"
            disabled_services.append(f"SFTP: {error_msg}")

        if disabled_services:
            error_detail = "Cannot process ingestion job. " + "; ".join(
                disabled_services
            )
            logger.warning(f"Ingestion blocked for tenant {tenant_id}: {error_detail}")
            raise HTTPException(status_code=400, detail=error_detail)

        # Generate unique job ID
        job_id = f"job_{uuid4().hex[:12]}"

        # Create job record
        job_data = {
            "job_id": job_id,
            "tenant_id": tenant_id,
            "status": "queued",
            "data_types": request.data_types,
            "start_date": request.start_date,
            "end_date": request.end_date,
        }
        await repo.create_processing_job(job_data)
        logger.info(
            f"Created ingestion job {job_id} for tenant {tenant_id}, sending to queue..."
        )

        # Send message to Azure Queue for background processing
        connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
        if not connection_string:
            msg = "AZURE_STORAGE_CONNECTION_STRING environment variable not set"
            raise ValueError(
                msg
            )

        queue_client = QueueClient.from_connection_string(
            connection_string, "ingestion-jobs"
        )

        message = {
            "job_id": job_id,
            "tenant_id": tenant_id,
            "start_date": request.start_date.isoformat(),
            "end_date": request.end_date.isoformat(),
            "data_types": request.data_types,
        }

        await queue_client.send_message(json.dumps(message))
        logger.info(f"Successfully queued ingestion job {job_id} for processing")

        return IngestionJobResponse(
            job_id=job_id,
            start_date=request.start_date,
            end_date=request.end_date,
            data_types=request.data_types,
            status="queued",
            created_at=datetime.now(),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise create_api_error(
            operation="creating ingestion job",
            status_code=500,
            internal_error=e,
            user_message="Failed to create ingestion job. Please try again later.",
        )


@router.get("/data-availability")
async def get_data_availability(
    tenant_id: str = Depends(get_tenant_id),
    repo: SqlAlchemyRepository = Depends(get_repository),
) -> dict[str, Any]:
    """
    Get the date range of available data for the tenant with detailed breakdown.

    This endpoint queries the database to determine what date ranges have been
    successfully ingested and are available for analytics queries. The response
    includes summary statistics and detailed breakdowns by event type.

    The data availability information is useful for:
    - Dashboard initialization (determining default date ranges)
    - Validating ingestion job completeness
    - Identifying data gaps that need re-ingestion
    - User-facing data availability indicators

    Args:
        tenant_id: Tenant ID extracted from X-Tenant-Id header
        repo: Database repository instance for querying data availability

    Returns:
        dict[str, Any]: Data availability information with structure:
            {
                "summary": {
                    "earliest_date": "YYYY-MM-DD" | None,
                    "latest_date": "YYYY-MM-DD" | None,
                    "total_events": int
                }
            }

    Performance:
        Uses optimized PostgreSQL function (get_data_availability_combined) for
        efficient querying across all event tables.

    Example:
        ```bash
        curl -H "X-Tenant-Id: tenant-uuid" \
             http://localhost:8002/api/v1/data-availability
        ```

    Raises:
        HTTPException: 500 if database query fails
    """
    try:
        return await repo.get_data_availability_with_breakdown(tenant_id)
    except HTTPException:
        raise
    except Exception as e:
        msg = "getting data availability"
        raise handle_database_error(msg, e)


@router.get("/jobs")
async def get_ingestion_jobs(
    tenant_id: str = Depends(get_tenant_id),
    repo: SqlAlchemyRepository = Depends(get_repository),
    limit: int | None = Query(default=50, le=100),
    offset: int | None = Query(default=0, ge=0),
) -> dict[str, Any]:
    """
    Get paginated ingestion job history for the tenant.

    This endpoint retrieves a paginated list of ingestion jobs for the specified
    tenant, ordered by creation time (most recent first). Each job includes
    comprehensive status information, progress details, and error messages if
    applicable.

    The job history is useful for:
    - Monitoring ingestion job status and progress
    - Debugging failed jobs
    - Auditing data ingestion activities
    - Dashboard job status displays

    Args:
        tenant_id: Tenant ID extracted from X-Tenant-Id header
        repo: Database repository instance for querying jobs
        limit: Maximum number of jobs to return (default: 50, max: 100)
        offset: Number of jobs to skip for pagination (default: 0)

    Returns:
        dict[str, Any]: Paginated job list with structure:
            {
                "jobs": [
                    {
                        "id": str,
                        "job_id": str,
                        "status": str,
                        "data_types": list[str],
                        "start_date": "YYYY-MM-DD",
                        "end_date": "YYYY-MM-DD",
                        "progress": dict,
                        "records_processed": dict,
                        "error_message": str | None,
                        "created_at": "ISO datetime",
                        "started_at": "ISO datetime" | None,
                        "completed_at": "ISO datetime" | None
                    },
                    ...
                ],
                "total": int,
                "limit": int,
                "offset": int
            }

    Performance:
        Uses optimized PostgreSQL function (get_tenant_jobs_paginated) for
        efficient pagination and counting.

    Example:
        ```bash
        # Get first page
        curl -H "X-Tenant-Id: tenant-uuid" \
             "http://localhost:8002/api/v1/jobs?limit=20&offset=0"
        
        # Get second page
        curl -H "X-Tenant-Id: tenant-uuid" \
             "http://localhost:8002/api/v1/jobs?limit=20&offset=20"
        ```

    Raises:
        HTTPException: 500 if database query fails
    """
    try:
        jobs = await repo.get_tenant_jobs(tenant_id, limit, offset)

        return {
            "jobs": jobs.get("jobs", []),
            "total": jobs.get("total", 0),
            "limit": limit,
            "offset": offset,
        }
    except HTTPException:
        raise
    except Exception as e:
        msg = "getting ingestion jobs"
        raise handle_database_error(msg, e)
