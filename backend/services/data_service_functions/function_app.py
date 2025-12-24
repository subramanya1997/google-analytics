"""
Azure Functions Data Service

Production serverless data ingestion and email service.
- Health check
- Data ingestion from BigQuery and SFTP
- Email reports with analytics
"""

import json
import logging
from datetime import datetime, date, timedelta
from uuid import uuid4

import azure.functions as func

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


# ============================================================================
# Helper Functions
# ============================================================================

def create_json_response(data: dict, status_code: int = 200) -> func.HttpResponse:
    """Create a JSON HTTP response."""
    return func.HttpResponse(
        json.dumps(data, default=str),
        status_code=status_code,
        mimetype="application/json"
    )


def create_error_response(status_code: int, message: str) -> func.HttpResponse:
    """Create an error HTTP response."""
    return func.HttpResponse(
        json.dumps({"error": message}),
        status_code=status_code,
        mimetype="application/json"
    )


def get_tenant_id(req: func.HttpRequest) -> str:
    """Extract and validate tenant ID from request headers."""
    tenant_id = req.headers.get("X-Tenant-Id")
    if not tenant_id:
        raise ValueError("X-Tenant-Id header is required")
    return tenant_id.strip()


# ============================================================================
# HTTP Triggers
# ============================================================================

@app.route(route="health", methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """
    Health check endpoint.
    
    Returns service status and version information.
    """
    return create_json_response({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "service": "data-ingestion-email"
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
        
        # Process the job directly (Azure Functions don't support background tasks)
        # The job will run synchronously and the response will be returned after completion
        # For large jobs, clients should expect longer response times (up to 10 minutes)
        ingestion_service = IngestionService(tenant_id)
        await ingestion_service.run_job_safe(job_id, tenant_id, request)
        
        # Get final job status
        final_job = await repo.get_job_by_id(job_id)
        final_status = final_job.get("status", "unknown") if final_job else "unknown"
        
        return create_json_response({
            "job_id": job_id,
            "tenant_id": tenant_id,
            "status": final_status,
            "data_types": request.data_types,
            "start_date": request.start_date.isoformat(),
            "end_date": request.end_date.isoformat(),
            "created_at": datetime.utcnow().isoformat(),
            "records_processed": final_job.get("records_processed", {}) if final_job else {},
            "message": f"Job {final_status}. Check /jobs/{job_id} for details."
        }, 200 if final_status == "completed" else 202)
        
    except ImportError as e:
        logging.error(f"Required module not available: {e}")
        return create_error_response(503, f"Service dependency unavailable: {str(e)}")
    except Exception as e:
        logging.error(f"Error creating/starting job: {e}")
        return create_error_response(500, f"Failed to create job: {str(e)}")



@app.route(route="email/send-reports", methods=["POST"])
async def send_reports(req: func.HttpRequest) -> func.HttpResponse:
    """
    Send branch reports via email.
    
    Creates an email job and processes it synchronously, sending reports to configured
    sales representatives for their branches.
    
    Note: Azure Functions Consumption plan doesn't reliably execute background tasks,
    so email processing is done synchronously. For large jobs, clients should expect
    longer response times (up to 10 minutes).
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
        
        logging.info(f"Created email job {job_id} for tenant {tenant_id}, starting processing...")
        
        # Process the job directly (Azure Functions don't support background tasks)
        # The job will run synchronously and the response will be returned after completion
        result = await email_service.process_email_job(
            tenant_id, job_id, request.report_date, request.branch_codes
        )
        
        # Get final status
        final_status = result.get("status", "unknown")
        
        return create_json_response({
            "job_id": job_id,
            "tenant_id": tenant_id,
            "status": final_status,
            "report_date": request.report_date.isoformat(),
            "target_branches": request.branch_codes or [],
            "total_emails": result.get("total_emails", 0),
            "emails_sent": result.get("emails_sent", 0),
            "emails_failed": result.get("emails_failed", 0),
            "message": f"Email job {final_status}. Check /email/jobs/{job_id} for details."
        }, 200 if final_status == "completed" else 202)
        
    except ImportError as e:
        logging.error(f"Required module not available: {e}")
        return create_error_response(503, f"Service dependency unavailable: {str(e)}")
    except Exception as e:
        logging.error(f"Error creating/processing email job: {e}")
        return create_error_response(500, f"Failed to process email job: {str(e)}")


