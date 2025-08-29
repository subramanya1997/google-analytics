from pydantic import BaseModel, validator
from datetime import datetime, date
from typing import List, Optional
from uuid import UUID


class DataIngestionRequest(BaseModel):
    """Request model for data ingestion."""
    tenant_id: str
    start_date: date
    end_date: date
    data_types: Optional[List[str]] = ["events", "users", "locations"]
    force_refresh: Optional[bool] = False
    
    @validator('end_date')
    def end_date_must_be_after_start_date(cls, v, values):
        if 'start_date' in values and v < values['start_date']:
            raise ValueError('end_date must be after start_date')
        return v
    
    @validator('data_types')
    def valid_data_types(cls, v):
        allowed_types = {"events", "users", "locations"}
        if not set(v).issubset(allowed_types):
            raise ValueError(f'data_types must be subset of {allowed_types}')
        return v
    
    class Config:
        json_encoders = {
            date: lambda v: v.isoformat()
        }


class DataIngestionResponse(BaseModel):
    """Response model for data ingestion."""
    job_id: str
    tenant_id: str
    start_date: date
    end_date: date
    data_types: List[str]
    status: str
    created_at: datetime
    estimated_completion: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat()
        }
