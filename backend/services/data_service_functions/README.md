# Data Service - Azure Functions

> **Runtime**: Azure Functions Python v2  
> **Trigger Types**: HTTP, Durable Functions, Timer

## Overview

This is the Azure Functions implementation of the data ingestion service. It replaces the FastAPI-based service with serverless functions that handle data ingestion from BigQuery and SFTP sources.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         HTTP Triggers                                │
│  POST /ingest  │  GET /jobs  │  GET /data-availability  │  etc.    │
└────────┬────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Durable Functions Orchestrator                    │
│                                                                      │
│  ┌──────────────┐                                                   │
│  │ Job Started  │                                                   │
│  └──────┬───────┘                                                   │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              Fan-out: Parallel Activities                     │  │
│  │                                                               │  │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐ │  │
│  │  │   Events    │ │   Users     │ │       Locations         │ │  │
│  │  │  (6 types)  │ │   (SFTP)    │ │        (SFTP)           │ │  │
│  │  └─────────────┘ └─────────────┘ └─────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────┐                                                   │
│  │Job Completed │                                                   │
│  └──────────────┘                                                   │
└─────────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
data_service_functions/
├── function_app.py           # Main function app (all triggers)
├── orchestrators/
│   └── ingestion_orchestrator.py
├── activities/
│   ├── process_events.py     # BigQuery event extraction
│   ├── process_users.py      # SFTP user processing
│   ├── process_locations.py  # SFTP location processing
│   └── job_management.py     # Job status updates
├── clients/
│   ├── bigquery_client.py    # BigQuery client (no thread pool)
│   ├── sftp_client.py        # SFTP client (sync methods)
│   └── tenant_client_factory.py
├── shared/
│   ├── database.py           # Per-request database sessions
│   └── models.py             # Pydantic models
├── tests/
│   ├── conftest.py           # Pytest fixtures
│   ├── test_http_triggers.py
│   └── test_activities.py
├── host.json                 # Function host configuration
├── local.settings.json       # Local environment settings
├── requirements.txt          # Python dependencies
└── README.md
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/ingest` | POST | Start new ingestion job |
| `/api/v1/jobs` | GET | List job history |
| `/api/v1/jobs/{job_id}` | GET | Get job status |
| `/api/v1/data-availability` | GET | Get data availability summary |
| `/api/v1/data/schedule` | POST | Create/update ingestion schedule |
| `/api/v1/data/schedule` | GET | Get ingestion schedule |

## Prerequisites

1. **Azure Functions Core Tools v4**
   ```bash
   npm install -g azure-functions-core-tools@4
   ```

2. **Azurite** (for local Durable Functions storage)
   ```bash
   npm install -g azurite
   ```

3. **Python 3.9+**

## Local Development

### 1. Install Dependencies

```bash
cd backend/services/data_service_functions
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### 2. Start Azurite (Storage Emulator)

In a separate terminal:
```bash
azurite --silent --location ./azurite-data --debug ./azurite-debug.log
```

### 3. Configure Local Settings

Edit `local.settings.json` with your database credentials:
```json
{
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
    "POSTGRES_USER": "postgres",
    "POSTGRES_PASSWORD": "your-password",
    "POSTGRES_DATABASE": "analytics"
  }
}
```

### 4. Run the Functions

```bash
func start
```

The functions will be available at:
- http://localhost:7071/api/v1/ingest
- http://localhost:7071/api/v1/jobs
- etc.

## Testing

### Run Unit Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/ -v
```

### Manual Testing

```bash
# Start an ingestion job
curl -X POST http://localhost:7071/api/v1/ingest \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Id: your-tenant-uuid" \
  -d '{"data_types": ["events", "users", "locations"]}'

# Check job status
curl http://localhost:7071/api/v1/jobs/job_abc123 \
  -H "X-Tenant-Id: your-tenant-uuid"

# Get data availability
curl http://localhost:7071/api/v1/data-availability \
  -H "X-Tenant-Id: your-tenant-uuid"
```

## Deployment

### Deploy to Azure

1. **Create Function App in Azure Portal** or via CLI:
   ```bash
   az functionapp create \
     --resource-group your-rg \
     --name your-function-app \
     --storage-account your-storage \
     --consumption-plan-location westus2 \
     --runtime python \
     --runtime-version 3.9 \
     --functions-version 4
   ```

2. **Configure Application Settings**:
   ```bash
   az functionapp config appsettings set \
     --name your-function-app \
     --resource-group your-rg \
     --settings \
       POSTGRES_HOST=your-db-host \
       POSTGRES_PORT=5432 \
       POSTGRES_USER=your-user \
       POSTGRES_PASSWORD=your-password \
       POSTGRES_DATABASE=analytics
   ```

3. **Deploy**:
   ```bash
   func azure functionapp publish your-function-app
   ```

## Configuration

### host.json Settings

| Setting | Value | Description |
|---------|-------|-------------|
| `functionTimeout` | 00:30:00 | Max execution time (30 min) |
| `maxConcurrentActivityFunctions` | 6 | Parallel activity functions |
| `maxConcurrentOrchestratorFunctions` | 10 | Concurrent orchestrations |

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AzureWebJobsStorage` | Yes | Azure Storage connection string |
| `POSTGRES_HOST` | Yes | PostgreSQL host |
| `POSTGRES_PORT` | Yes | PostgreSQL port |
| `POSTGRES_USER` | Yes | PostgreSQL username |
| `POSTGRES_PASSWORD` | Yes | PostgreSQL password |
| `POSTGRES_DATABASE` | Yes | PostgreSQL database name |
| `DATA_INGESTION_CRON` | No | Default cron schedule (default: "0 2 * * *") |
| `SCHEDULER_API_URL` | No | External scheduler API URL |

## Key Differences from FastAPI Version

| Aspect | FastAPI | Azure Functions |
|--------|---------|-----------------|
| **Background Jobs** | `BackgroundTasks` | Durable Functions Orchestrator |
| **Parallelism** | `ThreadPoolExecutor` | Activity Fan-out |
| **Connection Pooling** | `lru_cache` engines | Fresh connections per invocation |
| **Scheduling** | External scheduler | Timer Trigger |
| **Scaling** | Manual | Auto-scale |

## Monitoring

### Application Insights

Enable Application Insights in your Function App for:
- Function execution logs
- Performance metrics
- Durable Functions orchestration tracking

### Durable Functions Monitor

View orchestration status:
```bash
# Get orchestration status
curl http://localhost:7071/runtime/webhooks/durabletask/instances/{instanceId}
```

## Troubleshooting

### Common Issues

1. **"Orchestrator is not running"**
   - Ensure Azurite is running
   - Check `AzureWebJobsStorage` connection string

2. **Database connection timeout**
   - Verify PostgreSQL is accessible
   - Check firewall rules

3. **BigQuery authentication failed**
   - Verify tenant BigQuery configuration in database
   - Check service account credentials

### Logs

```bash
# View function logs
func start --verbose

# Or check Azure Portal -> Function App -> Monitor
```

