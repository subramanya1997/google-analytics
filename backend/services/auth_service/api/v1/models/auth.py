"""
Authentication API Request/Response Models

This module defines Pydantic models for request and response validation in the
authentication service API. All models use Pydantic's BaseModel for automatic
validation, serialization, and OpenAPI schema generation.

Models follow a consistent naming pattern:
    - Request models: {Action}Request (e.g., AuthRequest, LogoutRequest)
    - Response models: {Action}Response (e.g., AuthResponse, LogoutResponse)

All models are automatically included in the OpenAPI/Swagger documentation with
field descriptions and validation rules.

Example:
    ```python
    from services.auth_service.api.v1.models import AuthRequest, AuthResponse
    
    # Request validation
    request = AuthRequest(code="oauth_code_123")
    
    # Response serialization
    response = AuthResponse(
        success=True,
        message="Authentication successful",
        tenant_id="uuid-here",
        access_token="bearer_token"
    )
    ```
"""

from pydantic import BaseModel, Field


class AuthRequest(BaseModel):
    """
    Request model for OAuth authentication endpoint.

    This model represents the request body for the /authenticate endpoint,
    containing the OAuth authorization code received from the Identity Provider
    after user authentication.

    Attributes:
        code (str): OAuth 2.0 authorization code received from IdP redirect.
            This is a temporary, single-use code that will be exchanged for an
            access token. Typically 20-200 characters, alphanumeric.

    Example:
        ```json
        {
            "code": "4/0AeanS0b..."
        }
        ```
    """

    code: str = Field(..., description="OAuth authorization code from IdP redirect", min_length=1)


class AuthResponse(BaseModel):
    """
    Response model for OAuth authentication endpoint.

    This model represents the response from the /authenticate endpoint, containing
    authentication status, user information, access token, and configuration validation
    results.

    Attributes:
        success (bool): Whether authentication succeeded. False indicates
            authentication failure or configuration validation failure.
        message (str): Human-readable status message describing the result.
            Examples: "Authentication successful", "Invalid authentication code",
            "Authentication failed due to missing or invalid configurations"
        tenant_id (str | None): Unique tenant identifier (UUID format) if
            authentication succeeded. None if authentication failed.
        first_name (str | None): User's first name from IdP if available.
        username (str | None): User's email address or username from IdP.
        business_name (str | None): Tenant's business/organization name.
        access_token (str | None): OAuth access token (Bearer token) for
            subsequent API calls. Only present if success=True.
        missing_configs (list[str] | None): List of configuration keys that
            are required but missing. Examples: ["bigquery_config"]
        invalid_configs (list[str] | None): List of configuration keys that
            are present but invalid (e.g., connection failed). Examples:
            ["bigquery_config", "sftp_config"]

    Example:
        ```json
        {
            "success": true,
            "message": "Authentication successful",
            "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
            "first_name": "John",
            "username": "john@company.com",
            "business_name": "Acme Corp",
            "access_token": "eyJhbGciOiJIUzI1NiIs...",
            "missing_configs": null,
            "invalid_configs": null
        }
        ```
    """

    success: bool = Field(..., description="Whether authentication succeeded")
    message: str = Field(..., description="Human-readable status message")
    tenant_id: str | None = Field(None, description="Tenant UUID if authentication succeeded")
    first_name: str | None = Field(None, description="User's first name")
    username: str | None = Field(None, description="User's email/username")
    business_name: str | None = Field(None, description="Tenant's business name")
    access_token: str | None = Field(None, description="OAuth access token for API calls")
    missing_configs: list[str] | None = Field(None, description="List of missing required configurations")
    invalid_configs: list[str] | None = Field(None, description="List of invalid configurations")


class LogoutRequest(BaseModel):
    """
    Request model for logout endpoint.

    This model represents the request body for the /logout endpoint, containing
    the access token to be invalidated.

    Attributes:
        access_token (str): OAuth access token (Bearer token) to invalidate.
            This token will be sent to the external IdP for revocation.

    Example:
        ```json
        {
            "access_token": "eyJhbGciOiJIUzI1NiIs..."
        }
        ```
    """

    access_token: str = Field(..., description="OAuth access token to invalidate", min_length=1)


class LogoutResponse(BaseModel):
    """
    Response model for logout endpoint.

    This model represents the response from the /logout endpoint, indicating
    whether the logout operation completed successfully.

    Attributes:
        success (bool): Whether logout operation completed. May be True even
            if external logout failed (to allow frontend cleanup).
        message (str): Human-readable status message. Examples:
            - "Logout successful"
            - "Local logout successful (external logout not supported)"
            - "Logout successful (token already invalid)"

    Example:
        ```json
        {
            "success": true,
            "message": "Logout successful"
        }
        ```
    """

    success: bool = Field(..., description="Whether logout operation completed")
    message: str = Field(..., description="Human-readable logout status message")


class LoginUrlResponse(BaseModel):
    """
    Response model for login URL endpoint.

    This model represents the response from the /login-url endpoint, containing
    the OAuth login URL where users should be redirected.

    Attributes:
        login_url (str): Complete URL for OAuth login redirect. This is the
            external IdP's authentication page URL. Format: "{BASE_URL}/admin/"

    Example:
        ```json
        {
            "login_url": "https://idp.example.com/admin/"
        }
        ```
    """

    login_url: str = Field(..., description="Complete OAuth login URL for user redirect")


class ValidateTokenRequest(BaseModel):
    """
    Request model for token validation endpoint.

    This model represents the request body for the /validate-token endpoint,
    used by other services to verify token authenticity.

    Attributes:
        access_token (str): OAuth access token (Bearer token) to validate.
            This token will be verified against the external IdP.

    Example:
        ```json
        {
            "access_token": "eyJhbGciOiJIUzI1NiIs..."
        }
        ```
    """

    access_token: str = Field(..., description="OAuth access token to validate", min_length=1)


class ValidateTokenResponse(BaseModel):
    """
    Response model for token validation endpoint.

    This model represents the response from the /validate-token endpoint,
    indicating token validity and associated user information.

    Attributes:
        valid (bool): Whether the token is valid and not expired. False
            indicates the token is invalid, expired, or revoked.
        message (str): Human-readable validation status message. Examples:
            - "Token is valid"
            - "Token is invalid or expired"
            - "Token validation service unavailable"
        tenant_id (str | None): Tenant identifier if token is valid.
        first_name (str | None): User's first name if token is valid.
        username (str | None): User's email/username if token is valid.
        business_name (str | None): Tenant's business name if token is valid.

    Example:
        ```json
        {
            "valid": true,
            "message": "Token is valid",
            "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
            "first_name": "John",
            "username": "john@company.com",
            "business_name": "Acme Corp"
        }
        ```
    """

    valid: bool = Field(..., description="Whether the token is valid and not expired")
    message: str = Field(..., description="Human-readable validation status message")
    tenant_id: str | None = Field(None, description="Tenant UUID if token is valid")
    first_name: str | None = Field(None, description="User's first name if token is valid")
    username: str | None = Field(None, description="User's email/username if token is valid")
    business_name: str | None = Field(None, description="Tenant's business name if token is valid")
