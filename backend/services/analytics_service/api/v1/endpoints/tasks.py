"""
Tasks API endpoints
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from services.analytics_service.api.dependencies import get_tenant_id
from services.analytics_service.database.dependencies import get_analytics_db_client
from services.analytics_service.database.postgres_client import AnalyticsPostgresClient

router = APIRouter()

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 1000

# Task-specific endpoints
@router.get("/purchases", response_model=Dict[str, Any])
async def get_purchase_tasks(
    tenant_id: str = Depends(get_tenant_id),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(
        default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Items per page"
    ),
    query: Optional[str] = Query(default=None, description="Search query"),
    location_id: Optional[str] = Query(default=None, description="Location filter"),
    start_date: Optional[str] = Query(default=None, description="Start date filter"),
    end_date: Optional[str] = Query(default=None, description="End date filter"),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client),
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
            end_date=end_date,
        )

        logger.info(
            f"Retrieved {len(result['data'])} purchase tasks for tenant {tenant_id}"
        )

        return result

    except Exception as e:
        logger.error(f"Error fetching purchase tasks: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch purchase tasks: {str(e)}"
        )


@router.get("/cart-abandonment", response_model=Dict[str, Any])
async def get_cart_abandonment_tasks(
    tenant_id: str = Depends(get_tenant_id),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(
        default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Items per page"
    ),
    query: Optional[str] = Query(default=None, description="Search query"),
    location_id: Optional[str] = Query(default=None, description="Location filter"),
    start_date: Optional[str] = Query(default=None, description="Start date filter"),
    end_date: Optional[str] = Query(default=None, description="End date filter"),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client),
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
            end_date=end_date,
        )

        logger.info(
            f"Retrieved {len(result['data'])} cart abandonment tasks for tenant {tenant_id}"
        )

        return result

    except Exception as e:
        logger.error(f"Error fetching cart abandonment tasks: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch cart abandonment tasks: {str(e)}"
        )


@router.get("/search-analysis", response_model=Dict[str, Any])
async def get_search_analysis_tasks(
    tenant_id: str = Depends(get_tenant_id),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(
        default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Items per page"
    ),
    query: Optional[str] = Query(default=None, description="Search query"),
    location_id: Optional[str] = Query(default=None, description="Location filter"),
    start_date: Optional[str] = Query(default=None, description="Start date filter"),
    end_date: Optional[str] = Query(default=None, description="End date filter"),
    include_converted: bool = Query(
        default=False, description="Include sessions that resulted in a purchase"
    ),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client),
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
            include_converted=include_converted,
        )

        logger.info(
            f"Retrieved {len(result['data'])} search analysis tasks for tenant {tenant_id}"
        )

        return result

    except Exception as e:
        logger.error(f"Error fetching search analysis tasks: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch search analysis tasks: {str(e)}"
        )


@router.get("/performance", response_model=Dict[str, Any])
async def get_performance_tasks(
    tenant_id: str = Depends(get_tenant_id),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(
        default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Items per page"
    ),
    location_id: Optional[str] = Query(default=None, description="Location filter"),
    start_date: Optional[str] = Query(default=None, description="Start date filter"),
    end_date: Optional[str] = Query(default=None, description="End date filter"),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client),
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
            end_date=end_date,
        )

        logger.info(f"Retrieved performance tasks for tenant {tenant_id}")

        return result

    except Exception as e:
        logger.error(f"Error fetching performance tasks: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch performance tasks: {str(e)}"
        )


@router.get("/repeat-visits", response_model=Dict[str, Any])
async def get_repeat_visit_tasks(
    tenant_id: str = Depends(get_tenant_id),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(
        default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Items per page"
    ),
    query: Optional[str] = Query(
        default=None, description="Search query on user name, email, or company"
    ),
    location_id: Optional[str] = Query(default=None, description="Location filter"),
    start_date: Optional[str] = Query(default=None, description="Start date filter"),
    end_date: Optional[str] = Query(default=None, description="End date filter"),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client),
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
            end_date=end_date,
        )

        logger.info(
            f"Retrieved {len(result['data'])} repeat visit tasks for tenant {tenant_id}"
        )

        return result

    except Exception as e:
        logger.error(f"Error fetching repeat visit tasks: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch repeat visit tasks: {str(e)}"
        )
