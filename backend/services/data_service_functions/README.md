# Data Service - Azure Functions

> **Runtime**: Azure Functions Python v2  
> **Plan**: Standard Consumption (Serverless)  
> **Trigger Types**: HTTP (health check), Queue Triggers (background jobs)

## Overview

Serverless background worker service that:
- Processes data ingestion jobs from Azure Storage Queues
- Extracts events from BigQuery and users/locations from SFTP
- Sends branch reports via SMTP email
- Uses async functions for all database operations
- Automatically scales based on queue depth

## Architecture

```
FastAPI Services (data_service, analytics_service)
    ↓ Create job record in DB
    ↓ Send message to Azure Storage Queue
    ↓
Azure Storage Queues (ingestion-jobs, email-jobs)
    ↓ Queue Trigger (automatic)
    ↓
Azure Functions (Queue-based Background Workers)
    ↓ Process job
    ↓ Update job status in DB
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | Health check - returns service status |

**Note**: Ingestion and email jobs are triggered via Azure Storage Queues, not HTTP endpoints. 
FastAPI services handle job creation and queue the work for background processing.

## Queue Triggers (Background Workers)

| Queue Name | Function | Description |
|------------|----------|-------------|
| `ingestion-jobs` | `process_ingestion_job` | Processes data ingestion from BigQuery & SFTP |
| `email-jobs` | `process_email_job` | Sends branch analytics reports via email |

## Project Structure

```
data_service_functions/
├── function_app.py           # 1 HTTP + 2 Queue Triggers
│   ├── health_check()              # HTTP: GET /api/v1/health
│   ├── process_ingestion_job()     # Queue: ingestion-jobs
│   └── process_email_job()         # Queue: email-jobs
├── clients/
│   ├── bigquery_client.py    # BigQuery client for event extraction
│   ├── sftp_client.py        # SFTP client for users/locations
│   └── tenant_client_factory.py
├── services/
│   ├── ingestion_service.py  # Data ingestion orchestration
│   ├── email_service.py      # Email job processing & SMTP
│   ├── report_service.py     # Analytics report generation
│   └── template_service.py   # Jinja2 HTML templating
├── shared/
│   ├── database.py           # PostgreSQL async sessions & repository
│   └── models.py             # Pydantic request/response models
├── templates/
│   └── branch_report.html    # Email report template
├── tests/
│   ├── test_ingestion.py     # Test ingestion via queue
│   └── test_email_sending.py # Test email via queue
├── host.json                 # Azure Functions config (queue settings)
├── requirements.txt          # Python dependencies
├── README.md                 # This file
└── DEPLOYMENT.md             # Deployment instructions
```

## Local Development

### Prerequisites

- Python 3.10
- Azure Functions Core Tools v4
- PostgreSQL database

### Setup

```bash
cd backend/services/data_service_functions
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### Configure Local Settings

Edit `local.settings.json`:
```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
    "POSTGRES_USER": "postgres",
    "POSTGRES_PASSWORD": "password",
    "POSTGRES_DATABASE": "analytics"
  }
}
```

### Run Locally

```bash
func start
```

## Deployment

### GitHub Actions (Automated)

Push to `feat/azure_functions` or `main` branch triggers deployment.

### Required App Settings

```bash
az functionapp config appsettings set \
  --name gadataingestion \
  --resource-group FreelanceProjects \
  --settings \
    POSTGRES_HOST=your-db-host \
    POSTGRES_PORT=5432 \
    POSTGRES_USER=your-user \
    POSTGRES_PASSWORD=your-password \
    AzureWebJobsStorage="<storage-connection-string>"
```

**Important**: `AzureWebJobsStorage` must point to the same Storage Account that contains the `ingestion-jobs` and `email-jobs` queues.

## Testing

### Health Check

```bash
curl https://gadataingestion.azurewebsites.net/api/v1/health
# Returns: {"status": "healthy", "version": "1.0.0", "service": "data-ingestion-email", ...}
```

### Data Ingestion (Queue-Based)

```bash
# Test ingestion by sending message to queue
cd backend
uv run python services/data_service_functions/tests/test_ingestion.py \
  --tenant-id "your-tenant-uuid" \
  --days 7

# This will:
# 1. Create job record in database (status: queued)
# 2. Send message to 'ingestion-jobs' queue
# 3. Azure Function picks up message and processes in background
# 4. Job status updates: queued → processing → completed

# Monitor job status in database:
# SELECT * FROM processing_jobs WHERE job_id = 'job_xyz123';
```

### Email Reports (Queue-Based)

```bash
# Test email reports by sending message to queue
cd backend
uv run python services/data_service_functions/tests/test_email_sending.py \
  --tenant-id "your-tenant-uuid" \
  --report-date "2025-01-15" \
  --branch-codes "D01,D02"

# This will:
# 1. Create email job record in database (status: queued)
# 2. Send message to 'email-jobs' queue
# 3. Azure Function picks up message and sends emails in background
# 4. Job status updates: queued → processing → completed

# Monitor job status in database:
# SELECT * FROM email_jobs WHERE job_id = 'email_abc456';
```

### Notes

- Jobs run **asynchronously** in the background (non-blocking)
- FastAPI services return immediately with `status: "queued"`
- Azure Functions auto-scale based on queue depth (up to 200 instances)
- Check job status in database (`processing_jobs` and `email_jobs` tables)
- Email mappings in `branch_email_mappings` table
- SMTP config in `tenant_config.smtp_credentials` JSONB field

## Configuration

### Azure Functions Settings (`host.json`)

| Setting | Value | Description |
|---------|-------|-------------|
| `functionTimeout` | 10 min | Max execution time per job |
| `routePrefix` | api/v1 | API route prefix for HTTP endpoints |
| `queues.maxPollingInterval` | 10s | Check for new messages every 10 seconds |
| `queues.visibilityTimeout` | 5 min | Time to process before retry |
| `queues.batchSize` | 1 | Process 1 message per instance |
| `queues.maxDequeueCount` | 3 | Retry failed jobs 3 times before poison |
| `queues.messageEncoding` | none | Plain text JSON messages (not base64) |

### Database Configuration

**Email Mappings:** Managed in `branch_email_mappings` table
```sql
-- Example: Create email mapping
INSERT INTO branch_email_mappings (tenant_id, branch_code, branch_name, sales_rep_email, sales_rep_name, is_enabled)
VALUES ('tenant-uuid', 'D01', 'Main Branch', 'manager@company.com', 'John Doe', true);
```

**SMTP Configuration:** Stored in `tenant_config.smtp_credentials` (JSONB)
```sql
-- Example: Configure SMTP
UPDATE tenant_config 
SET smtp_credentials = '{
  "server": "smtp.gmail.com",
  "port": 587,
  "username": "your-email@gmail.com",
  "password": "your-app-password",
  "from_address": "noreply@company.com",
  "use_tls": true,
  "use_ssl": false
}'::jsonb;
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `POSTGRES_HOST` | Yes | PostgreSQL host |
| `POSTGRES_PORT` | Yes | PostgreSQL port |
| `POSTGRES_USER` | Yes | PostgreSQL username |
| `POSTGRES_PASSWORD` | Yes | PostgreSQL password |
| `POSTGRES_DATABASE` | Yes | PostgreSQL database |

## Job Flow

### Ingestion Job (Queue-Based Background Processing)
```
1. FastAPI Service (data_service)
   POST /api/v1/ingest
    └── Creates job record (status: queued)
    └── Sends message to Azure Storage Queue: ingestion-jobs
    └── Returns immediately: {"job_id": "...", "status": "queued"}

2. Azure Function (Queue Trigger)
   process_ingestion_job() triggered automatically
    └── Receives message from queue
    └── Updates status to "processing"
    └── Extracts events from BigQuery
    └── Downloads users from SFTP
    └── Downloads locations from SFTP
    └── Updates status to "completed"/"failed"
    └── On failure: Message auto-retries (max 3 times)
    └── After 3 failures: Message moves to poison queue

Job record in DB includes:
- job_id: Unique identifier
- status: queued → processing → completed | failed
- records_processed: {"events": N, "users": N, "locations": N}
- error_message: (if applicable)
```

### Email Job (Queue-Based Background Processing)
```
1. FastAPI Service (analytics_service)
   POST /api/v1/email/send-reports
    └── Creates email job record (status: queued)
    └── Sends message to Azure Storage Queue: email-jobs
    └── Returns immediately: {"job_id": "...", "status": "queued"}

2. Azure Function (Queue Trigger)
   process_email_job() triggered automatically
    └── Receives message from queue
    └── Updates status to "processing"
    └── Gets SMTP config from database
    └── Gets branch-email mappings from database
    └── For each branch:
        └── Fetches analytics data
        └── Generates HTML report with Jinja2
        └── Sends email via SMTP
        └── Logs to email_send_history
    └── Updates status to "completed"/"failed"
    └── On failure: Message auto-retries (max 3 times)
    └── After 3 failures: Message moves to poison queue

Job record in DB includes:
- job_id: Unique identifier
- status: queued → processing → completed | failed
- total_emails: Number attempted
- emails_sent: Number successfully sent
- emails_failed: Number that failed
```

## Scaling & Performance

- **Auto-scaling**: Azure Functions scales 0 to 200 instances based on queue depth
- **Parallelism**: Multiple jobs process simultaneously on different instances
- **Cost**: Pay only for execution time (Consumption Plan)
- **Resilience**: Failed jobs auto-retry up to 3 times
- **Poison Queue**: Permanently failed messages move to `{queue-name}-poison` for investigation
