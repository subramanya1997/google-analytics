# Development Guide

> **Last Updated**: November 2024  
> **Target Audience**: New developers, contributors

## Table of Contents

- [Quick Start](#quick-start)
- [Development Environment](#development-environment)
- [Project Structure](#project-structure)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Debugging](#debugging)
- [Common Tasks](#common-tasks)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites

| Tool | Version | Installation |
|------|---------|--------------|
| Python | 3.11+ | [python.org](https://www.python.org/downloads/) |
| PostgreSQL | 14+ | `brew install postgresql` (macOS) |
| uv | Latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |

### 5-Minute Setup

```bash
# 1. Navigate to backend
cd google-analytics/backend

# 2. Install dependencies
uv sync --dev

# 3. Set up environment
cp .env.example .env
# Edit .env with your PostgreSQL credentials

# 4. Initialize database
make db_setup
# Or: uv run python scripts/init_db.py

# 5. Start services
make services_start
# Or start individually:
#   make service_analytics  (port 8001)
#   make service_data       (port 8002)
#   make service_auth       (port 8003)

# 6. Verify
curl http://localhost:8001/health
```

### Environment Variables

Create a `.env` file in the backend directory:

```env
# Required: Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=analytics_user
POSTGRES_PASSWORD=your_password
POSTGRES_DATABASE=google_analytics_db

# Optional: Pool settings
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=5

# Optional: Service settings
ENVIRONMENT=DEV
DEBUG=true
LOG_LEVEL=DEBUG
```

---

## Development Environment

### IDE Setup

#### VS Code (Recommended)

Install these extensions:
- **Python** (Microsoft)
- **Pylance** (Microsoft)
- **Python Debugger** (Microsoft)
- **SQLTools** + **PostgreSQL Driver**

`.vscode/settings.json`:
```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.analysis.typeCheckingMode": "basic",
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  }
}
```

`.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Analytics Service",
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": ["services.analytics_service:app", "--port", "8001", "--reload"],
      "cwd": "${workspaceFolder}",
      "env": {"PYTHONPATH": "${workspaceFolder}"}
    },
    {
      "name": "Data Service",
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": ["services.data_service:app", "--port", "8002", "--reload"],
      "cwd": "${workspaceFolder}",
      "env": {"PYTHONPATH": "${workspaceFolder}"}
    },
    {
      "name": "Auth Service",
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": ["services.auth_service:app", "--port", "8003", "--reload"],
      "cwd": "${workspaceFolder}",
      "env": {"PYTHONPATH": "${workspaceFolder}"}
    }
  ]
}
```

#### PyCharm

1. Open project directory
2. Set Python interpreter: `.venv/bin/python`
3. Mark `backend` as Sources Root
4. Configure run configurations for each service

### Virtual Environment

The project uses `uv` for dependency management:

```bash
# Create/update virtual environment
uv sync

# Add a dependency
uv add package_name

# Add dev dependency
uv add --dev pytest

# Update all dependencies
uv sync --upgrade
```

---

## Project Structure

```
backend/
├── common/                      # Shared code across services
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py          # Pydantic settings classes
│   ├── database/
│   │   ├── __init__.py          # Exports: Base, get_async_db_session
│   │   ├── base.py              # SQLAlchemy declarative base
│   │   ├── session.py           # Engine & session management
│   │   └── tenant_config.py     # Multi-tenant config helpers
│   ├── fastapi/
│   │   ├── __init__.py
│   │   └── app_factory.py       # create_fastapi_app() factory
│   ├── models/
│   │   ├── __init__.py
│   │   ├── events.py            # Event SQLAlchemy models
│   │   ├── locations.py
│   │   ├── tenants.py
│   │   └── users.py
│   ├── logging.py               # Loguru configuration
│   └── scheduler_client.py      # External scheduler integration
│
├── database/                    # SQL schema files
│   ├── tables/                  # CREATE TABLE scripts
│   └── functions/               # PL/pgSQL function scripts
│
├── services/                    # Microservices
│   ├── analytics_service/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app entrypoint
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── dependencies.py  # FastAPI dependencies
│   │   │   └── v1/
│   │   │       ├── api.py       # Router aggregation
│   │   │       ├── endpoints/   # Endpoint modules
│   │   │       └── models/      # Pydantic request/response models
│   │   ├── database/
│   │   │   └── postgres_client.py
│   │   ├── services/            # Business logic
│   │   └── templates/           # Jinja2 email templates
│   │
│   ├── data_service/
│   │   ├── main.py
│   │   ├── api/...
│   │   ├── clients/             # BigQuery, SFTP clients
│   │   ├── database/
│   │   │   └── sqlalchemy_repository.py
│   │   └── services/
│   │       └── ingestion_service.py
│   │
│   └── auth_service/
│       ├── main.py
│       ├── api/...
│       └── services/
│           └── auth_service.py
│
├── scripts/                     # CLI scripts
│   ├── init_db.py
│   ├── clear_db.py
│   └── cancel_running_jobs.py
│
├── logs/                        # Log files (gitignored)
├── .env                         # Environment variables (gitignored)
├── pyproject.toml              # Project configuration
└── uv.lock                     # Locked dependencies
```

### Key Files Explained

| File | Purpose |
|------|---------|
| `common/fastapi/app_factory.py` | Factory that creates FastAPI apps with standard middleware |
| `common/database/session.py` | SQLAlchemy engine creation with connection pooling |
| `common/config/settings.py` | Pydantic settings classes for each service |
| `services/*/main.py` | Service entrypoint, creates FastAPI app |
| `services/*/api/v1/api.py` | Aggregates all endpoint routers |
| `services/*/database/*.py` | Database operations for the service |
| `services/*/services/*.py` | Business logic layer |

---

## Coding Standards

### Python Style Guide

We follow PEP 8 with these tools:
- **Black** for formatting
- **Flake8** for linting
- **isort** for import sorting
- **mypy** for type checking

```bash
# Format code
uv run black .

# Lint code
uv run flake8 .

# Sort imports
uv run isort .

# Type check
uv run mypy .
```

### Type Hints

Always use type hints for function parameters and return values:

```python
# ✅ Good
async def get_dashboard_stats(
    tenant_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Dict[str, Any]:
    ...

# ❌ Bad
async def get_dashboard_stats(tenant_id, start_date=None, end_date=None):
    ...
```

### Async/Await

Use async for all I/O operations:

```python
# ✅ Good - async database operation
async with get_async_db_session("analytics-service") as session:
    result = await session.execute(query)

# ❌ Bad - blocking database operation in async context
with get_db_session("analytics-service") as session:
    result = session.execute(query)  # Blocks event loop!
```

### Error Handling

Use structured logging and meaningful exceptions:

```python
from loguru import logger
from fastapi import HTTPException, status

async def process_data(tenant_id: str) -> Dict[str, Any]:
    try:
        # Business logic
        result = await some_operation()
        logger.info(f"Processed data for tenant", tenant_id=tenant_id)
        return result
    except ValueError as e:
        logger.warning(f"Invalid input", tenant_id=tenant_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Processing failed", tenant_id=tenant_id, error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing"
        )
```

### Docstrings

Use Google-style docstrings:

```python
async def get_purchase_tasks(
    tenant_id: str,
    page: int,
    limit: int,
    location_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get purchase follow-up tasks with pagination.

    Retrieves purchase events that represent sales opportunities,
    enriched with customer contact information.

    Args:
        tenant_id: UUID of the tenant.
        page: Page number (1-indexed).
        limit: Number of items per page.
        location_id: Optional branch filter.

    Returns:
        Dict containing:
            - data: List of purchase task objects
            - total: Total number of matching records
            - page: Current page number
            - limit: Items per page
            - has_more: Whether more pages exist

    Raises:
        HTTPException: If database query fails.

    Example:
        >>> result = await get_purchase_tasks("tenant-uuid", 1, 50)
        >>> print(result["total"])
        523
    """
```

### File Organization

```python
# Standard import order (enforced by isort)
# 1. Standard library
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

# 2. Third-party
from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy import text

# 3. Local imports
from common.config import get_settings
from common.database import get_async_db_session
from services.analytics_service.database import AnalyticsPostgresClient
```

---

## Testing

### Test Structure

```
tests/
├── conftest.py                  # Shared fixtures
├── unit/
│   ├── test_settings.py
│   ├── test_database.py
│   └── services/
│       ├── test_analytics.py
│       ├── test_data.py
│       └── test_auth.py
├── integration/
│   ├── test_api_analytics.py
│   ├── test_api_data.py
│   └── test_api_auth.py
└── e2e/
    └── test_full_flow.py
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=services --cov-report=html

# Run specific test file
uv run pytest tests/unit/test_settings.py

# Run tests matching pattern
uv run pytest -k "test_purchase"

# Run with verbose output
uv run pytest -v

# Run and stop on first failure
uv run pytest -x
```

### Writing Tests

```python
# tests/unit/services/test_analytics.py
import pytest
from unittest.mock import AsyncMock, patch

from services.analytics_service.database.postgres_client import AnalyticsPostgresClient


@pytest.fixture
def client():
    return AnalyticsPostgresClient()


@pytest.fixture
def mock_session():
    """Mock async database session."""
    session = AsyncMock()
    return session


class TestAnalyticsPostgresClient:
    @pytest.mark.asyncio
    async def test_get_locations_returns_list(self, client, mock_session):
        """Test that get_locations returns a list of location dicts."""
        # Arrange
        mock_result = AsyncMock()
        mock_result.fetchall.return_value = [
            type('Row', (), {
                'location_id': 'D01',
                'location_name': 'Downtown',
                'city': 'NYC',
                'state': 'NY'
            })()
        ]
        mock_session.execute.return_value = mock_result

        with patch(
            'services.analytics_service.database.postgres_client.get_async_db_session'
        ) as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            # Act
            result = await client.get_locations("tenant-uuid")
            
            # Assert
            assert len(result) == 1
            assert result[0]["locationId"] == "D01"
            assert result[0]["city"] == "NYC"


    @pytest.mark.asyncio
    async def test_get_locations_handles_empty_result(self, client, mock_session):
        """Test that get_locations returns empty list when no locations."""
        mock_result = AsyncMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result

        with patch(
            'services.analytics_service.database.postgres_client.get_async_db_session'
        ) as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            
            result = await client.get_locations("tenant-uuid")
            
            assert result == []
```

### Integration Tests

```python
# tests/integration/test_api_analytics.py
import pytest
from httpx import AsyncClient
from services.analytics_service.main import app


@pytest.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


class TestAnalyticsAPI:
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_locations_requires_auth(self, client):
        response = await client.get("/api/v1/locations")
        assert response.status_code == 401
```

---

## Debugging

### Logging

All services use Loguru for logging:

```python
from loguru import logger

# Info level
logger.info("Processing request", tenant_id=tenant_id, endpoint="/stats")

# Warning level
logger.warning("Rate limit approaching", current=95, limit=100)

# Error level with traceback
logger.error("Database query failed", error=str(e), exc_info=True)

# Debug level (only in DEV)
logger.debug("Query result", rows=len(result), query_time=elapsed)
```

Log files are in `backend/logs/`:
```
logs/
├── analytics-service.log
├── analytics-service-error.log
├── data-ingestion-service.log
├── data-ingestion-service-error.log
├── auth-service.log
└── auth-service-error.log
```

### Viewing Logs

```bash
# Real-time log viewing
tail -f logs/analytics-service.log

# Search for errors
grep -r "ERROR" logs/

# View last 100 lines
tail -100 logs/analytics-service.log
```

### Database Debugging

```python
# Enable SQL echo in .env
DATABASE_ECHO=true

# Or temporarily in code
engine = create_engine(url, echo=True)
```

### Breakpoint Debugging

```python
# Add breakpoint in code
import pdb; pdb.set_trace()

# Or use breakpoint() (Python 3.7+)
breakpoint()
```

### VS Code Debugging

1. Add breakpoints in the editor
2. Select debug configuration (e.g., "Analytics Service")
3. Press F5 to start debugging
4. Use Debug Console for inspection

---

## Common Tasks

### Adding a New Endpoint

1. **Create endpoint function**:
```python
# services/analytics_service/api/v1/endpoints/new_feature.py
from fastapi import APIRouter, Depends
from services.analytics_service.api.dependencies import get_current_tenant

router = APIRouter()

@router.get("/new-feature")
async def get_new_feature(
    tenant_id: str = Depends(get_current_tenant)
):
    # Implementation
    return {"data": "result"}
```

2. **Add to router**:
```python
# services/analytics_service/api/v1/api.py
from services.analytics_service.api.v1.endpoints import new_feature

api_router.include_router(new_feature.router, prefix="/new-feature", tags=["New Feature"])
```

### Adding a New Database Function

1. **Create SQL file**:
```sql
-- database/functions/get_new_feature.sql
CREATE OR REPLACE FUNCTION get_new_feature(
    p_tenant_id UUID,
    p_param TEXT
) RETURNS JSONB AS $$
BEGIN
    RETURN jsonb_build_object(
        'data', 'result'
    );
END;
$$ LANGUAGE plpgsql;
```

2. **Apply to database**:
```bash
make db_setup
```

3. **Call from Python**:
```python
result = await session.execute(
    text("SELECT get_new_feature(:tenant_id, :param)"),
    {"tenant_id": tenant_id, "param": param}
)
data = result.scalar()
```

### Adding a New Table

1. **Create SQL file**:
```sql
-- database/tables/new_table.sql
CREATE TABLE IF NOT EXISTS new_table (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    data TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_new_table_tenant ON new_table(tenant_id);
```

2. **Add to creation order**:
```python
# scripts/init_db.py
TABLE_CREATION_ORDER = [
    ...
    "new_table.sql",
]
```

3. **Create SQLAlchemy model** (optional):
```python
# common/models/new_table.py
from sqlalchemy import String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from common.database import Base

class NewTable(Base):
    __tablename__ = "new_table"
    
    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    data: Mapped[str] = mapped_column(String(500))
```

### Adding a New Service

1. **Create service directory**:
```
services/new_service/
├── __init__.py
├── main.py
├── api/
│   ├── __init__.py
│   ├── dependencies.py
│   └── v1/
│       ├── __init__.py
│       ├── api.py
│       └── endpoints/
│           └── __init__.py
└── services/
    └── __init__.py
```

2. **Create main.py**:
```python
from common.fastapi import create_fastapi_app
from services.new_service.api.v1.api import api_router

app = create_fastapi_app(
    service_name="new-service",
    description="New service description",
    api_router=api_router,
    root_path="/new",
)
```

3. **Add settings class**:
```python
# common/config/settings.py
class NewServiceSettings(BaseServiceSettings):
    SERVICE_NAME: str = "new-service"
    SERVICE_VERSION: str = "0.0.1"
    PORT: int = 8004
```

4. **Add to Makefile**:
```makefile
service_new:
    uv run uvicorn services.new_service:app --port 8004 --reload
```

---

## Troubleshooting

### Common Issues

#### Import Errors

```
ModuleNotFoundError: No module named 'common'
```

**Solution**: Ensure you're running from the `backend` directory:
```bash
cd backend
uv run uvicorn services.analytics_service:app --port 8001
```

#### Database Connection Failed

```
Connection refused on localhost:5432
```

**Solution**:
1. Check PostgreSQL is running: `brew services list | grep postgres`
2. Verify credentials in `.env`
3. Test connection: `psql -h localhost -U analytics_user -d google_analytics_db`

#### Port Already in Use

```
OSError: [Errno 48] Address already in use
```

**Solution**:
```bash
# Find process using port
lsof -i :8001

# Kill process
kill -9 <PID>
```

#### Async Session Errors

```
RuntimeError: Task attached to a different loop
```

**Solution**: Ensure you're using async session in async context:
```python
# ✅ Correct
async with get_async_db_session("service") as session:
    ...

# ❌ Wrong - mixing sync/async
with get_db_session("service") as session:
    await session.execute(...)  # Error!
```

### Getting Help

1. Check logs: `tail -f logs/*.log`
2. Ask in team Slack channel
3. Check the documentation

---

