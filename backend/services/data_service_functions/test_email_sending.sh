#!/bin/bash

# Test script for Azure Functions Email Service
# Quick bash version for testing email sending

set -e

# Configuration
BASE_URL="${BASE_URL:-https://gadataingestion.azurewebsites.net/api/v1}"
# For local testing: BASE_URL="http://localhost:7071/api/v1"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo ""
    echo -e "${BOLD}${BLUE}======================================================================${NC}"
    echo -e "${BOLD}${BLUE}$1${NC}"
    echo -e "${BOLD}${BLUE}======================================================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Parse arguments
TENANT_ID=""
REPORT_DATE=""
BRANCH_CODES=""
JOB_ID=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --tenant-id)
            TENANT_ID="$2"
            shift 2
            ;;
        --report-date)
            REPORT_DATE="$2"
            shift 2
            ;;
        --branch-codes)
            BRANCH_CODES="$2"
            shift 2
            ;;
        --job-id)
            JOB_ID="$2"
            shift 2
            ;;
        --base-url)
            BASE_URL="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 --tenant-id TENANT_ID [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --tenant-id TENANT_ID       Tenant ID (required)"
            echo "  --report-date YYYY-MM-DD    Report date (default: yesterday)"
            echo "  --branch-codes D01,D02      Comma-separated branch codes (default: all)"
            echo "  --job-id JOB_ID             Check status of existing job"
            echo "  --base-url URL              Base URL (default: $BASE_URL)"
            echo "  -h, --help                  Show this help message"
            echo ""
            echo "Examples:"
            echo "  # Send emails for all branches"
            echo "  $0 --tenant-id e0f01854-6c2e-4b76-bf7b-67f3c28dbdac --report-date 2025-12-23"
            echo ""
            echo "  # Send emails for specific branches"
            echo "  $0 --tenant-id e0f01854-6c2e-4b76-bf7b-67f3c28dbdac --report-date 2025-12-23 --branch-codes D01,D02"
            echo ""
            echo "  # Check job status"
            echo "  $0 --tenant-id e0f01854-6c2e-4b76-bf7b-67f3c28dbdac --job-id email_abc123"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Validate required arguments
if [ -z "$TENANT_ID" ]; then
    print_error "Tenant ID is required"
    echo "Use --help for usage information"
    exit 1
fi

# Set default report date to yesterday if not provided
if [ -z "$REPORT_DATE" ] && [ -z "$JOB_ID" ]; then
    REPORT_DATE=$(date -d "yesterday" +%Y-%m-%d 2>/dev/null || date -v-1d +%Y-%m-%d)
fi

print_header "Azure Functions Email Service Test"
echo -e "${BOLD}Configuration:${NC}"
echo "  Base URL: $BASE_URL"
echo "  Tenant ID: $TENANT_ID"
if [ -n "$REPORT_DATE" ]; then
    echo "  Report Date: $REPORT_DATE"
fi
if [ -n "$BRANCH_CODES" ]; then
    echo "  Target Branches: $BRANCH_CODES"
else
    echo "  Target Branches: All configured branches"
fi

# If job_id provided, just check status
if [ -n "$JOB_ID" ]; then
    print_header "Checking Email Job Status: $JOB_ID"
    
    RESPONSE=$(curl -s -w "\n%{http_code}" \
        -X GET \
        -H "X-Tenant-Id: $TENANT_ID" \
        "$BASE_URL/email/jobs/$JOB_ID")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_success "Job status retrieved"
        echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
    else
        print_error "Failed to get job status (HTTP $HTTP_CODE)"
        echo "$BODY"
        exit 1
    fi
    
    exit 0
fi

# Test 1: Health Check
print_header "1. Testing Health Check"

RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X GET \
    "$BASE_URL/health")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    print_success "Health check passed"
    echo "$BODY" | jq -r '"Status: \(.status), Version: \(.version)"' 2>/dev/null || echo "$BODY"
else
    print_warning "Health check failed (HTTP $HTTP_CODE), but continuing..."
fi

# Test 2: Get Email Mappings
print_header "2. Fetching Branch Email Mappings"

RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X GET \
    -H "X-Tenant-Id: $TENANT_ID" \
    "$BASE_URL/email/mappings")

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ]; then
    TOTAL=$(echo "$BODY" | jq -r '.total // 0' 2>/dev/null)
    print_success "Found $TOTAL email mappings"
    
    # Display mappings
    echo ""
    echo -e "${BOLD}Branch Email Mappings:${NC}"
    echo "$BODY" | jq -r '.mappings[] | "  [\(if .is_enabled then "✓" else "✗" end)] \(.branch_code) - \(.branch_name // "N/A")\n     → \(.sales_rep_name // "Unknown") <\(.sales_rep_email)>"' 2>/dev/null || echo "$BODY"
    
    if [ "$TOTAL" -eq 0 ]; then
        print_error "No email mappings configured!"
        exit 1
    fi
else
    print_error "Failed to fetch mappings (HTTP $HTTP_CODE)"
    echo "$BODY"
    exit 1
fi

# Test 3: Send Email Reports
print_header "3. Sending Email Reports"

# Build JSON payload
if [ -n "$BRANCH_CODES" ]; then
    # Convert comma-separated string to JSON array
    BRANCHES_JSON=$(echo "$BRANCH_CODES" | jq -R 'split(",") | map(gsub("^\\s+|\\s+$";""))')
    JSON_PAYLOAD=$(jq -n \
        --arg date "$REPORT_DATE" \
        --argjson branches "$BRANCHES_JSON" \
        '{report_date: $date, branch_codes: $branches}')
else
    JSON_PAYLOAD=$(jq -n \
        --arg date "$REPORT_DATE" \
        '{report_date: $date}')
fi

print_info "Sending reports for $REPORT_DATE..."
print_warning "This may take several minutes depending on the number of branches..."
echo ""

START_TIME=$(date +%s)

RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST \
    -H "X-Tenant-Id: $TENANT_ID" \
    -H "Content-Type: application/json" \
    -d "$JSON_PAYLOAD" \
    --max-time 600 \
    "$BASE_URL/email/send-reports")

END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))

HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "202" ]; then
    print_success "Email job completed in ${ELAPSED}s"
    
    JOB_ID=$(echo "$BODY" | jq -r '.job_id // "unknown"' 2>/dev/null)
    STATUS=$(echo "$BODY" | jq -r '.status // "unknown"' 2>/dev/null)
    TOTAL_EMAILS=$(echo "$BODY" | jq -r '.total_emails // 0' 2>/dev/null)
    EMAILS_SENT=$(echo "$BODY" | jq -r '.emails_sent // 0' 2>/dev/null)
    EMAILS_FAILED=$(echo "$BODY" | jq -r '.emails_failed // 0' 2>/dev/null)
    
    echo ""
    echo -e "${BOLD}Job Details:${NC}"
    echo "  Job ID: $JOB_ID"
    echo "  Status: $STATUS"
    echo "  Report Date: $(echo "$BODY" | jq -r '.report_date // "N/A"' 2>/dev/null)"
    
    echo ""
    echo -e "${BOLD}Results:${NC}"
    echo "  Total Emails: $TOTAL_EMAILS"
    echo -e "  ${GREEN}✓ Sent: $EMAILS_SENT${NC}"
    if [ "$EMAILS_FAILED" -gt 0 ]; then
        echo -e "  ${RED}✗ Failed: $EMAILS_FAILED${NC}"
    fi
    
    # Optionally check final status
    if [ "$STATUS" = "processing" ] || [ "$STATUS" = "queued" ]; then
        print_info "Waiting 5 seconds before checking final status..."
        sleep 5
        
        print_header "4. Checking Final Job Status"
        
        RESPONSE=$(curl -s -w "\n%{http_code}" \
            -X GET \
            -H "X-Tenant-Id: $TENANT_ID" \
            "$BASE_URL/email/jobs/$JOB_ID")
        
        HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
        BODY=$(echo "$RESPONSE" | sed '$d')
        
        if [ "$HTTP_CODE" = "200" ]; then
            echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
        fi
    fi
    
    echo ""
    print_success "Email service test completed!"
    
else
    print_error "Failed to send emails (HTTP $HTTP_CODE)"
    echo "$BODY"
    exit 1
fi

