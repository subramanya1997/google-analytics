"""
Sessions API endpoints
"""
from fastapi import APIRouter, HTTPException, Query, Path
from typing import List, Dict, Any
from loguru import logger

from fastapi import Depends
from services.analytics_service.app.database.postgres_client import AnalyticsPostgresClient
from services.analytics_service.app.database.dependencies import get_analytics_db_client
from services.analytics_service.app.core.config import settings

router = APIRouter()


@router.get("/{session_id}/history", response_model=List[Dict[str, Any]])
async def get_session_history(
    session_id: str = Path(..., description="Session ID"),
    tenant_id: str = Query(default=settings.DEFAULT_TENANT_ID, description="Tenant ID"),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client)
):
    """Get the event history for a specific session."""
    try:
        # Initialize database client
        # Database client injected via dependency
        
        # Get session history
        history = db_client.get_session_history(tenant_id, session_id)
        
        logger.info(f"Retrieved {len(history)} events for session {session_id}")
        
        return history
        
    except Exception as e:
        logger.error(f"Error fetching session history for {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch session history: {str(e)}")
