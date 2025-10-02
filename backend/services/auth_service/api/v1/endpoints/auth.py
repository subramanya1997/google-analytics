"""
Authentication API Endpoints.

This module implements the REST API endpoints for OAuth authentication, token
management, and session handling in the Google Analytics Intelligence System.
All endpoints handle OAuth 2.0 authentication flows and tenant configuration
validation.

The endpoints provide a complete authentication system including:
- OAuth code exchange for access tokens
- Token validation and user information retrieval
- Session logout and token invalidation
- Login URL generation for OAuth redirects

Each endpoint includes comprehensive error handling, input validation,
and proper HTTP status code responses. All operations integrate with
external authentication services and maintain tenant configuration
synchronization.

API Design:
- RESTful endpoints with appropriate HTTP methods
- Comprehensive request/response models using Pydantic
- Proper HTTP status codes and error responses
- OpenAPI/Swagger documentation integration
- Structured error handling with meaningful messages

Security Features:
- OAuth 2.0 compliance
- Token-based authentication
- Configuration validation before access
- Secure error messaging (no sensitive data exposure)
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from loguru import logger

from services.auth_service.services.auth_service import AuthenticationService

router = APIRouter()


class AuthRequest(BaseModel):
    """
    Request model for OAuth authentication code exchange.
    
    Used to initiate the authentication flow by exchanging an OAuth
    authorization code for an access token and user information.
    
    Attributes:
        code: OAuth authorization code received from the authentication provider
    """

    code: str


class AuthResponse(BaseModel):
    """
    Response model for authentication results.
    
    Contains the complete result of an authentication attempt including
    user information, access tokens, and configuration validation status.
    
    Attributes:
        success: Whether authentication was successful
        message: Human-readable status or error message
        tenant_id: Unique tenant identifier (accountId from auth service)
        first_name: User's first name from authentication provider
        username: User's username/login identifier
        business_name: Associated business or organization name
        access_token: Valid access token for API calls (only on success)
        missing_configs: List of required configurations that are missing
        invalid_configs: List of configurations that failed validation
    """

    success: bool
    message: str
    tenant_id: Optional[str] = None
    first_name: Optional[str] = None
    username: Optional[str] = None
    business_name: Optional[str] = None
    access_token: Optional[str] = None
    missing_configs: Optional[List[str]] = None
    invalid_configs: Optional[List[str]] = None


class LogoutRequest(BaseModel):
    """
    Request model for session logout.
    
    Used to invalidate an active access token and terminate the user session
    with the external authentication provider.
    
    Attributes:
        access_token: Valid access token to be invalidated
    """
    
    access_token: str


class LogoutResponse(BaseModel):
    """
    Response model for logout operations.
    
    Contains the result of a logout attempt, including success status
    and informational messages about the logout process.
    
    Attributes:
        success: Whether logout was successful (may be true even if external logout failed)
        message: Human-readable status message explaining the logout result
    """
    
    success: bool
    message: str


class LoginUrlResponse(BaseModel):
    """
    Response model for OAuth login URL requests.
    
    Provides the complete URL that clients should redirect users to
    for OAuth authentication with the external provider.
    
    Attributes:
        login_url: Complete OAuth login URL for user redirection
    """
    
    login_url: str


class ValidateTokenRequest(BaseModel):
    """
    Request model for access token validation.
    
    Used to verify that an access token is still valid and retrieve
    associated user information from the authentication provider.
    
    Attributes:
        access_token: Access token to validate
    """
    
    access_token: str


class ValidateTokenResponse(BaseModel):
    """
    Response model for token validation results.
    
    Contains validation status and associated user information if the
    token is valid and user data is available.
    
    Attributes:
        valid: Whether the access token is valid and active
        message: Human-readable validation status or error message
        tenant_id: Unique tenant identifier (if token is valid)
        first_name: User's first name (if token is valid and data available)
        username: User's username/login identifier (if available)
        business_name: Associated business name (if available)
    """
    
    valid: bool
    message: str
    tenant_id: Optional[str] = None
    first_name: Optional[str] = None
    username: Optional[str] = None
    business_name: Optional[str] = None


@router.post("/authenticate", response_model=AuthResponse)
async def authenticate(request: AuthRequest):
    """
    Authenticate user with OAuth code and validate tenant configurations.

    This is the primary authentication endpoint that handles the complete OAuth flow
    and tenant setup process. It exchanges an OAuth authorization code for access
    tokens, retrieves and validates tenant configurations, and ensures the tenant
    is properly set up in the database.

    The endpoint performs the following operations sequentially:
    1. Exchanges OAuth code for access token with external auth service
    2. Retrieves tenant application settings using the access token  
    3. Parses and validates all required configurations (PostgreSQL, BigQuery, SFTP, SMTP)
    4. Tests configuration connectivity and validity in parallel
    5. Creates or updates tenant record in database with validated configurations
    6. Returns authentication result with access token for subsequent API calls

    Args:
        request: AuthRequest containing the OAuth authorization code

    Returns:
        AuthResponse: Complete authentication result including:
        - success: True if authentication and configuration validation succeeded
        - message: Human-readable status message
        - tenant_id: Unique tenant identifier for subsequent API calls
        - user information: first_name, username, business_name
        - access_token: Valid token for API authentication (on success)
        - configuration issues: missing_configs, invalid_configs (on failure)

    Raises:
        HTTPException: 
        - 401 UNAUTHORIZED: Invalid authentication code
        - 503 SERVICE_UNAVAILABLE: External authentication service unavailable
        - 500 INTERNAL_SERVER_ERROR: Unexpected server errors

    Configuration Validation:
        The endpoint validates four types of configurations:
        - PostgreSQL: Database connectivity and credentials
        - BigQuery: Project access and service account validity
        - SFTP: Connection parameters and authentication
        - SMTP: Email server configuration and port validation

    Security Considerations:
        - OAuth codes are single-use and time-limited
        - Access tokens are validated with external auth service
        - Configuration validation happens in parallel for performance
        - Sensitive configuration data is encrypted in database
        - Failed authentication attempts are logged for monitoring

    Example Success Response:
        ```json
        {
            "success": true,
            "message": "Authentication successful",
            "tenant_id": "tenant-123",
            "first_name": "John",
            "username": "john.doe", 
            "business_name": "Acme Corp",
            "access_token": "eyJ..."
        }
        ```

    Example Failure Response:
        ```json
        {
            "success": false,
            "message": "Authentication failed due to missing or invalid configurations",
            "tenant_id": "tenant-123",
            "missing_configs": ["sftp_config"],
            "invalid_configs": ["postgres_config"]
        }
        ```
    """
    auth_service = AuthenticationService()
    result = await auth_service.authenticate_with_code(request.code)

    if not result["success"]:
        # Determine appropriate HTTP status code based on the error
        if "Invalid authentication code" in result["message"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=result["message"]
            )
        elif "service unavailable" in result["message"]:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=result["message"],
            )
        elif "configurations" in result["message"]:
            # Configuration issues are not HTTP errors, return as successful response
            return AuthResponse(**result)
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["message"],
            )

    return AuthResponse(**result)


@router.post("/logout", response_model=LogoutResponse)
async def logout(request: LogoutRequest):
    """
    Logout user by invalidating access token with external authentication service.
    
    This endpoint handles session termination by attempting to invalidate the
    access token with the external authentication provider. The endpoint is
    designed to be resilient and user-friendly, allowing local logout even
    if external logout fails.
    
    The logout process:
    1. Sends token invalidation request to external authentication service
    2. Handles various failure scenarios gracefully
    3. Returns appropriate success/failure status for frontend handling
    
    Args:
        request: LogoutRequest containing the access token to invalidate
        
    Returns:
        LogoutResponse: Logout result with success status and message
        
    Raises:
        HTTPException:
        - 503 SERVICE_UNAVAILABLE: External authentication service is unavailable
        
    Error Handling Philosophy:
        The endpoint prioritizes user experience over strict error reporting:
        - External service unavailable: Still allows local logout
        - Invalid token: Treats as successful logout (already logged out)
        - Endpoint not found: Assumes external service doesn't support logout
        - Network errors: Logs warning but allows local logout to proceed
        
    Success Scenarios:
        - Normal logout: External service confirms token invalidation
        - Graceful degradation: Local logout when external logout unavailable
        - Already logged out: Token already invalid, treat as success
        
    Frontend Integration:
        The frontend should handle logout responses appropriately:
        - success=true: Proceed with local logout and redirect
        - success=false with 503 status: Display service unavailable message
        - All other cases: Proceed with local logout
        
    Example Success Response:
        ```json
        {
            "success": true,
            "message": "Logout successful"
        }
        ```
        
    Example Graceful Failure Response:
        ```json
        {
            "success": true,
            "message": "Local logout successful (external logout not supported)"
        }
        ```
    """
    auth_service = AuthenticationService()
    result = await auth_service.logout_with_token(request.access_token)
    
    if not result["success"]:
        logger.warning(f"External logout failed: {result['message']}")
        
        # For certain errors, we still want to allow the frontend to proceed
        if "endpoint not found" in result["message"].lower() or "404" in result["message"]:
            # External service doesn't support logout, but we allow local logout
            return LogoutResponse(
                success=True, 
                message="Local logout successful (external logout not supported)"
            )
        elif "invalid token" in result["message"].lower() or "401" in result["message"]:
            # Token already invalid, treat as successful logout
            return LogoutResponse(
                success=True,
                message="Logout successful (token already invalid)"
            )
        elif "service unavailable" in result["message"].lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=result["message"],
            )
        else:
            # For other errors, still allow local logout but log the issue
            logger.error(f"Logout API error: {result['message']}")
            return LogoutResponse(
                success=True,
                message="Local logout successful (external logout failed)"
            )
    
    return LogoutResponse(**result)


@router.get("/login-url", response_model=LoginUrlResponse)
async def get_login_url():
    """
    Get OAuth login URL for user authentication redirection.
    
    This endpoint provides the complete OAuth login URL that frontend applications
    should redirect users to when authentication is required. The URL points to
    the external authentication provider's login interface.
    
    Returns:
        LoginUrlResponse: Contains the complete OAuth login URL
        
    Usage Flow:
        1. Frontend calls this endpoint to get the login URL
        2. Frontend redirects user's browser to the returned URL
        3. User authenticates with external provider
        4. External provider redirects back with authorization code
        5. Frontend uses authorization code with /authenticate endpoint
        
    URL Configuration:
        The login URL is constructed using the BASE_URL from service settings
        and points to the external authentication provider's admin interface.
        
    Example Response:
        ```json
        {
            "login_url": "https://external-auth-service.com/admin/"
        }
        ```
        
    Frontend Integration:
        ```javascript
        // Get login URL
        const response = await fetch('/auth/api/v1/login-url');
        const { login_url } = await response.json();
        
        // Redirect user to login
        window.location.href = login_url;
        ```
        
    Note:
        This endpoint requires no authentication and can be called by
        anonymous users who need to initiate the login process.
    """
    auth_service = AuthenticationService()
    login_url = auth_service.get_login_url()
    
    return LoginUrlResponse(login_url=login_url)


@router.post("/validate-token", response_model=ValidateTokenResponse)
async def validate_token(request: ValidateTokenRequest):
    """
    Validate access token and retrieve associated user information.
    
    This endpoint verifies that an access token is still valid with the external
    authentication service and returns associated user information if available.
    It's used for session validation and user context retrieval.
    
    The validation process:
    1. Sends token to external authentication service for verification
    2. Retrieves user information if token is valid and active
    3. Returns validation status with user data or appropriate error message
    
    Args:
        request: ValidateTokenRequest containing the access token to validate
        
    Returns:
        ValidateTokenResponse: Validation result with user information if valid
        
    Token Validation:
        The endpoint uses the external authentication service's getappproperity
        endpoint to validate tokens, as this is a known working endpoint that
        requires valid authentication.
        
    Response Scenarios:
        - Valid token: Returns valid=true with user information
        - Invalid/expired token: Returns valid=false with error message
        - Service unavailable: Returns valid=false with service error
        - Malformed response: Returns valid=true but with limited user data
        
    Frontend Usage:
        This endpoint is typically used for:
        - Session persistence checks on page load
        - Periodic token validation during long sessions
        - User context retrieval for UI personalization
        - API call authorization verification
        
    Example Valid Token Response:
        ```json
        {
            "valid": true,
            "message": "Token is valid",
            "tenant_id": "tenant-123",
            "first_name": "John",
            "username": "john.doe",
            "business_name": "Acme Corp"
        }
        ```
        
    Example Invalid Token Response:
        ```json
        {
            "valid": false,
            "message": "Token is invalid or expired",
            "tenant_id": null,
            "first_name": null,
            "username": null,
            "business_name": null
        }
        ```
        
    Error Handling:
        The endpoint does not raise HTTP exceptions for invalid tokens,
        instead returning validation failure in the response. This allows
        frontend applications to handle invalid tokens gracefully without
        triggering error handling code paths.
    """
    auth_service = AuthenticationService()
    result = await auth_service.validate_token(request.access_token)
    
    if not result["valid"]:
        # Return validation failure but don't raise HTTP exception
        # The frontend should handle invalid tokens gracefully
        return ValidateTokenResponse(**result)
    
    return ValidateTokenResponse(**result)
