"""
Authentication Service - FastAPI Application Entry Point.

This module provides the main FastAPI application for the Authentication Service,
which handles OAuth authentication, token validation, and tenant configuration
management for the Google Analytics Intelligence System.

The Authentication Service is responsible for:
- OAuth-based user authentication with external authentication providers
- Access token management and validation
- Tenant configuration retrieval and validation
- Multi-tenant database setup and configuration storage
- Integration with external authentication APIs

Key Features:
- OAuth 2.0 authentication flow
- Real-time configuration validation (PostgreSQL, BigQuery, SFTP, SMTP)
- Tenant configuration synchronization with external API
- Token-based session management
- Reverse proxy support for production deployments

API Endpoints:
- POST /api/v1/authenticate: Exchange auth code for access token
- POST /api/v1/logout: Invalidate access token
- GET /api/v1/login-url: Get OAuth login URL
- POST /api/v1/validate-token: Validate access token and get user info

Architecture:
The service follows a layered architecture:
1. FastAPI application layer (this file)
2. API endpoint layer (handles HTTP requests/responses)
3. Service layer (business logic and external API integration)
4. Database layer (tenant configuration persistence)

Production Configuration:
- Reverse proxy path: /auth/ (configured for Nginx deployment)
- Service name: auth-service
- Default port: 8003 (configurable via environment)
- Health check: /health
- API documentation: /auth/docs

Environment Variables:
- BASE_URL: External authentication service base URL
- POSTGRES_*: Database connection parameters
- CORS_ORIGINS: Allowed cross-origin request sources

Security Considerations:
- All authentication flows use secure OAuth 2.0
- Tokens are validated against external authentication service
- Configuration data is encrypted in database storage
- CORS policies restrict cross-origin access in production
"""

from common.fastapi import create_fastapi_app
from services.auth_service.api.v1.api import api_router

# Create FastAPI app with reverse proxy configuration
app = create_fastapi_app(
    service_name="auth-service",
    description="Authentication service for Google Analytics intelligence system",
    api_router=api_router,
    root_path="/auth",  # Nginx serves this at /auth/
)
