"""
Email Configuration and Management Pydantic Models.

This module provides Pydantic models for email-related operations in the analytics service,
including branch-to-sales-rep mappings, report sending requests, and email job tracking.
"""

from datetime import date, datetime, timedelta
from typing import List, Optional

from pydantic import BaseModel, EmailStr, validator


class BranchEmailMappingRequest(BaseModel):
    """Request model for creating or updating branch email mappings.
    
    Associates branch codes with sales representative email addresses for automated
    report distribution. Validates email format and ensures proper branch identification.
    """

    branch_code: str
    branch_name: Optional[str] = None
    sales_rep_email: EmailStr
    sales_rep_name: Optional[str] = None
    is_enabled: bool = True


class BranchEmailMappingResponse(BaseModel):
    """Response model for branch email mapping data.
    
    Returns complete branch email mapping information including timestamps and
    enabled status for tracking and management purposes.
    """

    id: str
    branch_code: str
    branch_name: Optional[str] = None
    sales_rep_email: str
    sales_rep_name: Optional[str] = None
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


class SendReportsRequest(BaseModel):
    """Request model for initiating automated report distribution.
    
    Specifies the report date and optional branch code filters for targeted
    report generation and email sending operations.
    """

    report_date: Optional[date] = None
    branch_codes: Optional[List[str]] = None  # None means all branches

    def __init__(self, **data):
        # Set default date if not provided
        if 'report_date' not in data or data['report_date'] is None:
            data['report_date'] = date.today() - timedelta(days=1)

        super().__init__(**data)


class EmailJobResponse(BaseModel):
    """Response model for email job status and progress tracking.
    
    Provides comprehensive status information for email sending operations,
    including success/failure counts, error messages, and timing data.
    """

    job_id: str
    status: str
    tenant_id: str
    report_date: date
    target_branches: List[str]
    total_emails: int = 0
    emails_sent: int = 0
    emails_failed: int = 0
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    message: Optional[str] = None


