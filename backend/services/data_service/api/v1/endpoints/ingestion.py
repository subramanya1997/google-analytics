from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from uuid import uuid4
from datetime import datetime

from services.data_service.api.v1.models import CreateIngestionJobRequest, IngestionJobResponse
from services.data_service.services import IngestionService
from loguru import logger
from services.data_service.api.dependencies import get_tenant_id

router = APIRouter()


@router.post("/ingest", response_model=IngestionJobResponse)
async def create_ingestion_job(
    request: CreateIngestionJobRequest,
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(get_tenant_id)
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
        background_tasks.add_task(
            ingestion_service.run_job,
            job_id,
            tenant_id,
            request
        )
        
        logger.info(f"Created ingestion job {job_id} for tenant {tenant_id}")
        
        return IngestionJobResponse(
            job_id=job_id,
            start_date=request.start_date,
            end_date=request.end_date,
            data_types=request.data_types,
            status="queued",
            created_at=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Error creating ingestion job: {e}")
        raise HTTPException(status_code=500, detail=str(e))
