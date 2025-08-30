"""
Common ORM models for all backend services.
"""

# Import all models to make them available
from .analytics import Tenants, TaskTracking
from .dimensions import Users, Locations
from .events import Purchase, AddToCart, PageView, ViewSearchResults, NoSearchResults, ViewItem
from .control import ProcessingJobs
from .data_ingestion import DataIngestionRequest, DataIngestionResponse
from .job_status import JobProgress, JobStatus, JobListResponse

__all__ = [
    # Control/Analytics models (SQLAlchemy ORM)
    "Tenants", "TaskTracking",
    
    # Dimension models (SQLAlchemy ORM)
    "Users", "Locations",
    
    # Event models (SQLAlchemy ORM)
    "Purchase", "AddToCart", "PageView", "ViewSearchResults", "NoSearchResults", "ViewItem",
    
    # Data processing models (SQLAlchemy ORM)
    "ProcessingJobs",
    
    # Data ingestion models (Pydantic)
    "DataIngestionRequest", "DataIngestionResponse",
    
    # Job status models (Pydantic)
    "JobProgress", "JobStatus", "JobListResponse",
]
