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
from typing import Any

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

    start_date: date | None = None
    end_date: date | None = None
    data_types: list[str] | None = ["events", "users", "locations"]

    def __init__(self, **data: Any) -> None:
        # Set default dates if not provided
        today = date.today()
        two_days_ago = today - timedelta(days=2)

        if "start_date" not in data or data["start_date"] is None:
            data["start_date"] = two_days_ago
        if "end_date" not in data or data["end_date"] is None:
            data["end_date"] = today

        super().__init__(**data)

    @validator("end_date")
    def end_date_must_be_after_start_date(cls, v: date, values: dict[str, Any]) -> date:
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
            msg = "end_date must be after start_date"
            raise ValueError(msg)
        return v

    @validator("data_types")
    def valid_data_types(cls, v: list[str]) -> list[str]:
        allowed_types = {"events", "users", "locations"}
        if not set(v).issubset(allowed_types):
            msg = f"data_types must be subset of {allowed_types}"
            raise ValueError(msg)
        return v

    class Config:
        json_encoders = {date: lambda v: v.isoformat()}


class IngestionJobResponse(BaseModel):
    """
    Response model for data ingestion job creation and status queries.

    This model represents the response returned when creating a new ingestion
    job or querying job status. It provides immediate feedback to the client
    about the job that was created, including its unique identifier and initial
    status.

    Attributes:
        job_id: Unique identifier for the ingestion job (format: "job_{hex}").
               Used for tracking job status and querying job details.
        start_date: Beginning of date range for data ingestion (inclusive).
                   ISO format date string (YYYY-MM-DD).
        end_date: End of date range for data ingestion (inclusive).
                 ISO format date string (YYYY-MM-DD).
        data_types: List of data types being processed in this job.
                   Valid values: "events", "users", "locations".
        status: Current status of the job.
               Valid values: "queued", "processing", "completed", "failed".
        created_at: Timestamp when the job was created.
                   ISO format datetime string with timezone.

    Status Lifecycle:
        - "queued": Job created, waiting for background worker to pick up
        - "processing": Job actively running data extraction/transformation
        - "completed": All data types processed successfully
        - "failed": Job encountered unrecoverable error

    Serialization:
        Dates and datetimes are serialized to ISO format strings for JSON
        compatibility and consistent API responses.

    Example:
        ```json
        {
            "job_id": "job_a1b2c3d4e5f6",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "data_types": ["events", "users", "locations"],
            "status": "queued",
            "created_at": "2024-02-01T08:00:00Z"
        }
        ```

    See Also:
        - CreateIngestionJobRequest: Request model for job creation
        - services.data_service.api.v1.endpoints.ingestion: Ingestion endpoints
    """

    job_id: str
    start_date: date
    end_date: date
    data_types: list[str]
    status: str
    created_at: datetime

    class Config:
        json_encoders = {
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat(),
        }
