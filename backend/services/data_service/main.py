from common.fastapi import create_fastapi_app
from services.data_service.api.v1.api import api_router

# Create FastAPI app with reverse proxy configuration
app = create_fastapi_app(
    service_name="data-ingestion-service",
    description="Data ingestion service for Google Analytics intelligence system",
    api_router=api_router,
    root_path="/data",  # Nginx serves this at /data/
)
