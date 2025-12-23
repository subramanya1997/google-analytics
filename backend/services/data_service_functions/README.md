# Data Service - Azure Functions

> **Runtime**: Azure Functions Python v2  
> **Plan**: Standard Consumption (Serverless)  
> **Trigger Types**: HTTP, Timer

## Overview

Serverless data ingestion and email service that:
- Processes events from BigQuery and users/locations from SFTP
- Sends branch reports via SMTP email
- Uses async functions for all database operations

## API Endpoints

### Data Ingestion

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | Health check |
| `/api/v1/ingest` | POST | Start new ingestion job (creates + processes automatically) |
| `/api/v1/jobs` | GET | List job history |
| `/api/v1/jobs/{job_id}` | GET | Get job status |
| `/api/v1/data-availability` | GET | Get data availability summary |
| `/api/v1/data/schedule` | GET | Get ingestion schedule |
| `/api/v1/data/schedule` | POST | Update ingestion schedule |

### Email

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/email/send-reports` | POST | Send branch reports via email |
| `/api/v1/email/jobs/{job_id}` | GET | Get email job status |
| `/api/v1/email/mappings` | GET | List branch email mappings |
| `/api/v1/email/mappings` | POST | Create branch email mapping |

## Project Structure

```
data_service_functions/
├── function_app.py           # Main function app with all triggers
├── clients/
│   ├── bigquery_client.py    # BigQuery client
│   ├── sftp_client.py        # SFTP client
│   └── tenant_client_factory.py
├── services/
│   ├── ingestion_service.py  # Data ingestion logic
│   └── email_service.py      # Email sending logic
├── shared/
│   ├── database.py           # Database sessions & repository
│   └── models.py             # Pydantic request/response models
├── host.json                 # Function host configuration
├── requirements.txt          # Python dependencies
└── README.md
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
    POSTGRES_DATABASE=analytics
```

## Testing

### Data Ingestion

```bash
# Health check
curl https://gadataingestion.azurewebsites.net/api/v1/health

# Start ingestion job (processes automatically)
curl -X POST https://gadataingestion.azurewebsites.net/api/v1/ingest \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Id: your-tenant-uuid" \
  -d '{"data_types": ["events"], "start_date": "2024-01-01", "end_date": "2024-01-15"}'
# Returns: {"job_id": "job_xyz123", "status": "processing", ...}

# Check job status
curl https://gadataingestion.azurewebsites.net/api/v1/jobs/job_xyz123 \
  -H "X-Tenant-Id: your-tenant-uuid"
# Returns: {"job_id": "job_xyz123", "status": "completed", "records_processed": {...}}

# List all jobs
curl https://gadataingestion.azurewebsites.net/api/v1/jobs \
  -H "X-Tenant-Id: your-tenant-uuid"
```

### Email

```bash
# Send branch reports
curl -X POST https://gadataingestion.azurewebsites.net/api/v1/email/send-reports \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Id: your-tenant-uuid" \
  -d '{"report_date": "2024-01-15", "branch_codes": ["BR001", "BR002"]}'
# Returns: {"job_id": "email_abc456", "status": "processing", ...}

# Check email job status
curl https://gadataingestion.azurewebsites.net/api/v1/email/jobs/email_abc456 \
  -H "X-Tenant-Id: your-tenant-uuid"
# Returns: {"job_id": "email_abc456", "status": "completed", "emails_sent": 5, ...}

# List email mappings
curl https://gadataingestion.azurewebsites.net/api/v1/email/mappings \
  -H "X-Tenant-Id: your-tenant-uuid"

# Create email mapping
curl -X POST https://gadataingestion.azurewebsites.net/api/v1/email/mappings \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Id: your-tenant-uuid" \
  -d '{"branch_code": "BR001", "sales_rep_email": "john@example.com", "sales_rep_name": "John Doe"}'
```

## Configuration

| Setting | Value | Description |
|---------|-------|-------------|
| `functionTimeout` | 10 min | Max execution time |
| `routePrefix` | api/v1 | API route prefix |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `POSTGRES_HOST` | Yes | PostgreSQL host |
| `POSTGRES_PORT` | Yes | PostgreSQL port |
| `POSTGRES_USER` | Yes | PostgreSQL username |
| `POSTGRES_PASSWORD` | Yes | PostgreSQL password |
| `POSTGRES_DATABASE` | Yes | PostgreSQL database |

## Job Flow

### Ingestion Job
```
POST /ingest
    └── Creates job record (status: queued)
    └── Starts background processing
    └── Returns immediately (status: processing)
    
Background Task:
    └── Updates status to "processing"
    └── Extracts events from BigQuery
    └── Downloads users from SFTP
    └── Downloads locations from SFTP
    └── Updates status to "completed" (or "failed")

Client polls GET /jobs/{job_id} until completed
```

### Email Job
```
POST /email/send-reports
    └── Creates email job record
    └── Starts background processing
    └── Returns immediately (status: processing)
    
Background Task:
    └── Gets SMTP config from database
    └── Gets branch-email mappings
    └── Generates branch reports
    └── Sends emails via SMTP
    └── Logs results to email_send_history
    └── Updates status to "completed" (or "failed")

Client polls GET /email/jobs/{job_id} until completed
```
