# Google Analytics Backend Services

A unified backend system for Google Analytics intelligence with multiple microservices.

## Architecture

This backend consists of three main services:
- **Analytics Service** (Port 8001) - Analytics and reporting
- **Data Service** (Port 8002) - Data ingestion and processing  
- **Auth Service** (Port 8003) - Authentication and authorization

## Unified Structure

### Common Modules
All services now share common code located in `/common/`:
- `config/` - Centralized configuration management
- `database/` - Shared database utilities and ORM base
- `security/` - Authentication and authorization utilities
- `fastapi/` - Common FastAPI app factory and middleware
- `logging.py` - Centralized logging configuration

### Configuration
- **Single `pyproject.toml`** - All dependencies managed in one file
- **Unified `.env`** - Single environment configuration for all services
- **Centralized config files** - All JSON configs in `/config/` directory

### Single Runner
Use `run_all_services.py` to start all services simultaneously on different ports.

## Quick Start

1. **Install Dependencies**:
   ```bash
   cd backend
   uv sync
   ```

2. **Setup Configuration**:
   ```bash
   # Copy example configs
   cp config/postgres.json.example config/postgres.json
   cp config/bigquery.json.example config/bigquery.json  
   cp config/sftp.json.example config/sftp.json
   
   # Edit the config files with your actual values
   ```

3. **Run All Services**:
   ```bash
   ./docker-entrypoint.sh
   ```

## Service URLs

Once running, the services will be available at:
- Analytics Service: http://localhost:8001
- Data Service: http://localhost:8002  
- Auth Service: http://localhost:8003

Each service provides:
- `/docs` - Interactive API documentation
- `/health` - Health check endpoint
- `/` - Service info

## Development

- All services use the common configuration and utilities
- Database sessions and models are shared via common modules
- FastAPI apps are created using the unified app factory
- Logging is centralized and consistent across services

## Benefits of This Structure

1. **DRY Principle** - No code duplication across services
2. **Consistency** - All services follow the same patterns
3. **Maintainability** - Changes to common functionality affect all services
4. **Single Dependency Management** - One uv project file for all services
5. **Unified Configuration** - One place to manage all settings
6. **Easy Development** - Single command to run all services
