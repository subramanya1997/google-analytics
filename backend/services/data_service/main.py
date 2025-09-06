from common.fastapi import create_fastapi_app
from common.config import get_settings
from services.data_service.api.v1.api import api_router

# Get settings for this service
settings = get_settings("data-ingestion-service")
# Create FastAPI app with reverse proxy configuration
app = create_fastapi_app(
    service_name="data-ingestion-service",
    description="Data ingestion service for Google Analytics intelligence system",
    api_router=api_router,
    root_path="/data"  # Nginx serves this at /data/
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
