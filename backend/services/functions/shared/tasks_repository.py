"""
Tasks Repository for Azure Functions.

Provides task query methods using the same PostgreSQL functions as the
analytics_service TasksRepository. Accepts a session_factory for dependency
injection, defaulting to the serverless get_db_session.
"""

import logging
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import text

from shared.database import get_db_session

logger = logging.getLogger(__name__)

_EMPTY_PAGE: dict[str, Any] = {
    "data": [],
    "total": 0,
    "page": 1,
    "limit": 50,
    "has_more": False,
}


class TasksRepository:
    """Task query repository with pluggable session management.

    Each method executes the corresponding PostgreSQL function and returns
    paginated results. The session_factory callable receives ``tenant_id``
    as a keyword argument and yields an ``AsyncSession``.
    """

    def __init__(
        self,
        session_factory: Callable[..., Any] | None = None,
    ) -> None:
        self._session_factory = session_factory or self._default_session_factory

    @staticmethod
    @asynccontextmanager
    async def _default_session_factory(tenant_id: str) -> AsyncIterator[Any]:
        async with get_db_session(tenant_id=tenant_id) as session:
            yield session

    async def get_purchase_tasks(
        self,
        tenant_id: str,
        page: int,
        limit: int,
        query: str | None = None,
        location_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Retrieve paginated purchase tasks."""
        try:
            async with self._session_factory(tenant_id=tenant_id) as session:
                result = await session.execute(
                    text(
                        "SELECT get_purchase_tasks("
                        ":p_tenant_id, :p_page, :p_limit, :p_query, "
                        ":p_location_id, :p_start_date, :p_end_date)"
                    ),
                    {
                        "p_tenant_id": tenant_id,
                        "p_page": page,
                        "p_limit": limit,
                        "p_query": query,
                        "p_location_id": location_id,
                        "p_start_date": start_date,
                        "p_end_date": end_date,
                    },
                )
                return result.scalar() or {
                    **_EMPTY_PAGE,
                    "page": page,
                    "limit": limit,
                }
        except Exception as e:
            logger.error(f"Error fetching purchase tasks: {e}")
            raise

    async def get_cart_abandonment_tasks(
        self,
        tenant_id: str,
        page: int,
        limit: int,
        query: str | None = None,
        location_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """Retrieve paginated cart abandonment tasks."""
        try:
            async with self._session_factory(tenant_id=tenant_id) as session:
                result = await session.execute(
                    text(
                        "SELECT get_cart_abandonment_tasks("
                        ":p_tenant_id, :p_page, :p_limit, :p_query, "
                        ":p_location_id, :p_start_date, :p_end_date)"
                    ),
                    {
                        "p_tenant_id": tenant_id,
                        "p_page": page,
                        "p_limit": limit,
                        "p_query": query,
                        "p_location_id": location_id,
                        "p_start_date": start_date,
                        "p_end_date": end_date,
                    },
                )
                return result.scalar() or {
                    **_EMPTY_PAGE,
                    "page": page,
                    "limit": limit,
                }
        except Exception as e:
            logger.error(f"Error fetching cart abandonment tasks: {e}")
            raise

    async def get_search_analysis_tasks(
        self,
        tenant_id: str,
        page: int,
        limit: int,
        query: str | None = None,
        location_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        include_converted: bool = False,
        sort_field: str | None = None,
        sort_order: str | None = None,
    ) -> dict[str, Any]:
        """Retrieve paginated search analysis tasks."""
        try:
            async with self._session_factory(tenant_id=tenant_id) as session:
                result = await session.execute(
                    text(
                        "SELECT get_search_analysis_tasks("
                        ":p_tenant_id, :p_page, :p_limit, :p_query, "
                        ":p_location_id, :p_start_date, :p_end_date, "
                        ":p_include_converted, :p_sort_field, :p_sort_order)"
                    ),
                    {
                        "p_tenant_id": tenant_id,
                        "p_page": page,
                        "p_limit": limit,
                        "p_query": query,
                        "p_location_id": location_id,
                        "p_start_date": start_date,
                        "p_end_date": end_date,
                        "p_include_converted": include_converted,
                        "p_sort_field": sort_field or "search_count",
                        "p_sort_order": sort_order or "desc",
                    },
                )
                return result.scalar() or {
                    **_EMPTY_PAGE,
                    "page": page,
                    "limit": limit,
                }
        except Exception as e:
            logger.error(f"Error fetching search analysis tasks: {e}")
            raise

    async def get_repeat_visit_tasks(
        self,
        tenant_id: str,
        page: int,
        limit: int,
        query: str | None = None,
        location_id: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        sort_field: str | None = None,
        sort_order: str | None = None,
    ) -> dict[str, Any]:
        """Retrieve paginated repeat visit tasks."""
        try:
            async with self._session_factory(tenant_id=tenant_id) as session:
                result = await session.execute(
                    text(
                        "SELECT get_repeat_visit_tasks("
                        ":p_tenant_id, :p_page, :p_limit, :p_query, "
                        ":p_location_id, :p_start_date, :p_end_date, "
                        ":p_sort_field, :p_sort_order)"
                    ),
                    {
                        "p_tenant_id": tenant_id,
                        "p_page": page,
                        "p_limit": limit,
                        "p_query": query,
                        "p_location_id": location_id,
                        "p_start_date": start_date,
                        "p_end_date": end_date,
                        "p_sort_field": sort_field or "page_views_count",
                        "p_sort_order": sort_order or "desc",
                    },
                )
                return result.scalar() or {
                    **_EMPTY_PAGE,
                    "page": page,
                    "limit": limit,
                }
        except Exception as e:
            logger.error(f"Error fetching repeat visit tasks: {e}")
            raise
