"""
History API Endpoints for Event Timeline Queries

This module provides RESTful API endpoints for retrieving chronological event
histories for users and sessions. These endpoints enable detailed analysis of
user journeys and session flows for debugging, customer support, and behavioral
analysis.

Endpoint Types:
    - User History: Complete event timeline across all sessions for a user
    - Session History: Event timeline for a specific session

Use Cases:
    - Customer support: Understanding what a user experienced
    - Debugging: Tracing issues in user flows
    - Analytics: Analyzing user behavior patterns
    - Audit: Compliance and audit trail requirements

Multi-Tenancy:
    All endpoints require X-Tenant-Id header for proper data isolation.

Example:
    ```python
    # Get user history
    GET /api/v1/history/user?user_id=user-123
    Headers:
        X-Tenant-Id: tenant-123
    
    # Get session history
    GET /api/v1/history/session?session_id=session-abc
    Headers:
        X-Tenant-Id: tenant-123
    ```

See Also:
    - services.analytics_service.database.history_repository: HistoryRepository
    - backend/database/functions/get_user_history.sql: SQL function
    - backend/database/functions/get_session_history.sql: SQL function
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from common.exceptions import handle_database_error
from services.analytics_service.api.dependencies import (
    get_history_repository,
    get_tenant_id,
)
from services.analytics_service.database import HistoryRepository

router = APIRouter()


# Backward compatibility endpoints
@router.get("/history/user", response_model=list[dict[str, Any]])
async def get_user_history_compat(
    user_id: str = Query(..., description="User ID"),
    tenant_id: str = Depends(get_tenant_id),
    repo: HistoryRepository = Depends(get_history_repository),
) -> list[dict[str, Any]]:
    """
    Retrieve the complete event history for a specific user across all sessions.

    Returns a chronological timeline of all events associated with a user
    across all their sessions. This provides a comprehensive view of a user's
    entire journey and engagement history with the platform.

    Args:
        user_id: Unique user identifier to retrieve history for (required).
        tenant_id: Tenant identifier extracted from X-Tenant-Id header.
        repo: HistoryRepository dependency injection.

    Returns:
        list[dict[str, Any]]: Chronologically ordered list of event objects
        across all sessions, each containing:
            - event_type (str): Type of event (page_view, purchase, etc.)
            - timestamp (datetime): When the event occurred
            - session_id (str): Session identifier for the event
            - event_data (dict): Event-specific data
            - location_id (str): Location where the event occurred

        Returns empty list if user not found or on error.

    Raises:
        HTTPException: 400 if tenant_id is invalid or user_id is missing.
        HTTPException: 500 if database query fails.

    Example:
        ```bash
        GET /api/v1/history/user?user_id=user-xyz-789
        Headers:
            X-Tenant-Id: tenant-123
        ```

    Note:
        This can return large result sets for highly active users. Consider
        implementing pagination or date range filtering in future versions.
    """
    try:
        return await repo.get_user_history(tenant_id, user_id)
    except HTTPException:
        raise
    except Exception as e:
        msg = "fetching user history"
        raise handle_database_error(msg, e)


@router.get("/history/session", response_model=list[dict[str, Any]])
async def get_session_history_compat(
    session_id: str = Query(..., description="Session ID"),
    tenant_id: str = Depends(get_tenant_id),
    repo: HistoryRepository = Depends(get_history_repository),
) -> list[dict[str, Any]]:
    """
    Retrieve the complete event history for a specific session.

    Returns a chronological timeline of all events (page views, searches,
    cart additions, purchases, etc.) that occurred during a single user
    session. This is useful for debugging, customer support, and understanding
    user behavior patterns.

    Args:
        session_id: Unique session identifier to retrieve history for (required).
        tenant_id: Tenant identifier extracted from X-Tenant-Id header.
        repo: HistoryRepository dependency injection.

    Returns:
        list[dict[str, Any]]: Chronologically ordered list of event objects,
        each containing:
            - event_type (str): Type of event (page_view, purchase, etc.)
            - timestamp (datetime): When the event occurred
            - event_data (dict): Event-specific data (page URL, product info, etc.)
            - user_id (str): User identifier associated with the session

        Returns empty list if session not found or on error.

    Raises:
        HTTPException: 400 if tenant_id is invalid or session_id is missing.
        HTTPException: 500 if database query fails.

    Example:
        ```bash
        GET /api/v1/history/session?session_id=session-abc-123
        Headers:
            X-Tenant-Id: tenant-123
        ```

    Note:
        Events are returned in chronological order (oldest to newest) to
        facilitate understanding of the user's session flow.
    """
    try:
        return await repo.get_session_history(tenant_id, session_id)
    except HTTPException:
        raise
    except Exception as e:
        msg = "fetching session history"
        raise handle_database_error(msg, e)
