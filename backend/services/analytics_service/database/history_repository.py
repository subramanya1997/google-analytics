"""
History Repository for Analytics Service

This module provides database operations for session and user history queries
in the Analytics Service. It handles retrieval of event timelines for individual
sessions and users, enabling debugging, customer support, and behavior analysis.

Example:
    ```python
    repo = HistoryRepository()
    session_events = await repo.get_session_history("tenant-123", "session-abc")
    user_events = await repo.get_user_history("tenant-123", "user-xyz")
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


class HistoryRepository:
    """
    Repository for session and user history database operations.

    This class provides methods for querying event history, enabling detailed
    analysis of user journeys and session activities. Events are returned in
    chronological order for timeline visualization.

    Thread Safety:
        This repository is thread-safe and can be used concurrently across
        multiple async tasks. Each method creates its own database session.

    Example:
        ```python
        repo = HistoryRepository()
        events = await repo.get_session_history("tenant-123", "session-abc")
        # [{"event_type": "page_view", "timestamp": "...", ...}, ...]
        ```
    """

    async def get_session_history(
        self, tenant_id: str, session_id: str
    ) -> list[dict[str, Any]]:
        """
        Retrieve the complete event history for a specific session.

        Returns a chronological timeline of all events (page views, searches,
        cart additions, purchases, etc.) that occurred during a single user
        session. This is useful for debugging, customer support, and understanding
        user behavior patterns.

        Args:
            tenant_id: Unique tenant identifier for data isolation.
            session_id: Unique session identifier to retrieve history for.

        Returns:
            list[dict[str, Any]]: Chronologically ordered list of event objects,
            each containing:
                - event_type (str): Type of event (page_view, purchase, etc.)
                - timestamp (datetime): When the event occurred
                - event_data (dict): Event-specific data (page URL, product info, etc.)
                - user_id (str): User identifier associated with the session

            Returns empty list if session not found or on error.

        Example:
            ```python
            events = await repo.get_session_history(
                tenant_id="tenant-123", session_id="session-abc-123"
            )
            # [
            #     {
            #         "event_type": "page_view",
            #         "timestamp": "2024-01-15T10:30:00Z",
            #         "page_url": "/products/widget",
            #         ...
            #     },
            #     {
            #         "event_type": "add_to_cart",
            #         "timestamp": "2024-01-15T10:35:00Z",
            #         "product_id": "prod-123",
            #         ...
            #     },
            #     ...
            # ]
            ```

        Note:
            Uses the `get_session_history()` PostgreSQL function which
            efficiently queries multiple event tables and orders by timestamp.
        """
        try:
            async with get_async_db_session(
                SERVICE_NAME, tenant_id=tenant_id
            ) as session:
                result = await session.execute(
                    text(
                        """
                    SELECT get_session_history(:p_tenant_id, :p_session_id)
                """
                    ),
                    {"p_tenant_id": tenant_id, "p_session_id": session_id},
                )
                history = result.scalar()

                return history or []

        except Exception as e:
            logger.error(
                f"Error fetching session history for session {session_id}: {e}"
            )
            raise

    async def get_user_history(
        self, tenant_id: str, user_id: str
    ) -> list[dict[str, Any]]:
        """
        Retrieve the complete event history for a specific user across all sessions.

        Returns a chronological timeline of all events associated with a user
        across all their sessions. This provides a comprehensive view of a user's
        entire journey and engagement history with the platform.

        Args:
            tenant_id: Unique tenant identifier for data isolation.
            user_id: Unique user identifier to retrieve history for.

        Returns:
            list[dict[str, Any]]: Chronologically ordered list of event objects
            across all sessions, each containing:
                - event_type (str): Type of event (page_view, purchase, etc.)
                - timestamp (datetime): When the event occurred
                - session_id (str): Session identifier for the event
                - event_data (dict): Event-specific data
                - location_id (str): Location where the event occurred

            Returns empty list if user not found or on error.

        Example:
            ```python
            events = await repo.get_user_history(
                tenant_id="tenant-123", user_id="user-xyz-789"
            )
            # Returns all events across all sessions for this user
            ```

        Note:
            Uses the `get_user_history()` PostgreSQL function which queries
            multiple event tables and orders by timestamp across all sessions.
            This can return large result sets for highly active users.
        """
        try:
            async with get_async_db_session(
                SERVICE_NAME, tenant_id=tenant_id
            ) as session:
                result = await session.execute(
                    text(
                        """
                    SELECT get_user_history(:p_tenant_id, :p_user_id)
                """
                    ),
                    {"p_tenant_id": tenant_id, "p_user_id": user_id},
                )
                history = result.scalar()

                return history or []

        except Exception as e:
            logger.error(f"Error fetching user history for user {user_id}: {e}")
            raise
