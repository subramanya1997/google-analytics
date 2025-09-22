"""
Authentication Service Package.

This package provides the complete OAuth authentication service for the Google
Analytics Intelligence System. It handles user authentication, tenant configuration
validation, and integration with external authentication providers.

The package is structured as a FastAPI microservice with the following components:

Package Structure:
- main.py: FastAPI application entry point with reverse proxy configuration
- api/: REST API endpoints and routing
  - v1/: API version 1 implementation
    - api.py: Main API router aggregating all endpoints
    - endpoints/: Individual endpoint implementations
      - auth.py: Authentication endpoints (login, logout, token validation)
- services/: Business logic and external service integration
  - auth_service.py: Core authentication service with OAuth and configuration management

Key Features:
- OAuth 2.0 authentication flow with external providers
- Real-time multi-service configuration validation (PostgreSQL, BigQuery, SFTP, SMTP)
- Tenant lifecycle management with database synchronization
- Token-based session management with validation and logout
- Parallel configuration validation for optimal performance
- Comprehensive error handling with appropriate HTTP status codes

Service Architecture:
The authentication service follows a layered architecture:
1. **API Layer**: FastAPI endpoints handling HTTP requests/responses
2. **Business Logic**: Authentication workflows and configuration validation
3. **External Integration**: OAuth provider and configuration API communication
4. **Database Layer**: Tenant management and configuration persistence

Production Deployment:
- Reverse proxy support with /auth/ path prefix
- Environment-aware CORS policies
- Comprehensive logging and monitoring
- Health checks and service discovery endpoints
- Docker containerization support


Environment Configuration:
- BASE_URL: External authentication service base URL
- POSTGRES_*: Database connection parameters
- CORS_ORIGINS: Allowed cross-origin request sources
- Various timeout and pooling configurations

The service provides endpoints at:
- POST /api/v1/authenticate: OAuth code to token exchange
- POST /api/v1/logout: Session termination
- GET /api/v1/login-url: OAuth login URL generation
- POST /api/v1/validate-token: Token validation and user info
- GET /health: Service health check
"""

from services.auth_service.main import app

__all__ = ["app"]
