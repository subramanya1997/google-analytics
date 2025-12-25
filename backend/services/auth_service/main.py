"""
Authentication Service - FastAPI Application Entrypoint

This module serves as the main entry point for the Authentication Service, a microservice
responsible for handling OAuth 2.0 authentication flows, token validation, and tenant
configuration management within the Google Analytics Intelligence Platform.

The service implements a stateless authentication architecture that delegates user
authentication to an external Identity Provider (IdP) while managing tenant-specific
configurations locally. It provides RESTful APIs for:

- OAuth 2.0 authentication flow initiation and callback handling
- Access token validation and user information retrieval
- Session management (logout)
- Tenant configuration validation and storage

Architecture:
    The service follows a microservices pattern with clear separation of concerns:
    - API Layer: FastAPI endpoints handling HTTP requests/responses
    - Service Layer: Business logic for authentication and validation
    - Database Layer: Tenant configuration persistence (via common.database)

Security Model:
    - All authentication credentials are validated against external IdP
    - Tenant configurations are encrypted at rest
    - PostgreSQL connection is required for authentication (blocks login if invalid)
    - Optional services (BigQuery, SFTP, SMTP) validated asynchronously

Example:
    To run the service locally:
        ```bash
        uv run uvicorn services.auth_service:app --port 8003 --reload
        ```

    The service will be available at:
        - API Base: http://localhost:8003/auth/api/v1
        - Swagger UI: http://localhost:8003/docs
        - Health Check: http://localhost:8003/health
    ```

Attributes:
    app (FastAPI): The FastAPI application instance configured with:
        - Service name: "auth-service"
        - Root path: "/auth" (for reverse proxy routing)
        - API router: Includes all v1 authentication endpoints
        - Standard middleware: CORS, logging, error handling

See Also:
    - services.auth_service.api.v1.api: API router definitions
    - services.auth_service.services.auth_service: Core authentication logic
    - common.fastapi.app_factory: FastAPI application factory
"""

from common.fastapi import create_fastapi_app
from services.auth_service.api.v1.api import api_router

# Create FastAPI app with reverse proxy configuration
# The root_path="/auth" ensures proper routing when behind Nginx reverse proxy
# In development (ENVIRONMENT=DEV), root_path is automatically set to ""
app = create_fastapi_app(
    service_name="auth-service",
    description="Authentication service for Google Analytics intelligence system",
    api_router=api_router,
    root_path="/auth",  # Nginx serves this at /auth/
)
