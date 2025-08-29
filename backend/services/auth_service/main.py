from fastapi import FastAPI, Depends
from services.common.security import get_current_user, AuthenticatedUser
from pydantic import BaseModel
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware 

app = FastAPI()


origins = [
    "http://localhost:3000", # The origin of your Next.js app
    # Add your production frontend URL here later
    # "https://your-production-domain.com",
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods (GET, POST, etc.)
    allow_headers=["*"], # Allows all headers
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

@app.get("/")
def read_root():
    return {"service": "Auth Service", "status": "ok"}