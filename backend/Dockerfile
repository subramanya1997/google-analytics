# Use Python 3.11 slim as base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH="/root/.local/bin:$PATH"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Set working directory
WORKDIR /app

# Copy dependency files first for better Docker layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies using uv
RUN uv sync --no-dev

# Copy the application code
COPY . .

# Create logs directory
RUN mkdir -p logs
