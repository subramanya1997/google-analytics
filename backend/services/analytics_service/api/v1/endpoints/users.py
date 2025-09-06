"""
Users API endpoints
"""
from fastapi import APIRouter, HTTPException, Path
from typing import List, Dict, Any
from loguru import logger

from fastapi import Depends
from services.analytics_service.database.postgres_client import AnalyticsPostgresClient
from services.analytics_service.database.dependencies import get_analytics_db_client
from services.analytics_service.api.dependencies import get_tenant_id

router = APIRouter()


@router.get("/{user_id}/history", response_model=List[Dict[str, Any]])
async def get_user_history(
    user_id: str = Path(..., description="User ID"),
    tenant_id: str = Depends(get_tenant_id),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client)
):
    """Get the event history for a specific user."""
    try:
        # Initialize database client
        # Database client injected via dependency
        
        # Get user history
        history = db_client.get_user_history(tenant_id, user_id)
        
        logger.info(f"Retrieved {len(history)} events for user {user_id}")
        
        return history
        
    except Exception as e:
        logger.error(f"Error fetching user history for {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch user history: {str(e)}")
