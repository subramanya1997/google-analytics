"""
Analytics Service Package

This package provides the Analytics Service application for the Google Analytics
Intelligence System. The service exposes RESTful APIs for analytics dashboard
functionality, task management, and automated email reporting.

Package Structure:
    - main.py: FastAPI application entry point
    - api/: API endpoint definitions and routing
    - database/: Database client and query operations
    - services/: Business logic services (if any)

Exports:
    app (FastAPI): The main FastAPI application instance that can be imported
        and run with uvicorn or other ASGI servers.

Usage:
    ```python
    from services.analytics_service import app
    
    # Run with uvicorn
    # uvicorn services.analytics_service:app --port 8001
    ```

    Or import directly:
    ```python
    from services.analytics_service.main import app
    ```

See Also:
    - services.analytics_service.main: Main application module
    - services.analytics_service.README.md: Detailed service documentation
"""

from services.analytics_service.main import app

__all__ = ["app"]
