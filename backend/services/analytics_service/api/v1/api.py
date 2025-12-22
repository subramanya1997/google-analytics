from fastapi import APIRouter

from services.analytics_service.api.v1.endpoints import email, history, locations, stats, tasks

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(locations.router, tags=["locations"])
api_router.include_router(stats.router, tags=["statistics"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
api_router.include_router(history.router, tags=["History"])
api_router.include_router(email.router, prefix="/email", tags=["Email"])
