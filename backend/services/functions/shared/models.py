"""
Pydantic models for data ingestion API.

These models are adapted from the original FastAPI service for use
with Azure Functions HTTP triggers.
"""

from datetime import date, datetime, timedelta
from typing import Any

from pydantic import BaseModel, ValidationInfo, field_validator


class CreateIngestionJobRequest(BaseModel):
    """
    Request model for creating data ingestion jobs.

    This Pydantic model validates and structures ingestion job requests,
    ensuring date ranges are valid and data types are allowed. Provides
    sensible defaults for date ranges (last 2 days) if not specified.

    Attributes:
        start_date: Beginning of date range for data ingestion (inclusive).
                   Defaults to 2 days ago if not provided.
        end_date: End of date range for data ingestion (inclusive).
                 Defaults to today if not provided.
        data_types: List of data types to process. Allowed values:
                   - "events": BigQuery GA4 event extraction
                   - "users": SFTP user data download
                   - "locations": SFTP location data download
                   Defaults to all three if not specified.

    Example:
        >>> request = CreateIngestionJobRequest(
        ...     start_date=date(2024, 1, 1),
        ...     end_date=date(2024, 1, 7),
        ...     data_types=["events", "users"]
        ... )
    """

    start_date: date | None = None
    end_date: date | None = None
    data_types: list[str] | None = ["events", "users", "locations"]

    def __init__(self, **data: Any) -> None:
        """
        Initialize request with default dates if not provided.

        Sets default date range to last 2 days (yesterday and today) if
        start_date or end_date are not explicitly provided. This ensures
        jobs always have valid date ranges.

        Args:
            **data: Keyword arguments for model initialization.

        Note:
            - Defaults to 2 days ago for start_date
            - Defaults to today for end_date
            - Only sets defaults if values are None or missing
        """
        # Set default dates if not provided
        today = date.today()
        two_days_ago = today - timedelta(days=2)

        if "start_date" not in data or data["start_date"] is None:
            data["start_date"] = two_days_ago
        if "end_date" not in data or data["end_date"] is None:
            data["end_date"] = today

        super().__init__(**data)

    @field_validator("end_date")
    @classmethod
    def end_date_must_be_after_start_date(cls, v: date, info: ValidationInfo) -> date:
        """
        Validate that end_date is not before start_date.

        Ensures date ranges are logically valid for data ingestion queries.

        Args:
            v: End date value being validated.
            info: Validation context containing other field values.

        Returns:
            date: Validated end date.

        Raises:
            ValueError: If end_date is before start_date.
        """
        if info.data.get("start_date") and v < info.data["start_date"]:
            msg = "end_date must be after start_date"
            raise ValueError(msg)
        return v

    @field_validator("data_types")
    @classmethod
    def valid_data_types(cls, v: list[str]) -> list[str]:
        """
        Validate that all data types are in the allowed set.

        Ensures only supported data types are specified in the request.

        Args:
            v: List of data type strings to validate.

        Returns:
            list[str]: Validated list of data types.

        Raises:
            ValueError: If any data type is not in the allowed set.
        """
        allowed_types = {"events", "users", "locations"}
        if not set(v).issubset(allowed_types):
            msg = f"data_types must be subset of {allowed_types}"
            raise ValueError(msg)
        return v

    def to_dict(self) -> dict[str, Any]:
        """
        Convert model instance to dictionary for JSON serialization.

        Transforms the Pydantic model to a dictionary with ISO-formatted
        dates suitable for queue message serialization.

        Returns:
            dict[str, Any]: Dictionary representation with ISO date strings.
        """
        return {
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "data_types": self.data_types,
        }

