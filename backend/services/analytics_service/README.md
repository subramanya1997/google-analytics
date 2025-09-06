# Analytics Service

A FastAPI-based microservice for providing analytics and reporting capabilities for the Google Analytics intelligence system.

## Features

- **Location Analytics**: Get active locations with analytics data
- **Dashboard Statistics**: Comprehensive metrics (revenue, purchases, abandonment, etc.)
- **Task Management**: Track and manage analysis tasks
- **Session Analytics**: Detailed session history and user behavior
- **User Analytics**: Cross-session user behavior analysis
- **REST API**: Full REST API with OpenAPI documentation

## Quick Start

### Prerequisites

- Python 3.9+
- Poetry
- PostgreSQL database (shared with data service)

### Installation

```bash
# Navigate to backend directory
cd backend

# Install dependencies with uv
uv sync

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Start the service
uv run uvicorn services.analytics_service.main:app --reload --port 8001
```

### API Endpoints

#### Core Analytics
- `GET /api/v1/locations` - Get active locations
- `GET /api/v1/stats` - Get dashboard statistics
- `GET /api/v1/stats/dashboard` - Get comprehensive dashboard data

#### Task Management
- `GET /api/v1/tasks/status` - Get task status
- `PUT /api/v1/tasks/status` - Update task status
- `GET /api/v1/tasks/purchases` - Get purchase analysis tasks
- `GET /api/v1/tasks/cart-abandonment` - Get cart abandonment tasks
- `GET /api/v1/tasks/search-analysis` - Get search analysis tasks
- `GET /api/v1/tasks/performance` - Get performance analysis tasks
- `GET /api/v1/tasks/repeat-visits` - Get repeat visit tasks

#### Session & User Analytics
- `GET /api/v1/sessions/{session_id}/history` - Get session history
- `GET /api/v1/users/{user_id}/history` - Get user history

#### Health & Info
- `GET /health` - Health check
- `GET /` - Service info
- `GET /docs` - API documentation

## Configuration

The service uses the same PostgreSQL database as the data service. Configure the connection in `config/postgres.json`:

```json
{
  "host": "your-postgres-host",
  "port": 5432,
  "user": "postgres",
  "password": "your-password",
  "database": "postgres",
  "connect_timeout_seconds": 10,
  "sslmode": "require"
}
```

## Development

```bash
# Format code
uv run black app/
uv run isort app/

# Type checking
uv run mypy app/

# Run tests
uv run pytest
```

## Architecture

```
Frontend (Next.js) 
    ↓ HTTP/REST calls
Analytics Service (FastAPI)
    ↓ Database queries  
PostgreSQL Database (Multi-tenant)
```

The service is designed to:
- Handle multi-tenant analytics data
- Provide high-performance analytics queries
- Support real-time dashboard updates
- Scale independently from other services
