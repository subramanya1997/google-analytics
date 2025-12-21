"""
Data Ingestion API Models.

This module defines the Pydantic models for the data ingestion service API,
providing comprehensive request and response schemas with validation for
the complete data ingestion workflow.

The models ensure type safety, data validation, and API documentation
generation while supporting the multi-source, multi-tenant data ingestion
architecture of the Google Analytics Intelligence System.

Model Categories:
- **Request Models**: Input validation for API endpoints
- **Response Models**: Structured API responses with proper serialization
- **Validation Logic**: Business rule enforcement and data integrity

Key Features:
- Comprehensive input validation with custom validators
- Date range validation for time-series data processing
- Data type enumeration with allowed values enforcement
- ISO format date/datetime serialization for API consistency
- Multi-tenant job tracking and status management
"""

from datetime import date, datetime, timedelta
from typing import List, Optional

from pydantic import BaseModel, validator


class CreateIngestionJobRequest(BaseModel):
    """
    Request model for creating data ingestion jobs.
    
    Defines the parameters for initiating a new data ingestion job including
    date range specification and data type selection. Includes comprehensive
    validation to ensure data integrity and prevent processing errors.
    
    Attributes:
        start_date: Beginning of date range for data ingestion (inclusive)
        end_date: End of date range for data ingestion (inclusive) 
        data_types: List of data types to process in this job
                   Default: ["events", "users", "locations"] (all types)
    
    Validation Rules:
        - end_date must be after start_date (prevents invalid date ranges)
        - data_types must be subset of allowed types (prevents invalid processing)
        - Date range should be reasonable for processing performance
    
    Supported Data Types:
        - "events": Google Analytics 4 event data from BigQuery
        - "users": User profile data from SFTP sources
        - "locations": Location/warehouse data from SFTP sources
    
    Business Logic:
        Jobs process data for the specified date range and data types:
        - Events are extracted from BigQuery for the date range
        - Users and locations are current snapshots (date range not applicable)
        - Each data type is processed independently with separate error handling
        - Job status is tracked throughout the processing pipeline
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
        """
        Validate that end_date is after start_date for logical date ranges.
        
        Prevents invalid date ranges that would cause processing errors or
        unexpected behavior in data extraction queries.
        
        Args:
            v: end_date value to validate
            values: Dictionary of previously validated field values
            
        Returns:
            date: Validated end_date value
            
        Raises:
            ValueError: If end_date is not after start_date
        """
        if "start_date" in values and v < values["start_date"]:
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
