# Architecture Documentation

> **Last Updated**: November 2024  
> **Status**: Living Document  
> **Owner**: Backend Team

## Table of Contents

- [Overview](#overview)
- [System Context](#system-context)
- [Architecture Principles](#architecture-principles)
- [Service Architecture](#service-architecture)
- [Data Architecture](#data-architecture)
- [Security Architecture](#security-architecture)
- [Infrastructure](#infrastructure)
- [Cross-Cutting Concerns](#cross-cutting-concerns)

---

## Overview

### Purpose

The Google Analytics Intelligence System is a multi-tenant SaaS platform that processes Google Analytics 4 (GA4) data to generate actionable business intelligence for e-commerce operations. The system ingests behavioral data, enriches it with business context, and delivers insights through dashboards and automated email reports.

### Business Context

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         BUSINESS CAPABILITIES                           │
├─────────────────────────────────────────────────────────────────────────┤
│  • Purchase Follow-up Intelligence    • Cart Abandonment Recovery       │
│  • Search Optimization Insights       • Repeat Visitor Engagement       │
│  • Branch Performance Analytics       • Automated Sales Rep Reports     │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| API Latency (p95) | < 500ms | Analytics endpoints |
| Data Freshness | < 24 hours | GA4 data availability |
| System Availability | 99.9% | Excluding planned maintenance |
| Concurrent Tenants | 100+ | Multi-tenant capacity |

---

## System Context

### C4 Context Diagram

```
                                    ┌─────────────────┐
                                    │   Sales Reps    │
                                    │    (Users)      │
                                    └────────┬────────┘
                                             │ Email Reports
                                             ▼
┌─────────────────┐              ┌─────────────────────────────────────────┐
│  Google         │              │                                         │
│  Analytics 4    │──BigQuery───▶│     Google Analytics Intelligence       │
│  (GA4)          │              │              System                     │
└─────────────────┘              │                                         │
                                 │  ┌─────────────────────────────────┐    │
┌─────────────────┐              │  │         Backend Services        │    │
│   SFTP Server   │──Users/──────│  │  • Auth Service (8003)          │    │
│  (Master Data)  │  Locations   │  │  • Data Service (8002)          │    │
└─────────────────┘              │  │  • Analytics Service (8001)     │    │
                                 │  └─────────────────────────────────┘    │
┌─────────────────┐              │                                         │
│   External      │◀─OAuth 2.0──│                                         │
│   Identity      │              │                                         │
│   Provider      │              └─────────────────────────────────────────┘
└─────────────────┘                              │
                                                 │ REST API
                                                 ▼
                                    ┌─────────────────────┐
                                    │   Next.js Dashboard │
                                    │     (Frontend)      │
                                    └─────────────────────┘
```

### External Dependencies

| System | Type | Purpose | SLA Dependency |
|--------|------|---------|----------------|
| Google BigQuery | Data Source | GA4 event data | High |
| SFTP Server | Data Source | User & location master data | Medium |
| External IdP | Auth Provider | OAuth 2.0 authentication | High |
| PostgreSQL | Database | Primary data store | Critical |
| SMTP Server | Email | Report delivery | Medium |

---

## Architecture Principles

### 1. Multi-Tenancy First

All data and operations are scoped by `tenant_id`. No cross-tenant data access is possible.

```python
# Every query includes tenant isolation
async def get_data(tenant_id: str, ...):
    query = "SELECT * FROM table WHERE tenant_id = :tenant_id"
```

### 2. Database-Centric Analytics

Complex analytics queries are implemented as PostgreSQL functions, not application code.

**Rationale**:
- 10-100x faster than ORM-based queries for aggregations
- Single round-trip for complex multi-table operations
- Database handles query optimization
- Easier to tune with EXPLAIN ANALYZE

```sql
-- Example: Individual function calls for dashboard data
SELECT get_dashboard_overview_stats(:tenant_id, :start_date, :end_date, :location_id);
SELECT get_chart_data(:tenant_id, :start_date, :end_date, :granularity, :location_id);
SELECT get_location_stats_bulk(:tenant_id, :start_date, :end_date);
```

### 3. Async-First Design

All I/O operations use async patterns for optimal resource utilization.

```python
# Async database session
async with get_async_db_session("analytics-service") as session:
    result = await session.execute(query)

# Parallel BigQuery extraction
results = await bigquery_client.get_date_range_events_async(start_date, end_date)
```

### 4. Fail-Safe Operations

Background jobs include timeout monitoring and automatic status updates.

```python
async def run_job_safe(self, job_id: str, ...):
    try:
        await asyncio.wait_for(self.run_job(...), timeout=1800)  # 30 min
    except asyncio.TimeoutError:
        await self.repo.update_job_status(job_id, "failed", error_message="Timeout")
```

### 5. Configuration Over Code

Tenant-specific configurations (BigQuery, SFTP, SMTP) are stored in database, not environment variables.

---

## Service Architecture

### Service Overview

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              API GATEWAY / NGINX                            │
│                        (Reverse Proxy, SSL Termination)                     │
└────────────────────────────────────────────────────────────────────────────┘
         │                           │                           │
         │ /auth/*                   │ /data/*                   │ /analytics/*
         ▼                           ▼                           ▼
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│  AUTH SERVICE   │       │  DATA SERVICE   │       │ANALYTICS SERVICE│
│    Port 8003    │       │    Port 8002    │       │    Port 8001    │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ • OAuth 2.0     │       │ • BigQuery ETL  │       │ • Dashboard API │
│ • Token Valid.  │       │ • SFTP Sync     │       │ • Task Lists    │
│ • Tenant Config │       │ • Job Mgmt      │       │ • Email Reports │
└────────┬────────┘       └────────┬────────┘       └────────┬────────┘
         │                         │                         │
         └─────────────────────────┼─────────────────────────┘
                                   │
                                   ▼
                    ┌─────────────────────────────┐
                    │         PostgreSQL          │
                    │   (Shared Database)         │
                    │                             │
                    │  • Tables (13)              │
                    │  • Functions (15)           │
                    │  • Indexes (Optimized)      │
                    └─────────────────────────────┘
```

### Service Responsibilities

#### Auth Service (Port 8003)

| Responsibility | Description |
|----------------|-------------|
| **Authentication** | OAuth 2.0 code exchange with external IdP |
| **Token Validation** | Verify access tokens on each request |
| **Tenant Provisioning** | Create/update tenant configurations |
| **Service Validation** | Background validation of BigQuery/SFTP/SMTP |

**Key Endpoints**:
```
GET  /api/v1/login          → Get OAuth login URL
POST /api/v1/callback       → Exchange code for session
POST /api/v1/logout         → Invalidate session
GET  /api/v1/validate       → Validate access token
```

#### Data Service (Port 8002)

| Responsibility | Description |
|----------------|-------------|
| **Event Ingestion** | Extract GA4 events from BigQuery |
| **Master Data Sync** | Download users/locations from SFTP |
| **Job Management** | Track ingestion job status |
| **Data Availability** | Report available date ranges |

**Key Endpoints**:
```
POST /api/v1/ingest/start   → Start ingestion job
GET  /api/v1/ingest/jobs    → List job history
GET  /api/v1/ingest/{id}    → Get job status
GET  /api/v1/availability   → Data availability report
```

#### Analytics Service (Port 8001)

| Responsibility | Description |
|----------------|-------------|
| **Dashboard Stats** | Aggregated metrics & charts |
| **Task Management** | Purchase/cart/search/repeat-visit tasks |
| **Email Management** | Branch mappings, job scheduling |
| **History Queries** | Session & user event timelines |

**Key Endpoints**:
```
GET  /api/v1/stats                    → Dashboard overview
GET  /api/v1/stats/chart              → Time-series data
GET  /api/v1/tasks/purchases          → Purchase follow-ups
GET  /api/v1/tasks/cart-abandonment   → Cart recovery tasks
GET  /api/v1/tasks/search-analysis    → Search insights
GET  /api/v1/email/jobs               → Email job history
POST /api/v1/email/send               → Trigger email reports
```

### Service Communication

Services communicate via:
1. **Shared Database** - All services read/write to PostgreSQL
2. **HTTP (internal)** - Minimal inter-service calls
3. **External Scheduler** - Cron-based job triggering

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    Auth     │     │    Data     │     │  Analytics  │
│   Service   │     │   Service   │     │   Service   │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       │   Shared State    │                   │
       └───────────────────┼───────────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  PostgreSQL │
                    │  (tenants,  │
                    │   events,   │
                    │   jobs)     │
                    └─────────────┘
```

---

## Data Architecture

### Event Data Model

```
┌─────────────────────────────────────────────────────────────────┐
│                        EVENT TABLES                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   purchase   │  │ add_to_cart  │  │  page_view   │          │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤          │
│  │ tenant_id    │  │ tenant_id    │  │ tenant_id    │          │
│  │ event_date   │  │ event_date   │  │ event_date   │          │
│  │ user_id      │  │ user_id      │  │ user_id      │          │
│  │ session_id   │  │ session_id   │  │ session_id   │          │
│  │ branch_id    │  │ branch_id    │  │ branch_id    │          │
│  │ revenue      │  │ item_id      │  │ page_title   │          │
│  │ items_json   │  │ item_price   │  │ page_url     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  view_item   │  │view_search   │  │no_search_res │          │
│  ├──────────────┤  ├──────────────┤  ├──────────────┤          │
│  │ tenant_id    │  │ tenant_id    │  │ tenant_id    │          │
│  │ event_date   │  │ event_date   │  │ event_date   │          │
│  │ user_id      │  │ user_id      │  │ user_id      │          │
│  │ item_id      │  │ search_term  │  │ search_term  │          │
│  │ item_name    │  │ session_id   │  │ session_id   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           DATA INGESTION FLOW                            │
└─────────────────────────────────────────────────────────────────────────┘

  ┌──────────────┐                                    ┌──────────────┐
  │   BigQuery   │                                    │     SFTP     │
  │   (GA4)      │                                    │   Server     │
  └──────┬───────┘                                    └──────┬───────┘
         │                                                   │
         │ 6 parallel queries                                │ 2 files
         │ (one per event type)                              │ (users, locations)
         ▼                                                   ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │                        DATA SERVICE                               │
  │                                                                   │
  │  1. Create job (status: queued)                                  │
  │  2. Extract events from BigQuery (parallel)                      │
  │  3. Download users/locations from SFTP                           │
  │  4. Transform & validate data                                    │
  │  5. Upsert to PostgreSQL (replace for date range)               │
  │  6. Update job status (completed/failed)                         │
  │                                                                   │
  └──────────────────────────────────────────────────────────────────┘
         │
         │ INSERT/UPDATE
         ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │                        PostgreSQL                                 │
  │                                                                   │
  │  ┌─────────────────────────────────────────────────────────┐     │
  │  │                    Event Tables                          │     │
  │  │  • Partitioned by tenant_id + event_date                │     │
  │  │  • Indexes on (tenant_id, event_date, branch_id)        │     │
  │  │  • JSONB for flexible item data                          │     │
  │  └─────────────────────────────────────────────────────────┘     │
  │                                                                   │
  │  ┌─────────────────────────────────────────────────────────┐     │
  │  │                    PL/pgSQL Functions                    │     │
  │  │  • get_purchase_tasks()                                  │     │
  │  │  • get_cart_abandonment_tasks()                          │     │
  │  │  • get_dashboard_overview_stats()                        │     │
  │  │  • ... (14 total)                                        │     │
  │  └─────────────────────────────────────────────────────────┘     │
  │                                                                   │
  └──────────────────────────────────────────────────────────────────┘
         │
         │ SELECT (via functions)
         ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │                     ANALYTICS SERVICE                             │
  │                                                                   │
  │  • Calls PostgreSQL functions                                    │
  │  • Returns JSON responses to frontend                            │
  │  • Generates HTML email reports                                  │
  │                                                                   │
  └──────────────────────────────────────────────────────────────────┘
```

### Data Retention

| Data Type | Retention | Rationale |
|-----------|-----------|-----------|
| Event Data | 2 years | Business analysis needs |
| User/Location | Indefinite | Master data |
| Email History | 1 year | Audit trail |
| Job History | 90 days | Troubleshooting |

---

## Security Architecture

### Authentication Flow

```
┌─────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Browser │     │  Frontend   │     │Auth Service │     │ External    │
│         │     │  (Next.js)  │     │   (8003)    │     │    IdP      │
└────┬────┘     └──────┬──────┘     └──────┬──────┘     └──────┬──────┘
     │                 │                   │                   │
     │  1. Login       │                   │                   │
     │────────────────▶│                   │                   │
     │                 │                   │                   │
     │                 │  2. Get login URL │                   │
     │                 │──────────────────▶│                   │
     │                 │                   │                   │
     │                 │  3. OAuth URL     │                   │
     │                 │◀──────────────────│                   │
     │                 │                   │                   │
     │  4. Redirect to IdP                 │                   │
     │◀────────────────│                   │                   │
     │                 │                   │                   │
     │  5. Authenticate with IdP           │                   │
     │─────────────────────────────────────────────────────────▶
     │                 │                   │                   │
     │  6. Redirect with code              │                   │
     │◀────────────────────────────────────────────────────────│
     │                 │                   │                   │
     │  7. Code        │                   │                   │
     │────────────────▶│                   │                   │
     │                 │                   │                   │
     │                 │  8. Exchange code │                   │
     │                 │──────────────────▶│                   │
     │                 │                   │                   │
     │                 │                   │  9. Validate      │
     │                 │                   │─────────────────▶│
     │                 │                   │                   │
     │                 │                   │  10. User + Token │
     │                 │                   │◀─────────────────│
     │                 │                   │                   │
     │                 │  11. Session      │                   │
     │                 │◀──────────────────│                   │
     │                 │                   │                   │
     │  12. Set cookies│                   │                   │
     │◀────────────────│                   │                   │
     │                 │                   │                   │
```

### Authorization Model

```
┌─────────────────────────────────────────────────────────────────┐
│                      REQUEST AUTHORIZATION                       │
└─────────────────────────────────────────────────────────────────┘

  Incoming Request
        │
        ▼
  ┌─────────────────┐
  │ Extract Headers │
  │ • Authorization │
  │ • X-Tenant-Id   │
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐     No      ┌─────────────────┐
  │ Token Present?  │────────────▶│   401 Unauth    │
  └────────┬────────┘             └─────────────────┘
           │ Yes
           ▼
  ┌─────────────────┐     No      ┌─────────────────┐
  │ Token Valid?    │────────────▶│   401 Unauth    │
  │ (call IdP)      │             └─────────────────┘
  └────────┬────────┘
           │ Yes
           ▼
  ┌─────────────────┐     No      ┌─────────────────┐
  │ Tenant Exists?  │────────────▶│   403 Forbidden │
  └────────┬────────┘             └─────────────────┘
           │ Yes
           ▼
  ┌─────────────────┐
  │ Process Request │
  │ (scoped to      │
  │  tenant_id)     │
  └─────────────────┘
```

### Data Security

| Layer | Control |
|-------|---------|
| **Transport** | TLS 1.3 (HTTPS) |
| **Database** | Connection encryption, parameterized queries |
| **Credentials** | Stored encrypted in tenant config (JSONB) |
| **Logs** | PII redaction, no credentials logged |
| **Multi-tenant** | Row-level tenant isolation |

---

## Infrastructure

### Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              PRODUCTION                                  │
└─────────────────────────────────────────────────────────────────────────┘

                         ┌─────────────────┐
                         │   CloudFlare    │
                         │   (CDN + WAF)   │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │     Nginx       │
                         │ (Load Balancer) │
                         │ SSL Termination │
                         └────────┬────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
          ▼                       ▼                       ▼
   ┌─────────────┐         ┌─────────────┐         ┌─────────────┐
   │    Auth     │         │    Data     │         │  Analytics  │
   │   Service   │         │   Service   │         │   Service   │
   │  (2 pods)   │         │  (2 pods)   │         │  (3 pods)   │
   └─────────────┘         └─────────────┘         └─────────────┘
          │                       │                       │
          └───────────────────────┼───────────────────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │   PostgreSQL    │
                         │  (Primary +     │
                         │   Read Replica) │
                         └─────────────────┘
```

### Resource Requirements

| Service | CPU | Memory | Replicas |
|---------|-----|--------|----------|
| Auth Service | 0.5 vCPU | 512 MB | 2 |
| Data Service | 2 vCPU | 2 GB | 2 |
| Analytics Service | 1 vCPU | 1 GB | 3 |
| PostgreSQL | 4 vCPU | 8 GB | 1 + replica |

---

## Cross-Cutting Concerns

### Logging

All services use **Loguru** with structured logging:

```python
from loguru import logger

logger.info("Processing job", job_id=job_id, tenant_id=tenant_id)
logger.error("Database error", error=str(e), exc_info=True)
```

**Log Locations**:
```
backend/logs/
├── analytics-service.log
├── analytics-service-error.log
├── data-ingestion-service.log
├── data-ingestion-service-error.log
├── auth-service.log
└── auth-service-error.log
```

### Error Handling

```python
# Global exception handler in app_factory.py
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )
```

### Health Checks

All services expose `/health` endpoint:

```json
{
  "service": "analytics-service",
  "version": "0.0.1",
  "status": "healthy",
  "timestamp": 1700000000.0
}
```

### Metrics & Monitoring

| Metric | Source | Alert Threshold |
|--------|--------|-----------------|
| Request latency | X-Process-Time header | p95 > 500ms |
| Error rate | Log aggregation | > 1% |
| Job failures | processing_jobs table | > 3 consecutive |
| DB connections | PostgreSQL | > 80% pool |

---

## Appendix

### Technology Decisions

See [ADR documents](./adr/) for detailed decision records.

### Related Documents

- [API Documentation](./API.md)
- [Database Schema](./DATABASE.md)
- [Development Guide](./DEVELOPMENT.md)
- [Deployment Runbook](./RUNBOOK.md)

---

