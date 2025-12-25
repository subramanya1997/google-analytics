"""
Authentication Service Package

This package provides the Authentication Service for the Google Analytics Intelligence
Platform. It exports the FastAPI application instance for use with ASGI servers
like Uvicorn or Gunicorn.

The package structure:
    - main.py: FastAPI application entrypoint
    - api/: API layer with endpoints and models
    - services/: Business logic layer

Usage:
    ```python
    from services.auth_service import app
    
    # Run with uvicorn
    # uvicorn services.auth_service:app --port 8003
    ```

Exports:
    app: FastAPI application instance configured for authentication service
"""

from services.auth_service.main import app

__all__ = ["app"]
