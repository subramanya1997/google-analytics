"""
API router for auth service v1.
"""
from fastapi import APIRouter
from services.auth_service.api.v1.endpoints import auth

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
