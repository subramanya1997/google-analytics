"""
Authentication API Models.

This module defines the Pydantic models for the authentication service API,
providing request and response schemas with validation for the authentication
and authorization workflow.
"""

from typing import List, Optional

from pydantic import BaseModel


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
