"""
Location Response Models.

This module provides Pydantic models for location-based data in the analytics service,
including branch information, location metadata, and geographic details.
"""

from typing import Optional

from pydantic import BaseModel


class LocationResponse(BaseModel):
    """Response model for active location data with analytics activity.
    
    Contains location identification, name, and geographic information for
    branches that have recorded analytics activity within the system.
    """

    locationId: str
    locationName: str
    city: Optional[str] = None
    state: Optional[str] = None
