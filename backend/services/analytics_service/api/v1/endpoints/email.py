"""
Email management API endpoints
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from loguru import logger

from services.analytics_service.api.dependencies import get_tenant_id
from common.config import get_settings
from services.analytics_service.api.v1.models import (
    BranchEmailMappingRequest,
    BranchEmailMappingResponse,
    EmailJobResponse,
    SendReportsRequest,
)
from services.analytics_service.database.dependencies import get_analytics_db_client
from services.analytics_service.database.postgres_client import AnalyticsPostgresClient
from services.analytics_service.services.email_service import EmailService

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
        
    except Exception as e:
        logger.error(f"Error fetching email config for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch email config: {str(e)}"
        )


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
        
    except Exception as e:
        logger.error(f"Error fetching email mappings for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch email mappings: {str(e)}"
        )


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
        
    except Exception as e:
        logger.error(f"Error creating email mapping for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create email mapping: {str(e)}"
        )


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
        logger.error(f"Error updating email mapping {mapping_id} for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to update email mapping: {str(e)}"
        )


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
        logger.error(f"Error deleting email mapping {mapping_id} for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to delete email mapping: {str(e)}"
        )


@router.post("/send-reports", response_model=EmailJobResponse)
async def send_reports(
    request: SendReportsRequest,
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(get_tenant_id),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client),
):
    """
    Send individual branch reports via email.
    
    Generates individual branch reports for the specified date and branches, 
    then sends them to the configured sales representatives. Each recipient gets 
    individual reports for each branch they handle.
    """
    try:
        # Initialize email service
        email_service = EmailService(db_client)
        
        # Create background email job
        job_id = await email_service.create_send_reports_job(
            tenant_id, request, background_tasks
        )
        
        logger.info(f"Created email sending job {job_id} for tenant {tenant_id}")
        
        return EmailJobResponse(
            job_id=job_id,
            status="queued",
            tenant_id=tenant_id,
            report_date=request.report_date,
            target_branches=request.branch_codes or [],
            message="Email sending job created successfully"
        )
        
    except Exception as e:
        logger.error(f"Error creating email job for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create email job: {str(e)}"
        )


@router.get("/jobs/{job_id}", response_model=EmailJobResponse)
async def get_email_job_status(
    job_id: str,
    tenant_id: str = Depends(get_tenant_id),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client),
):
    """
    Get status of an email sending job.
    """
    try:
        job = await db_client.get_email_job_status(tenant_id, job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Email job not found")
            
        return job
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching email job {job_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch email job: {str(e)}"
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
        
    except Exception as e:
        logger.error(f"Error fetching email history for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch email history: {str(e)}"
        )


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
        
    except Exception as e:
        logger.error(f"Error fetching email jobs for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch email jobs: {str(e)}"
        )
