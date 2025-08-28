"""
Users API endpoints
"""
from fastapi import APIRouter, HTTPException, Query, Path
from typing import List, Dict, Any
from loguru import logger

from app.database.supabase_client import AnalyticsSupabaseClient
from app.core.config import settings

router = APIRouter()


@router.get("/{user_id}/history", response_model=List[Dict[str, Any]])
async def get_user_history(
    user_id: str = Path(..., description="User ID"),
    tenant_id: str = Query(default=settings.DEFAULT_TENANT_ID, description="Tenant ID")
):
    """Get the event history for a specific user."""
    try:
        # Initialize database client
        supabase_config = settings.get_supabase_client_config()
        db_client = AnalyticsSupabaseClient(supabase_config)
        
        # Get user history
        history = db_client.get_user_history(tenant_id, user_id)
        
        logger.info(f"Retrieved {len(history)} events for user {user_id}")
        
        return history
        
    except Exception as e:
        logger.error(f"Error fetching user history for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch user history: {str(e)}")
