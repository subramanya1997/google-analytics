import json
import os
from datetime import datetime
from uuid import uuid4
from typing import Optional

from azure.storage.queue.aio import QueueClient
from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from common.exceptions import create_api_error, handle_database_error
from services.data_service.api.dependencies import get_tenant_id, get_repository
from services.data_service.api.v1.models import (
    CreateIngestionJobRequest,
    IngestionJobResponse,
)
from services.data_service.database.sqlalchemy_repository import SqlAlchemyRepository
from common.config import get_settings
from common.database import get_tenant_service_status

router = APIRouter()

# Get settings for Azure Functions URL
_settings = get_settings("data-service")


@router.post("/ingest", response_model=IngestionJobResponse)
async def create_ingestion_job(
    request: CreateIngestionJobRequest,
    tenant_id: str = Depends(get_tenant_id),
    repo: SqlAlchemyRepository = Depends(get_repository),
):
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
        service_status = await get_tenant_service_status(tenant_id, "data-ingestion-service")
        
        # Check if required services are enabled
        disabled_services = []
        
        if needs_bigquery and not service_status["bigquery"]["enabled"]:
            error_msg = service_status["bigquery"]["error"] or "BigQuery service is disabled"
            disabled_services.append(f"BigQuery: {error_msg}")
        
        if needs_sftp and not service_status["sftp"]["enabled"]:
            error_msg = service_status["sftp"]["error"] or "SFTP service is disabled"
            disabled_services.append(f"SFTP: {error_msg}")
        
        if disabled_services:
            error_detail = "Cannot process ingestion job. " + "; ".join(disabled_services)
            logger.warning(f"Ingestion blocked for tenant {tenant_id}: {error_detail}")
            raise HTTPException(
                status_code=400,
                detail=error_detail
            )
        
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
        logger.info(f"Created ingestion job {job_id} for tenant {tenant_id}, sending to queue...")

        # Send message to Azure Queue for background processing
        connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
        if not connection_string:
            raise ValueError("AZURE_STORAGE_CONNECTION_STRING environment variable not set")
        
        queue_client = QueueClient.from_connection_string(connection_string, "ingestion-jobs")
        
        message = {
            "job_id": job_id,
            "tenant_id": tenant_id,
            "start_date": request.start_date.isoformat(),
            "end_date": request.end_date.isoformat(),
            "data_types": request.data_types
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
            user_message="Failed to create ingestion job. Please try again later."
        )


@router.get("/data-availability")
async def get_data_availability(
    tenant_id: str = Depends(get_tenant_id),
    repo: SqlAlchemyRepository = Depends(get_repository),
):
    """
    Get the date range of available data for the tenant with detailed breakdown.
    """
    try:
        return await repo.get_data_availability_with_breakdown(tenant_id)
    except HTTPException:
        raise
    except Exception as e:
        raise handle_database_error("getting data availability", e)


@router.get("/jobs")
async def get_ingestion_jobs(
    tenant_id: str = Depends(get_tenant_id),
    repo: SqlAlchemyRepository = Depends(get_repository),
    limit: Optional[int] = Query(default=50, le=100),
    offset: Optional[int] = Query(default=0, ge=0)
):
    """
    Get ingestion job history for the tenant.
    """
    try:
        jobs = await repo.get_tenant_jobs(tenant_id, limit, offset)
        
        return {
            "jobs": jobs.get("jobs", []),
            "total": jobs.get("total", 0),
            "limit": limit,
            "offset": offset
        }
    except HTTPException:
        raise
    except Exception as e:
        raise handle_database_error("getting ingestion jobs", e)


