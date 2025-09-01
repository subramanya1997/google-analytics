from fastapi import APIRouter
from services.data_service.app.api.v1.endpoints import data_ingestion

api_router = APIRouter()

api_router.include_router(data_ingestion.router, prefix="/data", tags=["data-ingestion"])
