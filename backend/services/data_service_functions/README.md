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

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/health` | GET | Health check - returns service status |
| `/api/v1/ingest` | POST | Data ingestion from BigQuery & SFTP (synchronous) |
| `/api/v1/email/send-reports` | POST | Send branch analytics reports via email (synchronous) |

## Project Structure

```
data_service_functions/
├── function_app.py           # 3 HTTP functions (health, ingest, email)
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
│   ├── test_ingestion.py     # Test data ingestion
│   └── test_email_sending.py # Test email reports
├── host.json                 # Azure Functions configuration
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
    POSTGRES_DATABASE=analytics
```

## Testing

### Health Check

```bash
curl https://gadataingestion.azurewebsites.net/api/v1/health
# Returns: {"status": "healthy", "version": "1.0.0", "service": "data-ingestion-email", ...}
```

### Data Ingestion

```bash
# Start ingestion job (runs synchronously - returns when complete)
curl -X POST https://gadataingestion.azurewebsites.net/api/v1/ingest \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Id: your-tenant-uuid" \
  -d '{
    "data_types": ["events", "users", "locations"],
    "start_date": "2025-01-01",
    "end_date": "2025-01-15"
  }'
# Returns: {
#   "job_id": "job_xyz123",
#   "status": "completed",
#   "records_processed": {"events": 1000, "users": 50, "locations": 10},
#   ...
# }

# Test with Python script
python tests/test_ingestion.py \
  --tenant-id "your-tenant-uuid" \
  --days 7 \
  --base-url "https://gadataingestion.azurewebsites.net"
```

### Email Reports

```bash
# Send branch reports (runs synchronously - returns when complete)
curl -X POST https://gadataingestion.azurewebsites.net/api/v1/email/send-reports \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Id: your-tenant-uuid" \
  -d '{
    "report_date": "2025-01-15",
    "branch_codes": ["D01", "D02"]
  }'
# Returns: {
#   "job_id": "email_abc456",
#   "status": "completed",
#   "emails_sent": 2,
#   "emails_failed": 0,
#   ...
# }

# Test with Python script
python tests/test_email_sending.py \
  --tenant-id "your-tenant-uuid" \
  --report-date "2025-01-15" \
  --branch-codes "D01,D02" \
  --base-url "https://gadataingestion.azurewebsites.net/api/v1"
```

### Notes

- Both ingestion and email endpoints run **synchronously**
- Response times: 30 seconds to 10 minutes depending on data volume
- Email mappings managed directly in database (`branch_email_mappings` table)
- SMTP configuration in database (`tenant_config.smtp_credentials` JSONB field)

## Configuration

### Azure Functions Settings

| Setting | Value | Description |
|---------|-------|-------------|
| `functionTimeout` | 10 min | Max execution time (both endpoints are synchronous) |
| `routePrefix` | api/v1 | API route prefix for all endpoints |

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

### Ingestion Job (Synchronous)
```
POST /ingest
    └── Creates job record (status: queued)
    └── Updates status to "processing"
    └── Extracts events from BigQuery
    └── Downloads users from SFTP
    └── Downloads locations from SFTP
    └── Updates status to "completed"/"failed"/"completed_with_warnings"
    └── Returns final status with records processed

Response includes:
- job_id: Unique identifier
- status: completed | failed | completed_with_warnings
- records_processed: {"events": N, "users": N, "locations": N}
- error_message: (if applicable)
```

### Email Job (Synchronous)
```
POST /email/send-reports
    └── Creates email job record
    └── Gets SMTP config from database
    └── Gets branch-email mappings from database
    └── For each branch:
        └── Fetches analytics data (purchases, carts, searches, visits)
        └── Generates HTML report with Jinja2 template
        └── Sends email via SMTP
        └── Logs result to email_send_history
    └── Updates job status to "completed"/"failed"/"completed_with_errors"
    └── Returns final status with email counts

Response includes:
- job_id: Unique identifier
- status: completed | failed | completed_with_errors
- total_emails: Number of emails attempted
- emails_sent: Number successfully sent
- emails_failed: Number that failed
```
