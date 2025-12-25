"""
Scheduled Ingestion Endpoints

This module provides HTTP endpoints for managing scheduled data ingestion jobs.
Scheduled ingestion allows tenants to configure automatic, recurring data ingestion
jobs that run at specified intervals (via cron expressions).

Endpoints:
    - POST /data/schedule: Create or update ingestion schedule (upsert)
    - GET /data/schedule: Retrieve current ingestion schedule

Schedule Management:
    Schedules are stored in an external scheduler service (not in the database).
    The scheduler service handles:
    - Cron expression parsing and validation
    - Job execution timing
    - HTTP request dispatch to ingestion endpoints
    - Schedule status management (active/inactive)

Job Naming Convention:
    - Job Name: `data_{tenant_id}`
    - App Name: `google_analytics`
    This ensures unique schedule identification per tenant.

Default Schedule:
    If no schedule is configured, the default cron expression is retrieved from
    the DATA_INGESTION_CRON environment variable (typically "0 2 * * *" for 2 AM daily).

Authentication:
    All schedule endpoints require:
    - X-Tenant-Id header: Tenant identification
    - Authorization header: JWT token for scheduler service authentication

See Also:
    - common.scheduler_client: Scheduler service client implementation
    - services.data_service.api.v1.endpoints.ingestion: Ingestion job endpoints
"""

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from loguru import logger

from common.config import get_settings
from common.exceptions import create_api_error
from common.scheduler_client import create_scheduler_client
from services.data_service.api.dependencies import get_tenant_id
from services.data_service.api.v1.models import ScheduleRequest

router = APIRouter()

# Get settings for scheduler configuration
_settings = get_settings("data-ingestion-service")


@router.post("/schedule")
async def upsert_ingestion_schedule(
    request: ScheduleRequest,
    tenant_id: str = Depends(get_tenant_id),
    authorization: str = Header(...),
) -> dict[str, Any]:
    """
    Create or update the data ingestion schedule for the tenant (upsert operation).

    If a schedule already exists, it will be updated. Otherwise, a new schedule is created.

    Args:
        cron_expression: Optional cron expression. Defaults to DATA_INGESTION_CRON env var (2 AM daily)
        status: Optional status (active/inactive). Defaults to 'active' for new schedules
        tenant_id: Tenant ID from X-Tenant-Id header
        authorization: JWT token from Authorization header

    Returns:
        Response containing scheduler response and operation performed

    Example:
        POST /api/v1/schedule
        Headers:
            X-Tenant-Id: <tenant_uuid>
            Authorization: Bearer <jwt_token>
        Body (optional):
            {
                "cron_expression": "0 2 * * *",
                "status": "active"
            }

        Response:
            {
                "message": "Schedule created successfully",
                "cron_expression": "0 2 * * *",
                "operation": "created"
            }
    """
    try:
        # Extract JWT token from Authorization header
        auth_token = authorization.replace("Bearer ", "")

        # Get cron expression from request body or settings
        cron_exp = request.cron_expression or _settings.DATA_INGESTION_CRON
        schedule_status = request.status or "active"

        # Create scheduler client with URL from settings
        scheduler = create_scheduler_client(_settings.SCHEDULER_API_URL)

        # Job naming convention
        job_name = f"data_{tenant_id}"
        app_name = "google_analytics"

        # Check if schedule already exists using GET
        try:
            existing_schedule = scheduler.get_schedules(
                auth_token=auth_token, job_name=job_name, app_name=app_name, limit=1
            )
            schedule_exists = (
                existing_schedule.get("scheduler_details")
                and len(existing_schedule["scheduler_details"]) > 0
            )
        except Exception as e:
            logger.warning(f"Could not fetch existing schedule: {e}")
            schedule_exists = False

        # Prepare job configuration
        job_config = {
            "job_name": job_name,
            "app_name": app_name,
            "url": f"{_settings.DATA_SERVICE_URL}/api/v1/ingest",
            "method": "POST",
            "cron_exp": cron_exp,
            "status": schedule_status,
            "header": {"X-Tenant-Id": tenant_id, "Content-Type": "application/json"},
            "body": {"data_types": ["events", "users", "locations"]},
        }

        # Create or update schedule via POST (scheduler handles upsert)
        if schedule_exists:
            response = scheduler.update_schedule(
                auth_token=auth_token,
                job_name=job_config["job_name"],
                app_name=job_config["app_name"],
                url=job_config["url"],
                method=job_config["method"],
                cron_exp=job_config["cron_exp"],
                status=job_config["status"],
                headers=job_config["header"],
                body=job_config["body"],
            )
        else:
            response = scheduler.create_schedule(
                auth_token=auth_token,
                job_name=job_config["job_name"],
                app_name=job_config["app_name"],
                url=job_config["url"],
                method=job_config["method"],
                cron_exp=job_config["cron_exp"],
                status=job_config["status"],
                headers=job_config["header"],
                body=job_config["body"],
            )

        # Schedule is stored in external scheduler service (source of truth)
        # No need to duplicate in database

        return {
            "message": f"Schedule {'updated' if schedule_exists else 'created'} successfully",
            "cron_expression": cron_exp,
            "operation": "updated" if schedule_exists else "created",
            "scheduler_response": response,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise create_api_error(
            operation="upserting ingestion schedule",
            status_code=500,
            internal_error=e,
            user_message="Failed to update schedule. Please try again later.",
        )


@router.get("/schedule")
async def get_ingestion_schedule(
    tenant_id: str = Depends(get_tenant_id), authorization: str = Header(...)
) -> dict[str, Any]:
    """
    Get the data ingestion schedule details for the tenant.

    Returns the schedule from the scheduler API if it exists, otherwise returns the default.

    Args:
        tenant_id: Tenant ID from X-Tenant-Id header
        authorization: JWT token from Authorization header

    Returns:
        Schedule details with cron_expression, status, and source
    """
    try:
        # Extract JWT token
        auth_token = authorization.replace("Bearer ", "")

        # Job naming convention
        job_name = f"data_{tenant_id}"
        app_name = "google_analytics"

        # Create scheduler client with URL from settings
        scheduler = create_scheduler_client(_settings.SCHEDULER_API_URL)

        # Get schedules from scheduler API
        response = scheduler.get_schedules(
            auth_token=auth_token, job_name=job_name, app_name=app_name, limit=1
        )

        # Check if active schedule exists in scheduler
        has_active_schedule = (
            response.get("scheduler_details") and len(response["scheduler_details"]) > 0
        )

        if has_active_schedule:
            # Extract cron expression from active schedule
            schedule_data = response["scheduler_details"][0]
            cron_expression = schedule_data.get("cron_exp")
            status = schedule_data.get("status", "active")

            # If no cron expression in scheduler, use default
            if not cron_expression:
                cron_expression = _settings.DATA_INGESTION_CRON
                logger.warning("Scheduler returned no cron expression, using default")

            return {
                "cron_expression": cron_expression,
                "status": status,
                "source": "scheduler",
            }

        # No schedule in scheduler - return default
        return {
            "cron_expression": _settings.DATA_INGESTION_CRON,
            "status": "inactive",
            "source": "default",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise create_api_error(
            operation="getting ingestion schedule",
            status_code=500,
            internal_error=e,
            user_message="Failed to retrieve schedule. Please try again later.",
        )
