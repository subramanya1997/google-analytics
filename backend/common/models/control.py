"""
Control models for system-level operations and job tracking.

This module contains ORM models for tracking and managing system operations,
particularly data ingestion and processing jobs. These models are used for
monitoring, debugging, and managing asynchronous operations.

Models:
    ProcessingJobs: Tracks data ingestion and processing jobs with status,
        progress, and error information.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import TIMESTAMP, Date, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from common.database import Base


class ProcessingJobs(Base):
    """
    Model representing data ingestion and processing jobs.

    This model tracks the lifecycle of data processing jobs, including their status,
    progress, and any errors that occur during processing. It supports tracking
    multiple data types and provides detailed progress information.

    Attributes:
        id (str): Unique job identifier (UUID). Primary key. Auto-generated.
        tenant_id (str): Tenant ID (UUID) that owns this job. Required.
        job_id (str): External job identifier (e.g., from scheduler). Unique.
        status (str): Current job status. Common values: "pending", "running",
            "completed", "failed", "cancelled".
        data_types (dict): JSON object mapping data types to their processing status.
            Example: {"page_view": "completed", "purchase": "pending"}
        start_date (date): Start date for data extraction/processing.
        end_date (date): End date for data extraction/processing.
        progress (dict): JSON object tracking overall progress. May include:
            - "total_records": int
            - "processed_records": int
            - "percentage": float
        records_processed (dict): JSON object mapping data types to record counts.
            Example: {"page_view": 1000, "purchase": 500}
        error_message (str | None): Error message if job failed. None if successful.
        started_at (datetime | None): Timestamp when job started processing.
        completed_at (datetime | None): Timestamp when job completed (success or failure).

    Table:
        processing_jobs

    Example:
        ```python
        from common.models import ProcessingJobs
        from datetime import date
        
        # Create a new job
        job = ProcessingJobs(
            tenant_id="tenant-123",
            job_id="job-456",
            status="pending",
            data_types={"page_view": "pending", "purchase": "pending"},
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            progress={"total_records": 0, "processed_records": 0}
        )
        session.add(job)
        
        # Update job progress
        job.status = "running"
        job.progress = {"total_records": 1000, "processed_records": 500, "percentage": 50.0}
        job.records_processed = {"page_view": 500, "purchase": 0}
        ```

    Note:
        - All timestamps are timezone-aware
        - JSONB fields allow flexible schema for progress and data type tracking
        - Error messages should be descriptive for debugging purposes
    """
    __tablename__ = "processing_jobs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    job_id: Mapped[str] = mapped_column(String(255), unique=True)
    status: Mapped[str] = mapped_column(String(50))
    data_types: Mapped[dict] = mapped_column(JSONB)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    progress: Mapped[dict] = mapped_column(JSONB, default=dict)
    records_processed: Mapped[dict] = mapped_column(JSONB, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
