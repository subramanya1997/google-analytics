from fastapi import APIRouter

from services.data_service.api.v1.endpoints import ingestion, schedule

api_router = APIRouter()

api_router.include_router(ingestion.router, tags=["Ingestion"])
api_router.include_router(schedule.router, prefix="/data", tags=["Schedule"])
