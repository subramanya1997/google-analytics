# Data Service

> **Port**: 8002  
> **Base Path**: `/data/api/v1`  
> **Owner**: Backend Team

## Overview

The Data Service handles data ingestion from external sources (Google BigQuery and SFTP) into the PostgreSQL database. It manages ingestion jobs and provides data availability information.

## Responsibilities

| Feature | Description |
|---------|-------------|
| **Event Ingestion** | Extract GA4 events from BigQuery |
| **User Sync** | Download user data from SFTP |
| **Location Sync** | Download location data from SFTP |
| **Job Management** | Track ingestion job status and history |
| **Data Availability** | Report available date ranges |

## Quick Start

```bash
# From backend directory
cd backend

# Start service
uv run uvicorn services.data_service:app --port 8002 --reload

# Or via Makefile
make service_data

# Verify
curl http://localhost:8002/health
```

## API Endpoints

### Ingestion

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/ingest/start` | POST | Start new ingestion job |
| `/ingest/jobs` | GET | List job history |
| `/ingest/{job_id}` | GET | Get job status |

### Data Availability

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/availability` | GET | Data availability summary |
| `/availability/breakdown` | GET | Detailed availability by event type |

## Architecture

```
services/data_service/
├── main.py                      # FastAPI app entrypoint
├── api/
│   ├── dependencies.py          # FastAPI dependencies
│   └── v1/
│       ├── api.py               # Router aggregation
│       ├── endpoints/
│       │   ├── ingestion.py     # Ingestion job endpoints
│       │   └── schedule.py      # Scheduler integration
│       └── models/
│           └── ingestion.py     # Pydantic request/response models
├── clients/
│   ├── bigquery_client.py       # BigQuery data extraction
│   ├── sftp_client.py           # SFTP file download
│   └── tenant_client_factory.py # Factory for tenant-specific clients
├── database/
│   └── sqlalchemy_repository.py # Database CRUD operations
└── services/
    └── ingestion_service.py     # Ingestion orchestration
```

## Data Flow

```
┌─────────────────┐     ┌─────────────────┐
│    BigQuery     │     │      SFTP       │
│   (GA4 Events)  │     │  (Users/Locs)   │
└────────┬────────┘     └────────┬────────┘
         │                       │
         │ 6 parallel queries    │ 2 files
         ▼                       ▼
┌─────────────────────────────────────────┐
│           INGESTION SERVICE             │
│                                         │
│  1. Create job (queued)                 │
│  2. Extract from BigQuery (parallel)    │
│  3. Download from SFTP                  │
│  4. Transform & validate                │
│  5. Upsert to PostgreSQL                │
│  6. Update job status                   │
└─────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│             PostgreSQL                   │
│  • Event tables (upsert by date range)  │
│  • Users table (upsert by user_id)      │
│  • Locations table (upsert by loc_id)   │
└─────────────────────────────────────────┘
```

## Ingestion Process

### Starting a Job

```bash
curl -X POST "http://localhost:8002/api/v1/ingest/start" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-Id: $TENANT_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "data_types": ["events", "users", "locations"]
  }'
```

### Job Lifecycle

```
┌─────────┐    ┌────────────┐    ┌───────────┐    ┌──────────┐
│ queued  │───▶│ processing │───▶│ completed │ or │  failed  │
└─────────┘    └────────────┘    └───────────┘    └──────────┘
     │               │                                  │
     │               │                                  │
   Created      Started/Progress               Error captured
```

### Job Status Response

```json
{
  "job_id": "job_20240101_abc123",
  "status": "completed",
  "data_types": ["events", "users", "locations"],
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "records_processed": {
    "purchase": 1523,
    "add_to_cart": 8234,
    "page_view": 125000,
    "view_search_results": 45000,
    "no_search_results": 2300,
    "view_item": 67000,
    "users_processed": 5000,
    "locations_processed": 150
  },
  "created_at": "2024-02-01T08:00:00Z",
  "started_at": "2024-02-01T08:00:05Z",
  "completed_at": "2024-02-01T08:15:30Z"
}
```

## BigQuery Client

### Parallel Extraction

The BigQuery client extracts all 6 event types in parallel using a ThreadPoolExecutor:

```python
_BIGQUERY_EXECUTOR = ThreadPoolExecutor(max_workers=6)

async def get_date_range_events_async(self, start_date, end_date):
    # Run all 6 queries in parallel
    tasks = []
    for event_type, extractor in event_extractors.items():
        task = loop.run_in_executor(_BIGQUERY_EXECUTOR, extractor, ...)
        tasks.append((event_type, task))
    
    # Wait for all to complete
    results = {}
    for event_type, task in tasks:
        results[event_type] = await task
    return results
```

### Event Types Extracted

| Event | Table | Key Fields |
|-------|-------|------------|
| `purchase` | `purchase` | transaction_id, revenue, items |
| `add_to_cart` | `add_to_cart` | item_id, quantity, price |
| `page_view` | `page_view` | page_title, page_location |
| `view_item` | `view_item` | item_id, item_name |
| `view_search_results` | `view_search_results` | search_term |
| `no_search_results` | `no_search_results` | search_term |

## SFTP Client

### Files Downloaded

| File | Table | Key Fields |
|------|-------|------------|
| Users report | `users` | user_id, email, company_name |
| Locations report | `locations` | location_id, location_name, city |

### Connection

```python
async def get_tenant_sftp_client(tenant_id: str):
    # Get SFTP config from database
    config = await get_tenant_config(tenant_id)
    
    return SFTPClient(
        host=config["host"],
        port=config["port"],
        username=config["username"],
        password=config["password"]
    )
```

## Configuration

### Environment Variables

```env
# Service
DATA_SERVICE_PORT=8002
SERVICE_NAME=data-ingestion-service

# Database (shared)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Timeouts
JOB_TIMEOUT_SECONDS=1800  # 30 minutes
```

### Tenant Configuration

Each tenant's BigQuery and SFTP configuration is stored in the `tenant_config` table:

```sql
SELECT 
  bigquery_project_id,
  bigquery_dataset_id,
  bigquery_credentials,  -- Service account JSON
  sftp_config            -- {host, port, username, password}
FROM tenant_config 
WHERE id = 'tenant-uuid';
```

## Job Management

### View Running Jobs

```sql
SELECT job_id, status, data_types, start_date, end_date, created_at
FROM processing_jobs 
WHERE status IN ('queued', 'processing')
ORDER BY created_at DESC;
```

### Cancel Stuck Jobs

```bash
# Via script
uv run python scripts/cancel_running_jobs.py

# Manually
psql -c "UPDATE processing_jobs SET status='failed', error_message='Manually cancelled' WHERE job_id='job_id_here';"
```

### Job Timeout

Jobs automatically fail after 30 minutes:

```python
async def run_job_safe(self, job_id, ...):
    try:
        await asyncio.wait_for(
            self.run_job(job_id, ...),
            timeout=1800  # 30 minutes
        )
    except asyncio.TimeoutError:
        await self.repo.update_job_status(
            job_id, "failed",
            error_message="Job timed out after 30 minutes"
        )
```

## Error Handling

### BigQuery Errors

```python
try:
    events = await bigquery_client.get_date_range_events_async(...)
except Exception as e:
    if "credentials" in str(e).lower():
        raise Exception("BigQuery authentication error")
    elif "network" in str(e).lower():
        raise Exception("BigQuery network error")
    raise
```

### SFTP Errors

```python
try:
    data = await sftp_client.get_latest_users_data()
except Exception as e:
    if "file not found" in str(e).lower():
        raise Exception("SFTP file not found")
    elif "permission denied" in str(e).lower():
        raise Exception("SFTP authentication error")
    raise
```

## Testing

```bash
# Run data service tests
uv run pytest tests/services/data/ -v

# Test BigQuery client (requires credentials)
uv run pytest tests/services/data/test_bigquery.py -v

# With coverage
uv run pytest tests/services/data/ --cov=services.data_service
```

## Logging

Logs are written to:
- `logs/data-ingestion-service.log` - All logs
- `logs/data-ingestion-service-error.log` - Errors only

```bash
# Monitor ingestion job
grep "job_id_here" logs/data-ingestion-service.log

# View errors
tail -f logs/data-ingestion-service-error.log
```

## Common Issues

### Job Stuck in "Processing"

**Cause**: Timeout or crash during processing  
**Solution**: Cancel and retry

```bash
uv run python scripts/cancel_running_jobs.py
```

### BigQuery Connection Failed

**Cause**: Invalid credentials or network issue  
**Solution**: Verify tenant BigQuery configuration

```sql
SELECT bigquery_credentials FROM tenant_config WHERE id = 'tenant-uuid';
```

### SFTP File Not Found

**Cause**: Expected file doesn't exist on SFTP server  
**Solution**: Verify file path and SFTP configuration

## API Documentation

Interactive API docs available at:
- Swagger UI: http://localhost:8002/docs
- ReDoc: http://localhost:8002/redoc

