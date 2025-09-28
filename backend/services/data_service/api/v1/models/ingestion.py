from datetime import date, datetime, timedelta
from typing import List, Optional

from pydantic import BaseModel, validator


class CreateIngestionJobRequest(BaseModel):
    """Request model for data ingestion.

    If start_date and/or end_date are not provided, defaults to:
    - start_date: 2 days ago (including today as end_date)
    - end_date: today
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

    @validator("end_date")
    def end_date_must_be_after_start_date(cls, v, values):
        # Only validate if both dates are present (they should be set by __init__)
        if "start_date" in values and values["start_date"] is not None and v < values["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v

    @validator("data_types")
    def valid_data_types(cls, v):
        allowed_types = {"events", "users", "locations"}
        if not set(v).issubset(allowed_types):
            raise ValueError(f"data_types must be subset of {allowed_types}")
        return v

    class Config:
        json_encoders = {date: lambda v: v.isoformat()}


class IngestionJobResponse(BaseModel):
    """Response model for data ingestion."""

    job_id: str
    start_date: date
    end_date: date
    data_types: List[str]
    status: str
    created_at: datetime

    class Config:
        json_encoders = {
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat(),
        }
