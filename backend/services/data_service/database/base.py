"""
Base Utilities for Data Service Database Layer

This module provides shared utilities and constants used across all repository
implementations in the Data Service. It includes tenant ID normalization and
event table mappings that are essential for multi-tenant data isolation and
dynamic table access.

Key Components:
    - ensure_uuid_string: Normalizes tenant IDs to valid UUID format
    - EVENT_TABLES: Mapping of event type names to SQLAlchemy table objects

These utilities are used by both the IngestionRepository and EmailRepository
to ensure consistent database operations across all service endpoints.

See Also:
    - services.data_service.database.ingestion_repository: Ingestion operations
    - services.data_service.database.email_repository: Email operations
    - common.database: Shared database session management
"""

from __future__ import annotations

import hashlib
from typing import Any
import uuid

from common.models import (
    AddToCart,
    NoSearchResults,
    PageView,
    Purchase,
    ViewItem,
    ViewSearchResults,
)


def ensure_uuid_string(tenant_id: str) -> str:
    """
    Convert tenant_id to a consistent UUID string format.

    This utility function ensures that tenant IDs are always in valid UUID format
    for database operations. If the input is already a valid UUID, it's returned
    as-is. If not, a deterministic UUID is generated using MD5 hashing to ensure
    consistent mapping for the same input string.

    Args:
        tenant_id: Tenant identifier (may be UUID string or other format)

    Returns:
        str: Valid UUID string representation of the tenant ID

    Implementation Details:
        - Valid UUIDs are validated and returned unchanged
        - Invalid UUIDs are hashed using MD5 and converted to UUID format
        - The same input always produces the same UUID (deterministic)

    Example:
        ```python
        # Valid UUID
        ensure_uuid_string("550e8400-e29b-41d4-a716-446655440000")
        # Returns: "550e8400-e29b-41d4-a716-446655440000"

        # Invalid UUID (converted deterministically)
        ensure_uuid_string("tenant-123")
        # Returns: "a1b2c3d4-e5f6-7890-abcd-ef1234567890" (deterministic)
        ```

    Note:
        This function is critical for multi-tenant data isolation. All tenant IDs
        must be normalized before database operations to ensure proper schema routing.
    """
    try:
        # Validate and convert to UUID string
        uuid_obj = uuid.UUID(tenant_id)
        return str(uuid_obj)
    except ValueError:
        # If not a valid UUID, generate one from the string using MD5 hash
        tenant_uuid = uuid.UUID(bytes=hashlib.md5(tenant_id.encode()).digest()[:16])
        return str(tenant_uuid)


EVENT_TABLES: dict[str, Any] = {
    "purchase": Purchase.__table__,
    "add_to_cart": AddToCart.__table__,
    "page_view": PageView.__table__,
    "view_search_results": ViewSearchResults.__table__,
    "no_search_results": NoSearchResults.__table__,
    "view_item": ViewItem.__table__,
}
"""
Mapping of event type names to their corresponding SQLAlchemy table objects.

This dictionary is used for dynamic table access when processing different
event types during data ingestion. The keys match the event type identifiers
used in the ingestion pipeline.

Supported Event Types:
    - purchase: Purchase transaction events
    - add_to_cart: Add to cart events
    - page_view: Page view events
    - view_search_results: Search result view events
    - no_search_results: No search results events
    - view_item: Product view events
"""
