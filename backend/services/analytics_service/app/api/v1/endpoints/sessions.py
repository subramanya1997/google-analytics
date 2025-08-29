"""
Sessions API endpoints
"""
from fastapi import APIRouter, HTTPException, Query, Path
from typing import List, Dict, Any
from loguru import logger

from app.database.supabase_client import AnalyticsSupabaseClient
from app.core.config import settings

router = APIRouter()


@router.get("/{session_id}/history", response_model=List[Dict[str, Any]])
async def get_session_history(
    session_id: str = Path(..., description="Session ID"),
    tenant_id: str = Query(default=settings.DEFAULT_TENANT_ID, description="Tenant ID")
):
    """Get the event history for a specific session."""
    try:
        # Initialize database client
        supabase_config = settings.get_supabase_client_config()
        db_client = AnalyticsSupabaseClient(supabase_config)
        
        # Get session history
        history = db_client.get_session_history(tenant_id, session_id)
        
        logger.info(f"Retrieved {len(history)} events for session {session_id}")
        
        return history
        
    except Exception as e:
        logger.error(f"Error fetching session history for {session_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch session history: {str(e)}")
