# Database Documentation

> **Database**: PostgreSQL 14+  
> **Last Updated**: November 2024  
> **Owner**: Backend Team

## Table of Contents

- [Overview](#overview)
- [Schema Diagram](#schema-diagram)
- [Tables](#tables)
- [Functions](#functions)
- [Indexes](#indexes)
- [Data Types](#data-types)
- [Migration Strategy](#migration-strategy)
- [Performance Tuning](#performance-tuning)

---

## Overview

### Database Design Principles

1. **Multi-Tenant Isolation**: All tables include `tenant_id` for row-level tenant isolation
2. **Event Sourcing**: Raw event data preserved in JSONB for future reprocessing
3. **Denormalized Analytics**: PostgreSQL functions aggregate data at query time
4. **Upsert Patterns**: Date-range replacements for idempotent data ingestion

### Connection Configuration

```env
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=analytics_user
POSTGRES_PASSWORD=<secure_password>
POSTGRES_DATABASE=google_analytics_db
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=5
```

---

## Schema Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CORE TABLES                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐                                                        │
│  │  tenant_config   │◄──────────────────────────────────────────────┐       │
│  ├──────────────────┤                                               │       │
│  │ id (PK, UUID)    │                                               │       │
│  │ name             │                                               │       │
│  │ bigquery_*       │       ┌──────────────────┐                    │       │
│  │ postgres_config  │       │     users        │                    │       │
│  │ sftp_config      │       ├──────────────────┤                    │       │
│  │ email_config     │       │ user_id (PK)     │                    │       │
│  │ is_active        │       │ tenant_id (FK)───┼────────────────────┤       │
│  └──────────────────┘       │ email            │                    │       │
│                             │ company_name     │                    │       │
│                             └──────────────────┘                    │       │
│                                                                     │       │
│  ┌──────────────────┐       ┌──────────────────┐                    │       │
│  │    locations     │       │ processing_jobs  │                    │       │
│  ├──────────────────┤       ├──────────────────┤                    │       │
│  │ location_id (PK) │       │ id (PK, UUID)    │                    │       │
│  │ tenant_id (FK)───┼───────┼─tenant_id (FK)───┼────────────────────┤       │
│  │ location_name    │       │ job_id           │                    │       │
│  │ city, state      │       │ status           │                    │       │
│  └──────────────────┘       │ data_types       │                    │       │
│                             │ records_processed│                    │       │
│                             └──────────────────┘                    │       │
│                                                                     │       │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                             EVENT TABLES                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│  │     purchase     │  │   add_to_cart    │  │    page_view     │          │
│  ├──────────────────┤  ├──────────────────┤  ├──────────────────┤          │
│  │ id (PK, UUID)    │  │ id (PK, UUID)    │  │ id (PK, UUID)    │          │
│  │ tenant_id (FK)   │  │ tenant_id (FK)   │  │ tenant_id (FK)   │          │
│  │ event_date       │  │ event_date       │  │ event_date       │          │
│  │ event_timestamp  │  │ event_timestamp  │  │ event_timestamp  │          │
│  │ user_pseudo_id   │  │ user_pseudo_id   │  │ user_pseudo_id   │          │
│  │ user_prop_*      │  │ user_prop_*      │  │ user_prop_*      │          │
│  │ param_*          │  │ param_*          │  │ param_*          │          │
│  │ revenue          │  │ first_item_*     │  │ page_referrer    │          │
│  │ items_json       │  │ items_json       │  │ device_*         │          │
│  │ device_*, geo_*  │  │ device_*, geo_*  │  │ geo_*            │          │
│  │ raw_data (JSONB) │  │ raw_data (JSONB) │  │ raw_data (JSONB) │          │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘          │
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│  │    view_item     │  │view_search_result│  │ no_search_results│          │
│  ├──────────────────┤  ├──────────────────┤  ├──────────────────┤          │
│  │ id (PK, UUID)    │  │ id (PK, UUID)    │  │ id (PK, UUID)    │          │
│  │ tenant_id (FK)   │  │ tenant_id (FK)   │  │ tenant_id (FK)   │          │
│  │ event_date       │  │ event_date       │  │ event_date       │          │
│  │ first_item_*     │  │ search_term      │  │ search_term      │          │
│  │ items_json       │  │ param_*          │  │ param_*          │          │
│  │ raw_data (JSONB) │  │ raw_data (JSONB) │  │ raw_data (JSONB) │          │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                            EMAIL TABLES                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│  │branch_email_map  │  │email_sending_jobs│  │email_send_history│          │
│  ├──────────────────┤  ├──────────────────┤  ├──────────────────┤          │
│  │ id (PK, UUID)    │  │ id (PK, UUID)    │  │ id (PK, UUID)    │          │
│  │ tenant_id (FK)   │  │ tenant_id (FK)   │  │ tenant_id (FK)   │          │
│  │ branch_code      │  │ job_id           │  │ job_id           │          │
│  │ branch_name      │  │ status           │  │ branch_code      │          │
│  │ sales_rep_email  │  │ report_date      │  │ sales_rep_email  │          │
│  │ sales_rep_name   │  │ target_branches  │  │ status           │          │
│  │ is_enabled       │  │ total_emails     │  │ smtp_response    │          │
│  └──────────────────┘  │ emails_sent      │  │ error_message    │          │
│                        │ emails_failed    │  │ sent_at          │          │
│                        └──────────────────┘  └──────────────────┘          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Tables

### tenant_config

Tenant configuration table (single-tenant-per-database model). Each database has exactly one configuration row.

```sql
CREATE TABLE tenant_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    
    -- BigQuery configuration (optional)
    bigquery_project_id VARCHAR(255),
    bigquery_dataset_id VARCHAR(255),
    bigquery_credentials JSONB,
    bigquery_enabled BOOLEAN DEFAULT TRUE,
    bigquery_validation_error TEXT,
    
    -- PostgreSQL configuration (REQUIRED)
    postgres_config JSONB NOT NULL,
    
    -- SFTP configuration (optional)
    sftp_config JSONB,
    sftp_enabled BOOLEAN DEFAULT TRUE,
    sftp_validation_error TEXT,
    
    -- Email configuration (optional)
    email_config JSONB,
    smtp_enabled BOOLEAN DEFAULT TRUE,
    smtp_validation_error TEXT,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key, auto-generated |
| `name` | VARCHAR(255) | Tenant display name |
| `bigquery_*` | Various | GA4 BigQuery connection config |
| `postgres_config` | JSONB | Tenant's PostgreSQL connection |
| `sftp_config` | JSONB | SFTP server for master data |
| `email_config` | JSONB | SMTP configuration |
| `*_enabled` | BOOLEAN | Service availability flags |
| `*_validation_error` | TEXT | Last validation error message |

---

### users

Customer/user master data from SFTP.

```sql
CREATE TABLE users (
    user_id VARCHAR(100) NOT NULL,
    tenant_id UUID NOT NULL REFERENCES tenant_config(id),
    buying_company_name VARCHAR(255),
    email VARCHAR(255),
    cell_phone VARCHAR(50),
    office_phone VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    PRIMARY KEY (tenant_id, user_id)
);

CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);
```

| Column | Type | Description |
|--------|------|-------------|
| `user_id` | VARCHAR(100) | User identifier from source system |
| `tenant_id` | UUID | Foreign key to tenant_config |
| `buying_company_name` | VARCHAR(255) | Customer company name |
| `email` | VARCHAR(255) | Contact email |
| `cell_phone` | VARCHAR(50) | Mobile phone |
| `office_phone` | VARCHAR(50) | Office phone |

---

### locations

Branch/location master data from SFTP.

```sql
CREATE TABLE locations (
    location_id VARCHAR(100) NOT NULL,
    tenant_id UUID NOT NULL REFERENCES tenant_config(id),
    location_name VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    PRIMARY KEY (tenant_id, location_id)
);

CREATE INDEX idx_locations_tenant ON locations(tenant_id);
```

| Column | Type | Description |
|--------|------|-------------|
| `location_id` | VARCHAR(100) | Branch code (e.g., "D01") |
| `tenant_id` | UUID | Foreign key to tenant_config |
| `location_name` | VARCHAR(255) | Branch display name |
| `city` | VARCHAR(100) | City name |
| `state` | VARCHAR(100) | State/province |

---

### purchase

E-commerce purchase events from GA4.

```sql
CREATE TABLE purchase (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    event_date DATE NOT NULL,
    event_timestamp VARCHAR(50),
    
    -- User identification
    user_pseudo_id VARCHAR(255),
    user_prop_webuserid VARCHAR(100),
    user_prop_default_branch_id VARCHAR(100),
    
    -- Session & transaction
    param_ga_session_id VARCHAR(100),
    param_transaction_id VARCHAR(100),
    param_page_title VARCHAR(500),
    param_page_location TEXT,
    
    -- Revenue
    ecommerce_purchase_revenue DECIMAL(15, 2),
    items_json JSONB,
    
    -- Device & geo
    device_category VARCHAR(50),
    device_operating_system VARCHAR(50),
    geo_country VARCHAR(100),
    geo_city VARCHAR(100),
    
    -- Raw data for reprocessing
    raw_data JSONB
);

CREATE INDEX idx_purchase_tenant_date ON purchase(tenant_id, event_date);
CREATE INDEX idx_purchase_branch ON purchase(tenant_id, user_prop_default_branch_id);
CREATE INDEX idx_purchase_user ON purchase(tenant_id, user_prop_webuserid);
```

---

### add_to_cart

Cart addition events from GA4.

```sql
CREATE TABLE add_to_cart (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    event_date DATE NOT NULL,
    event_timestamp VARCHAR(50),
    
    -- User identification
    user_pseudo_id VARCHAR(255),
    user_prop_webuserid VARCHAR(100),
    user_prop_default_branch_id VARCHAR(100),
    
    -- Session
    param_ga_session_id VARCHAR(100),
    param_page_title VARCHAR(500),
    param_page_location TEXT,
    
    -- First item (denormalized for quick access)
    first_item_item_id VARCHAR(255),
    first_item_item_name VARCHAR(500),
    first_item_item_category VARCHAR(255),
    first_item_price DECIMAL(10, 2),
    first_item_quantity INTEGER,
    
    -- All items
    items_json JSONB,
    
    -- Device & geo
    device_category VARCHAR(50),
    device_operating_system VARCHAR(50),
    geo_country VARCHAR(100),
    geo_city VARCHAR(100),
    
    raw_data JSONB
);

CREATE INDEX idx_add_to_cart_tenant_date ON add_to_cart(tenant_id, event_date);
CREATE INDEX idx_add_to_cart_session ON add_to_cart(tenant_id, param_ga_session_id);
```

---

### page_view

Page view events from GA4.

```sql
CREATE TABLE page_view (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    event_date DATE NOT NULL,
    event_timestamp VARCHAR(50),
    
    user_pseudo_id VARCHAR(255),
    user_prop_webuserid VARCHAR(100),
    user_prop_default_branch_id VARCHAR(100),
    
    param_ga_session_id VARCHAR(100),
    param_page_title VARCHAR(500),
    param_page_location TEXT,
    param_page_referrer TEXT,
    
    device_category VARCHAR(50),
    device_operating_system VARCHAR(50),
    geo_country VARCHAR(100),
    geo_city VARCHAR(100),
    
    raw_data JSONB
);

CREATE INDEX idx_page_view_tenant_date ON page_view(tenant_id, event_date);
CREATE INDEX idx_page_view_session ON page_view(tenant_id, param_ga_session_id);
```

---

### view_search_results

Successful search events from GA4.

```sql
CREATE TABLE view_search_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    event_date DATE NOT NULL,
    event_timestamp VARCHAR(50),
    
    user_pseudo_id VARCHAR(255),
    user_prop_webuserid VARCHAR(100),
    user_prop_default_branch_id VARCHAR(100),
    
    param_ga_session_id VARCHAR(100),
    param_search_term VARCHAR(500),
    param_page_title VARCHAR(500),
    param_page_location TEXT,
    
    device_category VARCHAR(50),
    device_operating_system VARCHAR(50),
    geo_country VARCHAR(100),
    geo_city VARCHAR(100),
    
    raw_data JSONB
);

CREATE INDEX idx_view_search_results_tenant_date ON view_search_results(tenant_id, event_date);
CREATE INDEX idx_view_search_results_term ON view_search_results(tenant_id, param_search_term);
```

---

### no_search_results

Failed search events (no results found) from GA4.

```sql
CREATE TABLE no_search_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    event_date DATE NOT NULL,
    event_timestamp VARCHAR(50),
    
    user_pseudo_id VARCHAR(255),
    user_prop_webuserid VARCHAR(100),
    user_prop_default_branch_id VARCHAR(100),
    
    param_ga_session_id VARCHAR(100),
    param_no_search_results_term VARCHAR(500),
    param_page_title VARCHAR(500),
    param_page_location TEXT,
    
    device_category VARCHAR(50),
    device_operating_system VARCHAR(50),
    geo_country VARCHAR(100),
    geo_city VARCHAR(100),
    
    raw_data JSONB
);

CREATE INDEX idx_no_search_results_tenant_date ON no_search_results(tenant_id, event_date);
CREATE INDEX idx_no_search_results_term ON no_search_results(tenant_id, param_no_search_results_term);
```

---

### view_item

Product view events from GA4.

```sql
CREATE TABLE view_item (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    event_date DATE NOT NULL,
    event_timestamp VARCHAR(50),
    
    user_pseudo_id VARCHAR(255),
    user_prop_webuserid VARCHAR(100),
    user_prop_default_branch_id VARCHAR(100),
    
    param_ga_session_id VARCHAR(100),
    first_item_item_id VARCHAR(255),
    first_item_item_name VARCHAR(500),
    first_item_item_category VARCHAR(255),
    first_item_price DECIMAL(10, 2),
    param_page_title VARCHAR(500),
    param_page_location TEXT,
    
    items_json JSONB,
    
    device_category VARCHAR(50),
    device_operating_system VARCHAR(50),
    geo_country VARCHAR(100),
    geo_city VARCHAR(100),
    
    raw_data JSONB
);

CREATE INDEX idx_view_item_tenant_date ON view_item(tenant_id, event_date);
CREATE INDEX idx_view_item_product ON view_item(tenant_id, first_item_item_id);
```

---

### processing_jobs

Data ingestion job tracking.

```sql
CREATE TABLE processing_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenant_config(id),
    job_id VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'queued',
    data_types JSONB,
    start_date DATE,
    end_date DATE,
    records_processed JSONB,
    progress JSONB,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_processing_jobs_tenant ON processing_jobs(tenant_id);
CREATE INDEX idx_processing_jobs_status ON processing_jobs(status);
CREATE INDEX idx_processing_jobs_created ON processing_jobs(created_at DESC);
```

| Status Values | Description |
|---------------|-------------|
| `queued` | Job created, waiting to start |
| `processing` | Job is running |
| `completed` | Job finished successfully |
| `failed` | Job failed with error |

---

### branch_email_mappings

Branch to sales rep email mapping.

```sql
CREATE TABLE branch_email_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenant_config(id),
    branch_code VARCHAR(50) NOT NULL,
    branch_name VARCHAR(255),
    sales_rep_email VARCHAR(255) NOT NULL,
    sales_rep_name VARCHAR(255),
    is_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_branch_email_mappings_tenant ON branch_email_mappings(tenant_id);
CREATE INDEX idx_branch_email_mappings_branch ON branch_email_mappings(tenant_id, branch_code);
```

---

### email_sending_jobs

Email job tracking.

```sql
CREATE TABLE email_sending_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenant_config(id),
    job_id VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'queued',
    report_date DATE NOT NULL,
    target_branches JSONB,
    total_emails INTEGER DEFAULT 0,
    emails_sent INTEGER DEFAULT 0,
    emails_failed INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_email_sending_jobs_tenant ON email_sending_jobs(tenant_id);
CREATE INDEX idx_email_sending_jobs_status ON email_sending_jobs(status);
```

---

### email_send_history

Individual email send records.

```sql
CREATE TABLE email_send_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenant_config(id),
    job_id VARCHAR(100),
    branch_code VARCHAR(50),
    sales_rep_email VARCHAR(255),
    sales_rep_name VARCHAR(255),
    subject VARCHAR(500),
    report_date DATE,
    status VARCHAR(50),
    smtp_response TEXT,
    error_message TEXT,
    sent_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_email_send_history_tenant ON email_send_history(tenant_id);
CREATE INDEX idx_email_send_history_job ON email_send_history(job_id);
CREATE INDEX idx_email_send_history_sent ON email_send_history(sent_at DESC);
```

---

## Functions

All analytics queries are implemented as PostgreSQL functions for optimal performance.

### get_purchase_tasks

Returns purchase follow-up opportunities with pagination and filtering.

```sql
CREATE OR REPLACE FUNCTION get_purchase_tasks(
    p_tenant_id UUID,
    p_page INTEGER,
    p_limit INTEGER,
    p_query TEXT DEFAULT NULL,
    p_location_id TEXT DEFAULT NULL,
    p_start_date DATE DEFAULT NULL,
    p_end_date DATE DEFAULT NULL
) RETURNS JSONB AS $$
...
$$ LANGUAGE plpgsql;
```

**Returns**:
```json
{
  "data": [...],
  "total": 523,
  "page": 1,
  "limit": 50,
  "has_more": true
}
```

---

### get_cart_abandonment_tasks

Returns cart abandonment recovery opportunities.

```sql
CREATE OR REPLACE FUNCTION get_cart_abandonment_tasks(
    p_tenant_id UUID,
    p_page INTEGER,
    p_limit INTEGER,
    p_query TEXT DEFAULT NULL,
    p_location_id TEXT DEFAULT NULL,
    p_start_date DATE DEFAULT NULL,
    p_end_date DATE DEFAULT NULL
) RETURNS JSONB AS $$
...
$$ LANGUAGE plpgsql;
```

**Logic**: Finds users who added to cart but didn't purchase within the date range.

---

### get_search_analysis_tasks

Returns search optimization insights.

```sql
CREATE OR REPLACE FUNCTION get_search_analysis_tasks(
    p_tenant_id UUID,
    p_page INTEGER,
    p_limit INTEGER,
    p_query TEXT DEFAULT NULL,
    p_location_id TEXT DEFAULT NULL,
    p_start_date DATE DEFAULT NULL,
    p_end_date DATE DEFAULT NULL,
    p_include_converted BOOLEAN DEFAULT FALSE
) RETURNS JSONB AS $$
...
$$ LANGUAGE plpgsql;
```

**Logic**: Aggregates search terms by frequency, identifies zero-result searches.

---

### get_repeat_visit_tasks

Returns repeat visitor engagement opportunities.

```sql
CREATE OR REPLACE FUNCTION get_repeat_visit_tasks(
    p_tenant_id UUID,
    p_page INTEGER,
    p_limit INTEGER,
    p_query TEXT DEFAULT NULL,
    p_location_id TEXT DEFAULT NULL,
    p_start_date DATE DEFAULT NULL,
    p_end_date DATE DEFAULT NULL
) RETURNS JSONB AS $$
...
$$ LANGUAGE plpgsql;
```

**Logic**: Identifies users with multiple visits who haven't purchased.

---

### get_complete_dashboard_data

Single-call dashboard data including metrics, charts, and location stats.

```sql
CREATE OR REPLACE FUNCTION get_complete_dashboard_data(
    p_tenant_id UUID,
    p_start_date DATE,
    p_end_date DATE,
    p_granularity TEXT DEFAULT 'daily',
    p_location_id TEXT DEFAULT NULL
) RETURNS JSONB AS $$
...
$$ LANGUAGE plpgsql;
```

**Returns**:
```json
{
  "metrics": {
    "totalRevenue": 1523456.78,
    "totalPurchases": 4523,
    "totalVisitors": 125000,
    "abandonedCarts": 8234
  },
  "chartData": [...],
  "locationStats": [...]
}
```

---

### get_session_history

Returns event timeline for a specific session.

```sql
CREATE OR REPLACE FUNCTION get_session_history(
    p_tenant_id UUID,
    p_session_id TEXT
) RETURNS JSONB AS $$
...
$$ LANGUAGE plpgsql;
```

---

### get_user_history

Returns event timeline for a specific user.

```sql
CREATE OR REPLACE FUNCTION get_user_history(
    p_tenant_id UUID,
    p_user_id TEXT
) RETURNS JSONB AS $$
...
$$ LANGUAGE plpgsql;
```

---

## Indexes

### Index Strategy

| Index Type | Use Case |
|------------|----------|
| **Composite (tenant_id, event_date)** | All date-range queries |
| **Composite (tenant_id, branch_id)** | Location filtering |
| **Composite (tenant_id, session_id)** | Session timeline |
| **Covering Indexes** | Aggregation queries |

### Key Indexes

```sql
-- Event tables (repeated for each)
CREATE INDEX idx_purchase_tenant_date ON purchase(tenant_id, event_date);
CREATE INDEX idx_purchase_tenant_branch ON purchase(tenant_id, user_prop_default_branch_id);
CREATE INDEX idx_purchase_tenant_user ON purchase(tenant_id, user_prop_webuserid);
CREATE INDEX idx_purchase_tenant_session ON purchase(tenant_id, param_ga_session_id);

-- Covering index for revenue aggregation
CREATE INDEX idx_purchase_revenue_covering ON purchase(
    tenant_id, event_date, user_prop_default_branch_id
) INCLUDE (ecommerce_purchase_revenue);

-- Email history
CREATE INDEX idx_email_history_tenant_date ON email_send_history(tenant_id, sent_at DESC);

-- Job tables
CREATE INDEX idx_processing_jobs_tenant_created ON processing_jobs(tenant_id, created_at DESC);
```

---

## Data Types

### JSONB Structures

#### items_json (purchase, add_to_cart, view_item)

```json
[
  {
    "item_id": "SKU-001",
    "item_name": "Industrial Widget",
    "item_category": "Widgets",
    "price": 150.00,
    "quantity": 5
  }
]
```

#### records_processed (processing_jobs)

```json
{
  "purchase": 1523,
  "add_to_cart": 8234,
  "page_view": 125000,
  "view_search_results": 45000,
  "no_search_results": 2300,
  "view_item": 67000,
  "users_processed": 5000,
  "locations_processed": 150
}
```

#### postgres_config (tenant_config)

```json
{
  "host": "db.example.com",
  "port": 5432,
  "database": "analytics",
  "user": "analytics_user",
  "password": "encrypted_password"
}
```

---

## Migration Strategy

### Adding New Tables

1. Create SQL file in `database/tables/`
2. Add to `TABLE_CREATION_ORDER` in `scripts/init_db.py`
3. Run `make db_setup` or `python scripts/init_db.py`

### Adding New Functions

1. Create SQL file in `database/functions/`
2. Run `make db_setup` (functions are idempotent with `CREATE OR REPLACE`)

### Schema Changes

For production changes:
1. Create migration script with `ALTER TABLE` statements
2. Test in staging environment
3. Apply during maintenance window
4. Update documentation

---

## Performance Tuning

### Query Optimization

```sql
-- Analyze query plans
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT * FROM get_purchase_tasks('tenant-uuid', 1, 50, NULL, NULL, '2024-01-01', '2024-01-31');

-- Update statistics
ANALYZE purchase;
ANALYZE add_to_cart;
ANALYZE page_view;
```

### Connection Pool Settings

```env
DATABASE_POOL_SIZE=10          # Connections per service instance
DATABASE_MAX_OVERFLOW=5        # Additional connections allowed
DATABASE_POOL_TIMEOUT=30       # Wait time for connection (seconds)
DATABASE_POOL_RECYCLE=1800     # Connection max age (30 minutes)
```

### Recommended PostgreSQL Settings

```ini
# postgresql.conf
shared_buffers = 2GB                    # 25% of RAM
effective_cache_size = 6GB              # 75% of RAM
work_mem = 64MB                         # For complex aggregations
maintenance_work_mem = 512MB            # For VACUUM, CREATE INDEX
random_page_cost = 1.1                  # SSD storage
effective_io_concurrency = 200          # SSD storage

# Logging
log_min_duration_statement = 1000       # Log queries > 1 second
```

---

## Backup & Recovery

### Backup Strategy

```bash
# Daily full backup
pg_dump -h localhost -U analytics_user -Fc google_analytics_db > backup_$(date +%Y%m%d).dump

# Restore
pg_restore -h localhost -U analytics_user -d google_analytics_db backup_20240101.dump
```

### Point-in-Time Recovery

Enable WAL archiving for PITR capability:
```ini
wal_level = replica
archive_mode = on
archive_command = 'cp %p /path/to/archive/%f'
```

---

