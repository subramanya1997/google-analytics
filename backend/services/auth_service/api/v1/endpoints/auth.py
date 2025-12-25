"""
Authentication API Endpoints

This module defines the REST API endpoints for the authentication service, handling
OAuth 2.0 authentication flows, token validation, and session management.

Endpoints:
    POST /authenticate
        Exchange OAuth authorization code for access token and session.
        Validates tenant configurations and provisions database if needed.

    GET /login-url
        Retrieve the OAuth login URL for redirecting users to the Identity Provider.

    POST /validate-token
        Validate an access token and return associated user information.
        Used by other services to verify token authenticity.

    POST /logout
        Invalidate an access token and terminate the user session.
        Handles graceful degradation if external logout service is unavailable.

Error Handling:
    All endpoints follow consistent error handling patterns:
    - 401 Unauthorized: Invalid authentication credentials or expired token
    - 500 Internal Server Error: Unexpected server errors
    - 503 Service Unavailable: External IdP service unavailable

Security Considerations:
    - All tokens are validated against external IdP (no local token storage)
    - Sensitive configuration data is encrypted at rest
    - PostgreSQL connection validation is required for authentication
    - Background validation of optional services doesn't block authentication

Example Usage:
    ```python
    # Authenticate user
    response = await client.post("/api/v1/authenticate", json={"code": "oauth_code"})
    
    # Validate token
    response = await client.post(
        "/api/v1/validate-token",
        json={"access_token": "bearer_token"}
    )
    ```

See Also:
    - services.auth_service.services.auth_service.AuthenticationService: Core business logic
    - services.auth_service.api.v1.models: Request/response models
"""

from fastapi import APIRouter, HTTPException, status
from loguru import logger

from services.auth_service.api.v1.models import (
    AuthRequest,
    AuthResponse,
    LoginUrlResponse,
    LogoutRequest,
    LogoutResponse,
    ValidateTokenRequest,
    ValidateTokenResponse,
)
from services.auth_service.services.auth_service import AuthenticationService

router = APIRouter()


@router.post("/authenticate", response_model=AuthResponse)
async def authenticate(request: AuthRequest) -> AuthResponse:
    """
    Authenticate user with OAuth authorization code and validate tenant configurations.

    This endpoint implements the OAuth 2.0 authorization code exchange flow:
    1. Exchanges the authorization code for an access token via external IdP
    2. Retrieves tenant-specific application settings and configurations
    3. Validates required PostgreSQL configuration (blocks login if invalid)
    4. Logs warnings for missing optional configurations (BigQuery, SFTP, SMTP)
    5. Provisions tenant database if this is a new tenant
    6. Stores/updates tenant configurations in the database
    7. Returns authentication result with access token and user information

    The authentication flow is synchronous for PostgreSQL validation (required) but
    handles optional service validations asynchronously to avoid blocking the login
    process.

    Args:
        request: Authentication request containing the OAuth authorization code
            - code (str): OAuth authorization code received from IdP redirect

    Returns:
        AuthResponse containing:
            - success (bool): Whether authentication succeeded
            - message (str): Human-readable status message
            - tenant_id (str | None): Unique tenant identifier (UUID)
            - first_name (str | None): User's first name
            - username (str | None): User's email/username
            - business_name (str | None): Tenant's business name
            - access_token (str | None): OAuth access token for API calls
            - missing_configs (list[str] | None): List of missing configuration keys
            - invalid_configs (list[str] | None): List of invalid configuration keys

    Raises:
        HTTPException:
            - 401 Unauthorized: Invalid or expired authorization code
            - 500 Internal Server Error: Unexpected server error during authentication
            - 503 Service Unavailable: External IdP service unavailable

    Example:
        ```python
        # Frontend receives OAuth code from redirect
        response = await client.post(
            "/api/v1/authenticate",
            json={"code": "abc123xyz"}
        )
        
        if response.json()["success"]:
            access_token = response.json()["access_token"]
            tenant_id = response.json()["tenant_id"]
        ```

    Note:
        - PostgreSQL configuration is REQUIRED and validated synchronously
        - BigQuery, SFTP, and SMTP configurations are OPTIONAL
        - New tenants automatically get a provisioned database
        - Existing tenant configurations are always updated with latest values
    """
    auth_service = AuthenticationService()
    result = await auth_service.authenticate_with_code(request.code)

    if not result["success"]:
        # Determine appropriate HTTP status code based on the error
        if "Invalid authentication code" in result["message"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=result["message"]
            )
        if "service unavailable" in result["message"]:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=result["message"],
            )
        if "configurations" in result["message"]:
            # Configuration issues are not HTTP errors, return as successful response
            return AuthResponse(**result)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["message"],
        )

    return AuthResponse(**result)


@router.post("/logout", response_model=LogoutResponse)
async def logout(request: LogoutRequest) -> LogoutResponse:
    """
    Logout user by invalidating the access token with the external Identity Provider.

    This endpoint handles session termination by calling the external IdP's logout
    endpoint. The implementation follows a graceful degradation pattern:
    - If external logout succeeds: Returns success
    - If external logout fails (404, 401): Still returns success to allow local cleanup
    - If external service unavailable (503): Raises HTTPException

    The frontend should always proceed with local session cleanup (clearing cookies,
    localStorage, etc.) regardless of the external logout result, as tokens may
    already be invalid or the external service may not support logout.

    Args:
        request: Logout request containing the access token
            - access_token (str): OAuth access token to invalidate

    Returns:
        LogoutResponse containing:
            - success (bool): Whether logout operation completed (may be True even
              if external logout failed, to allow frontend cleanup)
            - message (str): Human-readable status message indicating logout result

    Raises:
        HTTPException:
            - 503 Service Unavailable: External IdP service unavailable

    Example:
        ```python
        response = await client.post(
            "/api/v1/logout",
            json={"access_token": "bearer_token_here"}
        )
        
        # Frontend should always clear local session regardless of response
        clear_local_session()
        ```

    Note:
        - Returns success even if external logout fails (404, 401) to allow
          frontend to proceed with local cleanup
        - Only raises exception for service unavailability (503)
        - Frontend should always clear local session state regardless of response
    """
    auth_service = AuthenticationService()
    result = await auth_service.logout_with_token(request.access_token)

    if not result["success"]:
        logger.warning(f"External logout failed: {result['message']}")

        # For certain errors, we still want to allow the frontend to proceed
        if (
            "endpoint not found" in result["message"].lower()
            or "404" in result["message"]
        ):
            # External service doesn't support logout, but we allow local logout
            return LogoutResponse(
                success=True,
                message="Local logout successful (external logout not supported)",
            )
        if "invalid token" in result["message"].lower() or "401" in result["message"]:
            # Token already invalid, treat as successful logout
            return LogoutResponse(
                success=True, message="Logout successful (token already invalid)"
            )
        if "service unavailable" in result["message"].lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=result["message"],
            )
        # For other errors, still allow local logout but log the issue
        logger.error(f"Logout API error: {result['message']}")
        return LogoutResponse(
            success=True, message="Local logout successful (external logout failed)"
        )

    return LogoutResponse(**result)


@router.get("/login-url", response_model=LoginUrlResponse)
async def get_login_url() -> LoginUrlResponse:
    """
    Get the OAuth login URL for redirecting users to the Identity Provider.

    This endpoint returns the complete URL where users should be redirected to
    initiate the OAuth 2.0 authentication flow. The URL is constructed from the
    BASE_URL configuration setting with the appropriate path suffix.

    The frontend should redirect users to this URL, which will handle the OAuth
    flow and redirect back to the frontend with an authorization code in the query
    parameters.

    Returns:
        LoginUrlResponse containing:
            - login_url (str): Complete URL for OAuth login redirect
                Format: "{BASE_URL}/admin/"

    Example:
        ```python
        response = await client.get("/api/v1/login-url")
        login_url = response.json()["login_url"]
        # Redirect user to login_url
        window.location.href = login_url
        ```

    Note:
        - The URL is constructed from the BASE_URL environment variable
        - Users will be redirected back to the frontend with a code parameter
        - The frontend should then call /authenticate with the received code
    """
    auth_service = AuthenticationService()
    login_url = auth_service.get_login_url()

    return LoginUrlResponse(login_url=login_url)


@router.post("/validate-token", response_model=ValidateTokenResponse)
async def validate_token(request: ValidateTokenRequest) -> ValidateTokenResponse:
    """
    Validate an access token and return associated user and tenant information.

    This endpoint is used by other services (analytics-service, data-service) to
    verify the authenticity and validity of access tokens before processing requests.
    It calls the external IdP to validate the token and retrieve user information.

    The endpoint follows a non-exception pattern for invalid tokens - it returns
    a response with valid=False rather than raising an HTTPException. This allows
    calling services to handle invalid tokens gracefully without exception handling.

    Args:
        request: Token validation request
            - access_token (str): OAuth access token to validate (Bearer token)

    Returns:
        ValidateTokenResponse containing:
            - valid (bool): Whether the token is valid and not expired
            - message (str): Human-readable validation status message
            - tenant_id (str | None): Tenant identifier if token is valid
            - first_name (str | None): User's first name if token is valid
            - username (str | None): User's email/username if token is valid
            - business_name (str | None): Tenant's business name if token is valid

    Example:
        ```python
        # In another service
        response = await client.post(
            "/api/v1/validate-token",
            json={"access_token": "bearer_token"}
        )
        
        if response.json()["valid"]:
            tenant_id = response.json()["tenant_id"]
            # Process request with tenant context
        else:
            # Return 401 to client
            return HTTPException(401, "Invalid token")
        ```

    Note:
        - Returns valid=False (not HTTPException) for invalid tokens
        - Calling services should check the valid field and handle accordingly
        - Token validation is performed synchronously against external IdP
        - User information is only returned if token is valid
    """
    auth_service = AuthenticationService()
    result = await auth_service.validate_token(request.access_token)

    if not result["valid"]:
        # Return validation failure but don't raise HTTP exception
        # The frontend should handle invalid tokens gracefully
        return ValidateTokenResponse(**result)

    return ValidateTokenResponse(**result)
