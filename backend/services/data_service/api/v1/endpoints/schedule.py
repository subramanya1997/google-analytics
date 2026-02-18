"""
Scheduled Ingestion and Email Report Endpoints

This module provides HTTP endpoints for managing scheduled data ingestion jobs
and email report distribution. Both scheduling systems integrate with an external
scheduler service to enable automated, cron-based execution.

Endpoints:
    Data Ingestion Scheduling:
    - POST /data/schedule: Create or update ingestion schedule (upsert)
    - GET /data/schedule: Retrieve current ingestion schedule

    Email Report Scheduling:
    - POST /email/schedule: Create or update email report schedule (upsert)
    - GET /email/schedule: Retrieve current email report schedule

Schedule Management:
    Schedules are stored in an external scheduler service (not in the database).
    The scheduler service handles:
    - Cron expression parsing and validation
    - Job execution timing
    - HTTP request dispatch to ingestion/email endpoints
    - Schedule status management (active/inactive)

Job Naming Convention:
    - Data Ingestion: `data_{tenant_id}`
    - Email Reports: `email_{tenant_id}`
    - App Name: `google_analytics`
    This ensures unique schedule identification per tenant.

Default Schedules:
    - Data Ingestion: DATA_INGESTION_CRON (typically "0 2 * * *" for 2 AM daily)
    - Email Reports: EMAIL_NOTIFICATION_CRON (typically "0 8 * * *" for 8 AM daily)

Authentication:
    All schedule endpoints require:
    - X-Tenant-Id header: Tenant identification
    - Authorization header: JWT token for scheduler service authentication

See Also:
    - common.scheduler_client: Scheduler service client implementation
    - services.data_service.api.v1.endpoints.ingestion: Ingestion job endpoints
    - services.data_service.api.v1.endpoints.email: Email management endpoints
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


@router.post("/data/schedule")
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
        schedule_exists = False
        existing_event_id = None
        try:
            existing_schedule = scheduler.get_schedules(
                auth_token=auth_token, job_name=job_name, app_name=app_name, limit=1
            )
            if (
                existing_schedule.get("scheduler_details")
                and len(existing_schedule["scheduler_details"]) > 0
            ):
                schedule_exists = True
                # Extract event_id for use in update operation
                existing_event_id = existing_schedule["scheduler_details"][0].get(
                    "event_id"
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

        # Create or update schedule
        if schedule_exists and existing_event_id:
            # Use event_id for update operation (required by scheduler API)
            response = scheduler.update_schedule(
                auth_token=auth_token,
                event_id=existing_event_id,
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
            # Create new schedule
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


@router.get("/data/schedule")
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


@router.delete("/data/schedule")
async def delete_ingestion_schedule(
    tenant_id: str = Depends(get_tenant_id),
    authorization: str = Header(...),
) -> dict[str, Any]:
    """
    Delete the data ingestion schedule for the tenant.

    Removes the scheduled job from the external scheduler service.

    Args:
        tenant_id: Tenant ID from X-Tenant-Id header
        authorization: JWT token from Authorization header

    Returns:
        Response confirming deletion
    """
    try:
        auth_token = authorization.replace("Bearer ", "")

        job_name = f"data_{tenant_id}"
        app_name = "google_analytics"

        scheduler = create_scheduler_client(_settings.SCHEDULER_API_URL)
        response = scheduler.delete_schedule(
            auth_token=auth_token, job_name=job_name, app_name=app_name
        )

        return {
            "message": "Data ingestion schedule deleted successfully",
            "scheduler_response": response,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise create_api_error(
            operation="deleting ingestion schedule",
            status_code=500,
            internal_error=e,
            user_message="Failed to delete schedule. Please try again later.",
        )


# ======================================
# EMAIL REPORT SCHEDULE ENDPOINTS
# ======================================


@router.post("/email/schedule")
async def upsert_email_schedule(
    request: ScheduleRequest,
    tenant_id: str = Depends(get_tenant_id),
    authorization: str = Header(...),
) -> dict[str, Any]:
    """
    Create or update the email report schedule for the tenant (upsert operation).

    If a schedule already exists, it will be updated. Otherwise, a new schedule is created.

    Args:
        cron_expression: Optional cron expression. Defaults to EMAIL_NOTIFICATION_CRON env var (8 AM daily)
        status: Optional status (active/inactive). Defaults to 'active' for new schedules
        tenant_id: Tenant ID from X-Tenant-Id header
        authorization: JWT token from Authorization header

    Returns:
        Response containing scheduler response and operation performed

    Example:
        POST /api/v1/data/email/schedule
        Headers:
            X-Tenant-Id: <tenant_uuid>
            Authorization: Bearer <jwt_token>
        Body (optional):
            {
                "cron_expression": "0 8 * * *",
                "status": "active"
            }

        Response:
            {
                "message": "Schedule created successfully",
                "cron_expression": "0 8 * * *",
                "operation": "created"
            }
    """
    try:
        # Extract JWT token from Authorization header
        auth_token = authorization.replace("Bearer ", "")

        # Get cron expression from request body or settings
        cron_exp = request.cron_expression or _settings.EMAIL_NOTIFICATION_CRON
        schedule_status = request.status or "active"

        # Create scheduler client with URL from settings
        scheduler = create_scheduler_client(_settings.SCHEDULER_API_URL)

        # Job naming convention
        job_name = f"email_{tenant_id}"
        app_name = "google_analytics"

        # Check if schedule already exists using GET
        schedule_exists = False
        existing_event_id = None
        try:
            existing_schedule = scheduler.get_schedules(
                auth_token=auth_token, job_name=job_name, app_name=app_name, limit=1
            )
            if (
                existing_schedule.get("scheduler_details")
                and len(existing_schedule["scheduler_details"]) > 0
            ):
                schedule_exists = True
                # Extract event_id for use in update operation
                existing_event_id = existing_schedule["scheduler_details"][0].get(
                    "event_id"
                )
        except Exception as e:
            logger.warning(f"Could not fetch existing email schedule: {e}")
            schedule_exists = False

        # Prepare job configuration - point to data service email endpoint
        job_config = {
            "job_name": job_name,
            "app_name": app_name,
            "url": f"{_settings.DATA_SERVICE_URL}/api/v1/email/send-reports",
            "method": "POST",
            "cron_exp": cron_exp,
            "status": schedule_status,
            "header": {
                "Authorization": f"Bearer {auth_token}",
                "X-Tenant-Id": tenant_id,
                "Content-Type": "application/json",
            },
            "body": {"report_date": None, "branch_codes": None},
        }

        # Create or update schedule
        if schedule_exists and existing_event_id:
            # Use event_id for update operation (required by scheduler API)
            response = scheduler.update_schedule(
                auth_token=auth_token,
                event_id=existing_event_id,
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
            # Create new schedule
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
        logger.error(f"Error upserting email schedule for tenant {tenant_id}: {e}")
        logger.exception("Full traceback:")
        raise create_api_error(
            operation="upserting email schedule",
            status_code=500,
            internal_error=e,
            user_message="Failed to update email schedule. Please try again later.",
        )


@router.get("/email/schedule")
async def get_email_schedule(
    tenant_id: str = Depends(get_tenant_id), authorization: str = Header(...)
) -> dict[str, Any]:
    """
    Get the email report schedule details for the tenant.

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
        job_name = f"email_{tenant_id}"
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
                cron_expression = _settings.EMAIL_NOTIFICATION_CRON
                logger.warning("Scheduler returned no cron expression, using default")

            return {
                "cron_expression": cron_expression,
                "status": status,
                "source": "scheduler",
            }

        # No schedule in scheduler - return default
        return {
            "cron_expression": _settings.EMAIL_NOTIFICATION_CRON,
            "status": "inactive",
            "source": "default",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting email schedule for tenant {tenant_id}: {e}")
        logger.exception("Full traceback:")
        raise create_api_error(
            operation="getting email schedule",
            status_code=500,
            internal_error=e,
            user_message="Failed to retrieve email schedule. Please try again later.",
        )


@router.delete("/email/schedule")
async def delete_email_schedule(
    tenant_id: str = Depends(get_tenant_id),
    authorization: str = Header(...),
) -> dict[str, Any]:
    """
    Delete the email report schedule for the tenant.

    Removes the scheduled job from the external scheduler service.

    Args:
        tenant_id: Tenant ID from X-Tenant-Id header
        authorization: JWT token from Authorization header

    Returns:
        Response confirming deletion
    """
    try:
        auth_token = authorization.replace("Bearer ", "")

        job_name = f"email_{tenant_id}"
        app_name = "google_analytics"

        scheduler = create_scheduler_client(_settings.SCHEDULER_API_URL)
        response = scheduler.delete_schedule(
            auth_token=auth_token, job_name=job_name, app_name=app_name
        )

        return {
            "message": "Email report schedule deleted successfully",
            "scheduler_response": response,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting email schedule for tenant {tenant_id}: {e}")
        logger.exception("Full traceback:")
        raise create_api_error(
            operation="deleting email schedule",
            status_code=500,
            internal_error=e,
            user_message="Failed to delete email schedule. Please try again later.",
        )
