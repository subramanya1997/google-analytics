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
    """
    Create a JSON HTTP response with proper serialization.

    This helper function serializes Python dictionaries to JSON format,
    handling date/datetime objects and other non-serializable types.

    Args:
        data: Dictionary containing response data to serialize.
        status_code: HTTP status code for the response. Defaults to 200.

    Returns:
        HttpResponse: Azure Functions HTTP response object with JSON content.

    Example:
        >>> response = create_json_response({"status": "ok", "data": {...}})
        >>> response.status_code
        200
    """
    return func.HttpResponse(
        json.dumps(data, default=str),
        status_code=status_code,
        mimetype="application/json",
    )


# ============================================================================
# HTTP Triggers
# ============================================================================


@app.route(route="health", methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """
    Health check endpoint for service monitoring and load balancer health probes.

    Returns service status, version information, and operational mode.
    This endpoint is used by Azure's health check system and external monitoring
    tools to verify the service is running and responsive.

    Note:
        This is the only HTTP endpoint exposed by the Azure Functions app.
        All job processing is triggered via Azure Queue messages sent from
        FastAPI services for better scalability and reliability.

    Args:
        req: Azure Functions HTTP request object (unused but required by decorator).

    Returns:
        HttpResponse: JSON response containing:
            - status: Service health status ("healthy")
            - timestamp: Current UTC timestamp in ISO format
            - version: Service version string
            - service: Service identifier name
            - mode: Operational mode description

    Example:
        >>> GET /api/health
        {
            "status": "healthy",
            "timestamp": "2024-01-15T10:30:00.123456",
            "version": "1.0.0",
            "service": "data-ingestion-email-worker",
            "mode": "queue-based background processing"
        }
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
    Queue trigger function to process data ingestion jobs asynchronously.

    This Azure Queue trigger function is automatically invoked when a message
    is added to the "ingestion-jobs" queue. It handles the complete ingestion
    workflow including BigQuery event extraction, SFTP user/location downloads,
    and database updates.

    The function processes jobs in a fire-and-forget manner, updating job status
    in the database throughout execution. Failures are logged and the queue
    message will be retried automatically by Azure Queue service.

    Args:
        msg: Azure Queue message containing job details in JSON format.
            Expected format:
            {
                "job_id": str,
                "tenant_id": str,
                "start_date": str (ISO date format),
                "end_date": str (ISO date format),
                "data_types": list[str] (e.g., ["events", "users", "locations"])
            }

    Returns:
        None: Function completes asynchronously. Results are persisted to database.

    Raises:
        Exception: Any unhandled exceptions are caught, logged, and the queue
                  message will be retried according to Azure Queue retry policy.

    Note:
        - Job status is updated to "processing" when started
        - Job status is updated to "completed" or "failed" when finished
        - Azure Queue automatically retries failed messages
        - Each tenant has isolated database access for SOC2 compliance

    Example:
        Queue message payload:
        {
            "job_id": "ingestion_abc123",
            "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
            "start_date": "2024-01-01",
            "end_date": "2024-01-07",
            "data_types": ["events", "users"]
        }
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
    Queue trigger function to process email sending jobs asynchronously.

    This Azure Queue trigger function is automatically invoked when a message
    is added to the "email-jobs" queue. It handles the complete email workflow
    including report generation, HTML template rendering, and SMTP delivery
    to configured branch sales representatives.

    The function processes email jobs for one or more branches, generating
    personalized analytics reports and sending them via SMTP. Each email
    send is logged to the database for audit purposes.

    Args:
        msg: Azure Queue message containing email job details in JSON format.
            Expected format:
            {
                "job_id": str,
                "tenant_id": str,
                "report_date": str (ISO date format),
                "branch_codes": list[str] | None (None = all branches)
            }

    Returns:
        None: Function completes asynchronously. Results are persisted to database.

    Raises:
        Exception: Any unhandled exceptions are caught, logged, and the queue
                  message will be retried according to Azure Queue retry policy.

    Note:
        - Email job status is updated throughout execution
        - Individual email failures are logged but don't fail the entire job
        - Job status can be "completed", "completed_with_errors", or "failed"
        - Each tenant has isolated SMTP configuration and email mappings
        - Email send history is logged for compliance and debugging

    Example:
        Queue message payload:
        {
            "job_id": "email_xyz789",
            "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
            "report_date": "2024-01-14",
            "branch_codes": ["BR001", "BR002"]  # or null for all branches
        }
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
