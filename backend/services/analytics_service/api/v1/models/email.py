"""
Email-related Pydantic models
"""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, validator


class BranchEmailMappingRequest(BaseModel):
    """Request model for branch email mapping."""

    branch_code: str
    branch_name: Optional[str] = None
    sales_rep_email: EmailStr
    sales_rep_name: Optional[str] = None
    is_enabled: bool = True


class BranchEmailMappingResponse(BaseModel):
    """Response model for branch email mapping."""

    id: str
    branch_code: str
    branch_name: Optional[str] = None
    sales_rep_email: str
    sales_rep_name: Optional[str] = None
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


class SendReportsRequest(BaseModel):
    """Request model for sending reports."""

    report_date: date
    branch_codes: Optional[List[str]] = None  # None means all branches


class EmailJobResponse(BaseModel):
    """Response model for email job."""

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


