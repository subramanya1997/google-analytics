"""
Email management API endpoints
"""

import json
import os
from typing import Any, Dict, List, Optional
from uuid import uuid4

from azure.storage.queue.aio import QueueClient
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from loguru import logger

from common.exceptions import handle_database_error, create_api_error
from services.analytics_service.api.dependencies import get_tenant_id
from common.config import get_settings
from common.database import get_tenant_service_status
from services.analytics_service.api.v1.models import (
    BranchEmailMappingRequest,
    BranchEmailMappingResponse,
    EmailJobResponse,
    SendReportsRequest,
)
from services.analytics_service.database.dependencies import get_analytics_db_client
from services.analytics_service.database.postgres_client import AnalyticsPostgresClient

router = APIRouter()

# Get settings for pagination constants
_settings = get_settings("analytics-service")


@router.get("/config", response_model=Dict[str, Any])
async def get_email_config(
    tenant_id: str = Depends(get_tenant_id),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client),
):
    """
    Get email configuration for the tenant.
    
    Returns the SMTP configuration stored in the tenants table.
    """
    try:
        config = await db_client.get_email_config(tenant_id)
        
        # Don't expose sensitive information like passwords
        if config and 'password' in config:
            config = config.copy()
            config['password'] = '***HIDDEN***'
        
        return {
            "tenant_id": tenant_id,
            "config": config or {},
            "configured": bool(config)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise handle_database_error("fetching email config", e)


@router.get("/mappings", response_model=List[BranchEmailMappingResponse])
async def get_branch_email_mappings(
    tenant_id: str = Depends(get_tenant_id),
    branch_code: Optional[str] = Query(default=None, description="Filter by branch code"),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client),
):
    """
    Get branch to email mappings for the tenant.
    
    Returns list of branch-email mappings showing which sales reps
    should receive reports for which branches.
    """
    try:
        mappings = await db_client.get_branch_email_mappings(tenant_id, branch_code)
        
        logger.info(f"Retrieved {len(mappings)} email mappings for tenant {tenant_id}")
        
        return mappings
        
    except HTTPException:
        raise
    except Exception as e:
        raise handle_database_error("fetching email mappings", e)


@router.post("/mappings", response_model=Dict[str, Any])
async def create_branch_email_mapping(
    mapping: BranchEmailMappingRequest,
    tenant_id: str = Depends(get_tenant_id),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client),
):
    """
    Create a new branch email mapping for the tenant.
    """
    try:
        result = await db_client.create_branch_email_mapping(tenant_id, mapping)
        
        logger.info(f"Created new email mapping for tenant {tenant_id}: {result}")
        
        return {
            "success": True,
            "message": "Successfully created mapping",
            "mapping_id": result.get("mapping_id")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise handle_database_error("creating email mapping", e)


@router.put("/mappings/{mapping_id}", response_model=Dict[str, Any])
async def update_branch_email_mapping(
    mapping_id: str,
    mapping: BranchEmailMappingRequest,
    tenant_id: str = Depends(get_tenant_id),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client),
):
    """
    Update a specific branch email mapping by ID.
    
    Updates the mapping identified by the given ID for the current tenant.
    """
    try:
        result = await db_client.update_branch_email_mapping(tenant_id, mapping_id, mapping)
        
        if not result:
            raise HTTPException(
                status_code=404, 
                detail=f"Branch email mapping with ID {mapping_id} not found"
            )
        
        logger.info(f"Updated email mapping {mapping_id} for tenant {tenant_id}")
        
        return {
            "success": True,
            "message": f"Successfully updated mapping with ID {mapping_id}",
            "mapping_id": mapping_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise handle_database_error("updating email mapping", e)


@router.delete("/mappings/{mapping_id}", response_model=Dict[str, Any])
async def delete_branch_email_mapping(
    mapping_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client),
):
    """
    Delete a specific branch email mapping by ID.
    
    Removes the mapping identified by the given ID for the current tenant.
    """
    try:
        result = await db_client.delete_branch_email_mapping(tenant_id, mapping_id)
        
        if not result:
            raise HTTPException(
                status_code=404, 
                detail=f"Branch email mapping with ID {mapping_id} not found"
            )
        
        logger.info(f"Deleted email mapping {mapping_id} for tenant {tenant_id}")
        
        return {
            "success": True,
            "message": f"Successfully deleted mapping with ID {mapping_id}",
            "mapping_id": mapping_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise handle_database_error("deleting email mapping", e)


@router.post("/send-reports", response_model=EmailJobResponse)
async def send_reports(
    request: SendReportsRequest,
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(get_tenant_id),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client),
):
    """
    Initiate automated branch report distribution via email.

    Creates and queues a background job for generating branch-specific analytics
    reports and distributing them to configured sales representatives via SMTP.

    Args:
        request (SendReportsRequest): Report distribution request containing:
            - report_date (date): Date for report generation
            - branch_codes (Optional[List[str]]): Specific branches or None for all
        background_tasks (BackgroundTasks): FastAPI background task scheduler
        tenant_id (str): Unique tenant identifier (from X-Tenant-Id header)
        db_client (AnalyticsPostgresClient): Database client dependency

    Returns:
        EmailJobResponse: Job information containing:
            - job_id (str): Unique job identifier for progress tracking
            - status (str): Initial job status
            - tenant_id (str): Tenant identifier
            - report_date (date): Report generation date
            - target_branches (List[str]): Target branch codes
            - message (Optional[str]): Status message

    Raises:
        HTTPException: 500 error for database failures or job creation errors
    """
    try:
        # Check SMTP service status
        service_status = await get_tenant_service_status(tenant_id, "analytics-service")
        
        if not service_status["smtp"]["enabled"]:
            error_msg = service_status["smtp"]["error"] or "SMTP service is disabled"
            logger.warning(f"Email sending blocked for tenant {tenant_id}: {error_msg}")
            raise HTTPException(
                status_code=400,
                detail=f"Cannot send emails. SMTP service is disabled: {error_msg}"
            )
        
        # Generate unique job ID
        job_id = f"email_job_{uuid4().hex[:12]}"
        
        # Create email job record in database
        job_data = {
            "job_id": job_id,
            "tenant_id": tenant_id,
            "status": "queued",
            "report_date": request.report_date,
            "target_branches": request.branch_codes or []
        }
        await db_client.create_email_job(job_data)
        
        logger.info(f"Created email job {job_id} for tenant {tenant_id}, sending to queue...")
        
        # Send message to Azure Queue for background processing
        connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
        if not connection_string:
            raise ValueError("AZURE_STORAGE_CONNECTION_STRING environment variable not set")
        
        queue_client = QueueClient.from_connection_string(connection_string, "email-jobs")
        
        message = {
            "job_id": job_id,
            "tenant_id": tenant_id,
            "report_date": request.report_date.isoformat(),
            "branch_codes": request.branch_codes
        }
        
        await queue_client.send_message(json.dumps(message))
        logger.info(f"Successfully queued email job {job_id} for processing")
        
        return EmailJobResponse(
            job_id=job_id,
            status="queued",
            tenant_id=tenant_id,
            report_date=request.report_date,
            target_branches=request.branch_codes or [],
            message="Email sending job created successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise create_api_error(
            operation="creating email job",
            status_code=500,
            internal_error=e,
            user_message="Failed to create email job. Please try again later."
        )


@router.get("/history", response_model=Dict[str, Any])
async def get_email_send_history(
    tenant_id: str = Depends(get_tenant_id),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(
        default=_settings.DEFAULT_PAGE_SIZE, ge=1, le=_settings.MAX_PAGE_SIZE, description="Items per page"
    ),
    branch_code: Optional[str] = Query(default=None, description="Filter by branch"),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    start_date: Optional[str] = Query(default=None, description="Filter from date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(default=None, description="Filter to date (YYYY-MM-DD)"),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client),
):
    """
    Get email sending history with pagination and filtering.
    """
    try:
        history = await db_client.get_email_send_history(
            tenant_id=tenant_id,
            page=page,
            limit=limit,
            branch_code=branch_code,
            status=status,
            start_date=start_date,
            end_date=end_date
        )
        
        logger.info(f"Retrieved email history for tenant {tenant_id}: {len(history.get('data', []))} records")
        
        return history
        
    except HTTPException:
        raise
    except Exception as e:
        raise handle_database_error("fetching email history", e)


@router.get("/jobs", response_model=Dict[str, Any]) 
async def get_email_jobs(
    tenant_id: str = Depends(get_tenant_id),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(
        default=_settings.DEFAULT_PAGE_SIZE, ge=1, le=_settings.MAX_PAGE_SIZE, description="Items per page"
    ),
    status: Optional[str] = Query(default=None, description="Filter by status"),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client),
):
    """
    Get email job history with pagination and filtering.
    """
    try:
        jobs = await db_client.get_email_jobs(
            tenant_id=tenant_id,
            page=page,
            limit=limit,
            status=status
        )
        
        logger.info(f"Retrieved email jobs for tenant {tenant_id}: {len(jobs.get('data', []))} jobs")
        
        return jobs
        
    except HTTPException:
        raise
    except Exception as e:
        raise handle_database_error("fetching email jobs", e)
