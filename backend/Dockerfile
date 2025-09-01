# Use Python 3.9 slim image
FROM python:3.9-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Set work directory
WORKDIR /app

# Copy Poetry configuration files
COPY pyproject.toml poetry.lock ./

# Configure Poetry to create virtual environment in the container
RUN poetry config virtualenvs.create true \
    && poetry config virtualenvs.in-project true

# Install dependencies in virtual environment (without dev dependencies and without installing the project itself)
RUN poetry install --only main --no-root

# Copy the entire backend codebase
COPY . .

# Create logs directory
RUN mkdir -p /app/logs

# Note: No config files needed - configurations are retrieved dynamically from tenant system

# Make sure the entrypoint script is executable
COPY docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# Expose ports for all services
EXPOSE 8001 8002 8003

# Use Poetry's virtual environment in the entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]
