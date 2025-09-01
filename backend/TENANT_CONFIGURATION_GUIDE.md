# Tenant Configuration System

This document describes the tenant-based configuration system that allows each tenant to have their own database, BigQuery, and SFTP configurations stored in the database and retrieved dynamically.

## Overview

The system has been updated to support true multi-tenancy where:
1. **Authentication Service**: Stores tenant configurations in the database during authentication
2. **Data Service**: Uses tenant-specific configurations from the database for BigQuery and SFTP operations
3. **Analytics Service**: Uses tenant-specific database configurations for data access

## Architecture

### 1. Configuration Storage

All tenant configurations are stored in the `tenants` table with the following structure:

```sql
CREATE TABLE tenants (
    id UUID PRIMARY KEY,
    name VARCHAR(255),
    domain VARCHAR(255),
    bigquery_project_id VARCHAR(255),
    bigquery_dataset_id VARCHAR(255),
    bigquery_credentials JSON,
    postgres_config JSON,
    sftp_config JSON,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);
```

### 2. Authentication Flow

When a user authenticates via `/api/v1/auth/authenticate`:

1. **Code Validation**: Validates authentication code with external service
2. **Settings Retrieval**: Fetches tenant configurations from external API
3. **Configuration Validation**: Tests all configurations (PostgreSQL, BigQuery, SFTP)
4. **Configuration Upsert**: Always updates tenant configurations with latest values from API
5. **Response**: Returns success with `tenant_id` for frontend use

**Important**: The system always updates tenant configurations on every authentication, ensuring that any changes made in the external authentication system are immediately reflected in the database. This means:
- New tenants get their configurations stored
- Existing tenants get their configurations refreshed with the latest values
- Configuration changes are automatically synchronized

### 3. Configuration Retrieval

#### Common Utilities

**Location**: `common/database/tenant_config.py`

```python
from common.database import get_tenant_bigquery_config, get_tenant_postgres_config, get_tenant_sftp_config

# Get configurations for a tenant
bigquery_config = get_tenant_bigquery_config(tenant_id)
postgres_config = get_tenant_postgres_config(tenant_id)
sftp_config = get_tenant_sftp_config(tenant_id)
```

#### Tenant Session Management

**Location**: `common/database/tenant_session.py`

```python
from common.database import get_tenant_session, get_tenant_engine

# Get tenant-specific database session
session = get_tenant_session(tenant_id, "service-name")

# Get tenant-specific database engine
engine = get_tenant_engine(tenant_id, "service-name")
```

## Service Integration

### 1. Data Service

**Location**: `services/data_service/app/clients/tenant_client_factory.py`

The data service uses tenant-aware client factories:

```python
from services.data_service.app.clients.tenant_client_factory import (
    get_tenant_enhanced_bigquery_client,
    get_tenant_azure_sftp_client
)

# Create tenant-specific clients
bigquery_client = get_tenant_enhanced_bigquery_client(tenant_id)
sftp_client = get_tenant_azure_sftp_client(tenant_id)
```

**Updated Services**:
- `ComprehensiveDataProcessingService` now uses tenant configurations
- BigQuery operations use tenant-specific credentials
- SFTP operations use tenant-specific connection details

### 2. Analytics Service

**Location**: `services/analytics_service/app/database/tenant_postgres_client.py`

The analytics service uses tenant-aware database clients:

```python
from services.analytics_service.app.database.dependencies import get_tenant_analytics_db_client

# Get tenant-specific analytics client
analytics_client = get_tenant_analytics_db_client(tenant_id)

# Use client for tenant-specific operations
locations = analytics_client.get_locations(tenant_id)
users = analytics_client.get_users(tenant_id)
stats = analytics_client.get_analytics_stats(tenant_id)
```

### 3. Auth Service

**Location**: `services/auth_service/app/services/auth_service.py`

The auth service validates and stores tenant configurations:

```python
# Validates all configurations
validation_result = self._validate_configurations(settings_data)

# Stores configurations in database
self._ensure_tenant_exists(account_id, postgres_config, bigquery_config, sftp_config)
```

## Usage Examples

### 1. Data Ingestion

```python
# The data service automatically uses tenant configurations
POST /api/v1/data/ingest
{
    "tenant_id": "e0f01854-6c2e-4b76-bf7b-67f3c28dbdac",
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "data_types": ["events", "users", "locations"]
}
```

### 2. Analytics Queries

```python
# Analytics endpoints automatically use tenant-specific database
GET /api/v1/analytics/stats?tenant_id=e0f01854-6c2e-4b76-bf7b-67f3c28dbdac
```

### 3. Authentication

```python
# Authentication stores tenant configurations
POST /api/v1/auth/authenticate
{
    "code": "authentication_code_here"
}

# Response includes tenant_id and user info for subsequent requests
{
    "success": true,
    "message": "Authentication successful",
    "tenant_id": "e0f01854-6c2e-4b76-bf7b-67f3c28dbdac",
    "first_name": "Subramanya",
    "username": "subramanyanagabhushan@gmail.com"
}
```

## Configuration Format

### BigQuery Configuration

```json
{
    "project_id": "your-project-id",
    "dataset_id": "your-dataset-id",
    "service_account": {
        "type": "service_account",
        "project_id": "your-project-id",
        "private_key_id": "key-id",
        "private_key": "-----BEGIN PRIVATE KEY-----\n...",
        "client_email": "service-account@project.iam.gserviceaccount.com",
        "client_id": "client-id",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token"
    }
}
```

### PostgreSQL Configuration

```json
{
    "host": "database-host",
    "port": 5432,
    "user": "username",
    "password": "password",
    "database": "database_name",
    "connect_timeout_seconds": 10,
    "sslmode": "require"
}
```

### SFTP Configuration

```json
{
    "host": "sftp-host",
    "port": 22,
    "username": "sftp-username",
    "password": "sftp-password",
    "remote_path": "remote-directory",
    "data_dir": "data-subdirectory",
    "user_file": "UserReport.xlsx",
    "locations_file": "Locations_List.xlsx"
}
```

## Migration Notes

### Existing Deployments

1. **Database Migration**: Add `postgres_config` column to `tenants` table
2. **Configuration**: Existing static configurations in `config/` directory are still used as fallbacks
3. **Gradual Migration**: Services can be migrated tenant by tenant

### Backward Compatibility

- Services maintain backward compatibility with static configurations
- Tenant-specific configurations take precedence over static ones
- Missing tenant configurations fall back to static configurations

## Security Considerations

1. **Encryption**: Sensitive configuration data is stored as JSON in the database
2. **Access Control**: Only authenticated requests can access tenant configurations
3. **Validation**: All configurations are validated before storage
4. **Connection Pooling**: Tenant-specific database connections use proper pooling

## Monitoring and Logging

- All tenant configuration operations are logged with tenant IDs
- Connection failures are logged with specific tenant context
- Configuration validation results are tracked per tenant

## Configuration Synchronization

### Automatic Updates

The system ensures configuration synchronization through:

1. **Authentication-Based Sync**: Every authentication call updates tenant configurations
2. **Latest Values Priority**: External API values always override database values
3. **Immediate Effect**: Configuration changes take effect on next service request
4. **No Manual Intervention**: Administrators don't need to manually update configurations

### Synchronization Flow

```
External Auth System → Authentication API → Database Update → Service Usage
```

1. **External Changes**: Configuration changes made in external authentication system
2. **Authentication Trigger**: User authenticates, triggering configuration fetch
3. **Database Update**: Latest configurations automatically stored in database
4. **Service Access**: Services immediately use updated configurations

### Benefits

- **Always Current**: Configurations are always up-to-date with external system
- **Zero Downtime**: Configuration updates happen without service interruption
- **Automatic Sync**: No manual configuration management required
- **Consistency**: All services use the same latest configuration values

## Future Enhancements

1. **Configuration Encryption**: Encrypt sensitive data in the database
2. **Configuration Versioning**: Track configuration changes over time
3. **Health Monitoring**: Monitor tenant-specific service health
4. **Configuration UI**: Admin interface for managing tenant configurations
5. **Webhook Integration**: Real-time configuration updates via webhooks
