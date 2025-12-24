"""
Pydantic models for data ingestion API.

These models are adapted from the original FastAPI service for use
with Azure Functions HTTP triggers.
"""

from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, field_validator


class CreateIngestionJobRequest(BaseModel):
    """
    Request model for creating data ingestion jobs.
    
    Attributes:
        start_date: Beginning of date range for data ingestion (inclusive)
        end_date: End of date range for data ingestion (inclusive) 
        data_types: List of data types to process in this job
    """

    start_date: Optional[date] = None
    end_date: Optional[date] = None
    data_types: Optional[List[str]] = ["events", "users", "locations"]

    def __init__(self, **data):
        # Set default dates if not provided
        today = date.today()
        two_days_ago = today - timedelta(days=2)

        if 'start_date' not in data or data['start_date'] is None:
            data['start_date'] = two_days_ago
        if 'end_date' not in data or data['end_date'] is None:
            data['end_date'] = today

        super().__init__(**data)

    @field_validator("end_date")
    @classmethod
    def end_date_must_be_after_start_date(cls, v, info):
        """Validate that end_date is after start_date."""
        if info.data.get("start_date") and v < info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v

    @field_validator("data_types")
    @classmethod
    def valid_data_types(cls, v):
        allowed_types = {"events", "users", "locations"}
        if not set(v).issubset(allowed_types):
            raise ValueError(f"data_types must be subset of {allowed_types}")
        return v

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "data_types": self.data_types,
        }


class IngestionJobResponse(BaseModel):
    """Response model for data ingestion."""

    job_id: str
    start_date: date
    end_date: date
    data_types: List[str]
    status: str
    created_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "job_id": self.job_id,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "data_types": self.data_types,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }


class JobStatusResponse(BaseModel):
    """Response model for job status queries."""
    
    job_id: str
    tenant_id: str
    status: str
    data_types: List[str]
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    progress: Optional[Dict[str, Any]] = None
    records_processed: Optional[Dict[str, int]] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class DataAvailabilityResponse(BaseModel):
    """Response model for data availability queries."""
    
    summary: Dict[str, Any]


class ScheduleRequest(BaseModel):
    """Request model for creating/updating schedule."""
    
    cron_expression: Optional[str] = None
    status: Optional[str] = None


class ScheduleResponse(BaseModel):
    """Response model for schedule operations."""
    
    cron_expression: str
    status: str
    source: str


# ============================================================================
# Email Models
# ============================================================================

class SendReportsRequest(BaseModel):
    """Request model for sending branch reports via email."""
    
    report_date: Optional[date] = None
    branch_codes: Optional[List[str]] = None  # None means all branches

    def __init__(self, **data):
        # Set default date if not provided (yesterday)
        if 'report_date' not in data or data['report_date'] is None:
            data['report_date'] = date.today() - timedelta(days=1)
        super().__init__(**data)




class EmailJobResponse(BaseModel):
    """Response model for email sending jobs."""
    
    job_id: str
    status: str
    tenant_id: str
    report_date: date
    target_branches: List[str] = []
    total_emails: int = 0
    emails_sent: int = 0
    emails_failed: int = 0
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "job_id": self.job_id,
            "status": self.status,
            "tenant_id": self.tenant_id,
            "report_date": self.report_date.isoformat() if self.report_date else None,
            "target_branches": self.target_branches,
            "total_emails": self.total_emails,
            "emails_sent": self.emails_sent,
            "emails_failed": self.emails_failed,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "message": self.message,
        }