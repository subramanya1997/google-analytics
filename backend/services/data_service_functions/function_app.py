"""
Azure Functions Data Service

This is the main function app that defines all HTTP triggers and registers
Durable Functions orchestrators and activities.
"""

import json
import logging
from datetime import datetime
from uuid import uuid4

import azure.functions as func
import azure.durable_functions as df

from shared.database import create_repository, get_db_session
from shared.models import (
    CreateIngestionJobRequest,
    IngestionJobResponse,
    ScheduleRequest,
)

# Create the function app with Durable Functions support
app = df.DFApp(http_auth_level=func.AuthLevel.ANONYMOUS)


# ============================================================================
# Helper Functions
# ============================================================================

def get_tenant_id(req: func.HttpRequest) -> str:
    """Extract tenant ID from request headers."""
    tenant_id = req.headers.get("X-Tenant-Id")
    if not tenant_id:
        raise ValueError("X-Tenant-Id header is required")
    return tenant_id.strip()


def create_error_response(status_code: int, message: str) -> func.HttpResponse:
    """Create a standardized error response."""
    return func.HttpResponse(
        json.dumps({"error": message}),
        status_code=status_code,
        mimetype="application/json"
    )


def create_json_response(data: dict, status_code: int = 200) -> func.HttpResponse:
    """Create a standardized JSON response."""
    return func.HttpResponse(
        json.dumps(data, default=str),
        status_code=status_code,
        mimetype="application/json"
    )


# ============================================================================
# HTTP Trigger: Start Ingestion Job
# ============================================================================

@app.route(route="ingest", methods=["POST"])
@app.durable_client_input(client_name="client")
async def start_ingestion_job(req: func.HttpRequest, client: df.DurableOrchestrationClient) -> func.HttpResponse:
    """
    Start a new data ingestion job.
    
    This HTTP trigger validates the request, creates a job record, and starts
    the Durable Functions orchestrator for background processing.
    """
    try:
        # Get tenant ID from header
        try:
            tenant_id = get_tenant_id(req)
        except ValueError as e:
            return create_error_response(400, str(e))
        
        # Parse request body
        try:
            body = req.get_json() if req.get_body() else {}
        except ValueError:
            body = {}
        
        # Create request model with defaults
        request = CreateIngestionJobRequest(**body)
        
        # Check service status
        repo = create_repository()
        service_status = await repo.get_tenant_service_status(tenant_id)
        
        needs_bigquery = "events" in request.data_types
        needs_sftp = "users" in request.data_types or "locations" in request.data_types
        
        disabled_services = []
        if needs_bigquery and not service_status["bigquery"]["enabled"]:
            error_msg = service_status["bigquery"]["error"] or "BigQuery service is disabled"
            disabled_services.append(f"BigQuery: {error_msg}")
        
        if needs_sftp and not service_status["sftp"]["enabled"]:
            error_msg = service_status["sftp"]["error"] or "SFTP service is disabled"
            disabled_services.append(f"SFTP: {error_msg}")
        
        if disabled_services:
            error_detail = "Cannot process ingestion job. " + "; ".join(disabled_services)
            return create_error_response(400, error_detail)
        
        # Generate job ID
        job_id = f"job_{uuid4().hex[:12]}"
        
        # Create job record
        await repo.create_processing_job({
            "job_id": job_id,
            "tenant_id": tenant_id,
            "status": "queued",
            "data_types": request.data_types,
            "start_date": request.start_date,
            "end_date": request.end_date,
        })
        
        # Start the orchestrator
        orchestrator_input = {
            "job_id": job_id,
            "tenant_id": tenant_id,
            "start_date": request.start_date.isoformat(),
            "end_date": request.end_date.isoformat(),
            "data_types": request.data_types,
        }
        
        instance_id = await client.start_new("ingestion_orchestrator", client_input=orchestrator_input)
        
        logging.info(f"Started orchestration {instance_id} for job {job_id}")
        
        # Return immediate response
        response = IngestionJobResponse(
            job_id=job_id,
            start_date=request.start_date,
            end_date=request.end_date,
            data_types=request.data_types,
            status="queued",
            created_at=datetime.now(),
        )
        
        return create_json_response(response.to_dict(), 202)
        
    except Exception as e:
        logging.error(f"Error creating ingestion job: {e}")
        return create_error_response(500, str(e))


# ============================================================================
# HTTP Trigger: Get Data Availability
# ============================================================================

@app.route(route="data-availability", methods=["GET"])
async def get_data_availability(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get the date range of available data for the tenant.
    """
    try:
        tenant_id = get_tenant_id(req)
    except ValueError as e:
        return create_error_response(400, str(e))
    
    try:
        repo = create_repository()
        data = await repo.get_data_availability_with_breakdown(tenant_id)
        return create_json_response(data)
    except Exception as e:
        logging.error(f"Error getting data availability: {e}")
        return create_error_response(500, str(e))


# ============================================================================
# HTTP Trigger: List Jobs
# ============================================================================

@app.route(route="jobs", methods=["GET"])
async def list_jobs(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get ingestion job history for the tenant.
    """
    try:
        tenant_id = get_tenant_id(req)
    except ValueError as e:
        return create_error_response(400, str(e))
    
    try:
        limit = int(req.params.get("limit", 50))
        offset = int(req.params.get("offset", 0))
        
        # Clamp values
        limit = min(limit, 100)
        offset = max(offset, 0)
        
        repo = create_repository()
        jobs_data = await repo.get_tenant_jobs(tenant_id, limit, offset)
        
        return create_json_response({
            "jobs": jobs_data.get("jobs", []),
            "total": jobs_data.get("total", 0),
            "limit": limit,
            "offset": offset
        })
    except Exception as e:
        logging.error(f"Error getting ingestion jobs: {e}")
        return create_error_response(500, str(e))


# ============================================================================
# HTTP Trigger: Get Job Status
# ============================================================================

@app.route(route="jobs/{job_id}", methods=["GET"])
async def get_job_status(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get specific ingestion job details.
    """
    try:
        tenant_id = get_tenant_id(req)
    except ValueError as e:
        return create_error_response(400, str(e))
    
    job_id = req.route_params.get("job_id")
    if not job_id:
        return create_error_response(400, "job_id is required")
    
    try:
        repo = create_repository()
        job = await repo.get_job_by_id(job_id)
        
        if not job:
            return create_error_response(404, "Job not found")
        
        # Security check: verify job belongs to tenant
        if job.get("tenant_id") != tenant_id:
            return create_error_response(404, "Job not found")
        
        return create_json_response(job)
    except Exception as e:
        logging.error(f"Error getting job {job_id}: {e}")
        return create_error_response(500, str(e))


# ============================================================================
# HTTP Trigger: Schedule Management
# ============================================================================

@app.route(route="data/schedule", methods=["POST"])
async def upsert_schedule(req: func.HttpRequest) -> func.HttpResponse:
    """
    Create or update the data ingestion schedule for the tenant.
    """
    try:
        tenant_id = get_tenant_id(req)
    except ValueError as e:
        return create_error_response(400, str(e))
    
    # Get authorization header
    authorization = req.headers.get("Authorization")
    if not authorization:
        return create_error_response(401, "Authorization header is required")
    
    try:
        body = req.get_json() if req.get_body() else {}
    except ValueError:
        body = {}
    
    try:
        import os
        from shared.database import get_db_session
        from sqlalchemy import text
        
        # Get settings
        default_cron = os.getenv("DATA_INGESTION_CRON", "0 2 * * *")
        scheduler_url = os.getenv("SCHEDULER_API_URL", "http://localhost:8080")
        
        cron_exp = body.get("cron_expression") or default_cron
        schedule_status = body.get("status") or "active"
        
        auth_token = authorization.replace("Bearer ", "")
        job_name = f"data_{tenant_id}"
        app_name = "google_analytics"
        
        # Note: In production, you would call the external scheduler API here
        # For now, just update the database
        
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
            "message": "Schedule updated successfully",
            "cron_expression": cron_exp,
            "status": schedule_status
        })
        
    except Exception as e:
        logging.error(f"Error upserting schedule for tenant {tenant_id}: {e}")
        return create_error_response(500, str(e))


@app.route(route="data/schedule", methods=["GET"])
async def get_schedule(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get the data ingestion schedule details for the tenant.
    """
    try:
        tenant_id = get_tenant_id(req)
    except ValueError as e:
        return create_error_response(400, str(e))
    
    authorization = req.headers.get("Authorization")
    if not authorization:
        return create_error_response(401, "Authorization header is required")
    
    try:
        import os
        from shared.database import get_db_session
        from sqlalchemy import text
        
        default_cron = os.getenv("DATA_INGESTION_CRON", "0 2 * * *")
        
        # Query schedule from database
        async with get_db_session() as session:
            result = await session.execute(
                text("SELECT data_ingestion_schedule FROM tenants WHERE id = :tenant_id"),
                {"tenant_id": tenant_id}
            )
            row = result.mappings().first()
        
        if row and row.get("data_ingestion_schedule"):
            return create_json_response({
                "cron_expression": row["data_ingestion_schedule"],
                "status": "active",
                "source": "database"
            })
        
        return create_json_response({
            "cron_expression": default_cron,
            "status": "inactive",
            "source": "default"
        })
        
    except Exception as e:
        logging.error(f"Error getting schedule for tenant {tenant_id}: {e}")
        return create_error_response(500, str(e))


# ============================================================================
# Durable Functions Orchestrator
# ============================================================================

@app.orchestration_trigger(context_name="context")
def ingestion_orchestrator(context: df.DurableOrchestrationContext):
    """
    Orchestrator function for data ingestion jobs.
    
    Coordinates the processing of events, users, and locations data
    using a fan-out/fan-in pattern for parallel execution.
    """
    # Get input
    input_data = context.get_input()
    job_id = input_data["job_id"]
    tenant_id = input_data["tenant_id"]
    start_date = input_data["start_date"]
    end_date = input_data["end_date"]
    data_types = input_data["data_types"]
    
    results = {
        "purchase": 0,
        "add_to_cart": 0,
        "page_view": 0,
        "view_search_results": 0,
        "no_search_results": 0,
        "view_item": 0,
        "users_processed": 0,
        "locations_processed": 0,
    }
    
    try:
        # Update job status to processing
        yield context.call_activity("update_job_status_activity", {
            "job_id": job_id,
            "status": "processing",
            "started_at": context.current_utc_datetime.isoformat()
        })
        
        # Create parallel tasks for each data type
        tasks = []
        
        if "events" in data_types:
            # Fan-out: process all 6 event types in parallel
            event_types = ["purchase", "add_to_cart", "page_view", 
                          "view_search_results", "no_search_results", "view_item"]
            for event_type in event_types:
                task = context.call_activity("process_events_activity", {
                    "job_id": job_id,
                    "tenant_id": tenant_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "event_type": event_type
                })
                tasks.append((event_type, task))
        
        if "users" in data_types:
            task = context.call_activity("process_users_activity", {
                "job_id": job_id,
                "tenant_id": tenant_id
            })
            tasks.append(("users_processed", task))
        
        if "locations" in data_types:
            task = context.call_activity("process_locations_activity", {
                "job_id": job_id,
                "tenant_id": tenant_id
            })
            tasks.append(("locations_processed", task))
        
        # Fan-in: wait for all tasks to complete
        for key, task in tasks:
            try:
                count = yield task
                results[key] = count or 0
            except Exception as e:
                logging.error(f"Activity {key} failed: {e}")
                results[key] = 0
        
        # Update job status to completed
        yield context.call_activity("update_job_status_activity", {
            "job_id": job_id,
            "status": "completed",
            "completed_at": context.current_utc_datetime.isoformat(),
            "records_processed": results
        })
        
        return results
        
    except Exception as e:
        # Update job status to failed
        yield context.call_activity("update_job_status_activity", {
            "job_id": job_id,
            "status": "failed",
            "completed_at": context.current_utc_datetime.isoformat(),
            "error_message": str(e)
        })
        raise


# ============================================================================
# Activity Functions
# ============================================================================

@app.activity_trigger(input_name="input")
async def update_job_status_activity(input: dict) -> bool:
    """Activity to update job status in the database."""
    from shared.database import create_repository
    from datetime import datetime
    
    repo = create_repository()
    
    kwargs = {}
    if input.get("started_at"):
        kwargs["started_at"] = datetime.fromisoformat(input["started_at"])
    if input.get("completed_at"):
        kwargs["completed_at"] = datetime.fromisoformat(input["completed_at"])
    if input.get("error_message"):
        kwargs["error_message"] = input["error_message"]
    if input.get("records_processed"):
        kwargs["records_processed"] = input["records_processed"]
    if input.get("progress"):
        kwargs["progress"] = input["progress"]
    
    return await repo.update_job_status(input["job_id"], input["status"], **kwargs)


@app.activity_trigger(input_name="input")
async def process_events_activity(input: dict) -> int:
    """
    Activity to process events from BigQuery for a specific event type.
    """
    from clients import get_tenant_bigquery_client
    from shared.database import create_repository
    from datetime import date
    
    job_id = input["job_id"]
    tenant_id = input["tenant_id"]
    start_date = date.fromisoformat(input["start_date"])
    end_date = date.fromisoformat(input["end_date"])
    event_type = input["event_type"]
    
    logging.info(f"Processing {event_type} events for job {job_id}")
    
    try:
        # Get BigQuery client
        bigquery_client = await get_tenant_bigquery_client(tenant_id)
        if not bigquery_client:
            raise ValueError(f"BigQuery configuration not found for tenant {tenant_id}")
        
        # Extract events (uses sync method - no thread pool in serverless)
        extractor_map = {
            "purchase": bigquery_client._extract_purchase_events,
            "add_to_cart": bigquery_client._extract_add_to_cart_events,
            "page_view": bigquery_client._extract_page_view_events,
            "view_search_results": bigquery_client._extract_view_search_results_events,
            "no_search_results": bigquery_client._extract_no_search_results_events,
            "view_item": bigquery_client._extract_view_item_events,
        }
        
        extractor = extractor_map.get(event_type)
        if not extractor:
            raise ValueError(f"Unknown event type: {event_type}")
        
        events_data = extractor(input["start_date"], input["end_date"])
        
        if events_data:
            repo = create_repository()
            count = await repo.replace_event_data(
                tenant_id, event_type, start_date, end_date, events_data
            )
            logging.info(f"Processed {count} {event_type} events")
            return count
        
        return 0
        
    except Exception as e:
        logging.error(f"Error processing {event_type} events: {e}")
        raise


@app.activity_trigger(input_name="input")
async def process_users_activity(input: dict) -> int:
    """
    Activity to process users from SFTP.
    """
    from clients import get_tenant_sftp_client
    from shared.database import create_repository
    import pandas as pd
    import numpy as np
    
    job_id = input["job_id"]
    tenant_id = input["tenant_id"]
    
    logging.info(f"Processing users for job {job_id}")
    
    try:
        sftp_client = await get_tenant_sftp_client(tenant_id)
        if not sftp_client:
            logging.warning(f"SFTP not configured for tenant {tenant_id}")
            return 0
        
        # Get users data (sync method wrapped)
        users_data = sftp_client._get_users_data_sync()
        
        if users_data is not None and len(users_data) > 0:
            # Clean data
            users_data = users_data.replace({np.nan: None})
            users_list = users_data.to_dict("records")
            
            # Clean records
            cleaned_users = []
            for record in users_list:
                cleaned_record = {}
                for key, value in record.items():
                    if pd.isna(value) if hasattr(pd, "isna") else (value is None or str(value) == "nan"):
                        cleaned_record[key] = None
                    elif isinstance(value, pd.Timestamp):
                        cleaned_record[key] = value.to_pydatetime()
                    else:
                        cleaned_record[key] = value
                cleaned_users.append(cleaned_record)
            
            repo = create_repository()
            count = await repo.upsert_users(tenant_id, cleaned_users)
            logging.info(f"Processed {count} users")
            return count
        
        return 0
        
    except Exception as e:
        logging.error(f"Error processing users: {e}")
        raise


@app.activity_trigger(input_name="input")
async def process_locations_activity(input: dict) -> int:
    """
    Activity to process locations from SFTP.
    """
    from clients import get_tenant_sftp_client
    from shared.database import create_repository
    import pandas as pd
    import numpy as np
    
    job_id = input["job_id"]
    tenant_id = input["tenant_id"]
    
    logging.info(f"Processing locations for job {job_id}")
    
    try:
        sftp_client = await get_tenant_sftp_client(tenant_id)
        if not sftp_client:
            logging.warning(f"SFTP not configured for tenant {tenant_id}")
            return 0
        
        # Get locations data (sync method wrapped)
        locations_data = sftp_client._get_locations_data_sync()
        
        if locations_data is not None and len(locations_data) > 0:
            # Clean data
            locations_data = locations_data.replace({np.nan: None})
            locations_list = locations_data.to_dict("records")
            
            # Clean records
            cleaned_locations = []
            for record in locations_list:
                cleaned_record = {}
                for key, value in record.items():
                    if pd.isna(value) if hasattr(pd, "isna") else (value is None or str(value) == "nan"):
                        cleaned_record[key] = None
                    elif isinstance(value, pd.Timestamp):
                        cleaned_record[key] = value.to_pydatetime()
                    else:
                        cleaned_record[key] = value
                cleaned_locations.append(cleaned_record)
            
            repo = create_repository()
            count = await repo.upsert_locations(tenant_id, cleaned_locations)
            logging.info(f"Processed {count} locations")
            return count
        
        return 0
        
    except Exception as e:
        logging.error(f"Error processing locations: {e}")
        raise


# ============================================================================
# Timer Trigger: Scheduled Ingestion
# ============================================================================

@app.timer_trigger(schedule="0 0 2 * * *", arg_name="timer", run_on_startup=False)
@app.durable_client_input(client_name="client")
async def scheduled_ingestion(timer: func.TimerRequest, client: df.DurableOrchestrationClient) -> None:
    """
    Timer trigger for scheduled data ingestion.
    
    Runs daily at 2 AM UTC to process ingestion for all active tenants.
    """
    from shared.database import get_db_session
    from sqlalchemy import text
    from datetime import date, timedelta
    
    logging.info("Starting scheduled ingestion run")
    
    try:
        # Get all tenants with active schedules
        async with get_db_session() as session:
            result = await session.execute(
                text("""
                    SELECT id, data_ingestion_schedule
                    FROM tenants
                    WHERE data_ingestion_schedule IS NOT NULL
                """)
            )
            tenants = result.mappings().all()
        
        today = date.today()
        two_days_ago = today - timedelta(days=2)
        
        for tenant in tenants:
            tenant_id = str(tenant["id"])
            
            try:
                # Generate job ID
                job_id = f"scheduled_job_{uuid4().hex[:12]}"
                
                # Create job record
                repo = create_repository()
                await repo.create_processing_job({
                    "job_id": job_id,
                    "tenant_id": tenant_id,
                    "status": "queued",
                    "data_types": ["events", "users", "locations"],
                    "start_date": two_days_ago,
                    "end_date": today,
                })
                
                # Start orchestrator
                orchestrator_input = {
                    "job_id": job_id,
                    "tenant_id": tenant_id,
                    "start_date": two_days_ago.isoformat(),
                    "end_date": today.isoformat(),
                    "data_types": ["events", "users", "locations"],
                }
                
                instance_id = await client.start_new("ingestion_orchestrator", client_input=orchestrator_input)
                logging.info(f"Started scheduled ingestion {instance_id} for tenant {tenant_id}")
                
            except Exception as e:
                logging.error(f"Failed to start scheduled ingestion for tenant {tenant_id}: {e}")
        
        logging.info(f"Scheduled ingestion: processed {len(tenants)} tenants")
        
    except Exception as e:
        logging.error(f"Error in scheduled ingestion: {e}")

