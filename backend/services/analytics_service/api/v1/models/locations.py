"""
Location Response Models for API Endpoints

This module defines Pydantic models for location/branch data returned by
the analytics service API endpoints.

Models:
    - LocationResponse: Response model for location data

Example:
    ```python
    from services.analytics_service.api.v1.models.locations import LocationResponse
    
    location = LocationResponse(
        locationId="loc-001",
        locationName="Downtown Branch",
        city="San Francisco",
        state="CA"
    )
    ```

See Also:
    - services.analytics_service.api.v1.endpoints.locations: Location endpoints
"""

from pydantic import BaseModel


class LocationResponse(BaseModel):
    """
    Response model for location/branch data.

    This model represents a location (branch/store) that has analytics activity
    within the tenant's data. Used for populating location filters and selection
    components in the dashboard.

    Attributes:
        locationId: Unique identifier for the location (required).
            Used as a key for filtering and referencing locations.
        locationName: Display name of the location (required).
            Used for UI display in dropdowns and filters.
        city: City name where the location is located (optional).
            Used for geographic filtering and display.
        state: State/province where the location is located (optional).
            Used for geographic filtering and display.

    Example:
        ```python
        {
            "locationId": "loc-001",
            "locationName": "Downtown Branch",
            "city": "San Francisco",
            "state": "CA"
        }
        ```

    Note:
        Only locations with actual analytics activity (page views) are returned.
        Inactive locations without data are excluded.
    """

    locationId: str
    locationName: str
    city: str | None = None
    state: str | None = None
