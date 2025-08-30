from fastapi import Depends
from common.security import get_current_user, AuthenticatedUser
from common.fastapi import create_fastapi_app
from pydantic import BaseModel
from typing import Optional

app = create_fastapi_app(
    service_name="auth-service",
    description="Authentication and authorization service for Google Analytics Intelligence System"
)

class UserProfile(BaseModel):
    id: str
    tenant_id: str
    email: Optional[str] = None

@app.get("/v1/auth/me", response_model=UserProfile)
async def read_users_me(current_user: AuthenticatedUser = Depends(get_current_user)):
    """
    Returns the profile of the currently authenticated user based on their JWT.
    """
    return UserProfile(id=current_user.id, tenant_id=current_user.tenant_id, email=current_user.email)

# Root and health endpoints are provided by create_fastapi_app