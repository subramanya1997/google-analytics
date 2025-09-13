"""
History API endpoints for users and sessions
"""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from services.analytics_service.api.dependencies import get_tenant_id
from services.analytics_service.database.dependencies import get_analytics_db_client
from services.analytics_service.database.postgres_client import AnalyticsPostgresClient

router = APIRouter()


# Backward compatibility endpoints
@router.get("/history/user", response_model=List[Dict[str, Any]])
async def get_user_history_compat(
    user_id: str = Query(..., description="User ID"),
    tenant_id: str = Depends(get_tenant_id),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client),
):
    """Get the event history for a specific user."""
    try:
        history = await db_client.get_user_history(tenant_id, user_id)
        return history
    except Exception as e:
        logger.error(f"Error fetching user history for {user_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch user history: {str(e)}"
        )


@router.get("/history/session", response_model=List[Dict[str, Any]])
async def get_session_history_compat(
    session_id: str = Query(..., description="Session ID"),
    tenant_id: str = Depends(get_tenant_id),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client),
):
    """Get the event history for a specific session."""
    try:
        history = await db_client.get_session_history(tenant_id, session_id)
        return history
    except Exception as e:
        logger.error(f"Error fetching session history for {session_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch session history: {str(e)}"
        )
