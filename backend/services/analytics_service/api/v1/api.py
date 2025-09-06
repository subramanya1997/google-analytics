from fastapi import APIRouter
from services.analytics_service.api.v1.endpoints import stats, tasks, locations, sessions, users

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(locations.router, prefix="/locations", tags=["locations"])
api_router.include_router(stats.router, prefix="/stats", tags=["statistics"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
