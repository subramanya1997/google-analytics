from fastapi import APIRouter, HTTPException, BackgroundTasks
from uuid import uuid4
from datetime import datetime

from common.models import DataIngestionRequest, DataIngestionResponse
from services.data_service.app.services.comprehensive_data_processing import ComprehensiveDataProcessingService
from loguru import logger

router = APIRouter()


@router.post("/ingest", response_model=DataIngestionResponse)
async def trigger_data_ingestion(
    request: DataIngestionRequest,
    background_tasks: BackgroundTasks
):
    """
    Trigger data ingestion for specified date range.
    
    - **tenant_id**: Tenant identifier
    - **start_date**: Start date (YYYY-MM-DD)
    - **end_date**: End date (YYYY-MM-DD)
    - **data_types**: Types of data to process ["events", "users", "locations"]
    - **force_refresh**: Force reprocess even if data exists
    """
    try:
        # Generate unique job ID
        job_id = f"job_{uuid4().hex[:12]}"
        
        # Create data processing service
        processing_service = ComprehensiveDataProcessingService()
        
        # Create processing job record
        processing_service.create_processing_job(job_id, request)
        
        # Start background processing
        background_tasks.add_task(
            process_data_ingestion_background,
            job_id,
            request
        )
        
        logger.info(f"Created data ingestion job {job_id} for tenant {request.tenant_id}")
        
        return DataIngestionResponse(
            job_id=job_id,
            tenant_id=request.tenant_id,
            start_date=request.start_date,
            end_date=request.end_date,
            data_types=request.data_types,
            status="queued",
            created_at=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Error creating data ingestion job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def process_data_ingestion_background(
    job_id: str,
    request: DataIngestionRequest
):
    """Background task for data processing."""
    try:
        processing_service = ComprehensiveDataProcessingService()
        await processing_service.process_data_ingestion(job_id, request)
    except Exception as e:
        logger.error(f"Background processing failed for job {job_id}: {e}")
        # The service should handle updating job status to failed
