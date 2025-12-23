# Testing Data Ingestion API

This guide provides examples for testing the data ingestion API.

## Prerequisites

- Tenant UUID (your tenant ID)
- Azure Functions base URL (or localhost for local testing)
- `requests` library installed (for Python script): `pip install requests`

## Quick Test with cURL

### 1. Health Check

```bash
curl -X GET "https://func-data-ingestion-prod.azurewebsites.net/api/v1/health"
```

### 2. Start Ingestion Job (Last 7 Days)

```bash
# Replace TENANT_UUID with your actual tenant UUID
TENANT_UUID="123e4567-e89b-12d3-a456-426614174000"
BASE_URL="https://func-data-ingestion-prod.azurewebsites.net"

# Calculate dates (last 7 days)
START_DATE=$(date -d "7 days ago" +%Y-%m-%d)
END_DATE=$(date +%Y-%m-%d)

# Start ingestion job
curl -X POST "${BASE_URL}/api/v1/ingest" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Id: ${TENANT_UUID}" \
  -d "{
    \"start_date\": \"${START_DATE}\",
    \"end_date\": \"${END_DATE}\",
    \"data_types\": [\"events\", \"users\", \"locations\"]
  }"
```

**Response:**
```json
{
  "job_id": "job_abc123def456",
  "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "processing",
  "data_types": ["events", "users", "locations"],
  "start_date": "2024-01-08",
  "end_date": "2024-01-15",
  "created_at": "2024-01-15T10:30:00",
  "message": "Job created and processing started. Poll /jobs/{job_id} for status."
}
```

### 3. Check Job Status

```bash
JOB_ID="job_abc123def456"

curl -X GET "${BASE_URL}/api/v1/jobs/${JOB_ID}" \
  -H "X-Tenant-Id: ${TENANT_UUID}"
```

**Response:**
```json
{
  "job_id": "job_abc123def456",
  "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "data_types": ["events", "users", "locations"],
  "start_date": "2024-01-08",
  "end_date": "2024-01-15",
  "records_processed": {
    "purchase": 1250,
    "add_to_cart": 3420,
    "page_view": 15600,
    "view_search_results": 890,
    "no_search_results": 120,
    "view_item": 2100,
    "users_processed": 450,
    "locations_processed": 12
  },
  "created_at": "2024-01-15T10:30:00",
  "started_at": "2024-01-15T10:30:01",
  "completed_at": "2024-01-15T10:32:45"
}
```

### 4. Check Data Availability

```bash
curl -X GET "${BASE_URL}/api/v1/data-availability" \
  -H "X-Tenant-Id: ${TENANT_UUID}"
```

## Python Test Script

Use the provided `test_ingestion.py` script for automated testing:

### Basic Usage

```bash
# Test with default settings (last 7 days, all data types)
python test_ingestion.py --tenant-id "123e4567-e89b-12d3-a456-426614174000"

# Test with Azure Functions URL
python test_ingestion.py \
  --tenant-id "123e4567-e89b-12d3-a456-426614174000" \
  --base-url "https://func-data-ingestion-prod.azurewebsites.net"

# Test only events (skip users/locations)
python test_ingestion.py \
  --tenant-id "123e4567-e89b-12d3-a456-426614174000" \
  --data-types events

# Test last 14 days
python test_ingestion.py \
  --tenant-id "123e4567-e89b-12d3-a456-426614174000" \
  --days 14

# Start job but don't poll (just get job_id)
python test_ingestion.py \
  --tenant-id "123e4567-e89b-12d3-a456-426614174000" \
  --no-poll
```

### Options

- `--tenant-id` (required): Tenant UUID to test with
- `--base-url`: Base URL of Azure Functions (default: `http://localhost:7071`)
- `--days`: Number of days to go back from today (default: 7)
- `--data-types`: Data types to ingest: `events`, `users`, `locations` (default: all)
- `--no-poll`: Don't poll for completion, just start the job
- `--max-wait`: Maximum wait time in seconds (default: 1800 = 30 minutes)
- `--poll-interval`: Seconds between status polls (default: 5)

## Example: Complete Test Flow

```bash
#!/bin/bash

# Configuration
TENANT_UUID="123e4567-e89b-12d3-a456-426614174000"
BASE_URL="https://func-data-ingestion-prod.azurewebsites.net"

# Calculate dates (last 7 days)
START_DATE=$(date -d "7 days ago" +%Y-%m-%d)
END_DATE=$(date +%Y-%m-%d)

echo "Starting ingestion test for tenant: ${TENANT_UUID}"
echo "Date range: ${START_DATE} to ${END_DATE}"

# 1. Health check
echo -e "\n1. Health check..."
curl -s "${BASE_URL}/api/v1/health" | jq '.'

# 2. Start ingestion job
echo -e "\n2. Starting ingestion job..."
RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/ingest" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Id: ${TENANT_UUID}" \
  -d "{
    \"start_date\": \"${START_DATE}\",
    \"end_date\": \"${END_DATE}\",
    \"data_types\": [\"events\", \"users\", \"locations\"]
  }")

JOB_ID=$(echo $RESPONSE | jq -r '.job_id')
echo "Job ID: ${JOB_ID}"
echo $RESPONSE | jq '.'

# 3. Poll for completion
echo -e "\n3. Polling job status..."
STATUS="processing"
while [ "$STATUS" != "completed" ] && [ "$STATUS" != "failed" ]; do
  sleep 5
  STATUS_RESPONSE=$(curl -s "${BASE_URL}/api/v1/jobs/${JOB_ID}" \
    -H "X-Tenant-Id: ${TENANT_UUID}")
  STATUS=$(echo $STATUS_RESPONSE | jq -r '.status')
  echo "Status: ${STATUS}"
done

# 4. Final status
echo -e "\n4. Final job status:"
echo $STATUS_RESPONSE | jq '.'

# 5. Data availability
echo -e "\n5. Data availability:"
curl -s "${BASE_URL}/api/v1/data-availability" \
  -H "X-Tenant-Id: ${TENANT_UUID}" | jq '.'
```

## Testing Different Scenarios

### Test Only Events (BigQuery)

```bash
python test_ingestion.py \
  --tenant-id "YOUR_TENANT_ID" \
  --data-types events
```

### Test Only Users/Locations (SFTP)

```bash
python test_ingestion.py \
  --tenant-id "YOUR_TENANT_ID" \
  --data-types users locations
```

### Test Specific Date Range

```bash
# Using curl
curl -X POST "${BASE_URL}/api/v1/ingest" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Id: ${TENANT_UUID}" \
  -d '{
    "start_date": "2024-01-01",
    "end_date": "2024-01-07",
    "data_types": ["events", "users", "locations"]
  }'
```

## Troubleshooting

### Job Status: "queued" or "processing"

The job is still running. This is normal for large date ranges. Wait and poll again.

### Job Status: "failed"

Check the `error_message` field in the job status response:

```bash
curl -X GET "${BASE_URL}/api/v1/jobs/${JOB_ID}" \
  -H "X-Tenant-Id: ${TENANT_UUID}" | jq '.error_message'
```

Common errors:
- **BigQuery not configured**: Check tenant_config table has BigQuery credentials
- **SFTP not configured**: Check tenant_config table has SFTP config
- **Network error**: Check connectivity to BigQuery/SFTP servers
- **Authentication error**: Verify credentials are valid

### Service Unavailable (503)

- Check if Azure Functions app is running
- Verify database connectivity
- Check Application Insights for errors

### 404 Not Found

- Verify tenant database exists: `google-analytics-{tenant_id}`
- Check tenant_id format (should be valid UUID)
- Ensure tenant_config table is initialized

## Expected Processing Times

| Date Range | Data Types | Estimated Time |
|------------|------------|----------------|
| 1 day | events only | 1-2 minutes |
| 7 days | events only | 5-10 minutes |
| 7 days | all types | 10-20 minutes |
| 30 days | all types | 30-60 minutes |

*Times vary based on data volume and network conditions.*

