"""
Schedule management endpoints for email report jobs.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Body
from pydantic import BaseModel
from loguru import logger
from sqlalchemy import text

from services.analytics_service.api.dependencies import get_tenant_id
from common.scheduler_client import create_scheduler_client
from common.config import get_settings
from common.database import get_async_db_session


router = APIRouter()

# Get settings for scheduler configuration
_settings = get_settings("analytics-service")


class ScheduleRequest(BaseModel):
    """Request model for creating/updating schedule."""
    cron_expression: Optional[str] = None
    status: Optional[str] = None


@router.post("/schedule")
async def upsert_email_schedule(
    request: ScheduleRequest,
    tenant_id: str = Depends(get_tenant_id),
    authorization: str = Header(...)
):
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
                auth_token=auth_token,
                job_name=job_name,
                app_name=app_name,
                limit=1
            )
            schedule_exists = existing_schedule.get("scheduler_details") and len(existing_schedule["scheduler_details"]) > 0
        except Exception as e:
            logger.warning(f"Could not fetch existing schedule: {e}")
            schedule_exists = False
        
        # Prepare job configuration
        job_config = {
            "job_name": job_name,
            "app_name": app_name,
            "url": "https://devenv-ai-tech-assistant.extremeb2b.com/analytics/api/v1/email/send-reports",
            "method": "POST",
            "cron_exp": cron_exp,
            "status": schedule_status,
            "header": {
                "Authorization": f"Bearer {auth_token}",
                "X-Tenant-Id": tenant_id,
                "Content-Type": "application/json"
            },
            "body": {
                "report_date": "auto",
                "branch_codes": None
            }
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
                body=job_config["body"]
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
                body=job_config["body"]
            )
        
        # Update the cron expression in the database
        try:
            async with get_async_db_session("analytics-service") as session:
                await session.execute(
                    text("""
                        UPDATE tenants 
                        SET email_schedule = :cron_exp, updated_at = NOW()
                        WHERE id = :tenant_id
                    """),
                    {"cron_exp": cron_exp, "tenant_id": tenant_id}
                )
                await session.commit()
        except Exception as db_error:
            logger.error(f"Failed to update email_schedule in database: {db_error}")
            # Don't fail the whole operation if database update fails
        
        return {
            "message": f"Schedule {'updated' if schedule_exists else 'created'} successfully",
            "cron_expression": cron_exp,
            "operation": "updated" if schedule_exists else "created",
            "scheduler_response": response
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error upserting email schedule for tenant {tenant_id}: {e}")
        logger.exception("Full traceback:")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schedule")
async def get_email_schedule(
    tenant_id: str = Depends(get_tenant_id),
    authorization: str = Header(...)
):
    """
    Get the email report schedule details for the tenant.
    
    Fallback order:
    1. Try to get from scheduler API
    2. If not found, get from database (tenants.email_schedule)
    3. If not in database, use default from settings
    
    Args:
        tenant_id: Tenant ID from X-Tenant-Id header
        authorization: JWT token from Authorization header
        
    Returns:
        Schedule details
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
            auth_token=auth_token,
            job_name=job_name,
            app_name=app_name,
            limit=1
        )
        
        # Always fetch from database for comparison/fallback
        cron_from_db = None
        try:
            async with get_async_db_session("analytics-service") as session:
                result = await session.execute(
                    text("SELECT email_schedule FROM tenants WHERE id = :tenant_id"),
                    {"tenant_id": tenant_id}
                )
                row = result.fetchone()
                if row and row[0]:
                    cron_from_db = row[0]
        except Exception as db_error:
            logger.error(f"Failed to get email_schedule from database: {db_error}")
        
        # Check if active schedule exists in scheduler
        has_active_schedule = response.get("scheduler_details") and len(response["scheduler_details"]) > 0
        
        if has_active_schedule:
            # Extract cron expression from active schedule
            schedule_data = response["scheduler_details"][0]
            cron_from_scheduler = schedule_data.get("cron_exp")
            status = schedule_data.get("status", "active")
            
            # Use scheduler value if available, otherwise fall back to DB
            cron_expression = cron_from_scheduler if cron_from_scheduler else cron_from_db
            
            if not cron_expression:
                cron_expression = _settings.EMAIL_NOTIFICATION_CRON
                logger.warning(f"Both scheduler and DB returned null, using default")
            
            return {
                "cron_expression": cron_expression,
                "status": status,
                "source": "scheduler" if cron_from_scheduler else ("database" if cron_from_db else "default")
            }
        
        # No schedule in scheduler - use database or default
        # Use database value or default from settings
        cron_expression = cron_from_db or _settings.EMAIL_NOTIFICATION_CRON
        
        return {
            "cron_expression": cron_expression,
            "status": "inactive",
            "source": "database" if cron_from_db else "default"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting email schedule for tenant {tenant_id}: {e}")
        logger.exception("Full traceback:")
        raise HTTPException(status_code=500, detail=str(e))

