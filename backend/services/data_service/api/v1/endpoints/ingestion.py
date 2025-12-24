import asyncio
import json
import os
from datetime import datetime, date
from uuid import uuid4
from typing import Optional, List, Dict, Any

from azure.storage.queue.aio import QueueClient
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from loguru import logger

from services.data_service.api.dependencies import get_tenant_id, get_ingestion_service
from services.data_service.api.v1.models import (
    CreateIngestionJobRequest,
    IngestionJobResponse,
)
from services.data_service.services import IngestionService
from common.config import get_settings
from common.database import get_tenant_service_status

router = APIRouter()

# Get settings for Azure Functions URL
_settings = get_settings("data-service")


@router.post("/ingest", response_model=IngestionJobResponse)
async def create_ingestion_job(
    request: CreateIngestionJobRequest,
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(get_tenant_id),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
):
    """
    Create and start a new data ingestion job for multi-source analytics data processing.

    This endpoint initiates a comprehensive data ingestion job that processes analytics
    data from multiple sources based on the specified date range and data types. The job
    executes asynchronously in the background while returning immediate job information
    to the client.

    **Data Processing Pipeline:**
    
    1. **Job Creation**: Creates job record with queued status
    2. **Background Execution**: Starts async processing in thread pool
    3. **Multi-Source Ingestion**: Parallel processing of selected data types:
       - **BigQuery Events**: GA4 event data (purchase, add_to_cart, page_view, etc.)
       - **SFTP Users**: Customer profile and demographic data
       - **SFTP Locations**: Warehouse and branch location information
    4. **Data Transformation**: Normalization, validation, and database storage
    5. **Status Updates**: Real-time job progress and completion tracking

    **Supported Data Types:**
    - `events`: Google Analytics 4 event data from BigQuery (6 event types)
    - `users`: Customer profile data from SFTP sources
    - `locations`: Warehouse/branch data from SFTP sources

    **Multi-Tenant Security:**
    Requires X-Tenant-Id header for proper data isolation and tenant-specific
    configuration retrieval (BigQuery project, SFTP credentials, etc.)

    **Background Processing:**
    Jobs execute asynchronously using FastAPI BackgroundTasks with dedicated
    thread pools for heavy operations. Clients receive immediate response
    and can poll job status for completion monitoring.

    Args:
        request: Job configuration including date range and data types
        background_tasks: FastAPI background task manager for async execution
        tenant_id: Validated tenant ID from X-Tenant-Id header (via dependency)
    
    Returns:
        IngestionJobResponse: Job information with unique ID and initial status

    Raises:
        HTTPException:
        - 400 BAD REQUEST: Invalid date range or unsupported data types
        - 400 BAD REQUEST: Missing or invalid X-Tenant-Id header
        - 500 INTERNAL SERVER ERROR: Job creation or initialization failure

    **Processing Details:**
    - **Events Processing**: Extracts 6 GA4 event types with full attribution
    - **Users Processing**: SFTP download with Excel parsing and data cleaning
    - **Locations Processing**: Warehouse data with address normalization
    - **Error Handling**: Individual data type failures don't stop other types
    - **Progress Tracking**: Records processed counts by data type
    - **Performance**: Batch operations (1000 records) for optimal throughput

    **Job Status Workflow:**
    1. `queued` → Job created, waiting for background processing
    2. `processing` → Job actively running data extraction/transformation
    3. `completed` → All data types processed successfully
    4. `failed` → Job encountered unrecoverable error

    **Client Usage Pattern:**
    1. POST /ingest → Get job_id
    2. Poll GET /jobs/{job_id} → Monitor progress
    3. Handle completion or error states appropriately
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
        await ingestion_service.create_job(job_id, tenant_id, request)

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

    except Exception as e:
        logger.error(f"Error creating ingestion job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data-availability")
async def get_data_availability(
    tenant_id: str = Depends(get_tenant_id),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
):
    """
    Get the date range of available data for the tenant with detailed breakdown.
    """
    try:
        # Call the async method directly
        combined_data = await ingestion_service.get_data_availability_with_breakdown(tenant_id)
        return combined_data
    except Exception as e:
        logger.error(f"Error getting data availability: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs")
async def get_ingestion_jobs(
    tenant_id: str = Depends(get_tenant_id),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    limit: Optional[int] = Query(default=50, le=100),
    offset: Optional[int] = Query(default=0, ge=0)
):
    """
    Get ingestion job history for the tenant.
    """
    try:
        # Call the async method directly
        jobs = await ingestion_service.get_tenant_jobs(tenant_id, limit, offset)
        
        return {
            "jobs": jobs.get("jobs", []),
            "total": jobs.get("total", 0),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Error getting ingestion jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}")
async def get_ingestion_job(
    job_id: str,
    tenant_id: str = Depends(get_tenant_id),
    ingestion_service: IngestionService = Depends(get_ingestion_service),
):
    """
    Get specific ingestion job details.
    """
    try:
        # Call the async method directly
        job = await ingestion_service.get_job_status(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Verify the job belongs to the tenant (security check)
        if job.get("tenant_id") != tenant_id:
            raise HTTPException(status_code=404, detail="Job not found")
            
        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ingestion job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
