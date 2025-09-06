from fastapi import APIRouter
from services.data_service.api.v1.endpoints import ingestion

api_router = APIRouter()

api_router.include_router(ingestion.router, tags=["Ingestion"])
