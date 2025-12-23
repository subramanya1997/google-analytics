# Azure Functions Alignment with data_service

This document summarizes the changes made to align the Azure Functions implementation with the FastAPI data_service for consistency and correctness.

## Date: 2025-12-24

## Changes Made

### 1. Fixed `data_types` Column Type (CRITICAL FIX)
**File**: `backend/services/data_service_functions/shared/database.py`

**Issue**: Azure Functions was trying to cast `data_types` to `TEXT[]` (array), but the database column is `JSONB`.

**Fix in `create_processing_job()`**:
```python
# BEFORE (WRONG):
data_types_array = data_types
stmt = text("""
    INSERT INTO processing_jobs (...)
    VALUES (..., CAST(:data_types AS TEXT[]), ...)
""")

# AFTER (CORRECT):
data_types_json = json.dumps(data_types)
stmt = text("""
    INSERT INTO processing_jobs (...)
    VALUES (..., CAST(:data_types AS jsonb), ...)
""")
```

**Note**: Using `CAST(:param AS jsonb)` instead of `:param::jsonb` because SQLAlchemy's text() with asyncpg driver requires the CAST() syntax for proper parameter binding.

**Additional Fix**: Must include `progress` and `records_processed` columns in INSERT with empty JSON objects (`{}`) since:
- Database schema: `progress jsonb NOT NULL`, `records_processed jsonb NOT NULL`
- SQLAlchemy ORM model uses `default=dict` which only works with ORM, not raw SQL

```python
# Must explicitly provide these NOT NULL columns:
progress_json = json.dumps(job_data.get("progress", {}))
records_processed_json = json.dumps(job_data.get("records_processed", {}))

stmt = text("""
    INSERT INTO processing_jobs (..., progress, records_processed, ...)
    VALUES (..., CAST(:progress AS jsonb), CAST(:records_processed AS jsonb), ...)
""")
```

**Reference**: 
- Database schema: `backend/database/tables/processing_jobs.sql` line 7: `data_types jsonb NOT NULL`
- SQLAlchemy model: `backend/common/models/control.py` line 20: `data_types: Mapped[dict] = mapped_column(JSONB)`

---

### 2. Fixed `progress` and `records_processed` JSONB Casting
**File**: `backend/services/data_service_functions/shared/database.py`

**Issue**: `update_job_status()` was JSON-encoding the fields but not casting them to JSONB in SQL.

**Fix**:
```python
# BEFORE:
set_clauses.append("progress = :progress")
set_clauses.append("records_processed = :records_processed")

# AFTER:
set_clauses.append("progress = CAST(:progress AS jsonb)")
set_clauses.append("records_processed = CAST(:records_processed AS jsonb)")
```

**Note**: Using `CAST(:param AS jsonb)` syntax is required for SQLAlchemy's text() with asyncpg driver.

---

### 3. Added Explicit tenant_id Filtering in Config Queries
**File**: `backend/services/data_service_functions/shared/database.py`

**Issue**: Queries used `LIMIT 1` instead of explicitly filtering by `tenant_id` and `is_active`.

**Changes in**:
- `get_tenant_service_status()`
- `get_tenant_bigquery_config()`
- `get_tenant_sftp_config()`

**Fix**:
```sql
-- BEFORE:
SELECT ... FROM tenant_config LIMIT 1

-- AFTER (matches data_service pattern):
SELECT ... FROM tenant_config 
WHERE id = :tenant_id AND is_active = true
```

**Reference**: `backend/common/database/tenant_config.py` line 55-56

**Rationale**:
- Each tenant database has a single `tenant_config` row where `id = tenant_id`
- Explicit filtering is clearer and safer than relying on `LIMIT 1`
- Matches the pattern used in `backend/common/database/tenant_config.py`
- Adds `is_active` check for proper tenant status validation

---

### 4. Fixed BigQuery Config Key Name
**File**: `backend/services/data_service_functions/shared/database.py`

**Issue**: `get_tenant_bigquery_config()` returned `"credentials"` key, but `BigQueryClient` expects `"service_account"`.

**Fix**:
```python
# BEFORE:
return {
    "project_id": ...,
    "dataset_id": ...,
    "credentials": ...  # WRONG KEY
}

# AFTER:
return {
    "project_id": ...,
    "dataset_id": ...,
    "service_account": ...  # CORRECT KEY
}
```

**Also added JSON parsing** for string-encoded credentials:
```python
credentials = row.get("bigquery_credentials")
if isinstance(credentials, str):
    credentials = json.loads(credentials)
```

**Reference**: 
- `backend/services/data_service/clients/bigquery_client.py` line 32: `bigquery_config["service_account"]`
- `backend/services/data_service_functions/clients/bigquery_client.py` line 32: `bigquery_config["service_account"]`

---

## Impact

These changes ensure:
1. ✅ **Data integrity**: JSONB fields are properly stored and queried
2. ✅ **Consistency**: Azure Functions match data_service patterns
3. ✅ **Safety**: Explicit tenant filtering and status checks
4. ✅ **Compatibility**: BigQuery client receives correct config format
5. ✅ **Maintainability**: Code follows same patterns across services

---

## Testing Recommendations

After deployment, test:
1. Creating ingestion jobs with various data_types arrays
2. Updating job progress and records_processed
3. Retrieving BigQuery/SFTP configurations
4. Verifying tenant isolation (queries only return data for correct tenant)

---

## Related Files

### Database Schema
- `backend/database/tables/processing_jobs.sql` - Processing jobs table definition
- `backend/database/tables/tenant_config.sql` - Tenant config table definition

### Models
- `backend/common/models/control.py` - SQLAlchemy models for control tables
- `backend/common/models/tenants.py` - TenantConfig model

### Data Service (Reference Implementation)
- `backend/services/data_service/database/sqlalchemy_repository.py` - Repository pattern
- `backend/common/database/tenant_config.py` - Tenant config manager
- `backend/services/data_service/clients/bigquery_client.py` - BigQuery client

### Azure Functions (Updated)
- `backend/services/data_service_functions/shared/database.py` - All fixes applied here
- `backend/services/data_service_functions/services/ingestion_service.py` - Uses fixed repository
- `backend/services/data_service_functions/clients/bigquery_client.py` - Expects correct config format

