"""
Azure Functions Data Service

Production serverless data ingestion and email service.
- Health check
- Data ingestion from BigQuery and SFTP
- Email reports with analytics
"""

from datetime import date, datetime
import json
import logging

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
        mimetype="application/json",
    )


def create_error_response(status_code: int, message: str) -> func.HttpResponse:
    """Create an error HTTP response."""
    return func.HttpResponse(
        json.dumps({"error": message}),
        status_code=status_code,
        mimetype="application/json",
    )


def get_tenant_id(req: func.HttpRequest) -> str:
    """Extract and validate tenant ID from request headers."""
    tenant_id = req.headers.get("X-Tenant-Id")
    if not tenant_id:
        msg = "X-Tenant-Id header is required"
        raise ValueError(msg)
    return tenant_id.strip()


# ============================================================================
# HTTP Triggers
# ============================================================================


@app.route(route="health", methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """
    Health check endpoint.

    Returns service status and version information.

    Note: This is the only HTTP endpoint. All job processing is triggered
    via Azure Queue messages sent from FastAPI services.
    """
    return create_json_response(
        {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "service": "data-ingestion-email-worker",
            "mode": "queue-based background processing",
        }
    )


# ============================================================================
# Queue Triggers - Background Processing
# ============================================================================


@app.queue_trigger(
    arg_name="msg", queue_name="ingestion-jobs", connection="AzureWebJobsStorage"
)
async def process_ingestion_job(msg: func.QueueMessage) -> None:
    """
    Queue trigger to process data ingestion jobs.

    This function is triggered when a message is added to the ingestion-jobs queue.
    It processes the job asynchronously and updates the job status in the database.
    """
    try:
        # Parse queue message
        message_body = json.loads(msg.get_body().decode("utf-8"))
        job_id = message_body["job_id"]
        tenant_id = message_body["tenant_id"]
        start_date = date.fromisoformat(message_body["start_date"])
        end_date = date.fromisoformat(message_body["end_date"])
        data_types = message_body["data_types"]

        logging.info(
            f"Processing ingestion job {job_id} for tenant {tenant_id} from queue"
        )

        from shared.models import CreateIngestionJobRequest

        from services.ingestion_service import IngestionService

        # Create request object
        request = CreateIngestionJobRequest(
            start_date=start_date, end_date=end_date, data_types=data_types
        )

        # Process the job
        ingestion_service = IngestionService(tenant_id)
        await ingestion_service.run_job_safe(job_id, tenant_id, request)

        logging.info(f"Successfully processed ingestion job {job_id}")

    except Exception as e:
        logging.exception(f"Error processing ingestion job from queue: {e}")
        # Azure Queue will automatically retry the message


@app.queue_trigger(
    arg_name="msg", queue_name="email-jobs", connection="AzureWebJobsStorage"
)
async def process_email_job(msg: func.QueueMessage) -> None:
    """
    Queue trigger to process email sending jobs.

    This function is triggered when a message is added to the email-jobs queue.
    It processes the job asynchronously and sends emails to configured recipients.
    """
    try:
        # Parse queue message
        message_body = json.loads(msg.get_body().decode("utf-8"))
        job_id = message_body["job_id"]
        tenant_id = message_body["tenant_id"]
        report_date = date.fromisoformat(message_body["report_date"])
        branch_codes = message_body.get("branch_codes")

        logging.info(f"Processing email job {job_id} for tenant {tenant_id} from queue")

        from services.email_service import EmailService

        # Process the email job
        email_service = EmailService(tenant_id)
        result = await email_service.process_email_job(
            tenant_id, job_id, report_date, branch_codes
        )

        logging.info(
            f"Successfully processed email job {job_id}: {result.get('emails_sent', 0)} emails sent"
        )

    except Exception as e:
        logging.exception(f"Error processing email job from queue: {e}")
        # Azure Queue will automatically retry the message
