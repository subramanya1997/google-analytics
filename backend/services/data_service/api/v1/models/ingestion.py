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

from datetime import date, datetime
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

    start_date: date
    end_date: date
    data_types: Optional[List[str]] = ["events", "users", "locations"]

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
        """
        Validate data_types contains only supported data processing types.
        
        Ensures that only supported data types are requested for processing
        to prevent errors in the ingestion pipeline and ensure proper resource
        allocation.
        
        Args:
            v: List of data_types to validate
            
        Returns:
            List[str]: Validated data_types list
            
        Raises:
            ValueError: If any data_types are not in the allowed set
        """
        allowed_types = {"events", "users", "locations"}
        if not set(v).issubset(allowed_types):
            raise ValueError(f"data_types must be subset of {allowed_types}")
        return v

    class Config:
        """Pydantic model configuration for JSON serialization."""
        json_encoders = {date: lambda v: v.isoformat()}


class IngestionJobResponse(BaseModel):
    """
    Response model for data ingestion job information.
    
    Provides comprehensive job information including status, configuration,
    and timing data for client applications to track job progress and results.
    
    Attributes:
        job_id: Unique identifier for the ingestion job
        start_date: Job start date (data range beginning)
        end_date: Job end date (data range end)
        data_types: List of data types being processed in this job
        status: Current job status (queued, processing, completed, failed)
        created_at: Timestamp when the job was created
    
    Job Status Values:
        - "queued": Job created and waiting for processing
        - "processing": Job currently being executed
        - "completed": Job finished successfully
        - "failed": Job encountered errors and stopped
    
    Usage Context:
        Used for both job creation responses and status query responses,
        providing consistent job information across all job-related endpoints.
    
    Client Integration:
        Clients can use this response to:
        - Track job progress through status field
        - Display job configuration to users  
        - Implement polling for job completion
        - Handle error scenarios appropriately
    """

    job_id: str
    start_date: date
    end_date: date
    data_types: List[str]
    status: str
    created_at: datetime

    class Config:
        """Pydantic model configuration for JSON serialization."""
        json_encoders = {
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat(),
        }
