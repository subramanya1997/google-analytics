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
    Create a new data ingestion job.

    - **start_date**: Start date (YYYY-MM-DD)
    - **end_date**: End date (YYYY-MM-DD)
    - **data_types**: Types of data to process ["events", "users", "locations"]
    """
    try:
        # Generate unique job ID
        job_id = f"job_{uuid4().hex[:12]}"

        # Create ingestion service
        ingestion_service = IngestionService()

        # Create job record
        ingestion_service.create_job(job_id, tenant_id, request)

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
    include_breakdown: bool = Query(False, description="Include detailed date-wise breakdown"),
):
    """
    Get the date range of available data for the tenant, optionally with detailed breakdown.
    """
    try:
        ingestion_service = IngestionService()
        
        if include_breakdown:
            # Get both summary and breakdown in one call
            combined_data = ingestion_service.get_data_availability_with_breakdown(tenant_id)
            return combined_data
        else:
            # Just get summary data
            data_range = ingestion_service.get_data_availability(tenant_id)
            return {
                "earliest_date": data_range.get("earliest_date"),
                "latest_date": data_range.get("latest_date"),
                "total_events": data_range.get("total_events", 0)
            }
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
    Get ingestion job history for the tenant.
    """
    try:
        ingestion_service = IngestionService()
        jobs = ingestion_service.get_tenant_jobs(tenant_id, limit=limit, offset=offset)
        
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
    Get specific ingestion job details.
    """
    try:
        ingestion_service = IngestionService()
        job = ingestion_service.get_job_status(job_id)
        
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
