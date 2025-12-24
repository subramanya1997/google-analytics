# Email Service Implementation for Azure Functions

## Overview

The email service has been fully implemented with complete report generation and email sending capabilities, matching the analytics_service functionality.

## ✅ Changes Made

### 1. **Created `services/report_service.py`**
   - Full report generation service adapted from analytics_service
   - Fetches analytics data for:
     - Purchase tasks
     - Cart abandonment tasks
     - Search analysis tasks  
     - Repeat visit tasks
   - Aggregates data and generates report structure for template rendering
   - Includes error handling and fallback logic

### 2. **Created `services/template_service.py`**
   - Jinja2 template rendering service
   - Custom filters for currency, dates, and JSON parsing
   - Transforms raw analytics data into template-ready format
   - Includes fallback HTML generation if template fails

### 3. **Created `templates/branch_report.html`**
   - Professional HTML email template
   - Shows branch sales metrics:
     - Total purchases & revenue
     - Cart abandonments & recovery opportunities
     - Failed searches requiring attention
     - Repeat visitors to contact
   - Detailed customer information with products viewed/purchased
   - Contact details (email, phone) for follow-up

### 4. **Updated `services/email_service.py`**
   - Integrated `ReportService` for full analytics report generation
   - Removed simple placeholder report
   - Now generates comprehensive branch reports with real data
   - Email sending logic remains the same (SMTP)

### 5. **Fixed `function_app.py` - Critical AsyncIO Issue**
   **Before:**
   ```python
   # ❌ Doesn't work reliably in Azure Functions
   asyncio.create_task(email_service.process_email_job(...))
   return {"status": "processing"}  # Job may never complete
   ```

   **After:**
   ```python
   # ✅ Synchronous execution (same fix as ingestion)
   result = await email_service.process_email_job(...)
   return {"status": result["status"], "emails_sent": ...}
   ```

   - Changed from `asyncio.create_task` (background) to direct `await` (synchronous)
   - Matches the ingestion service pattern
   - Azure Functions Consumption plan doesn't reliably execute background tasks
   - Response now includes full job results immediately

### 6. **Added Analytics Query Methods to `shared/database.py`**
   - `get_purchase_tasks()` - Fetch purchase analytics
   - `get_cart_abandonment_tasks()` - Fetch cart abandonment data
   - `get_search_analysis_tasks()` - Fetch failed search data
   - `get_repeat_visit_tasks()` - Fetch repeat visitor data
   - All methods call PostgreSQL RPC functions (stored procedures)
   - Include error handling with fallback to empty results

## 🔍 Architecture Comparison

### Analytics Service (FastAPI)
```
FastAPI Endpoint
  └─> EmailService (uses BackgroundTasks)
       ├─> ReportService
       │    └─> AnalyticsPostgresClient (RPC calls)
       └─> TemplateService (Jinja2)
            └─> templates/branch_report.html
```

### Azure Functions (Serverless)
```
HTTP Trigger
  └─> EmailService (synchronous processing)
       ├─> ReportService
       │    └─> FunctionsRepository (RPC calls)
       └─> TemplateService (Jinja2)
            └─> templates/branch_report.html
```

**Key Difference:** Synchronous execution in Azure Functions vs. Background tasks in FastAPI

## 📊 What the Email Report Contains

Each branch manager receives:

1. **Summary Metrics**
   - Total purchases & revenue
   - Cart abandonments & value at risk
   - Failed searches needing catalog updates
   - Repeat visitors ready for outreach

2. **Purchase Follow-ups**
   - Customer name, company
   - Transaction ID and revenue
   - Products purchased (quantity, name, ID)
   - Contact info (email, phone)

3. **Cart Recovery Tasks**
   - Customer details
   - Cart value
   - Products in cart
   - Contact information

4. **Failed Search Analysis**
   - Search terms with no results
   - Number of searches
   - Affected customers
   - Opportunity for catalog expansion

5. **Repeat Visit Conversion**
   - High-engagement customers
   - Products they viewed
   - Pages visited
   - Contact details for outreach

## 🚀 Deployment Notes

1. **Dependencies Updated**
   - `jinja2` - Already in requirements.txt
   - No new dependencies needed

2. **Database Requirements**
   - PostgreSQL RPC functions must exist:
     - `get_purchase_tasks()`
     - `get_cart_abandonment_tasks()`
     - `get_search_analysis_tasks()`
     - `get_repeat_visit_tasks()`
   - These are created during tenant provisioning

3. **File Structure**
   ```
   backend/services/data_service_functions/
   ├── function_app.py (updated)
   ├── services/
   │   ├── email_service.py (updated)
   │   ├── report_service.py (NEW)
   │   └── template_service.py (NEW)
   ├── templates/
   │   └── branch_report.html (NEW)
   └── shared/
       └── database.py (updated with analytics queries)
   ```

## 🧪 Testing

### Test Email Sending
```bash
curl -X POST "https://gadataingestion.azurewebsites.net/api/v1/email/send-reports" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-Id: YOUR_TENANT_ID" \
  -d '{
    "report_date": "2025-12-23",
    "branch_codes": ["D01"]
  }'
```

### Expected Response
```json
{
  "job_id": "email_abc123",
  "tenant_id": "...",
  "status": "completed",
  "report_date": "2025-12-23",
  "target_branches": ["D01"],
  "total_emails": 1,
  "emails_sent": 1,
  "emails_failed": 0,
  "message": "Email job completed. Check /email/jobs/email_abc123 for details."
}
```

### Check Email Job Status
```bash
curl -X GET "https://gadataingestion.azurewebsites.net/api/v1/email/jobs/email_abc123" \
  -H "X-Tenant-Id: YOUR_TENANT_ID"
```

## ⚡ Performance Considerations

1. **Synchronous Processing**
   - Email job runs to completion before returning response
   - For 10 branches: ~30-60 seconds
   - For 50+ branches: May approach Azure Functions timeout (10 minutes)

2. **Optimization Opportunities**
   - Reports are generated per-branch (allows customization)
   - SMTP connection reused where possible
   - Parallel data fetching using `asyncio.gather`

3. **Monitoring**
   - Check Azure Functions logs for email send status
   - Email send history logged to `email_send_history` table
   - Job status tracked in `email_jobs` table

## 🔒 Security & Compliance

- Each tenant's data isolated in separate database
- SMTP credentials stored encrypted in `tenant_config.smtp_credentials`
- Only sends to configured branch email mappings
- Validates tenant access via `X-Tenant-Id` header

## 📝 Next Steps

1. Deploy the updated Azure Functions
2. Test with a single branch first
3. Verify email delivery and report formatting
4. Scale to all branches

## 🐛 Known Limitations

1. **Large Tenant Handling**
   - Tenants with 50+ branches may hit Azure Functions timeout
   - Consider chunking: Send 20 branches at a time

2. **Template Customization**
   - Template is shared across all tenants
   - Future: Support tenant-specific templates

3. **Attachment Support**
   - Currently only HTML email body
   - Future: PDF attachments, CSV exports

