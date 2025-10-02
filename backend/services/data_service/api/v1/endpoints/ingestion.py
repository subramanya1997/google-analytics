"""
Data Ingestion API Endpoints.

This module implements the REST API endpoints for data ingestion operations
in the Google Analytics Intelligence System. It provides comprehensive job
management, data availability monitoring, and status tracking functionality
for the multi-source, multi-tenant data pipeline.

The endpoints handle the complete data ingestion workflow from job creation
through completion, supporting BigQuery event data extraction and SFTP-based
user/location data processing with real-time status monitoring.

Key Features:
- **Asynchronous Job Processing**: Background execution with immediate response
- **Multi-Tenant Security**: X-Tenant-Id header enforcement for all operations
- **Comprehensive Status Tracking**: Real-time job progress and error reporting
- **Data Availability Queries**: Historical data range and statistics
- **Pagination Support**: Efficient handling of large job history datasets
- **Error Handling**: Detailed error responses with appropriate HTTP status codes

Endpoint Categories:
- Job Management: Create and monitor ingestion jobs
- Data Queries: Availability and statistics reporting  
- Status Monitoring: Real-time job progress tracking

All endpoints enforce multi-tenant security through dependency injection
and provide comprehensive error handling with structured responses.
"""

import asyncio
from datetime import datetime, date
from uuid import uuid4
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from loguru import logger

from services.data_service.api.dependencies import get_tenant_id
from services.data_service.api.v1.models import (
    CreateIngestionJobRequest,
    IngestionJobResponse,
)
from services.data_service.services import IngestionService

router = APIRouter()


@router.post("/ingest", response_model=IngestionJobResponse)
async def create_ingestion_job(
    request: CreateIngestionJobRequest,
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(get_tenant_id),
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
        # Generate unique job ID
        job_id = f"job_{uuid4().hex[:12]}"

        # Create ingestion service
        ingestion_service = IngestionService()

        # Create job record
        await ingestion_service.create_job(job_id, tenant_id, request)

        # Start background processing
        background_tasks.add_task(ingestion_service.run_job, job_id, tenant_id, request)

        logger.info(f"Created ingestion job {job_id} for tenant {tenant_id}")

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
):
    """
    Get comprehensive data availability summary for tenant analytics data.

    This endpoint provides a detailed overview of available analytics data including
    date ranges, record counts, and data quality metrics for the requesting tenant.
    It's essential for understanding data coverage and planning ingestion jobs.

    **Data Analysis Scope:**
    The endpoint analyzes all event data types stored in the analytics database:
    - Purchase events (e-commerce transactions)
    - Add to cart events (shopping behavior)
    - Page view events (website navigation)
    - View search results (successful searches)
    - No search results (failed searches)
    - View item events (product engagement)

    **Response Information:**
    - **Date Range**: Earliest and latest dates across all event types
    - **Record Counts**: Total event count across all types
    - **Data Quality**: Insights into data completeness and coverage

    **Multi-Tenant Security:**
    Data availability is scoped to the requesting tenant only, ensuring
    proper data isolation and preventing cross-tenant information disclosure.

    Args:
        tenant_id: Validated tenant ID from X-Tenant-Id header (via dependency)

    Returns:
        Dict[str, Any]: Comprehensive data availability summary containing:
        - summary: Overall data availability information
          - earliest_date: First date with any data (ISO format)
          - latest_date: Last date with any data (ISO format)  
          - total_events: Total number of events across all types

    Raises:
        HTTPException:
        - 400 BAD REQUEST: Missing or invalid X-Tenant-Id header
        - 500 INTERNAL SERVER ERROR: Database query or processing failure

    """
    try:
        ingestion_service = IngestionService()
        
        # Call the async method directly
        combined_data = await ingestion_service.get_data_availability_with_breakdown(tenant_id)
        return combined_data
    except Exception as e:
        logger.error(f"Error getting data availability: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs")
async def get_ingestion_jobs(
    tenant_id: str = Depends(get_tenant_id),
    limit: Optional[int] = Query(default=50, le=100),
    offset: Optional[int] = Query(default=0, ge=0)
):
    """
    Get paginated ingestion job history for tenant with comprehensive job details.

    This endpoint provides a paginated list of all ingestion jobs for the requesting
    tenant, including job status, configuration, timing information, and processing
    results. It supports efficient browsing of job history for monitoring and auditing.

    **Pagination Support:**
    Uses offset/limit pagination for efficient handling of large job histories
    without performance degradation. Supports up to 100 jobs per request with
    default page size of 50.

    **Job Information Included:**
    - Job identification (job_id, tenant_id)
    - Configuration (date range, data types)
    - Status tracking (status, progress, completion)
    - Timing (created_at, started_at, completed_at)
    - Results (records_processed, error_message)

    **Sorting and Ordering:**
    Jobs are returned in reverse chronological order (newest first) for
    optimal user experience when viewing recent job activity.

    **Multi-Tenant Security:**
    Only returns jobs belonging to the requesting tenant, ensuring proper
    data isolation and preventing cross-tenant information disclosure.

    Args:
        tenant_id: Validated tenant ID from X-Tenant-Id header (via dependency)
        limit: Maximum number of jobs to return (1-100, default: 50)
        offset: Number of jobs to skip for pagination (>=0, default: 0)

    Returns:
        Dict[str, Any]: Paginated job history response containing:
        - jobs: List of job objects with complete details
        - total: Total number of jobs for the tenant
        - limit: Requested page size limit
        - offset: Requested pagination offset

    Raises:
        HTTPException:
        - 400 BAD REQUEST: Invalid pagination parameters or missing X-Tenant-Id
        - 500 INTERNAL SERVER ERROR: Database query or processing failure

    **Status Values:**
    - `queued`: Job created but not yet started
    - `processing`: Job currently executing
    - `completed`: Job finished successfully
    - `failed`: Job encountered errors and stopped

    """
    try:
        ingestion_service = IngestionService()
        
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
):
    """
    Get detailed information for a specific ingestion job with comprehensive status tracking.

    This endpoint retrieves complete details for a single ingestion job, providing
    real-time status information, processing progress, error details, and performance
    metrics. It's essential for job monitoring and troubleshooting workflows.

    **Detailed Job Information:**
    Returns comprehensive job data including configuration, status, timing,
    progress metrics, error details, and processing results with full
    attribution and context for effective monitoring.

    **Real-Time Status Tracking:**
    Provides up-to-the-minute job status information including:
    - Current processing phase
    - Records processed by data type
    - Error messages and stack traces
    - Performance timing metrics

    **Multi-Tenant Security:**
    Enforces tenant isolation by validating job ownership before returning
    details, preventing cross-tenant information disclosure and ensuring
    proper access control.


    Args:
        job_id: Unique identifier for the ingestion job to retrieve
        tenant_id: Validated tenant ID from X-Tenant-Id header (via dependency)

    Returns:
        Dict[str, Any]: Complete job details including:
        - Job identification and configuration
        - Current status and progress information
        - Timing data (created, started, completed)
        - Processing results and record counts
        - Error information (if applicable)
        - Performance metrics

    Raises:
        HTTPException:
        - 404 NOT FOUND: Job does not exist or doesn't belong to tenant
        - 400 BAD REQUEST: Invalid job_id format or missing X-Tenant-Id
        - 500 INTERNAL SERVER ERROR: Database query or processing failure

    **Status Values and Meanings:**
    - `queued`: Job created, waiting in background task queue
    - `processing`: Job actively executing, data being processed
    - `completed`: All requested data types processed successfully
    - `failed`: Job stopped due to unrecoverable error

    **Progress Tracking:**
    For active jobs, the progress field shows current status of each
    data type being processed, enabling granular monitoring and
    estimation of remaining completion time.

    **Performance Metrics:**
    Timing information supports:
    - Job duration analysis
    - Performance trend monitoring
    - Capacity planning decisions
    - SLA compliance tracking

    """
    try:
        ingestion_service = IngestionService()
        
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
