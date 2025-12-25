# Analytics Service

> **Port**: 8001  
> **Base Path**: `/analytics/api/v1`  
> **Owner**: Backend Team

## Overview

The Analytics Service provides the dashboard API, task management, and email reporting capabilities for the Google Analytics Intelligence System.

## Responsibilities

| Feature | Description |
|---------|-------------|
| **Dashboard Stats** | Aggregated metrics for revenue, purchases, visitors |
| **Task Management** | Purchase follow-ups, cart abandonment, search analysis |
| **Email Reports** | Branch-level performance reports to sales reps |
| **History Queries** | Session and user event timelines |

## Quick Start

```bash
# From backend directory
cd backend

# Start service
uv run uvicorn services.analytics_service:app --port 8001 --reload

# Or via Makefile
make service_analytics

# Verify
curl http://localhost:8001/health
```

## API Endpoints

### Statistics

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/stats` | GET | Dashboard overview metrics |
| `/stats/complete` | GET | Complete dashboard data (optimized) |
| `/stats/chart` | GET | Time-series chart data |

### Locations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/locations` | GET | List active locations/branches |

### Tasks

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/tasks/purchases` | GET | Purchase follow-up opportunities |
| `/tasks/cart-abandonment` | GET | Cart recovery tasks |
| `/tasks/search-analysis` | GET | Search optimization insights |
| `/tasks/repeat-visits` | GET | Repeat visitor engagement |
| `/tasks/performance` | GET | Branch performance metrics |

### History

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/history/session/{id}` | GET | Session event timeline |
| `/history/user/{id}` | GET | User event timeline |

### Email

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/email/mappings` | GET | List branch email mappings |
| `/email/mappings` | POST | Create email mapping |
| `/email/mappings/{id}` | PUT | Update email mapping |
| `/email/mappings/{id}` | DELETE | Delete email mapping |
| `/email/send` | POST | Trigger email report job |
| `/email/jobs` | GET | List email job history |
| `/email/jobs/{id}` | GET | Get email job status |

## Architecture

```
services/analytics_service/
├── main.py                      # FastAPI app entrypoint
├── api/
│   ├── dependencies.py          # FastAPI dependencies
│   └── v1/
│       ├── api.py               # Router aggregation
│       ├── endpoints/
│       │   ├── email.py         # Email management
│       │   ├── history.py       # Session/user history
│       │   ├── locations.py     # Location queries
│       │   ├── schedule.py      # Scheduler integration
│       │   ├── stats.py         # Dashboard statistics
│       │   └── tasks.py         # Task management
│       └── models/
│           ├── email.py         # Email Pydantic models
│           └── locations.py     # Location models
├── database/
│   └── postgres_client.py       # Database operations
├── services/
│   ├── email_service.py         # SMTP email sending
│   ├── report_service.py        # Report generation
│   └── template_service.py      # Jinja2 templates
├── templates/
│   └── branch_report.html       # Email report template
└── utils.py                     # Utility functions
```

## Database Operations

All complex analytics queries are implemented as PostgreSQL functions:

```python
# Example: Get purchase tasks
async def get_purchase_tasks(self, tenant_id: str, page: int, limit: int, ...):
    async with get_async_db_session("analytics-service") as session:
        result = await session.execute(
            text("SELECT get_purchase_tasks(:tenant_id, :page, :limit, ...)"),
            params
        )
        return result.scalar()
```

### PostgreSQL Functions Used

| Function | Purpose |
|----------|---------|
| `get_purchase_tasks()` | Purchase follow-up data |
| `get_cart_abandonment_tasks()` | Cart recovery data |
| `get_search_analysis_tasks()` | Search insights |
| `get_repeat_visit_tasks()` | Repeat visitor data |
| `get_performance_tasks()` | Branch performance |
| `get_session_history()` | Session timeline |
| `get_user_history()` | User timeline |

## Email System

### Configuration

Email configuration is stored per-tenant in the `tenants` table:

```json
{
  "server": "smtp.example.com",
  "port": 587,
  "from_address": "reports@company.com",
  "username": "smtp_user",
  "password": "smtp_password",
  "use_tls": true
}
```

### Email Flow

```
1. POST /email/send
   └── Create email_sending_job (status: queued)
   
2. Background task starts
   └── Update job (status: processing)
   
3. For each branch:
   ├── Generate HTML report (Jinja2)
   ├── Send via SMTP
   └── Log to email_send_history
   
4. Complete
   └── Update job (status: completed)
```

### Email Template

The report template is in `templates/branch_report.html` and includes:
- Branch performance summary
- Top purchases
- Cart abandonment alerts
- Search analysis

## Configuration

### Environment Variables

```env
# Service
ANALYTICS_SERVICE_PORT=8001
SERVICE_NAME=analytics-service

# Database (shared)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=google_analytics_db

# Pagination
DEFAULT_PAGE_SIZE=50
MAX_PAGE_SIZE=1000
```

### Settings Class

```python
# common/config/settings.py
class AnalyticsServiceSettings(BaseServiceSettings):
    SERVICE_NAME: str = "analytics-service"
    SERVICE_VERSION: str = "0.0.1"
    PORT: int = 8001
    EMAIL_NOTIFICATION_CRON: str = "0 8 * * *"
```

## Testing

```bash
# Run all analytics tests
uv run pytest tests/services/analytics/ -v

# Run specific test
uv run pytest tests/services/analytics/test_tasks.py -v

# With coverage
uv run pytest tests/services/analytics/ --cov=services.analytics_service
```

## Logging

Logs are written to:
- `logs/analytics-service.log` - All logs
- `logs/analytics-service-error.log` - Errors only

```bash
# View logs
tail -f logs/analytics-service.log

# Search for errors
grep "ERROR" logs/analytics-service.log
```

## Common Issues

### Slow Dashboard Loading

**Cause**: PostgreSQL function not using indexes  
**Solution**: Run `ANALYZE` on event tables

```sql
ANALYZE purchase;
ANALYZE add_to_cart;
ANALYZE page_view;
```

### Email Sending Fails

**Cause**: Invalid SMTP configuration  
**Solution**: Verify tenant email_config in database

```sql
SELECT email_config FROM tenant_config WHERE id = 'tenant-uuid';
```

### Empty Task Lists

**Cause**: No data for date range  
**Solution**: Check data availability

```bash
curl "http://localhost:8002/api/v1/availability" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-Id: $TENANT_ID"
```

## API Documentation

Interactive API docs available at:
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

