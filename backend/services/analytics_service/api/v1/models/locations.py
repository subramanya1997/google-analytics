"""
Location response model
"""

from typing import Optional

from pydantic import BaseModel


class LocationResponse(BaseModel):
    """Response model for location data."""

    locationId: str
    locationName: str
    city: Optional[str] = None
    state: Optional[str] = None
