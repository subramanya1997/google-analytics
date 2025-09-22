"""
Pydantic Models for Analytics Service API.

This module provides response and request models for the analytics service API endpoints,
including location data, email configuration models, and various response structures.
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
