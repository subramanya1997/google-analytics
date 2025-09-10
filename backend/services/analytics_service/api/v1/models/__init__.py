"""
Response models for analytics service API endpoints.
"""

from .locations import LocationResponse
from .email import (
    BranchEmailMappingRequest,
    BranchEmailMappingResponse,
    SendReportsRequest,
    EmailJobResponse,
)

__all__ = [
    "LocationResponse",
    "BranchEmailMappingRequest",
    "BranchEmailMappingResponse", 
    "SendReportsRequest",
    "EmailJobResponse",
]
