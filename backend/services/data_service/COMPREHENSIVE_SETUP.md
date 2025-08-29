# 🚀 Comprehensive Analytics Data Ingestion Setup

## ⚠️ CRITICAL: Complete Table Setup Required

This service now provides **comprehensive analytics** including:
- Purchase tracking & revenue analysis
- Cart abandonment recovery
- Search analysis (successful & failed searches)
- Product view tracking
- Performance analysis
- Multi-location analytics

## 📋 Required Database Tables

### 1. Create Tables in Supabase Dashboard

**IMPORTANT**: You must create these tables manually in your Supabase dashboard before running the service.

Go to your Supabase project → SQL Editor → New Query and execute these SQL statements:

#### Core Tables:

```sql
-- Tenants table
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) UNIQUE,
    bigquery_project_id VARCHAR(255),
    bigquery_dataset_id VARCHAR(255),
    bigquery_credentials JSONB,
    sftp_config JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_tenants_name ON tenants(name);
CREATE INDEX IF NOT EXISTS idx_tenants_domain ON tenants(domain);

-- Processing Jobs table
CREATE TABLE IF NOT EXISTS processing_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    job_id VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(50) NOT NULL,
    data_types JSONB,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    progress JSONB DEFAULT '{}',
    records_processed JSONB DEFAULT '{}',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_tenant ON processing_jobs(tenant_id);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_status ON processing_jobs(status);
CREATE INDEX IF NOT EXISTS idx_processing_jobs_dates ON processing_jobs(start_date, end_date);
```

#### Reference Data Tables:

```sql
-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    user_id INTEGER NOT NULL,
    name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    office_phone VARCHAR(50),
    customer_name VARCHAR(255),
    customer_erp_id VARCHAR(100),
    user_type VARCHAR(100),
    branch_id VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(tenant_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_users_tenant_user ON users(tenant_id, user_id);
CREATE INDEX IF NOT EXISTS idx_users_branch ON users(branch_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Locations table
CREATE TABLE IF NOT EXISTS locations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    location_id VARCHAR(100) NOT NULL,
    warehouse_code VARCHAR(100),
    warehouse_name VARCHAR(255),
    name VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(tenant_id, location_id)
);
CREATE INDEX IF NOT EXISTS idx_locations_tenant_location ON locations(tenant_id, location_id);
CREATE INDEX IF NOT EXISTS idx_locations_warehouse ON locations(warehouse_code);
CREATE INDEX IF NOT EXISTS idx_locations_city_state ON locations(city, state);
```

#### Analytics Event Tables:

```sql
-- Purchase events (revenue tracking)
CREATE TABLE IF NOT EXISTS purchase (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    event_date DATE NOT NULL,
    event_timestamp VARCHAR(50),
    user_pseudo_id VARCHAR(255),
    user_prop_webuserid VARCHAR(100),
    user_prop_default_branch_id VARCHAR(100),
    param_ga_session_id VARCHAR(100),
    param_transaction_id VARCHAR(100),
    param_page_title VARCHAR(500),
    param_page_location TEXT,
    ecommerce_purchase_revenue DECIMAL(15,2),
    items_json JSONB,
    device_category VARCHAR(50),
    device_operating_system VARCHAR(50),
    geo_country VARCHAR(100),
    geo_city VARCHAR(100),
    raw_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_purchase_tenant_date ON purchase(tenant_id, event_date);
CREATE INDEX IF NOT EXISTS idx_purchase_session ON purchase(param_ga_session_id);
CREATE INDEX IF NOT EXISTS idx_purchase_user ON purchase(user_prop_webuserid);
CREATE INDEX IF NOT EXISTS idx_purchase_branch ON purchase(user_prop_default_branch_id);
CREATE INDEX IF NOT EXISTS idx_purchase_transaction ON purchase(param_transaction_id);

-- Cart abandonment tracking
CREATE TABLE IF NOT EXISTS add_to_cart (
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
    first_item_item_id VARCHAR(255),
    first_item_item_name VARCHAR(500),
    first_item_item_category VARCHAR(255),
    first_item_price DECIMAL(10,2),
    first_item_quantity INTEGER,
    items_json JSONB,
    device_category VARCHAR(50),
    device_operating_system VARCHAR(50),
    geo_country VARCHAR(100),
    geo_city VARCHAR(100),
    raw_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_add_to_cart_tenant_date ON add_to_cart(tenant_id, event_date);
CREATE INDEX IF NOT EXISTS idx_add_to_cart_session ON add_to_cart(param_ga_session_id);
CREATE INDEX IF NOT EXISTS idx_add_to_cart_user ON add_to_cart(user_prop_webuserid);
CREATE INDEX IF NOT EXISTS idx_add_to_cart_branch ON add_to_cart(user_prop_default_branch_id);

-- Page view tracking
CREATE TABLE IF NOT EXISTS page_view (
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
    raw_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_page_view_tenant_date ON page_view(tenant_id, event_date);
CREATE INDEX IF NOT EXISTS idx_page_view_session ON page_view(param_ga_session_id);
CREATE INDEX IF NOT EXISTS idx_page_view_user ON page_view(user_prop_webuserid);
CREATE INDEX IF NOT EXISTS idx_page_view_branch ON page_view(user_prop_default_branch_id);

-- Successful search tracking
CREATE TABLE IF NOT EXISTS view_search_results (
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
    raw_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_view_search_results_tenant_date ON view_search_results(tenant_id, event_date);
CREATE INDEX IF NOT EXISTS idx_view_search_results_session ON view_search_results(param_ga_session_id);
CREATE INDEX IF NOT EXISTS idx_view_search_results_user ON view_search_results(user_prop_webuserid);
CREATE INDEX IF NOT EXISTS idx_view_search_results_branch ON view_search_results(user_prop_default_branch_id);
CREATE INDEX IF NOT EXISTS idx_view_search_results_term ON view_search_results(param_search_term);

-- Failed search analysis (CRITICAL for search optimization)
CREATE TABLE IF NOT EXISTS no_search_results (
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
    raw_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_no_search_results_tenant_date ON no_search_results(tenant_id, event_date);
CREATE INDEX IF NOT EXISTS idx_no_search_results_session ON no_search_results(param_ga_session_id);
CREATE INDEX IF NOT EXISTS idx_no_search_results_user ON no_search_results(user_prop_webuserid);
CREATE INDEX IF NOT EXISTS idx_no_search_results_branch ON no_search_results(user_prop_default_branch_id);
CREATE INDEX IF NOT EXISTS idx_no_search_results_term ON no_search_results(param_no_search_results_term);

-- Product view tracking
CREATE TABLE IF NOT EXISTS view_item (
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
    first_item_price DECIMAL(10,2),
    param_page_title VARCHAR(500),
    param_page_location TEXT,
    items_json JSONB,
    device_category VARCHAR(50),
    device_operating_system VARCHAR(50),
    geo_country VARCHAR(100),
    geo_city VARCHAR(100),
    raw_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_view_item_tenant_date ON view_item(tenant_id, event_date);
CREATE INDEX IF NOT EXISTS idx_view_item_session ON view_item(param_ga_session_id);
CREATE INDEX IF NOT EXISTS idx_view_item_user ON view_item(user_prop_webuserid);
CREATE INDEX IF NOT EXISTS idx_view_item_branch ON view_item(user_prop_default_branch_id);
CREATE INDEX IF NOT EXISTS idx_view_item_item_id ON view_item(first_item_item_id);

-- Task tracking
CREATE TABLE IF NOT EXISTS task_tracking (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    task_id VARCHAR(255) NOT NULL,
    task_type VARCHAR(100) NOT NULL,
    completed BOOLEAN DEFAULT false,
    notes TEXT,
    completed_at TIMESTAMP WITH TIME ZONE,
    completed_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(tenant_id, task_id, task_type)
);
CREATE INDEX IF NOT EXISTS idx_task_tracking_tenant ON task_tracking(tenant_id);
CREATE INDEX IF NOT EXISTS idx_task_tracking_type ON task_tracking(task_type);
CREATE INDEX IF NOT EXISTS idx_task_tracking_completed ON task_tracking(completed);
```

### 2. Configuration Files

Ensure your configuration files are properly set up:

#### `config/supabase.json`:
```json
{
  "project_url": "https://your-project.supabase.co",
  "anon_key": "your-anon-key",
  "service_role_key": "your-service-role-key"
}
```

#### `config/bigquery.json`:
```json
{
  "project_id": "your-gcp-project",
  "dataset_id": "your-dataset",
  "service_account": {
    "type": "service_account",
    "project_id": "your-project",
    "private_key_id": "...",
    "private_key": "...",
    "client_email": "...",
    "client_id": "...",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "...",
    "universe_domain": "googleapis.com"
  }
}
```

#### `config/sftp.json`:
```json
{
  "host": "your-sftp-host",
  "port": 22,
  "username": "your-username",
  "password": "your-password",
  "remote_path": "hercules",
  "data_dir": "data",
  "user_file": "UserReport.xlsx",
  "locations_file": "Locations_List1750281613134.xlsx"
}
```

## 🎯 Analytics Capabilities

With this setup, you can now track:

### 💰 Revenue Analytics
- Purchase tracking with transaction IDs
- Revenue by location/branch
- Purchase conversion rates

### 🛒 Cart Abandonment
- Sessions with cart additions but no purchases
- Cart value analysis
- Recovery opportunities

### 🔍 Search Analysis
- Successful searches (`view_search_results`)
- Failed searches (`no_search_results`) - **Critical for search optimization**
- Popular search terms by location

### 👁️ Product Analytics
- Product view tracking
- Popular products by location
- View-to-purchase conversion

### 📊 Performance Analysis
- Page bounce rates
- Session duration analysis
- User journey tracking

### 🏢 Multi-Location Intelligence
- Branch-wise performance comparison
- Location-specific user behavior
- Geographic analytics

## 🚀 Running the Service

After creating all tables:

```bash
cd backend/services/data_service
poetry install
poetry run python run_windows.py
```

## 🧪 Testing Data Ingestion

Use the API endpoint:

```bash
POST http://localhost:8001/api/v1/data/ingest
```

```json
{
  "tenant_id": "your-tenant",
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "data_types": ["events", "users", "locations"],
  "force_refresh": true
}
```

This will now process:
- All 6 event types from BigQuery
- User data from SFTP
- Location data from SFTP

## ✅ Verification

After ingestion, verify data in Supabase:
- Check each event table for data
- Verify users and locations are populated
- Check processing_jobs table for job status
