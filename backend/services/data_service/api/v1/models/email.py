"""
Email-Related Pydantic Models for Request/Response Validation

This module defines Pydantic models for email management API endpoints.
These models provide type safety, automatic validation, and OpenAPI schema
generation for email-related operations.

Models:
    - BranchEmailMappingRequest: Request model for creating/updating mappings
    - BranchEmailMappingResponse: Response model for mapping data
    - SendReportsRequest: Request model for triggering report distribution
    - EmailJobResponse: Response model for email job status

Validation:
    All models include automatic validation:
    - Email addresses are validated using EmailStr
    - Required fields are enforced
    - Default values are provided where appropriate

Example:
    ```python
    from services.data_service.api.v1.models.email import (
        BranchEmailMappingRequest,
        SendReportsRequest
    )
    
    # Create mapping request
    mapping = BranchEmailMappingRequest(
        branch_code="BRANCH-001",
        sales_rep_email="rep@company.com",
        sales_rep_name="John Doe"
    )
    
    # Send reports request
    request = SendReportsRequest(
        report_date=date(2024, 1, 15),
        branch_codes=["BRANCH-001"]
    )
    ```

See Also:
    - pydantic.BaseModel: Base class for all models
    - fastapi: Uses these models for request/response validation
"""

from datetime import date, datetime, timedelta
from typing import Any

from pydantic import BaseModel, EmailStr


class BranchEmailMappingRequest(BaseModel):
    """
    Request model for creating or updating branch-to-email mappings.

    This model represents the data required to associate a branch/location
    with a sales representative's email address for automated report distribution.

    Attributes:
        branch_code: Unique branch/location code identifier (required).
            Used to match analytics data to the correct branch.
        branch_name: Display name of the branch (optional).
            Used for UI display purposes.
        sales_rep_email: Email address of the sales representative (required).
            Reports will be sent to this address. Validated as a proper email format.
        sales_rep_name: Name of the sales representative (optional).
            Used for personalization in email templates.
        is_enabled: Whether this mapping is active (default: True).
            Disabled mappings will not receive automated reports.

    Example:
        ```python
        mapping = BranchEmailMappingRequest(
            branch_code="BRANCH-001",
            branch_name="Downtown Branch",
            sales_rep_email="john.doe@company.com",
            sales_rep_name="John Doe",
            is_enabled=True
        )
        ```

    Validation:
        - branch_code: Must be non-empty string
        - sales_rep_email: Must be valid email format (validated by EmailStr)
        - is_enabled: Boolean, defaults to True
    """

    branch_code: str
    branch_name: str | None = None
    sales_rep_email: EmailStr
    sales_rep_name: str | None = None
    is_enabled: bool = True


class BranchEmailMappingResponse(BaseModel):
    """
    Response model for branch-to-email mapping data.

    This model represents a complete branch email mapping as returned from
    the database, including metadata like creation and update timestamps.

    Attributes:
        id: Unique database identifier for this mapping (UUID string).
        branch_code: Branch/location code identifier.
        branch_name: Display name of the branch, if available.
        sales_rep_email: Email address of the sales representative.
        sales_rep_name: Name of the sales representative, if available.
        is_enabled: Whether this mapping is currently active.
        created_at: Timestamp when the mapping was created.
        updated_at: Timestamp when the mapping was last updated.

    Example:
        ```python
        {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "branch_code": "BRANCH-001",
            "branch_name": "Downtown Branch",
            "sales_rep_email": "john.doe@company.com",
            "sales_rep_name": "John Doe",
            "is_enabled": True,
            "created_at": "2024-01-15T10:30:00Z",
            "updated_at": "2024-01-15T10:30:00Z"
        }
        ```
    """

    id: str
    branch_code: str
    branch_name: str | None = None
    sales_rep_email: str
    sales_rep_name: str | None = None
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


class SendReportsRequest(BaseModel):
    """
    Request model for initiating automated report distribution.

    This model specifies the parameters for generating and distributing
    analytics reports via email to configured sales representatives.

    Attributes:
        report_date: Date for the report being generated (optional).
            If not provided, defaults to yesterday's date (most recent complete day).
            Format: YYYY-MM-DD.
        branch_codes: List of branch codes to target (optional).
            If None or empty list, reports are generated for all branches.
            If specified, only reports for these branches are generated.

    Behavior:
        The __init__ method automatically sets report_date to yesterday if
        not provided, ensuring reports are generated for the most recent
        complete day by default.

    Example:
        ```python
        # Generate reports for yesterday (default)
        request = SendReportsRequest()
        
        # Generate reports for specific date
        request = SendReportsRequest(report_date=date(2024, 1, 15))
        
        # Generate reports for specific branches only
        request = SendReportsRequest(
            report_date=date(2024, 1, 15),
            branch_codes=["BRANCH-001", "BRANCH-002"]
        )
        
        # Generate reports for all branches on specific date
        request = SendReportsRequest(
            report_date=date(2024, 1, 15),
            branch_codes=None
        )
        ```

    Note:
        Reports are generated asynchronously. The API returns immediately
        with a job ID that can be used to track progress.
    """

    report_date: date | None = None
    branch_codes: list[str] | None = None  # None means all branches

    def __init__(self, **data: Any) -> None:
        """
        Initialize SendReportsRequest with default report_date if not provided.

        Automatically sets report_date to yesterday's date if not specified,
        ensuring reports are generated for the most recent complete day by default.
        """
        # Set default date if not provided
        if "report_date" not in data or data["report_date"] is None:
            data["report_date"] = date.today() - timedelta(days=1)

        super().__init__(**data)


class EmailJobResponse(BaseModel):
    """
    Response model for email job status and progress information.

    This model represents the current state of an email sending job, including
    progress metrics and timestamps for tracking job lifecycle.

    Attributes:
        job_id: Unique identifier for this email job.
        status: Current job status. Common values:
            - "queued": Job created but not yet started
            - "processing": Job is currently being processed
            - "completed": Job finished successfully
            - "failed": Job failed with errors
        tenant_id: Tenant identifier for this job.
        report_date: Date for the report being generated.
        target_branches: List of branch codes targeted by this job.
            Empty list means all branches.
        total_emails: Total number of emails to be sent (updated during processing).
        emails_sent: Number of emails successfully sent.
        emails_failed: Number of emails that failed to send.
        error_message: Error message if job failed, None otherwise.
        created_at: Timestamp when job was created.
        started_at: Timestamp when job processing started, None if not started.
        completed_at: Timestamp when job completed, None if still processing.
        message: Optional status message providing additional context.

    Example:
        ```python
        {
            "job_id": "email_job_abc123",
            "status": "processing",
            "tenant_id": "tenant-123",
            "report_date": "2024-01-15",
            "target_branches": ["BRANCH-001", "BRANCH-002"],
            "total_emails": 10,
            "emails_sent": 7,
            "emails_failed": 0,
            "error_message": None,
            "created_at": "2024-01-16T08:00:00Z",
            "started_at": "2024-01-16T08:00:05Z",
            "completed_at": None,
            "message": "Email sending job created successfully"
        }
        ```

    Note:
        Progress fields (total_emails, emails_sent, emails_failed) are
        updated in real-time as the job processes. Monitor these fields
        to track job progress.
    """

    job_id: str
    status: str
    tenant_id: str
    report_date: date
    target_branches: list[str]
    total_emails: int = 0
    emails_sent: int = 0
    emails_failed: int = 0
    error_message: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    message: str | None = None
