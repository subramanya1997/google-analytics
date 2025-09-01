"""
Tasks API endpoints
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from loguru import logger

from fastapi import Depends
from services.analytics_service.app.models import (
    TaskStatusResponse,
    TaskStatusRequest,
    TaskStatusUpdateRequest,
    TaskListRequest,
    PagedResponse
)
from services.analytics_service.app.database.postgres_client import AnalyticsPostgresClient
from services.analytics_service.app.database.dependencies import get_analytics_db_client
from services.analytics_service.app.core.config import settings

router = APIRouter()


@router.get("/status", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str = Query(..., description="Task ID"),
    task_type: str = Query(..., description="Task type"),
    tenant_id: str = Query(default=settings.DEFAULT_TENANT_ID, description="Tenant ID"),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client)
):
    """Get task completion status."""
    try:
        # Database client injected via dependency
        
        # Get task status
        status = db_client.get_task_status(tenant_id, task_id, task_type)
        
        logger.info(f"Retrieved task status for {task_id} ({task_type})")
        
        return TaskStatusResponse(**status)
        
    except Exception as e:
        logger.error(f"Error fetching task status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch task status: {str(e)}")


@router.put("/status", response_model=Dict[str, Any])
async def update_task_status(
    request: TaskStatusUpdateRequest,
    task_id: str = Query(..., description="Task ID"),
    task_type: str = Query(..., description="Task type"),
    tenant_id: str = Query(default=settings.DEFAULT_TENANT_ID, description="Tenant ID"),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client)
):
    """Update task completion status."""
    try:
        # Database client injected via dependency
        
        # Update task status
        result = db_client.update_task_status(
            tenant_id=tenant_id,
            task_id=task_id,
            task_type=task_type,
            completed=request.completed,
            notes=request.notes,
            completed_by=request.completed_by
        )
        
        logger.info(f"Updated task status for {task_id} ({task_type})")
        
        return result
        
    except Exception as e:
        logger.error(f"Error updating task status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update task status: {str(e)}")


# Task-specific endpoints
@router.get("/purchases", response_model=Dict[str, Any])
async def get_purchase_tasks(
    tenant_id: str = Query(default=settings.DEFAULT_TENANT_ID, description="Tenant ID"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE, description="Items per page"),
    query: Optional[str] = Query(default=None, description="Search query"),
    location_id: Optional[str] = Query(default=None, description="Location filter"),
    start_date: Optional[str] = Query(default=None, description="Start date filter"),
    end_date: Optional[str] = Query(default=None, description="End date filter"),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client)
):
    """Get purchase analysis tasks."""
    try:
        # Database client injected via dependency
        
        # Fetch purchase tasks
        result = db_client.get_purchase_tasks(
            tenant_id=tenant_id,
            page=page,
            limit=limit,
            query=query,
            location_id=location_id,
            start_date=start_date,
            end_date=end_date
        )
        
        logger.info(f"Retrieved {len(result['data'])} purchase tasks for tenant {tenant_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching purchase tasks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch purchase tasks: {str(e)}")


@router.get("/cart-abandonment", response_model=Dict[str, Any])
async def get_cart_abandonment_tasks(
    tenant_id: str = Query(default=settings.DEFAULT_TENANT_ID, description="Tenant ID"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE, description="Items per page"),
    query: Optional[str] = Query(default=None, description="Search query"),
    location_id: Optional[str] = Query(default=None, description="Location filter"),
    start_date: Optional[str] = Query(default=None, description="Start date filter"),
    end_date: Optional[str] = Query(default=None, description="End date filter"),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client)
):
    """Get cart abandonment analysis tasks."""
    try:
        # Database client injected via dependency
        
        # Fetch cart abandonment tasks
        result = db_client.get_cart_abandonment_tasks(
            tenant_id=tenant_id,
            page=page,
            limit=limit,
            query=query,
            location_id=location_id,
            start_date=start_date,
            end_date=end_date
        )
        
        logger.info(f"Retrieved {len(result['data'])} cart abandonment tasks for tenant {tenant_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching cart abandonment tasks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch cart abandonment tasks: {str(e)}")


@router.get("/search-analysis", response_model=Dict[str, Any])
async def get_search_analysis_tasks(
    tenant_id: str = Query(default=settings.DEFAULT_TENANT_ID, description="Tenant ID"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE, description="Items per page"),
    query: Optional[str] = Query(default=None, description="Search query"),
    location_id: Optional[str] = Query(default=None, description="Location filter"),
    start_date: Optional[str] = Query(default=None, description="Start date filter"),
    end_date: Optional[str] = Query(default=None, description="End date filter"),
    include_converted: bool = Query(default=False, description="Include sessions that resulted in a purchase"),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client)
):
    """Get search analysis tasks."""
    try:
        # Database client injected via dependency
        
        # Fetch search analysis tasks
        result = db_client.get_search_analysis_tasks(
            tenant_id=tenant_id,
            page=page,
            limit=limit,
            query=query,
            location_id=location_id,
            start_date=start_date,
            end_date=end_date,
            include_converted=include_converted
        )
        
        logger.info(f"Retrieved {len(result['data'])} search analysis tasks for tenant {tenant_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching search analysis tasks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch search analysis tasks: {str(e)}")


@router.get("/performance", response_model=Dict[str, Any])
async def get_performance_tasks(
    tenant_id: str = Query(default=settings.DEFAULT_TENANT_ID, description="Tenant ID"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE, description="Items per page"),
    location_id: Optional[str] = Query(default=None, description="Location filter"),
    start_date: Optional[str] = Query(default=None, description="Start date filter"),
    end_date: Optional[str] = Query(default=None, description="End date filter"),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client)
):
    """Get performance analysis tasks."""
    try:
        # Database client injected via dependency
        
        # Fetch performance tasks
        result = db_client.get_performance_tasks(
            tenant_id=tenant_id,
            page=page,
            limit=limit,
            location_id=location_id,
            start_date=start_date,
            end_date=end_date
        )
        
        logger.info(f"Retrieved performance tasks for tenant {tenant_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching performance tasks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch performance tasks: {str(e)}")


@router.get("/repeat-visits", response_model=Dict[str, Any])
async def get_repeat_visit_tasks(
    tenant_id: str = Query(default=settings.DEFAULT_TENANT_ID, description="Tenant ID"),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(default=settings.DEFAULT_PAGE_SIZE, ge=1, le=settings.MAX_PAGE_SIZE, description="Items per page"),
    query: Optional[str] = Query(default=None, description="Search query on user name, email, or company"),
    location_id: Optional[str] = Query(default=None, description="Location filter"),
    start_date: Optional[str] = Query(default=None, description="Start date filter"),
    end_date: Optional[str] = Query(default=None, description="End date filter"),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client)
):
    """Get repeat visit analysis tasks."""
    try:
        # Database client injected via dependency
        
        # Fetch repeat visit tasks
        result = db_client.get_repeat_visit_tasks(
            tenant_id=tenant_id,
            page=page,
            limit=limit,
            query=query,
            location_id=location_id,
            start_date=start_date,
            end_date=end_date
        )
        
        logger.info(f"Retrieved {len(result['data'])} repeat visit tasks for tenant {tenant_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching repeat visit tasks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch repeat visit tasks: {str(e)}")
