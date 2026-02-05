"""
Response models for analytics service API endpoints.

Note:
    Email-related models (BranchEmailMappingRequest, BranchEmailMappingResponse,
    EmailJobResponse, SendReportsRequest) have been moved to the Data Service.
    See: services.data_service.api.v1.models.email
"""

from .locations import LocationResponse

__all__ = [
    "LocationResponse",
]
