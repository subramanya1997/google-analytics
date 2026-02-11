"""
Email Management API Endpoints for Report Distribution

This module provides RESTful API endpoints for managing email configuration,
branch-to-email mappings, and automated report distribution. The email system
enables automated delivery of analytics reports to sales representatives
based on branch assignments.

Features:
    - Email Configuration: SMTP settings management
    - Branch Mappings: Associate branches with sales rep email addresses
    - Report Distribution: Trigger automated email report generation
    - Job Tracking: Monitor email job status and history
    - Send History: Track individual email delivery status

Email Flow:
    1. Configure SMTP settings in tenant_config
    2. Create branch-to-email mappings
    3. Trigger report distribution via /email/send-reports
    4. Background workers process jobs and send emails
    5. Track status via /email/jobs and /email/history

Multi-Tenancy:
    All endpoints require X-Tenant-Id header for proper data isolation.

Security:
    - SMTP passwords are masked when returned via API
    - Email sending requires SMTP service to be enabled for tenant

Example:
    ```python
    # Get email config
    GET /api/v1/email/config
    Headers:
        X-Tenant-Id: tenant-123

    # Create branch mapping
    POST /api/v1/email/mappings
    Body:
        {
            "branch_code": "BRANCH-001",
            "sales_rep_email": "rep@company.com"
        }

    # Send reports
    POST /api/v1/email/send-reports
    Body:
        {
            "report_date": "2024-01-15",
            "branch_codes": ["BRANCH-001"]
        }
    ```

See Also:
    - services.data_service.database.email_repository: Database repository methods
    - common.database.get_tenant_service_status: Service status checking
"""

import json
import os
from typing import Any
from uuid import uuid4

from azure.storage.queue.aio import QueueClient
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from loguru import logger

from common.config import get_settings
from common.database import get_tenant_service_status
from common.exceptions import create_api_error, handle_database_error
from services.data_service.api.dependencies import get_email_repository, get_tenant_id
from services.data_service.api.v1.models.email import (
    BranchEmailMappingRequest,
    BranchEmailMappingResponse,
    EmailJobResponse,
    SendReportsRequest,
)
from services.data_service.database.email_repository import EmailRepository

router = APIRouter()

# Get settings for pagination constants
_settings = get_settings("data-ingestion-service")


@router.get("/config", response_model=dict[str, Any])
async def get_email_config(
    tenant_id: str = Depends(get_tenant_id),
    repo: EmailRepository = Depends(get_email_repository),
) -> dict[str, Any]:
    """
    Get email configuration for the tenant.

    Returns the SMTP configuration stored in the tenant_config table.
    """
    try:
        config = await repo.get_email_config(tenant_id)

        # Don't expose sensitive information like passwords
        if config and "password" in config:
            config = config.copy()
            config["password"] = "***HIDDEN***"

        return {
            "tenant_id": tenant_id,
            "config": config or {},
            "configured": bool(config),
        }

    except HTTPException:
        raise
    except Exception as e:
        msg = "fetching email config"
        raise handle_database_error(msg, e)


@router.get("/mappings", response_model=list[BranchEmailMappingResponse])
async def get_branch_email_mappings(
    tenant_id: str = Depends(get_tenant_id),
    branch_code: str | None = Query(default=None, description="Filter by branch code"),
    repo: EmailRepository = Depends(get_email_repository),
) -> list[BranchEmailMappingResponse]:
    """
    Get branch to email mappings for the tenant.

    Returns list of branch-email mappings showing which sales reps
    should receive reports for which branches.
    """
    try:
        mappings = await repo.get_branch_email_mappings(tenant_id, branch_code)

        logger.info(f"Retrieved {len(mappings)} email mappings for tenant {tenant_id}")

        return mappings

    except HTTPException:
        raise
    except Exception as e:
        msg = "fetching email mappings"
        raise handle_database_error(msg, e)


@router.post("/mappings", response_model=dict[str, Any])
async def create_branch_email_mapping(
    mapping: BranchEmailMappingRequest,
    tenant_id: str = Depends(get_tenant_id),
    repo: EmailRepository = Depends(get_email_repository),
) -> dict[str, Any]:
    """
    Create a new branch email mapping for the tenant.
    """
    try:
        result = await repo.create_branch_email_mapping(tenant_id, mapping)

        logger.info(f"Created new email mapping for tenant {tenant_id}: {result}")

        return {
            "success": True,
            "message": "Successfully created mapping",
            "mapping_id": result.get("mapping_id"),
        }

    except HTTPException:
        raise
    except Exception as e:
        msg = "creating email mapping"
        raise handle_database_error(msg, e)


@router.put("/mappings/{mapping_id}", response_model=dict[str, Any])
async def update_branch_email_mapping(
    mapping_id: str,
    mapping: BranchEmailMappingRequest,
    tenant_id: str = Depends(get_tenant_id),
    repo: EmailRepository = Depends(get_email_repository),
) -> dict[str, Any]:
    """
    Update a specific branch email mapping by ID.

    Updates the mapping identified by the given ID for the current tenant.
    """
    try:
        result = await repo.update_branch_email_mapping(tenant_id, mapping_id, mapping)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Branch email mapping with ID {mapping_id} not found",
            )

        logger.info(f"Updated email mapping {mapping_id} for tenant {tenant_id}")

        return {
            "success": True,
            "message": f"Successfully updated mapping with ID {mapping_id}",
            "mapping_id": mapping_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        msg = "updating email mapping"
        raise handle_database_error(msg, e)


@router.delete("/mappings/{mapping_id}", response_model=dict[str, Any])
async def delete_branch_email_mapping(
    mapping_id: str,
    tenant_id: str = Depends(get_tenant_id),
    repo: EmailRepository = Depends(get_email_repository),
) -> dict[str, Any]:
    """
    Delete a specific branch email mapping by ID.

    Removes the mapping identified by the given ID for the current tenant.
    """
    try:
        result = await repo.delete_branch_email_mapping(tenant_id, mapping_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"Branch email mapping with ID {mapping_id} not found",
            )

        logger.info(f"Deleted email mapping {mapping_id} for tenant {tenant_id}")

        return {
            "success": True,
            "message": f"Successfully deleted mapping with ID {mapping_id}",
            "mapping_id": mapping_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        msg = "deleting email mapping"
        raise handle_database_error(msg, e)


@router.post("/send-reports", response_model=EmailJobResponse)
async def send_reports(
    request: SendReportsRequest,
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(get_tenant_id),
    repo: EmailRepository = Depends(get_email_repository),
) -> EmailJobResponse:
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
        repo (EmailRepository): Database repository dependency

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
        service_status = await get_tenant_service_status(tenant_id, "data-service")

        if not service_status["smtp"]["enabled"]:
            error_msg = service_status["smtp"]["error"] or "SMTP service is disabled"
            logger.warning(f"Email sending blocked for tenant {tenant_id}: {error_msg}")
            raise HTTPException(
                status_code=400,
                detail=f"Cannot send emails. SMTP service is disabled: {error_msg}",
            )

        # Generate unique job ID
        job_id = f"email_job_{uuid4().hex[:12]}"

        # Create email job record in database
        job_data = {
            "job_id": job_id,
            "tenant_id": tenant_id,
            "status": "queued",
            "report_date": request.report_date,
            "target_branches": request.branch_codes or [],
        }
        await repo.create_email_job(job_data)

        logger.info(
            f"Created email job {job_id} for tenant {tenant_id}, sending to queue..."
        )

        # Send message to Azure Queue for background processing
        connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
        if not connection_string:
            msg = "AZURE_STORAGE_CONNECTION_STRING environment variable not set"
            raise ValueError(msg)

        message = {
            "job_id": job_id,
            "tenant_id": tenant_id,
            "report_date": request.report_date.isoformat(),
            "branch_codes": request.branch_codes,
        }

        async with QueueClient.from_connection_string(
            connection_string, "email-jobs"
        ) as queue_client:
            await queue_client.send_message(json.dumps(message))
            logger.info(f"Successfully queued email job {job_id} for processing")

        return EmailJobResponse(
            job_id=job_id,
            status="queued",
            tenant_id=tenant_id,
            report_date=request.report_date,
            target_branches=request.branch_codes or [],
            message="Email sending job created successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise create_api_error(
            operation="creating email job",
            status_code=500,
            internal_error=e,
            user_message="Failed to create email job. Please try again later.",
        )


@router.get("/history", response_model=dict[str, Any])
async def get_email_send_history(
    tenant_id: str = Depends(get_tenant_id),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(
        default=_settings.DEFAULT_PAGE_SIZE,
        ge=1,
        le=_settings.MAX_PAGE_SIZE,
        description="Items per page",
    ),
    branch_code: str | None = Query(default=None, description="Filter by branch"),
    status: str | None = Query(default=None, description="Filter by status"),
    start_date: str | None = Query(
        default=None, description="Filter from date (YYYY-MM-DD)"
    ),
    end_date: str | None = Query(
        default=None, description="Filter to date (YYYY-MM-DD)"
    ),
    repo: EmailRepository = Depends(get_email_repository),
) -> dict[str, Any]:
    """
    Get email sending history with pagination and filtering.
    """
    try:
        history = await repo.get_email_send_history(
            tenant_id=tenant_id,
            page=page,
            limit=limit,
            branch_code=branch_code,
            status=status,
            start_date=start_date,
            end_date=end_date,
        )

        logger.info(
            f"Retrieved email history for tenant {tenant_id}: {len(history.get('data', []))} records"
        )

        return history

    except HTTPException:
        raise
    except Exception as e:
        msg = "fetching email history"
        raise handle_database_error(msg, e)


@router.get("/jobs", response_model=dict[str, Any])
async def get_email_jobs(
    tenant_id: str = Depends(get_tenant_id),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(
        default=_settings.DEFAULT_PAGE_SIZE,
        ge=1,
        le=_settings.MAX_PAGE_SIZE,
        description="Items per page",
    ),
    status: str | None = Query(default=None, description="Filter by status"),
    repo: EmailRepository = Depends(get_email_repository),
) -> dict[str, Any]:
    """
    Get email job history with pagination and filtering.
    """
    try:
        jobs = await repo.get_email_jobs(
            tenant_id=tenant_id, page=page, limit=limit, status=status
        )

        logger.info(
            f"Retrieved email jobs for tenant {tenant_id}: {len(jobs.get('data', []))} jobs"
        )

        return jobs

    except HTTPException:
        raise
    except Exception as e:
        msg = "fetching email jobs"
        raise handle_database_error(msg, e)
