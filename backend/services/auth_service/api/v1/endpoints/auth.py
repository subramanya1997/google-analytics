"""
Authentication endpoints.
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from loguru import logger

from services.auth_service.services.auth_service import AuthenticationService

router = APIRouter()


class AuthRequest(BaseModel):
    """Request model for authentication."""

    code: str


class AuthResponse(BaseModel):
    """Response model for authentication."""

    success: bool
    message: str
    tenant_id: Optional[str] = None
    first_name: Optional[str] = None
    username: Optional[str] = None
    access_token: Optional[str] = None
    missing_configs: Optional[List[str]] = None
    invalid_configs: Optional[List[str]] = None


class LogoutRequest(BaseModel):
    """Request model for logout."""
    
    access_token: str


class LogoutResponse(BaseModel):
    """Response model for logout."""
    
    success: bool
    message: str


class LoginUrlResponse(BaseModel):
    """Response model for login URL."""
    
    login_url: str


@router.post("/authenticate", response_model=AuthResponse)
async def authenticate(request: AuthRequest):
    """
    Authenticate user with code and validate configurations.

    This endpoint:
    1. Validates the authentication code with the external service
    2. Retrieves application settings using the obtained tokens
    3. Validates all required configurations (postgres, bigquery, sftp)
    4. Ensures the tenant exists in the database
    5. Returns authentication result with tenant_id for frontend use
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
    Logout user by invalidating the access token.
    
    This endpoint:
    1. Calls the external logout service to invalidate the token
    2. Returns success/failure status
    
    Note: Even if the external logout fails, we return success to allow
    the frontend to continue with local logout and redirect.
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
    Get the login URL for OAuth authentication.
    
    This endpoint returns the external login URL that users should be redirected to
    when they need to authenticate.
    """
    auth_service = AuthenticationService()
    login_url = auth_service.get_login_url()
    
    return LoginUrlResponse(login_url=login_url)
