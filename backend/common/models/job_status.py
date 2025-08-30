from pydantic import BaseModel
from datetime import datetime, date
from typing import Dict, Optional, List
from uuid import UUID


class JobProgress(BaseModel):
    """Progress information for a job."""
    events: Optional[int] = None
    users: Optional[int] = None
    locations: Optional[int] = None


class JobStatus(BaseModel):
    """Status information for a processing job."""
    job_id: str
    tenant_id: str
    status: str
    progress: Dict[str, int] = {}
    start_date: date
    end_date: date
    data_types: List[str]
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    records_processed: Dict[str, int] = {}
    
    class Config:
        json_encoders = {
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat()
        }


class JobListResponse(BaseModel):
    """Response model for job listing."""
    jobs: List[JobStatus]
    total: int
    page: int
    limit: int