# Data Ingestion Service

A FastAPI-based microservice for ingesting Google Analytics 4 data from BigQuery and user/location data from SFTP into a multi-tenant PostgreSQL database.

## Features

- **BigQuery Integration**: Direct querying of GA4 events by date range
- **SFTP Integration**: User and location data synchronization
- **Multi-tenant Support**: Isolated data processing per tenant
- **Replace/Upsert Logic**: Events are replaced, Users/Locations are upserted
- **Job Tracking**: Comprehensive processing status and progress tracking
- **REST API**: Trigger data ingestion via API endpoints

## Quick Start

### Prerequisites

- Python 3.9+
- Poetry
- PostgreSQL database
- BigQuery service account credentials
- SFTP access credentials

### Installation

```bash
# Install dependencies
poetry install

# Activate virtual environment
poetry shell

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start the service
poetry run uvicorn app.main:app --reload --port 8001
```

### API Endpoints

- `POST /api/v1/data/ingest` - Trigger data ingestion
- `GET /api/v1/data/jobs/{job_id}` - Get job status
- `GET /api/v1/data/jobs` - List jobs
- `GET /health` - Health check

## Configuration

The service uses environment variables for configuration. See `.env.example` for all available options.

## Development

```bash
# Run tests
poetry run pytest

# Format code
poetry run black app/
poetry run isort app/

# Type checking
poetry run mypy app/

# Run linting
poetry run flake8 app/
```

## Architecture

```
app/
├── api/           # API endpoints
├── core/          # Core business logic
├── clients/       # External service clients (BigQuery, SFTP)
├── database/      # Database models and operations
├── models/        # Pydantic models
├── services/      # Business logic services
└── utils/         # Utility functions
```
