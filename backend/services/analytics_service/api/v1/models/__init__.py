"""
Response models for analytics service API endpoints.
"""

from .email import (
    BranchEmailMappingRequest,
    BranchEmailMappingResponse,
    EmailJobResponse,
    SendReportsRequest,
)
from .locations import LocationResponse

__all__ = [
    "BranchEmailMappingRequest",
    "BranchEmailMappingResponse",
    "EmailJobResponse",
    "LocationResponse",
    "SendReportsRequest",
]
