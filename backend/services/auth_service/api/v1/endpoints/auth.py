"""
Authentication endpoints.
"""

from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from pydantic import BaseModel
from loguru import logger

from services.auth_service.services.auth_service import AuthenticationService
from services.auth_service.api.dependencies import get_auth_service
from common.database import get_tenant_service_status

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
    business_name: Optional[str] = None
    access_token: Optional[str] = None


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


class ValidateTokenRequest(BaseModel):
    """Request model for token validation."""
    
    access_token: str


class ValidateTokenResponse(BaseModel):
    """Response model for token validation."""
    
    valid: bool
    message: str
    tenant_id: Optional[str] = None
    first_name: Optional[str] = None
    username: Optional[str] = None
    business_name: Optional[str] = None


class ServiceStatusDetail(BaseModel):
    """Service status details."""
    
    enabled: bool
    error: Optional[str] = None


class ServiceStatusResponse(BaseModel):
    """Response model for service status."""
    
    tenant_id: str
    services: Dict[str, ServiceStatusDetail]


class RevalidateServicesRequest(BaseModel):
    """Request model for revalidating services."""
    
    tenant_id: str


class RevalidateServicesResponse(BaseModel):
    """Response model for revalidating services."""
    
    success: bool
    message: str
    tenant_id: str


@router.post("/authenticate", response_model=AuthResponse)
async def authenticate(
    request: AuthRequest,
    auth_service: AuthenticationService = Depends(get_auth_service)
):
    """
    Authenticate user with code and validate configurations.

    This endpoint:
    1. Validates the authentication code with the external service
    2. Retrieves application settings using the obtained tokens
    3. Validates all required configurations (postgres, bigquery, sftp)
    4. Ensures the tenant exists in the database
    5. Returns authentication result with tenant_id for frontend use
    """
    result = await auth_service.authenticate_with_code(request.code)
    return AuthResponse(**result)


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: LogoutRequest,
    auth_service: AuthenticationService = Depends(get_auth_service)
):
    """
    Logout user by invalidating the access token.
    
    This endpoint:
    1. Calls the external logout service to invalidate the token
    2. Returns success/failure status
    
    Note: Even if the external logout fails, we return success to allow
    the frontend to continue with local logout and redirect.
    """
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
async def get_login_url(
    auth_service: AuthenticationService = Depends(get_auth_service)
):
    """
    Get the login URL for OAuth authentication.
    
    This endpoint returns the external login URL that users should be redirected to
    when they need to authenticate.
    """
    login_url = auth_service.get_login_url()
    
    return LoginUrlResponse(login_url=login_url)


@router.post("/validate-token", response_model=ValidateTokenResponse)
async def validate_token(
    request: ValidateTokenRequest,
    auth_service: AuthenticationService = Depends(get_auth_service)
):
    """
    Validate an access token and return user information.
    
    This endpoint:
    1. Validates the access token with the external service
    2. Returns user information if the token is valid
    3. Returns validation failure if the token is invalid or expired
    """
    result = await auth_service.validate_token(request.access_token)
    
    if not result["valid"]:
        # Return validation failure but don't raise HTTP exception
        # The frontend should handle invalid tokens gracefully
        return ValidateTokenResponse(**result)
    
    return ValidateTokenResponse(**result)


@router.get("/service-status", response_model=ServiceStatusResponse)
async def get_service_status(
    tenant_id: str,
):
    """
    Get service enable/disable status for a tenant.
    
    This endpoint returns the current status of all services (BigQuery, SFTP, SMTP)
    for the specified tenant. Services may be disabled if their configurations
    failed validation.
    
    Args:
        tenant_id: The tenant ID to check service status for
    
    Returns:
        ServiceStatusResponse containing enabled/disabled status and error messages
        for each service
    """
    try:
        service_status = await get_tenant_service_status(tenant_id, "auth-service")
        
        # Convert to response model format
        services = {
            service_name: ServiceStatusDetail(
                enabled=status["enabled"],
                error=status["error"]
            )
            for service_name, status in service_status.items()
        }
        
        return ServiceStatusResponse(
            tenant_id=tenant_id,
            services=services
        )
        
    except Exception as e:
        logger.error(f"Error fetching service status for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch service status: {str(e)}"
        )


@router.post("/revalidate-services", response_model=RevalidateServicesResponse)
async def revalidate_services(
    request: RevalidateServicesRequest,
    background_tasks: BackgroundTasks,
    auth_service: AuthenticationService = Depends(get_auth_service)
):
    """
    Trigger background re-validation of all service configurations.
    
    This endpoint is useful after updating tenant configurations to re-check
    if services should be enabled or disabled. The validation runs in the
    background and updates the database.
    
    Args:
        request: Contains tenant_id to revalidate
        background_tasks: FastAPI background tasks manager
        auth_service: Authentication service dependency
    
    Returns:
        RevalidateServicesResponse indicating the revalidation was triggered
    """
    try:
        # Trigger background revalidation
        background_tasks.add_task(
            auth_service.revalidate_tenant_services,
            request.tenant_id
        )
        
        logger.info(f"Triggered service revalidation for tenant {request.tenant_id}")
        
        return RevalidateServicesResponse(
            success=True,
            message="Service revalidation triggered successfully",
            tenant_id=request.tenant_id
        )
        
    except Exception as e:
        logger.error(f"Error triggering service revalidation for tenant {request.tenant_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger service revalidation: {str(e)}"
        )
