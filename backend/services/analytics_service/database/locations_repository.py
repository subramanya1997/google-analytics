"""
Locations Repository for Analytics Service

This module provides database operations for location/branch queries in the
Analytics Service. It handles retrieval of active locations for dashboard
filters and other UI components.

Example:
    ```python
    repo = LocationsRepository()
    locations = await repo.get_locations("tenant-123")
    ```

See Also:
    - services.analytics_service.database.base: Shared constants
    - common.database.get_async_db_session: Database session management
"""

from typing import Any

from loguru import logger
from sqlalchemy import text

from common.database import get_async_db_session

from .base import SERVICE_NAME


class LocationsRepository:
    """
    Repository for location/branch database operations.

    This class provides methods for querying location data used in the
    analytics dashboard. It uses PostgreSQL functions for optimized queries.

    Thread Safety:
        This repository is thread-safe and can be used concurrently across
        multiple async tasks. Each method creates its own database session.

    Example:
        ```python
        repo = LocationsRepository()
        locations = await repo.get_locations("tenant-123")
        # [{"locationId": "loc-001", "locationName": "Downtown", ...}, ...]
        ```
    """

    async def get_locations(self, tenant_id: str) -> list[dict[str, Any]]:
        """
        Retrieve all active locations (branches) for a tenant.

        Returns locations that have analytics activity (page views) within the
        tenant's data. This is used to populate location filters in the dashboard
        and other UI components.

        Args:
            tenant_id: Unique tenant identifier for data isolation.

        Returns:
            list[dict[str, Any]]: List of location dictionaries, each containing:
                - locationId (str): Unique location identifier
                - locationName (str): Display name of the location
                - city (str | None): City name if available
                - state (str | None): State/province name if available

            Returns empty list if no locations found or on error.

        Example:
            ```python
            locations = await repo.get_locations("tenant-123")
            # [
            #     {
            #         "locationId": "loc-001",
            #         "locationName": "Downtown Branch",
            #         "city": "San Francisco",
            #         "state": "CA"
            #     },
            #     ...
            # ]
            ```

        Note:
            Uses the `get_locations()` PostgreSQL function which optimizes
            the query by filtering only locations with activity.
        """
        try:
            async with get_async_db_session(
                SERVICE_NAME, tenant_id=tenant_id
            ) as session:
                # Get all active locations using the optimized function
                result = await session.execute(
                    text(
                        """
                    SELECT * FROM get_locations(:tenant_id)
                """
                    ),
                    {"tenant_id": tenant_id},
                )
                locations_data = result.fetchall()

                locations = []
                for location in locations_data:
                    locations.append(
                        {
                            "locationId": location.location_id,
                            "locationName": location.location_name,
                            "city": location.city,
                            "state": location.state,
                        }
                    )

                return locations

        except Exception as e:
            logger.error(f"Error fetching locations: {e}")
            return []
