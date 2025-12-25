"""
Schedule Management Endpoints for Automated Email Report Distribution

This module provides RESTful API endpoints for managing scheduled email report
distribution. It integrates with an external scheduler service to enable
automated, cron-based report generation and distribution.

Features:
    - Create/Update Schedules: Upsert email report schedules with cron expressions
    - Get Schedule: Retrieve current schedule configuration
    - Cron Support: Standard cron expression format for flexible scheduling

Scheduler Integration:
    The service integrates with an external scheduler API that handles:
    - Cron expression parsing and validation
    - Job execution at scheduled times
    - HTTP callback to trigger report distribution endpoint

Schedule Naming:
    Schedules use the naming convention: `email_{tenant_id}` to ensure
    uniqueness and easy identification per tenant.

Default Schedule:
    If no schedule exists, defaults to daily at 8 AM (configurable via
    EMAIL_NOTIFICATION_CRON environment variable).

Multi-Tenancy:
    All endpoints require X-Tenant-Id header and Authorization header
    (JWT token) for proper authentication and data isolation.

Example:
    ```python
    # Create/update schedule
    POST /api/v1/email/schedule
    Headers:
        X-Tenant-Id: tenant-123
        Authorization: Bearer <jwt_token>
    Body:
        {
            "cron_expression": "0 8 * * *",  # Daily at 8 AM
            "status": "active"
        }
    
    # Get current schedule
    GET /api/v1/email/schedule
    Headers:
        X-Tenant-Id: tenant-123
        Authorization: Bearer <jwt_token>
    ```

See Also:
    - common.scheduler_client: Scheduler service client
    - services.analytics_service.api.v1.endpoints.email: Email endpoints
"""

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from loguru import logger
from pydantic import BaseModel

from common.config import get_settings
from common.scheduler_client import create_scheduler_client
from services.analytics_service.api.dependencies import get_tenant_id

router = APIRouter()

# Get settings for scheduler configuration
_settings = get_settings("analytics-service")


class ScheduleRequest(BaseModel):
    """
    Request model for creating or updating email report schedules.

    This model represents the configuration for scheduled email report
    distribution, including cron expression and activation status.

    Attributes:
        cron_expression: Cron expression defining when reports should be sent
            (optional). If not provided, uses default from EMAIL_NOTIFICATION_CRON
            environment variable (typically "0 8 * * *" for daily at 8 AM).
            Format: "minute hour day month weekday"
        status: Schedule activation status (optional). Valid values:
            - "active": Schedule is enabled and will execute
            - "inactive": Schedule is disabled
            If not provided, defaults to "active" for new schedules.

    Example:
        ```python
        # Daily at 8 AM
        request = ScheduleRequest(
            cron_expression="0 8 * * *",
            status="active"
        )
        
        # Weekly on Monday at 9 AM
        request = ScheduleRequest(
            cron_expression="0 9 * * 1",
            status="active"
        )
        
        # Disable schedule
        request = ScheduleRequest(status="inactive")
        ```

    Cron Expression Format:
        Standard cron format: "minute hour day month weekday"
        - minute: 0-59
        - hour: 0-23
        - day: 1-31
        - month: 1-12
        - weekday: 0-7 (0 and 7 are Sunday)
    """

    cron_expression: str | None = None
    status: str | None = None


@router.post("/schedule")
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
        POST /api/v1/email/schedule
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
            "url": f"{_settings.ANALYTICS_SERVICE_URL}/api/v1/email/send-reports",
            "method": "POST",
            "cron_exp": cron_exp,
            "status": schedule_status,
            "header": {
                "Authorization": f"Bearer {auth_token}",
                "X-Tenant-Id": tenant_id,
                "Content-Type": "application/json",
            },
            "body": {"report_date": "auto", "branch_codes": None},
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
        logger.error(f"Error upserting email schedule for tenant {tenant_id}: {e}")
        logger.exception("Full traceback:")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schedule")
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
        raise HTTPException(status_code=500, detail=str(e))
