"""
Authentication Service API v1 Models Package

This package exports all Pydantic models used for request/response validation
in the authentication service API v1.

Models:
    - AuthRequest: OAuth authentication request
    - AuthResponse: OAuth authentication response
    - LoginUrlResponse: OAuth login URL response
    - LogoutRequest: Logout request
    - LogoutResponse: Logout response
    - ValidateTokenRequest: Token validation request
    - ValidateTokenResponse: Token validation response

All models use Pydantic BaseModel for automatic validation, serialization,
and OpenAPI schema generation.
"""

from .auth import (
    AuthRequest,
    AuthResponse,
    LoginUrlResponse,
    LogoutRequest,
    LogoutResponse,
    ValidateTokenRequest,
    ValidateTokenResponse,
)

__all__ = [
    "AuthRequest",
    "AuthResponse",
    "LoginUrlResponse",
    "LogoutRequest",
    "LogoutResponse",
    "ValidateTokenRequest",
    "ValidateTokenResponse",
]
