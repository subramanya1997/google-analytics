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

---

## Email Service Testing

### Prerequisites

1. **Configure Email Mappings**
   - Branch codes must be configured with sales rep emails
   - Use `POST /api/v1/email/mappings` to create mappings
   - Or configure directly in the database `branch_email_mappings` table

2. **SMTP Configuration**
   - SMTP credentials must be configured in `tenant_config.smtp_credentials`
   - Test SMTP connectivity before sending emails

### Quick Test (Bash)

```bash
# Make script executable (Linux/Mac)
chmod +x test_email_sending.sh

# Send emails for all branches (yesterday's data)
./test_email_sending.sh --tenant-id YOUR_TENANT_ID

# Send emails for specific branches
./test_email_sending.sh \
  --tenant-id YOUR_TENANT_ID \
  --report-date 2025-12-23 \
  --branch-codes D01,D02

# Check existing job status
./test_email_sending.sh \
  --tenant-id YOUR_TENANT_ID \
  --job-id email_abc123

# Test against local Azure Functions (development)
./test_email_sending.sh \
  --tenant-id YOUR_TENANT_ID \
  --report-date 2025-12-23 \
  --base-url http://localhost:7071/api/v1
```

### Comprehensive Test (Python)

```bash
# Install dependencies
pip install requests

# Send emails for all branches
python test_email_sending.py \
  --tenant-id YOUR_TENANT_ID \
  --report-date 2025-12-23

# Send emails for specific branches
python test_email_sending.py \
  --tenant-id YOUR_TENANT_ID \
  --report-date 2025-12-23 \
  --branch-codes D01,D02,D03

# Check existing job status
python test_email_sending.py \
  --tenant-id YOUR_TENANT_ID \
  --job-id email_abc123

# Skip health check
python test_email_sending.py \
  --tenant-id YOUR_TENANT_ID \
  --report-date 2025-12-23 \
  --skip-health-check
```

### Manual Testing with cURL

#### 1. Check Email Mappings

```bash
curl -X GET \
  "https://gadataingestion.azurewebsites.net/api/v1/email/mappings" \
  -H "X-Tenant-Id: YOUR_TENANT_ID"

# Filter by branch
curl -X GET \
  "https://gadataingestion.azurewebsites.net/api/v1/email/mappings?branch_code=D01" \
  -H "X-Tenant-Id: YOUR_TENANT_ID"
```

**Expected Response:**
```json
{
  "mappings": [
    {
      "branch_code": "D01",
      "branch_name": "Main Branch",
      "sales_rep_email": "manager@company.com",
      "sales_rep_name": "John Doe",
      "is_enabled": true
    }
  ],
  "total": 1
}
```

#### 2. Create Email Mapping

```bash
curl -X POST \
  "https://gadataingestion.azurewebsites.net/api/v1/email/mappings" \
  -H "X-Tenant-Id: YOUR_TENANT_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "branch_code": "D01",
    "branch_name": "Main Branch",
    "sales_rep_email": "manager@company.com",
    "sales_rep_name": "John Doe",
    "is_enabled": true
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Email mapping created successfully",
  "mapping_id": "mapping-uuid-here"
}
```

#### 3. Send Email Reports

```bash
# Send to all configured branches
curl -X POST \
  "https://gadataingestion.azurewebsites.net/api/v1/email/send-reports" \
  -H "X-Tenant-Id: YOUR_TENANT_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "report_date": "2025-12-23"
  }'

# Send to specific branches
curl -X POST \
  "https://gadataingestion.azurewebsites.net/api/v1/email/send-reports" \
  -H "X-Tenant-Id: YOUR_TENANT_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "report_date": "2025-12-23",
    "branch_codes": ["D01", "D02"]
  }'
```

**Expected Response (Synchronous):**
```json
{
  "job_id": "email_abc123def456",
  "tenant_id": "e0f01854-6c2e-4b76-bf7b-67f3c28dbdac",
  "status": "completed",
  "report_date": "2025-12-23",
  "target_branches": ["D01", "D02"],
  "total_emails": 2,
  "emails_sent": 2,
  "emails_failed": 0,
  "message": "Email job completed. Check /email/jobs/email_abc123def456 for details."
}
```

#### 4. Check Email Job Status

```bash
curl -X GET \
  "https://gadataingestion.azurewebsites.net/api/v1/email/jobs/email_abc123def456" \
  -H "X-Tenant-Id: YOUR_TENANT_ID"
```

**Expected Response:**
```json
{
  "job_id": "email_abc123def456",
  "tenant_id": "e0f01854-6c2e-4b76-bf7b-67f3c28dbdac",
  "status": "completed",
  "report_date": "2025-12-23",
  "target_branches": ["D01", "D02"],
  "total_emails": 2,
  "emails_sent": 2,
  "emails_failed": 0,
  "created_at": "2025-12-24T03:00:00Z",
  "started_at": "2025-12-24T03:00:01Z",
  "completed_at": "2025-12-24T03:01:30Z"
}
```

### Email Report Contents

Each branch manager receives a comprehensive HTML email with:

| Section | Description |
|---------|-------------|
| **Summary Metrics** | Total purchases, revenue, cart abandonments, failed searches |
| **Purchase Follow-ups** | Customer details, products purchased, contact information |
| **Cart Recovery** | Abandoned carts with value and customer contact info |
| **Search Analysis** | Failed searches indicating catalog gaps |
| **Repeat Visitors** | High-engagement customers ready for outreach |

### Testing Checklist

- [ ] Health check passes
- [ ] Email mappings exist and are enabled
- [ ] SMTP credentials are configured
- [ ] Email job creates successfully
- [ ] Emails send without errors
- [ ] HTML report renders correctly
- [ ] Customer data appears accurately
- [ ] Contact information is present
- [ ] Job status updates correctly
- [ ] Failed emails are logged properly

### Troubleshooting

#### No Email Mappings

**Error:** `No branch email mappings configured`

**Solution:** Create email mappings using the API or database:
```sql
INSERT INTO branch_email_mappings (tenant_id, branch_code, branch_name, sales_rep_email, sales_rep_name, is_enabled)
VALUES ('tenant-uuid', 'D01', 'Main Branch', 'manager@company.com', 'John Doe', true);
```

#### SMTP Configuration Missing

**Error:** `Cannot send emails: SMTP service is disabled`

**Solution:** Configure SMTP in `tenant_config`:
```sql
UPDATE tenant_config 
SET smtp_credentials = '{
  "server": "smtp.gmail.com",
  "port": 587,
  "username": "your-email@gmail.com",
  "password": "your-app-password",
  "from_address": "noreply@yourcompany.com",
  "use_tls": true,
  "use_ssl": false
}'::jsonb
WHERE tenant_id = 'tenant-uuid';
```

#### Timeout Errors

**Error:** `Request timed out after 10 minutes`

**Cause:** Too many branches being processed at once

**Solution:** 
- Reduce the number of branches per request
- Send in batches of 10-20 branches
- Check Azure Functions logs for processing details

#### Email Not Received

**Checklist:**
1. Check spam folder
2. Verify `sales_rep_email` is correct in mappings
3. Check SMTP credentials are valid
4. Review email send history in database:
   ```sql
   SELECT * FROM email_send_history 
   WHERE tenant_id = 'tenant-uuid' 
   ORDER BY sent_at DESC LIMIT 10;
   ```
5. Check Azure Functions logs for SMTP errors

### Performance Expectations

| Branches | Estimated Time | Notes |
|----------|----------------|-------|
| 1-5 | 30-60 seconds | Quick test |
| 10-20 | 2-4 minutes | Standard daily run |
| 50+ | 5-10 minutes | Large tenant |

*Times include report generation, data fetching, and email sending.*

### Integration Testing

For automated testing in CI/CD:

```python
import requests
import time

def test_email_service(tenant_id: str, branch_code: str):
    base_url = "https://gadataingestion.azurewebsites.net/api/v1"
    headers = {"X-Tenant-Id": tenant_id}
    
    # 1. Verify mapping exists
    resp = requests.get(f"{base_url}/email/mappings", headers=headers)
    assert resp.status_code == 200
    mappings = resp.json()["mappings"]
    assert len(mappings) > 0
    
    # 2. Send email
    resp = requests.post(
        f"{base_url}/email/send-reports",
        headers=headers,
        json={"report_date": "2025-12-23", "branch_codes": [branch_code]},
        timeout=600
    )
    assert resp.status_code in [200, 202]
    job_id = resp.json()["job_id"]
    
    # 3. Verify job completed
    resp = requests.get(f"{base_url}/email/jobs/{job_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] in ["completed", "completed_with_errors"]
    
    print(f"✓ Email service test passed for tenant {tenant_id}")
```

