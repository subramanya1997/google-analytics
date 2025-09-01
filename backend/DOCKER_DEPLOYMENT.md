# Docker Deployment Guide

This guide explains how to deploy the Google Analytics Backend Services using Docker.

## Overview

The Docker setup provides a containerized environment that runs all 3 backend services:
- **Analytics Service** (Port 8001) - Analytics and reporting
- **Data Service** (Port 8002) - Data ingestion and processing  
- **Auth Service** (Port 8003) - Authentication and authorization

Each service writes logs to separate log files for easy monitoring and debugging.

## Prerequisites

- Docker and Docker Compose installed
- PostgreSQL database accessible
- Environment variables configured in `.env` file (copy from `.env.template`)

## Quick Start

### 1. Environment Setup

The services get configurations dynamically from the tenant system and environment variables. Set up your environment using the `.env` file:

```bash
# Navigate to the backend directory
cd backend

# Copy the environment template
cp env.example .env

# Edit the .env file with your actual values
# nano .env
```

### 2. Build and Run with Docker Compose (Recommended)

```bash
# Build and start all services
docker-compose up --build

# Or run in background
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 3. Alternative: Using Docker Directly

```bash
# Build the image
docker build -t google-analytics-backend .

# Run the container with environment variables from .env file
docker run -d \
  --name google-analytics-backend \
  -p 8001:8001 \
  -p 8002:8002 \
  -p 8003:8003 \
  -v $(pwd)/logs:/app/logs \
  --env-file .env \
  google-analytics-backend

# View logs
docker logs -f google-analytics-backend

# Stop the container
docker stop google-analytics-backend
```

## Configuration

The backend services use a **dynamic configuration system**:
- **PostgreSQL**: Configure via environment variables
- **BigQuery & SFTP**: Retrieved dynamically from tenant configuration system via database
- **No static config files needed!**

### Environment Variables

Create a `.env` file from the template with your actual values:

```bash
# Copy the template
cp env.example .env

# Edit with your values
nano .env
```

Key environment variables in `.env`:

```bash
# PostgreSQL Database
POSTGRES_HOST=your_postgres_host      # e.g., localhost or postgres container  
POSTGRES_PORT=5432                    # PostgreSQL port
POSTGRES_USER=your_postgres_user      # Database user
POSTGRES_PASSWORD=your_password       # Database password
POSTGRES_DATABASE=your_database_name  # Database name

# Application Settings
DEBUG=false                           # Set to true for development
LOG_LEVEL=INFO                        # DEBUG, INFO, WARNING, ERROR
CORS_ORIGINS=http://localhost:3000    # Comma-separated allowed origins
```

### How Configuration Works

1. **PostgreSQL**: Environment variables → Database connection
2. **BigQuery/SFTP**: Database → Tenant-specific configurations retrieved dynamically
3. **Service Settings**: Auto-detected based on service name and environment

## Service URLs

Once running, the services are available at:

- **Analytics Service**: http://localhost:8001
  - API Docs: http://localhost:8001/docs
  - Health Check: http://localhost:8001/health

- **Data Service**: http://localhost:8002
  - API Docs: http://localhost:8002/docs
  - Health Check: http://localhost:8002/health

- **Auth Service**: http://localhost:8003
  - API Docs: http://localhost:8003/docs
  - Health Check: http://localhost:8003/health

## Logging

Each service writes logs to separate files in the `logs/` directory:

- `logs/analytics-service.log` - Analytics service logs
- `logs/data-ingestion-service.log` - Data service logs
- `logs/auth-service.log` - Auth service logs
- `logs/analytics-service-error.log` - Analytics service errors
- `logs/data-ingestion-service-error.log` - Data service errors
- `logs/auth-service-error.log` - Auth service errors

### Viewing Logs

```bash
# View all logs
tail -f logs/*.log

# View specific service logs
tail -f logs/analytics-service.log

# View error logs only
tail -f logs/*-error.log

# Using Docker Compose
docker-compose logs -f
```

## Environment Variables

You can override default settings using environment variables:

```bash
# In docker-compose.yml or when running docker
environment:
  - DEBUG=true
  - LOG_LEVEL=DEBUG
  - PYTHONUNBUFFERED=1
```

## Health Checks

The Docker setup includes health checks for all services:

```bash
# Check health status
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health

# Using Docker
docker ps  # Shows health status in STATUS column
```

## Troubleshooting

### Common Issues

1. **Services not starting**: Check PostgreSQL environment variables are set correctly
2. **Port conflicts**: Make sure ports 8001, 8002, 8003 are not in use
3. **Database connection issues**: Verify PostgreSQL environment variables and database connectivity
4. **Permission errors**: Ensure Docker has read/write access to the logs directory
5. **Configuration errors**: Tenant-specific configs (BigQuery/SFTP) are retrieved from database - ensure tenant system is set up

### Debugging

```bash
# View service logs
docker-compose logs service-name

# Access container shell
docker exec -it google-analytics-backend bash

# Check running processes inside container
docker exec -it google-analytics-backend ps aux

# View specific log files
docker exec -it google-analytics-backend tail -f logs/analytics-service.log
```

### Log Analysis

```bash
# Search for errors in logs
grep -i error logs/*.log

# View recent errors
tail -n 100 logs/*-error.log

# Monitor logs in real-time
watch 'tail -n 20 logs/*.log'
```

## Production Deployment

For production deployment:

1. **Security**: 
   - Use environment variables for sensitive data instead of config files
   - Set up proper firewall rules
   - Use HTTPS reverse proxy (nginx/traefik)

2. **Monitoring**:
   - Set up log aggregation (ELK stack, Splunk, etc.)
   - Configure alerting for service failures
   - Monitor resource usage

3. **Backup**:
   - Regular backup of configuration and logs
   - Database backup strategy

4. **Updates**:
   - Use specific version tags instead of `latest`
   - Implement proper CI/CD pipeline
   - Test updates in staging environment

## Docker Compose Options

The `docker-compose.yml` includes several useful configurations:

- **Volume mounts**: Persists logs and config files
- **Health checks**: Monitors service health
- **Network**: Isolates services in custom network
- **Restart policy**: Auto-restarts on failure
- **Optional PostgreSQL**: Uncomment to run PostgreSQL in Docker

For more advanced setups, modify the `docker-compose.yml` file as needed.
