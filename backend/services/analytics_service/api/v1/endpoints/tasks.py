"""
Tasks API Endpoints for Analytics Task Management

This module provides RESTful API endpoints for retrieving and managing various
types of analytics tasks. Tasks represent actionable insights derived from
analytics data, such as purchase follow-ups, cart abandonment recovery,
search optimization opportunities, and performance metrics.

Task Types:
    - Purchase Tasks: Customers who made purchases (follow-up opportunities)
    - Cart Abandonment: Sessions with abandoned carts (recovery opportunities)
    - Search Analysis: Search behavior insights (optimization opportunities)
    - Repeat Visits: Users with multiple visits (engagement opportunities)
    - Performance: Branch-level performance metrics (comparison insights)

Pagination:
    All task endpoints support pagination with configurable page size limits.
    Default page size is defined in settings, with a maximum enforced limit.

Filtering:
    Tasks can be filtered by:
    - Date range (start_date, end_date)
    - Location (location_id)
    - Search query (query parameter for text search)

Multi-Tenancy:
    All endpoints require X-Tenant-Id header for proper data isolation.

Example:
    ```python
    # Get purchase tasks
    GET /api/v1/tasks/purchases?page=1&limit=50&location_id=loc-001
    Headers:
        X-Tenant-Id: tenant-123
    ```

See Also:
    - services.analytics_service.database.postgres_client: Database client methods
    - backend/database/functions/: PostgreSQL task functions
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from common.config import get_settings
from common.exceptions import handle_database_error
from services.analytics_service.api.dependencies import get_tenant_id
from services.analytics_service.database.dependencies import get_analytics_db_client
from services.analytics_service.database.postgres_client import AnalyticsPostgresClient

router = APIRouter()

# Get settings for pagination constants
_settings = get_settings("analytics-service")


# Task-specific endpoints
@router.get("/purchases", response_model=dict[str, Any])
async def get_purchase_tasks(
    tenant_id: str = Depends(get_tenant_id),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(
        default=_settings.DEFAULT_PAGE_SIZE,
        ge=1,
        le=_settings.MAX_PAGE_SIZE,
        description="Items per page",
    ),
    query: str | None = Query(default=None, description="Search query"),
    location_id: str | None = Query(default=None, description="Location filter"),
    start_date: str | None = Query(default=None, description="Start date filter"),
    end_date: str | None = Query(default=None, description="End date filter"),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client),
) -> dict[str, Any]:
    """
    Retrieve paginated purchase analysis tasks with optional filtering.

    Purchase tasks identify customers who have made purchases and may benefit
    from follow-up engagement, cross-selling, or loyalty program enrollment.

    Args:
        tenant_id: Tenant identifier extracted from X-Tenant-Id header.
        page: Page number (1-indexed) for pagination. Must be >= 1.
        limit: Maximum items per page. Must be between 1 and MAX_PAGE_SIZE.
        query: Optional search query to filter by customer name, email, or company.
            Performs case-insensitive partial matching.
        location_id: Optional location filter to restrict results to a specific branch.
        start_date: Optional start date filter (YYYY-MM-DD format).
        end_date: Optional end date filter (YYYY-MM-DD format).
        db_client: Database client dependency injection.

    Returns:
        dict[str, Any]: Paginated response containing:
            - data (list[dict]): List of purchase task objects with customer
              information, purchase details, and engagement metrics
            - total (int): Total number of matching tasks across all pages
            - page (int): Current page number
            - limit (int): Items per page
            - has_more (bool): Whether more pages are available

    Raises:
        HTTPException: 400 if tenant_id is invalid or pagination parameters invalid.
        HTTPException: 500 if database query fails.

    Example:
        ```bash
        GET /api/v1/tasks/purchases?page=1&limit=50&location_id=loc-001&start_date=2024-01-01
        Headers:
            X-Tenant-Id: tenant-123
        ```
    """
    try:
        # Database client injected via dependency

        # Fetch purchase tasks
        result = await db_client.get_purchase_tasks(
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

    except HTTPException:
        raise
    except Exception as e:
        msg = "fetching purchase tasks"
        raise handle_database_error(msg, e)


@router.get("/cart-abandonment", response_model=dict[str, Any])
async def get_cart_abandonment_tasks(
    tenant_id: str = Depends(get_tenant_id),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(
        default=_settings.DEFAULT_PAGE_SIZE,
        ge=1,
        le=_settings.MAX_PAGE_SIZE,
        description="Items per page",
    ),
    query: str | None = Query(default=None, description="Search query"),
    location_id: str | None = Query(default=None, description="Location filter"),
    start_date: str | None = Query(default=None, description="Start date filter"),
    end_date: str | None = Query(default=None, description="End date filter"),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client),
) -> dict[str, Any]:
    """
    Retrieve paginated cart abandonment tasks with optional filtering.

    Cart abandonment tasks identify sessions where users added items to their
    cart but did not complete the purchase. These represent recovery opportunities
    for sales teams to re-engage potential customers.

    Args:
        tenant_id: Tenant identifier extracted from X-Tenant-Id header.
        page: Page number (1-indexed) for pagination. Must be >= 1.
        limit: Maximum items per page. Must be between 1 and MAX_PAGE_SIZE.
        query: Optional search query to filter by customer name, email, or company.
        location_id: Optional location filter to restrict results to a specific branch.
        start_date: Optional start date filter (YYYY-MM-DD format).
        end_date: Optional end date filter (YYYY-MM-DD format).
        db_client: Database client dependency injection.

    Returns:
        dict[str, Any]: Paginated response containing:
            - data (list[dict]): List of cart abandonment task objects with
              session details, cart contents, and customer information
            - total (int): Total number of matching tasks
            - page (int): Current page number
            - limit (int): Items per page
            - has_more (bool): Whether more pages are available

    Raises:
        HTTPException: 400 if tenant_id is invalid or pagination parameters invalid.
        HTTPException: 500 if database query fails.

    Example:
        ```bash
        GET /api/v1/tasks/cart-abandonment?page=1&limit=50&start_date=2024-01-01
        Headers:
            X-Tenant-Id: tenant-123
        ```
    """
    try:
        # Database client injected via dependency

        # Fetch cart abandonment tasks
        result = await db_client.get_cart_abandonment_tasks(
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

    except HTTPException:
        raise
    except Exception as e:
        msg = "fetching cart abandonment tasks"
        raise handle_database_error(msg, e)


@router.get("/search-analysis", response_model=dict[str, Any])
async def get_search_analysis_tasks(
    tenant_id: str = Depends(get_tenant_id),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(
        default=_settings.DEFAULT_PAGE_SIZE,
        ge=1,
        le=_settings.MAX_PAGE_SIZE,
        description="Items per page",
    ),
    query: str | None = Query(default=None, description="Search query"),
    location_id: str | None = Query(default=None, description="Location filter"),
    start_date: str | None = Query(default=None, description="Start date filter"),
    end_date: str | None = Query(default=None, description="End date filter"),
    include_converted: bool = Query(
        default=False, description="Include sessions that resulted in a purchase"
    ),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client),
) -> dict[str, Any]:
    """
    Retrieve paginated search analysis tasks with optional filtering.

    Search analysis tasks provide insights into user search behavior, including
    searches that returned no results (failed searches) and search patterns
    that led to conversions. This helps identify product gaps and optimization
    opportunities.

    Args:
        tenant_id: Tenant identifier extracted from X-Tenant-Id header.
        page: Page number (1-indexed) for pagination. Must be >= 1.
        limit: Maximum items per page. Must be between 1 and MAX_PAGE_SIZE.
        query: Optional search query to filter by search term or customer information.
        location_id: Optional location filter to restrict results to a specific branch.
        start_date: Optional start date filter (YYYY-MM-DD format).
        end_date: Optional end date filter (YYYY-MM-DD format).
        include_converted: If True, includes searches that resulted in purchases.
            If False (default), only includes searches without conversions.
        db_client: Database client dependency injection.

    Returns:
        dict[str, Any]: Paginated response containing:
            - data (list[dict]): List of search analysis task objects with
              search terms, result counts, conversion status, and session details
            - total (int): Total number of matching tasks
            - page (int): Current page number
            - limit (int): Items per page
            - has_more (bool): Whether more pages are available

    Raises:
        HTTPException: 400 if tenant_id is invalid or pagination parameters invalid.
        HTTPException: 500 if database query fails.

    Example:
        ```bash
        # Get failed searches only
        GET /api/v1/tasks/search-analysis?include_converted=false
        
        # Get all searches including converted
        GET /api/v1/tasks/search-analysis?include_converted=true
        Headers:
            X-Tenant-Id: tenant-123
        ```
    """
    try:
        # Database client injected via dependency

        # Fetch search analysis tasks
        result = await db_client.get_search_analysis_tasks(
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

    except HTTPException:
        raise
    except Exception as e:
        msg = "fetching search analysis tasks"
        raise handle_database_error(msg, e)


@router.get("/performance", response_model=dict[str, Any])
async def get_performance_tasks(
    tenant_id: str = Depends(get_tenant_id),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(
        default=_settings.DEFAULT_PAGE_SIZE,
        ge=1,
        le=_settings.MAX_PAGE_SIZE,
        description="Items per page",
    ),
    location_id: str | None = Query(default=None, description="Location filter"),
    start_date: str | None = Query(default=None, description="Start date filter"),
    end_date: str | None = Query(default=None, description="End date filter"),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client),
) -> dict[str, Any]:
    """
    Retrieve paginated branch performance tasks with optional filtering.

    Performance tasks provide aggregated metrics for each branch/location,
    including revenue, visitor counts, conversion rates, and other KPIs.
    This helps identify top-performing locations and areas for improvement.

    Args:
        tenant_id: Tenant identifier extracted from X-Tenant-Id header.
        page: Page number (1-indexed) for pagination. Must be >= 1.
        limit: Maximum items per page. Must be between 1 and MAX_PAGE_SIZE.
        location_id: Optional location filter. If provided, returns only the
            specified location. If None, returns all locations.
        start_date: Optional start date filter (YYYY-MM-DD format).
        end_date: Optional end date filter (YYYY-MM-DD format).
        db_client: Database client dependency injection.

    Returns:
        dict[str, Any]: Paginated response containing:
            - data (list[dict]): List of performance task objects with
              location details, revenue, visitor counts, conversion rates,
              and other performance metrics
            - total (int): Total number of matching tasks
            - page (int): Current page number
            - limit (int): Items per page
            - has_more (bool): Whether more pages are available

    Raises:
        HTTPException: 400 if tenant_id is invalid or pagination parameters invalid.
        HTTPException: 500 if database query fails.

    Example:
        ```bash
        # Get all branch performance
        GET /api/v1/tasks/performance?start_date=2024-01-01&end_date=2024-01-31
        
        # Get specific branch performance
        GET /api/v1/tasks/performance?location_id=loc-001
        Headers:
            X-Tenant-Id: tenant-123
        ```
    """
    try:
        # Database client injected via dependency

        # Fetch performance tasks
        result = await db_client.get_performance_tasks(
            tenant_id=tenant_id,
            page=page,
            limit=limit,
            location_id=location_id,
            start_date=start_date,
            end_date=end_date,
        )

        logger.info(f"Retrieved performance tasks for tenant {tenant_id}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        msg = "fetching performance tasks"
        raise handle_database_error(msg, e)


@router.get("/repeat-visits", response_model=dict[str, Any])
async def get_repeat_visit_tasks(
    tenant_id: str = Depends(get_tenant_id),
    page: int = Query(default=1, ge=1, description="Page number"),
    limit: int = Query(
        default=_settings.DEFAULT_PAGE_SIZE,
        ge=1,
        le=_settings.MAX_PAGE_SIZE,
        description="Items per page",
    ),
    query: str | None = Query(
        default=None, description="Search query on user name, email, or company"
    ),
    location_id: str | None = Query(default=None, description="Location filter"),
    start_date: str | None = Query(default=None, description="Start date filter"),
    end_date: str | None = Query(default=None, description="End date filter"),
    db_client: AnalyticsPostgresClient = Depends(get_analytics_db_client),
) -> dict[str, Any]:
    """
    Retrieve paginated repeat visit tasks with optional filtering.

    Repeat visit tasks identify users who have visited multiple times, indicating
    high engagement or potential for loyalty programs. These users may benefit
    from personalized offers or VIP treatment.

    Args:
        tenant_id: Tenant identifier extracted from X-Tenant-Id header.
        page: Page number (1-indexed) for pagination. Must be >= 1.
        limit: Maximum items per page. Must be between 1 and MAX_PAGE_SIZE.
        query: Optional search query to filter by user name, email, or company.
            Performs case-insensitive partial matching.
        location_id: Optional location filter to restrict results to a specific branch.
        start_date: Optional start date filter (YYYY-MM-DD format).
        end_date: Optional end date filter (YYYY-MM-DD format).
        db_client: Database client dependency injection.

    Returns:
        dict[str, Any]: Paginated response containing:
            - data (list[dict]): List of repeat visit task objects with
              user information, visit counts, purchase history, and engagement
              metrics
            - total (int): Total number of matching tasks
            - page (int): Current page number
            - limit (int): Items per page
            - has_more (bool): Whether more pages are available

    Raises:
        HTTPException: 400 if tenant_id is invalid or pagination parameters invalid.
        HTTPException: 500 if database query fails.

    Example:
        ```bash
        GET /api/v1/tasks/repeat-visits?page=1&limit=50&query=Acme%20Corp
        Headers:
            X-Tenant-Id: tenant-123
        ```
    """
    try:
        # Database client injected via dependency

        # Fetch repeat visit tasks
        result = await db_client.get_repeat_visit_tasks(
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

    except HTTPException:
        raise
    except Exception as e:
        msg = "fetching repeat visit tasks"
        raise handle_database_error(msg, e)
