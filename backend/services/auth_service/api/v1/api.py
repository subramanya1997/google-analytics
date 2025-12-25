"""
API Router Aggregation for Authentication Service v1

This module aggregates all API endpoint routers for version 1 of the authentication
service API. It provides a single router that can be included in the main FastAPI
application.

The v1 API provides the following endpoint groups:
    - Authentication: OAuth flow, token validation, logout
        - POST /authenticate: Exchange OAuth code for session
        - GET /login-url: Get OAuth login URL
        - POST /validate-token: Validate access token
        - POST /logout: Invalidate session

Router Structure:
    All endpoints are tagged with "authentication" for organized API documentation.
    The router uses FastAPI's dependency injection system for request validation
    and response serialization.

Example:
    ```python
    from services.auth_service.api.v1.api import api_router
    
    app.include_router(api_router, prefix="/api/v1")
    ```

Attributes:
    api_router (APIRouter): FastAPI router containing all v1 authentication endpoints
"""

from fastapi import APIRouter

from services.auth_service.api.v1.endpoints import auth

api_router = APIRouter()

# Include all endpoint routers
# Tags are used for organizing endpoints in Swagger/OpenAPI documentation
api_router.include_router(auth.router, tags=["authentication"])
