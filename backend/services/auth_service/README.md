# Auth Service

> **Port**: 8003  
> **Base Path**: `/auth/api/v1`  
> **Owner**: Backend Team

## Overview

The Auth Service handles OAuth 2.0 authentication with an external identity provider, manages tenant configurations, and validates access tokens for all API requests.

## Responsibilities

| Feature | Description |
|---------|-------------|
| **OAuth Authentication** | Login flow with external IdP |
| **Token Validation** | Verify access tokens |
| **Tenant Management** | Create/update tenant configurations |
| **Service Validation** | Validate BigQuery, SFTP, SMTP configs |

## Quick Start

```bash
# From backend directory
cd backend

# Start service
uv run uvicorn services.auth_service:app --port 8003 --reload

# Or via Makefile
make service_auth

# Verify
curl http://localhost:8003/health
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/login` | GET | Get OAuth login URL |
| `/callback` | POST | Exchange OAuth code for session |
| `/logout` | POST | Invalidate current session |
| `/validate` | GET | Validate access token |

## Architecture

```
services/auth_service/
├── main.py                      # FastAPI app entrypoint
├── api/
│   ├── dependencies.py          # FastAPI dependencies
│   └── v1/
│       ├── api.py               # Router aggregation
│       └── endpoints/
│           └── auth.py          # Auth endpoints
└── services/
    └── auth_service.py          # Authentication logic
```

## Authentication Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           OAUTH 2.0 FLOW                                 │
└─────────────────────────────────────────────────────────────────────────┘

  ┌──────────┐                                              ┌──────────────┐
  │ Frontend │                                              │ External IdP │
  └────┬─────┘                                              └──────┬───────┘
       │                                                           │
       │  1. GET /auth/api/v1/login                                │
       │─────────────────────────────▶                             │
       │                              │                            │
       │  2. Return login_url         │                            │
       │◀─────────────────────────────│                            │
       │                              │                            │
       │  3. Redirect to IdP          │                            │
       │──────────────────────────────────────────────────────────▶│
       │                              │                            │
       │  4. User authenticates       │                            │
       │                              │                            │
       │  5. Redirect with code       │                            │
       │◀──────────────────────────────────────────────────────────│
       │                              │                            │
       │  6. POST /auth/api/v1/callback                            │
       │     {code: "..."}            │                            │
       │─────────────────────────────▶│                            │
       │                              │                            │
       │                              │  7. Exchange code          │
       │                              │─────────────────────────────▶
       │                              │                            │
       │                              │  8. User info + configs    │
       │                              │◀─────────────────────────────
       │                              │                            │
       │                              │  9. Validate PostgreSQL    │
       │                              │  10. Store tenant config   │
       │                              │  11. Background: validate  │
       │                              │      BigQuery/SFTP/SMTP    │
       │                              │                            │
       │  12. Return session          │                            │
       │◀─────────────────────────────│                            │
       │                              │                            │
```

## Callback Response

```json
{
  "success": true,
  "message": "Authentication successful",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "first_name": "John",
  "username": "john@company.com",
  "business_name": "Acme Corp",
  "access_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

## Tenant Configuration

When a user authenticates, their tenant configuration is retrieved from the external IdP and stored:

### Configuration Structure

```json
{
  "postgres_config": {
    "host": "db.example.com",
    "port": 5432,
    "database": "analytics",
    "user": "user",
    "password": "password"
  },
  "bigquery_config": {
    "project_id": "my-project",
    "dataset_id": "analytics_dataset",
    "service_account": { /* JSON credentials */ }
  },
  "sftp_config": {
    "host": "sftp.example.com",
    "port": 22,
    "username": "user",
    "password": "password"
  },
  "email_config": {
    "server": "smtp.example.com",
    "port": 587,
    "from_address": "reports@company.com",
    "username": "user",
    "password": "password",
    "use_tls": true
  }
}
```

### Validation Flow

1. **PostgreSQL** - Required, validated synchronously (blocks login if fails)
2. **BigQuery** - Optional, validated in background
3. **SFTP** - Optional, validated in background
4. **SMTP** - Optional, validated in background

```python
# Synchronous: must pass
postgres_valid = await self._test_postgres_connection_async(postgres_config)
if not postgres_valid:
    raise HTTPException(401, "PostgreSQL connection failed")

# Background: doesn't block login
asyncio.create_task(
    self._validate_and_update_services_async(
        tenant_id, bigquery_config, sftp_config, email_config
    )
)
```

## Token Validation

Other services validate tokens by calling the auth service:

```python
# In other services (analytics, data)
async def validate_token(token: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "http://localhost:8003/api/v1/validate",
            headers={"Authorization": f"Bearer {token}"}
        )
        return response.json()
```

### Validation Response

```json
{
  "valid": true,
  "message": "Token is valid",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "first_name": "John",
  "username": "john@company.com",
  "business_name": "Acme Corp"
}
```

## Configuration

### Environment Variables

```env
# Service
AUTH_SERVICE_PORT=8003
SERVICE_NAME=auth-service

# External IdP
BASE_URL=https://idp.example.com

# Database (shared)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

### Settings Class

```python
class AuthServiceSettings(BaseServiceSettings):
    SERVICE_NAME: str = "auth-service"
    SERVICE_VERSION: str = "0.0.1"
    PORT: int = 8003
    BASE_URL: str = "https://idp.example.com"
```

## Service Validation

### PostgreSQL Validation

```python
async def _test_postgres_connection_async(self, config: dict) -> bool:
    connection_string = f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    engine = create_engine(connection_string)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True
```

### BigQuery Validation

```python
async def _test_bigquery_config_async(self, config: dict) -> bool:
    required = ["project_id", "dataset_id", "service_account"]
    if not all(field in config for field in required):
        return False
    
    # Validate service account structure
    sa = config.get("service_account", {})
    required_sa = ["type", "project_id", "private_key", "client_email"]
    return all(field in sa for field in required_sa)
```

### Validation Status Storage

```sql
-- After background validation completes
UPDATE tenant_config SET
    bigquery_enabled = true,
    bigquery_validation_error = NULL,
    sftp_enabled = false,
    sftp_validation_error = 'Connection timeout',
    smtp_enabled = true,
    smtp_validation_error = NULL
WHERE id = 'tenant-uuid';
```

## Testing

```bash
# Run auth service tests
uv run pytest tests/services/auth/ -v

# Test OAuth flow (requires mock IdP)
uv run pytest tests/services/auth/test_oauth.py -v

# With coverage
uv run pytest tests/services/auth/ --cov=services.auth_service
```

## Logging

Logs are written to:
- `logs/auth-service.log` - All logs
- `logs/auth-service-error.log` - Errors only

```bash
# View auth attempts
grep "Authentication" logs/auth-service.log

# View validation errors
grep "validation" logs/auth-service-error.log
```

## Common Issues

### OAuth Code Exchange Failed

**Cause**: Invalid or expired code  
**Solution**: User must re-authenticate

```bash
# Check logs
grep "Invalid authentication code" logs/auth-service-error.log
```

### PostgreSQL Connection Failed

**Cause**: Invalid credentials or network issue  
**Solution**: User must update configuration in external IdP

```bash
grep "PostgreSQL connection failed" logs/auth-service-error.log
```

### Token Validation Returns Invalid

**Cause**: Token expired or IdP unavailable  
**Solution**: User must re-authenticate

```bash
curl "http://localhost:8003/api/v1/validate" \
  -H "Authorization: Bearer $TOKEN"
```

## Security Considerations

1. **Credentials Storage**: All credentials encrypted in `tenants.postgres_config`, etc.
2. **Token Validation**: Tokens validated against external IdP on each check
3. **PostgreSQL Required**: Login blocked if PostgreSQL connection fails
4. **Background Validation**: Non-critical services validated async

## API Documentation

Interactive API docs available at:
- Swagger UI: http://localhost:8003/docs
- ReDoc: http://localhost:8003/redoc

