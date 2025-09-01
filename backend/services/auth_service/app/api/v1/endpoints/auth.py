"""
Authentication endpoints.
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List

from services.auth_service.app.services.auth_service import AuthenticationService

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
    missing_configs: Optional[List[str]] = None
    invalid_configs: Optional[List[str]] = None


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
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=result["message"]
            )
        elif "service unavailable" in result["message"]:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=result["message"]
            )
        elif "configurations" in result["message"]:
            # Configuration issues are not HTTP errors, return as successful response
            return AuthResponse(**result)
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["message"]
            )
    
    return AuthResponse(**result)
