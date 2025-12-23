#!/bin/bash
#
# Quick test script for data ingestion API
# Tests ingestion for last 7 days
#
# Usage:
#   ./test_ingestion.sh <tenant-id> [base-url]
#
# Example:
#   ./test_ingestion.sh "123e4567-e89b-12d3-a456-426614174000"
#   ./test_ingestion.sh "123e4567-e89b-12d3-a456-426614174000" "https://func-data-ingestion-prod.azurewebsites.net"

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check arguments
if [ -z "$1" ]; then
    echo -e "${RED}Error: Tenant ID is required${NC}"
    echo "Usage: $0 <tenant-id> [base-url]"
    exit 1
fi

TENANT_ID="$1"
BASE_URL="${2:-http://localhost:7071}"

# Calculate dates (last 7 days)
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    START_DATE=$(date -v-7d +%Y-%m-%d)
    END_DATE=$(date +%Y-%m-%d)
else
    # Linux
    START_DATE=$(date -d "7 days ago" +%Y-%m-%d)
    END_DATE=$(date +%Y-%m-%d)
fi

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Data Ingestion API Test${NC}"
echo -e "${BLUE}========================================${NC}"
echo "Tenant ID: $TENANT_ID"
echo "Base URL: $BASE_URL"
echo "Date Range: $START_DATE to $END_DATE (7 days)"
echo -e "${BLUE}========================================${NC}"

# Health check
echo -e "\n${YELLOW}1. Health check...${NC}"
HEALTH_RESPONSE=$(curl -s "${BASE_URL}/api/v1/health" || echo "{}")
if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    echo -e "${GREEN}✓ Service is healthy${NC}"
else
    echo -e "${YELLOW}⚠ Health check failed or service not responding${NC}"
fi

# Start ingestion job
echo -e "\n${YELLOW}2. Starting ingestion job...${NC}"
INGEST_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/v1/ingest" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Id: ${TENANT_ID}" \
  -d "{
    \"start_date\": \"${START_DATE}\",
    \"end_date\": \"${END_DATE}\",
    \"data_types\": [\"events\", \"users\", \"locations\"]
  }")

# Check if job was created
if echo "$INGEST_RESPONSE" | grep -q "job_id"; then
    JOB_ID=$(echo "$INGEST_RESPONSE" | grep -o '"job_id":"[^"]*"' | cut -d'"' -f4)
    echo -e "${GREEN}✓ Job created successfully${NC}"
    echo "Job ID: $JOB_ID"
    echo "Response:"
    echo "$INGEST_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$INGEST_RESPONSE"
else
    echo -e "${RED}✗ Failed to create job${NC}"
    echo "Response:"
    echo "$INGEST_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$INGEST_RESPONSE"
    exit 1
fi

# Poll for job status
echo -e "\n${YELLOW}3. Polling job status (will check every 5 seconds)...${NC}"
echo "Press Ctrl+C to stop polling and check status manually"

STATUS="processing"
ATTEMPTS=0
MAX_ATTEMPTS=360  # 30 minutes max (360 * 5 seconds)

while [ "$STATUS" != "completed" ] && [ "$STATUS" != "failed" ] && [ $ATTEMPTS -lt $MAX_ATTEMPTS ]; do
    sleep 5
    ATTEMPTS=$((ATTEMPTS + 1))
    
    STATUS_RESPONSE=$(curl -s "${BASE_URL}/api/v1/jobs/${JOB_ID}" \
      -H "X-Tenant-Id: ${TENANT_ID}")
    
    STATUS=$(echo "$STATUS_RESPONSE" | grep -o '"status":"[^"]*"' | cut -d'"' -f4 || echo "unknown")
    
    if [ "$STATUS" != "processing" ] && [ "$STATUS" != "queued" ]; then
        echo -e "\n${GREEN}Status changed: ${STATUS}${NC}"
        break
    fi
    
    if [ $((ATTEMPTS % 12)) -eq 0 ]; then
        # Print status every minute
        echo "[$((ATTEMPTS * 5))s] Status: $STATUS"
    fi
done

# Final status
echo -e "\n${YELLOW}4. Final job status:${NC}"
FINAL_RESPONSE=$(curl -s "${BASE_URL}/api/v1/jobs/${JOB_ID}" \
  -H "X-Tenant-Id: ${TENANT_ID}")

echo "$FINAL_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$FINAL_RESPONSE"

FINAL_STATUS=$(echo "$FINAL_RESPONSE" | grep -o '"status":"[^"]*"' | cut -d'"' -f4 || echo "unknown")

if [ "$FINAL_STATUS" == "completed" ]; then
    echo -e "\n${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ Test completed successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    
    # Show records processed
    RECORDS=$(echo "$FINAL_RESPONSE" | grep -o '"records_processed":{[^}]*}' || echo "")
    if [ -n "$RECORDS" ]; then
        echo -e "\n${BLUE}Records processed:${NC}"
        echo "$RECORDS" | python3 -m json.tool 2>/dev/null || echo "$RECORDS"
    fi
else
    echo -e "\n${RED}========================================${NC}"
    echo -e "${RED}❌ Test completed with status: ${FINAL_STATUS}${NC}"
    echo -e "${RED}========================================${NC}"
    
    # Show error if any
    ERROR=$(echo "$FINAL_RESPONSE" | grep -o '"error_message":"[^"]*"' | cut -d'"' -f4 || echo "")
    if [ -n "$ERROR" ]; then
        echo -e "${RED}Error: $ERROR${NC}"
    fi
fi

# Data availability
echo -e "\n${YELLOW}5. Current data availability:${NC}"
AVAILABILITY=$(curl -s "${BASE_URL}/api/v1/data-availability" \
  -H "X-Tenant-Id: ${TENANT_ID}")

echo "$AVAILABILITY" | python3 -m json.tool 2>/dev/null || echo "$AVAILABILITY"

echo -e "\n${BLUE}To check job status manually:${NC}"
echo "curl -H 'X-Tenant-Id: ${TENANT_ID}' ${BASE_URL}/api/v1/jobs/${JOB_ID}"

