"""
Control and job processing models.

This module defines database models for tracking and managing data processing jobs
within the Google Analytics Intelligence System. These models support multi-tenant
job tracking with detailed progress monitoring and error reporting.
"""
from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from sqlalchemy import TIMESTAMP, Date, String, Text, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, declared_attr

from common.database import Base


class ProcessingJobs(Base):
    """
    Model for tracking data processing jobs across tenants.
    
    Tracks the lifecycle of data processing jobs including ingestion tasks,
    analytics computations, and report generation. Provides detailed progress
    monitoring, error tracking, and status management for long-running operations.
    
    Attributes:
        id: Unique job identifier (UUID)
        tenant_id: Tenant this job belongs to
        job_id: Human-readable job identifier, must be unique
        status: Current job status (pending, running, completed, failed, etc.)
        data_types: JSON object defining what data types are being processed
        start_date: Date range start for data processing
        end_date: Date range end for data processing
        progress: JSON object tracking progress by data type or stage
        records_processed: JSON object with counts of records processed by type
        error_message: Detailed error information if job failed
        started_at: Timestamp when job execution began
        completed_at: Timestamp when job finished (success or failure)
        created_at: Inherited from Base - when job was created
        updated_at: Inherited from Base - last status update
        
    """
    __tablename__ = "processing_jobs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    job_id: Mapped[str] = mapped_column(String(255), unique=True)
    status: Mapped[str] = mapped_column(String(50))
    data_types: Mapped[dict] = mapped_column(JSONB)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    progress: Mapped[dict] = mapped_column(JSONB, default=dict)
    records_processed: Mapped[dict] = mapped_column(JSONB, default=dict)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))