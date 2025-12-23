"""
Azure Functions Data Service

Serverless data ingestion service using regular async functions.
Processes events from BigQuery and users/locations from SFTP.
"""

import json
import logging
import os
from datetime import datetime, date, timedelta
from uuid import uuid4

import azure.functions as func

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


# ============================================================================
# Helper Functions
# ============================================================================

def create_json_response(data: dict, status_code: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(data, default=str),
        status_code=status_code,
        mimetype="application/json"
    )


def create_error_response(status_code: int, message: str) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({"error": message}),
        status_code=status_code,
        mimetype="application/json"
    )


def get_tenant_id(req: func.HttpRequest) -> str:
    tenant_id = req.headers.get("X-Tenant-Id")
    if not tenant_id:
        raise ValueError("X-Tenant-Id header is required")
    return tenant_id.strip()


# ============================================================================
# HTTP Triggers
# ============================================================================

@app.route(route="health", methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint."""
    return create_json_response({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    })


@app.route(route="ingest", methods=["POST"])
async def start_ingestion_job(req: func.HttpRequest) -> func.HttpResponse:
    """
    Start a new data ingestion job.
    Creates job record AND immediately starts processing in background.
    
    The endpoint returns immediately with status "processing", and clients
    can poll /jobs/{job_id} to check progress.
    """
    try:
        tenant_id = get_tenant_id(req)
    except ValueError as e:
        return create_error_response(400, str(e))
    
    try:
        body = req.get_json() if req.get_body() else {}
    except ValueError:
        body = {}
    
    # Generate job parameters
    job_id = f"job_{uuid4().hex[:12]}"
    
    try:
        from shared.database import create_repository
        from shared.models import CreateIngestionJobRequest
        from services.ingestion_service import IngestionService
        import asyncio
        
        # Validate request
        request = CreateIngestionJobRequest(**body)
        repo = create_repository(tenant_id)
        
        # Check service availability
        service_status = await repo.get_tenant_service_status(tenant_id)
        
        needs_bigquery = "events" in request.data_types
        needs_sftp = "users" in request.data_types or "locations" in request.data_types
        
        disabled_services = []
        if needs_bigquery and not service_status["bigquery"]["enabled"]:
            disabled_services.append(f"BigQuery: {service_status['bigquery'].get('error', 'Not configured')}")
        if needs_sftp and not service_status["sftp"]["enabled"]:
            disabled_services.append(f"SFTP: {service_status['sftp'].get('error', 'Not configured')}")
        
        if disabled_services:
            return create_error_response(400, "Services unavailable: " + "; ".join(disabled_services))
        
        # Create job record
        await repo.create_processing_job({
            "job_id": job_id,
            "tenant_id": tenant_id,
            "status": "queued",
            "data_types": request.data_types,
            "start_date": request.start_date,
            "end_date": request.end_date,
        })
        
        logging.info(f"Created job {job_id} for tenant {tenant_id}, starting processing...")
        
        # Start background processing immediately
        ingestion_service = IngestionService(tenant_id)
        asyncio.create_task(ingestion_service.run_job_safe(job_id, tenant_id, request))
        
        return create_json_response({
            "job_id": job_id,
            "tenant_id": tenant_id,
            "status": "processing",
            "data_types": request.data_types,
            "start_date": request.start_date.isoformat(),
            "end_date": request.end_date.isoformat(),
            "created_at": datetime.utcnow().isoformat(),
            "message": "Job created and processing started. Poll /jobs/{job_id} for status."
        }, 202)
        
    except ImportError as e:
        logging.error(f"Required module not available: {e}")
        return create_error_response(503, f"Service dependency unavailable: {str(e)}")
    except Exception as e:
        logging.error(f"Error creating/starting job: {e}")
        return create_error_response(500, f"Failed to create job: {str(e)}")


@app.route(route="data-availability", methods=["GET"])
async def get_data_availability(req: func.HttpRequest) -> func.HttpResponse:
    """Get data availability summary for the tenant."""
    try:
        tenant_id = get_tenant_id(req)
    except ValueError as e:
        return create_error_response(400, str(e))
    
    try:
        from shared.database import create_repository
        
        repo = create_repository(tenant_id)
        data = await repo.get_data_availability_with_breakdown(tenant_id)
        return create_json_response(data)
        
    except ImportError as e:
        logging.error(f"Database module not available: {e}")
        return create_error_response(503, "Database service unavailable")
    except Exception as e:
        logging.error(f"Error getting data availability: {e}")
        return create_error_response(500, str(e))


@app.route(route="jobs", methods=["GET"])
async def list_jobs(req: func.HttpRequest) -> func.HttpResponse:
    """Get job history for the tenant."""
    try:
        tenant_id = get_tenant_id(req)
    except ValueError as e:
        return create_error_response(400, str(e))
    
    try:
        limit = min(int(req.params.get("limit", 50)), 100)
        offset = max(int(req.params.get("offset", 0)), 0)
        
        from shared.database import create_repository
        
        repo = create_repository(tenant_id)
        jobs_data = await repo.get_tenant_jobs(tenant_id, limit, offset)
        
        return create_json_response({
            "jobs": jobs_data.get("jobs", []),
            "total": jobs_data.get("total", 0),
            "limit": limit,
            "offset": offset
        })
        
    except ImportError as e:
        logging.error(f"Database module not available: {e}")
        return create_error_response(503, "Database service unavailable")
    except Exception as e:
        logging.error(f"Error listing jobs: {e}")
        return create_error_response(500, str(e))


@app.route(route="jobs/{job_id}", methods=["GET"])
async def get_job_status(req: func.HttpRequest) -> func.HttpResponse:
    """Get specific job details."""
    try:
        tenant_id = get_tenant_id(req)
    except ValueError as e:
        return create_error_response(400, str(e))
    
    job_id = req.route_params.get("job_id")
    if not job_id:
        return create_error_response(400, "job_id is required")
    
    try:
        from shared.database import create_repository
        
        repo = create_repository(tenant_id)
        job = await repo.get_job_by_id(job_id)
        
        if not job:
            return create_error_response(404, "Job not found")
        
        # Verify tenant ownership
        if job.get("tenant_id") != tenant_id:
            return create_error_response(404, "Job not found")
        
        return create_json_response(job)
        
    except ImportError as e:
        logging.error(f"Database module not available: {e}")
        return create_error_response(503, "Database service unavailable")
    except Exception as e:
        logging.error(f"Error getting job {job_id}: {e}")
        return create_error_response(500, str(e))


@app.route(route="data/schedule", methods=["GET"])
async def get_schedule(req: func.HttpRequest) -> func.HttpResponse:
    """Get ingestion schedule for the tenant."""
    try:
        tenant_id = get_tenant_id(req)
    except ValueError as e:
        return create_error_response(400, str(e))
    
    try:
        from shared.database import get_db_session
        from sqlalchemy import text
        
        default_cron = os.getenv("DATA_INGESTION_CRON", "0 2 * * *")
        
        async with get_db_session() as session:
            result = await session.execute(
                text("SELECT data_ingestion_schedule FROM tenants WHERE id = :tenant_id"),
                {"tenant_id": tenant_id}
            )
            row = result.mappings().first()
        
        if row and row.get("data_ingestion_schedule"):
            return create_json_response({
                "cron_expression": row["data_ingestion_schedule"],
                "status": "active"
            })
        
        return create_json_response({
            "cron_expression": default_cron,
            "status": "inactive"
        })
        
    except ImportError as e:
        logging.error(f"Database module not available: {e}")
        return create_error_response(503, "Database service unavailable")
    except Exception as e:
        logging.error(f"Error getting schedule: {e}")
        return create_error_response(500, str(e))


@app.route(route="data/schedule", methods=["POST"])
async def update_schedule(req: func.HttpRequest) -> func.HttpResponse:
    """Update ingestion schedule for the tenant."""
    try:
        tenant_id = get_tenant_id(req)
    except ValueError as e:
        return create_error_response(400, str(e))
    
    # Check authorization
    if not req.headers.get("Authorization"):
        return create_error_response(401, "Authorization required")
    
    try:
        body = req.get_json() if req.get_body() else {}
    except ValueError:
        body = {}
    
    try:
        from shared.database import get_db_session
        from sqlalchemy import text
        
        default_cron = os.getenv("DATA_INGESTION_CRON", "0 2 * * *")
        cron_exp = body.get("cron_expression") or default_cron
        
        async with get_db_session() as session:
            await session.execute(
                text("""
                    UPDATE tenants 
                    SET data_ingestion_schedule = :cron_exp, updated_at = NOW()
                    WHERE id = :tenant_id
                """),
                {"cron_exp": cron_exp, "tenant_id": tenant_id}
            )
            await session.commit()
        
        return create_json_response({
            "message": "Schedule updated",
            "cron_expression": cron_exp,
            "status": "active"
        })
        
    except ImportError as e:
        logging.error(f"Database module not available: {e}")
        return create_error_response(503, "Database service unavailable")
    except Exception as e:
        logging.error(f"Error updating schedule: {e}")
        return create_error_response(500, str(e))


# ============================================================================
# Email HTTP Triggers
# ============================================================================

@app.route(route="email/send-reports", methods=["POST"])
async def send_reports(req: func.HttpRequest) -> func.HttpResponse:
    """
    Send branch reports via email.
    
    Creates an email job and processes it, sending reports to configured
    sales representatives for their branches.
    """
    try:
        tenant_id = get_tenant_id(req)
    except ValueError as e:
        return create_error_response(400, str(e))
    
    try:
        body = req.get_json() if req.get_body() else {}
    except ValueError:
        body = {}
    
    try:
        from shared.database import create_repository
        from shared.models import SendReportsRequest
        from services.email_service import EmailService
        import asyncio
        
        # Validate request
        request = SendReportsRequest(**body)
        repo = create_repository(tenant_id)
        
        # Check SMTP service status
        smtp_status = await repo.get_smtp_service_status(tenant_id)
        
        if not smtp_status["enabled"]:
            error_msg = smtp_status.get("error", "SMTP service is disabled")
            return create_error_response(400, f"Cannot send emails: {error_msg}")
        
        # Create and start email job
        email_service = EmailService(tenant_id)
        job_id = await email_service.create_and_process_email_job(
            tenant_id, request.report_date, request.branch_codes
        )
        
        logging.info(f"Created email job {job_id} for tenant {tenant_id}")
        
        # Start processing in background
        asyncio.create_task(email_service.process_email_job(
            tenant_id, job_id, request.report_date, request.branch_codes
        ))
        
        return create_json_response({
            "job_id": job_id,
            "status": "processing",
            "tenant_id": tenant_id,
            "report_date": request.report_date.isoformat(),
            "target_branches": request.branch_codes or [],
            "message": "Email job created and processing started. Poll /email/jobs/{job_id} for status."
        }, 202)
        
    except ImportError as e:
        logging.error(f"Required module not available: {e}")
        return create_error_response(503, f"Service dependency unavailable: {str(e)}")
    except Exception as e:
        logging.error(f"Error creating email job: {e}")
        return create_error_response(500, f"Failed to create email job: {str(e)}")


@app.route(route="email/jobs/{job_id}", methods=["GET"])
async def get_email_job_status(req: func.HttpRequest) -> func.HttpResponse:
    """Get status of an email sending job."""
    try:
        tenant_id = get_tenant_id(req)
    except ValueError as e:
        return create_error_response(400, str(e))
    
    job_id = req.route_params.get("job_id")
    if not job_id:
        return create_error_response(400, "job_id is required")
    
    try:
        from shared.database import create_repository
        
        repo = create_repository(tenant_id)
        job = await repo.get_email_job_status(tenant_id, job_id)
        
        if not job:
            return create_error_response(404, "Email job not found")
        
        return create_json_response(job)
        
    except ImportError as e:
        logging.error(f"Database module not available: {e}")
        return create_error_response(503, "Database service unavailable")
    except Exception as e:
        logging.error(f"Error fetching email job {job_id}: {e}")
        return create_error_response(500, str(e))


@app.route(route="email/mappings", methods=["GET"])
async def get_email_mappings(req: func.HttpRequest) -> func.HttpResponse:
    """Get branch email mappings for the tenant."""
    try:
        tenant_id = get_tenant_id(req)
    except ValueError as e:
        return create_error_response(400, str(e))
    
    branch_code = req.params.get("branch_code")
    
    try:
        from shared.database import create_repository
        
        repo = create_repository(tenant_id)
        mappings = await repo.get_branch_email_mappings(tenant_id, branch_code)
        
        return create_json_response({
            "mappings": mappings,
            "total": len(mappings)
        })
        
    except ImportError as e:
        logging.error(f"Database module not available: {e}")
        return create_error_response(503, "Database service unavailable")
    except Exception as e:
        logging.error(f"Error fetching email mappings: {e}")
        return create_error_response(500, str(e))


@app.route(route="email/mappings", methods=["POST"])
async def create_email_mapping(req: func.HttpRequest) -> func.HttpResponse:
    """Create a new branch email mapping."""
    try:
        tenant_id = get_tenant_id(req)
    except ValueError as e:
        return create_error_response(400, str(e))
    
    try:
        body = req.get_json() if req.get_body() else {}
    except ValueError:
        return create_error_response(400, "Invalid JSON body")
    
    if not body:
        return create_error_response(400, "Request body is required")
    
    try:
        from shared.database import create_repository
        from shared.models import BranchEmailMappingRequest
        
        # Validate request
        mapping_request = BranchEmailMappingRequest(**body)
        
        repo = create_repository(tenant_id)
        result = await repo.create_branch_email_mapping(tenant_id, {
            "branch_code": mapping_request.branch_code,
            "branch_name": mapping_request.branch_name,
            "sales_rep_email": mapping_request.sales_rep_email,
            "sales_rep_name": mapping_request.sales_rep_name,
            "is_enabled": mapping_request.is_enabled
        })
        
        logging.info(f"Created email mapping for tenant {tenant_id}: {result}")
        
        return create_json_response({
            "success": True,
            "message": "Email mapping created successfully",
            "mapping_id": result.get("mapping_id")
        }, 201)
        
    except ValueError as e:
        return create_error_response(400, str(e))
    except ImportError as e:
        logging.error(f"Database module not available: {e}")
        return create_error_response(503, "Database service unavailable")
    except Exception as e:
        logging.error(f"Error creating email mapping: {e}")
        return create_error_response(500, f"Failed to create email mapping: {str(e)}")


# ============================================================================
# Timer Trigger: Scheduled Ingestion
# ============================================================================

@app.timer_trigger(schedule="0 0 2 * * *", arg_name="timer", run_on_startup=False)
async def scheduled_ingestion(timer: func.TimerRequest) -> None:
    """
    Daily scheduled ingestion at 2 AM UTC.
    Creates and processes jobs for all tenants with active schedules.
    
    Note: Tenant discovery requires SCHEDULED_TENANT_IDS environment variable
    containing comma-separated tenant IDs. Each tenant has their own database.
    """
    logging.info("Starting scheduled ingestion")
    
    try:
        from shared.database import create_repository
        from shared.models import CreateIngestionJobRequest
        from services.ingestion_service import IngestionService
        import asyncio
        
        # Get tenant IDs from environment variable
        # Format: comma-separated UUIDs, e.g., "uuid1,uuid2,uuid3"
        tenant_ids_str = os.getenv("SCHEDULED_TENANT_IDS", "")
        if not tenant_ids_str:
            logging.warning("No SCHEDULED_TENANT_IDS configured, skipping scheduled ingestion")
            return
        
        tenant_ids = [t.strip() for t in tenant_ids_str.split(",") if t.strip()]
        
        today = date.today()
        two_days_ago = today - timedelta(days=2)
        jobs_created = 0
        
        for tenant_id in tenant_ids:
            job_id = f"scheduled_{uuid4().hex[:12]}"
            
            try:
                # Each tenant has their own database
                repo = create_repository(tenant_id)
                await repo.create_processing_job({
                    "job_id": job_id,
                    "tenant_id": tenant_id,
                    "status": "queued",
                    "data_types": ["events", "users", "locations"],
                    "start_date": two_days_ago,
                    "end_date": today,
                })
                jobs_created += 1
                logging.info(f"Created scheduled job {job_id} for tenant {tenant_id}")
                
                # Start processing immediately
                request = CreateIngestionJobRequest(
                    data_types=["events", "users", "locations"],
                    start_date=two_days_ago,
                    end_date=today
                )
                ingestion_service = IngestionService(tenant_id)
                asyncio.create_task(ingestion_service.run_job_safe(job_id, tenant_id, request))
                
            except Exception as e:
                logging.error(f"Failed to create/start job for tenant {tenant_id}: {e}")
        
        logging.info(f"Scheduled ingestion complete: {jobs_created} jobs created and started")
        
    except ImportError as e:
        logging.error(f"Database module not available: {e}")
    except Exception as e:
        logging.error(f"Error in scheduled ingestion: {e}")
