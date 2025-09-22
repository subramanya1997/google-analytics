"""
Authentication Service API Router - Version 1.

This module defines the main API router for the Authentication Service v1 API,
aggregating all endpoint routers and providing a centralized configuration
point for API routing and documentation.

The API router organizes all authentication-related endpoints under a unified
structure with proper tagging for OpenAPI documentation generation.

Router Structure:
- Base path: /api/v1/ (configured in main app)
- Authentication endpoints: /api/v1/* (auth operations)
- Tags: ["authentication"] (for OpenAPI grouping)

Endpoint Categories:
- Authentication: OAuth login, logout, token validation
- Configuration: Tenant setup and validation
- Session Management: Token lifecycle operations

OpenAPI Integration:
All endpoints are automatically included in the OpenAPI schema generation
with proper tagging and categorization for clear API documentation.

"""

from fastapi import APIRouter

from services.auth_service.api.v1.endpoints import auth

api_router = APIRouter()

# Include all endpoint routers with proper tagging for OpenAPI documentation
api_router.include_router(auth.router, tags=["authentication"])
