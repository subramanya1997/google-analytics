from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from loguru import logger
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert

from common.models import (
    AddToCart,
    NoSearchResults,
    PageView,
    ProcessingJobs,
    Purchase,
    ViewItem,
    ViewSearchResults,
)
from common.database import get_async_db_session


def ensure_uuid_string(tenant_id: str) -> str:
    """Convert tenant_id to a consistent UUID string format."""
    try:
        # Validate and convert to UUID string
        uuid_obj = uuid.UUID(tenant_id)
        return str(uuid_obj)
    except ValueError:
        # If not a valid UUID, generate one from the string using MD5 hash
        import hashlib

        tenant_uuid = uuid.UUID(bytes=hashlib.md5(tenant_id.encode()).digest()[:16])
        return str(tenant_uuid)


EVENT_TABLES: Dict[str, Any] = {
    "purchase": Purchase.__table__,
    "add_to_cart": AddToCart.__table__,
    "page_view": PageView.__table__,
    "view_search_results": ViewSearchResults.__table__,
    "no_search_results": NoSearchResults.__table__,
    "view_item": ViewItem.__table__,
}


class SqlAlchemyRepository:
    """Data-access layer client with SQLAlchemy."""

    def __init__(self, service_name: str = "data-service"):
        self.service_name = service_name

    # ---------- Job operations ----------
    async def create_processing_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        # Extract tenant_id for database routing
        tenant_id = job_data.get("tenant_id")
        
        async with get_async_db_session(self.service_name, tenant_id=tenant_id) as session:
            # Ensure tenant_id is properly formatted for UUID column
            if "tenant_id" in job_data:
                job_data["tenant_id"] = ensure_uuid_string(job_data["tenant_id"])

            stmt = (
                insert(ProcessingJobs.__table__)
                .values(job_data)
                .returning(*ProcessingJobs.__table__.columns)
            )
            result = await session.execute(stmt)
            await session.commit()
            row = result.mappings().first()
            return dict(row) if row else {}

    async def get_data_availability_with_breakdown(self, tenant_id: str) -> Dict[str, Any]:
        """Get data availability summary using optimized function."""
        tenant_uuid_str = ensure_uuid_string(tenant_id)
        
        async with get_async_db_session(self.service_name, tenant_id=tenant_id) as session:
            # Call simplified function that only returns summary data
            combined_query = text("SELECT * FROM get_data_availability_combined(:tenant_id)")
            result_obj = await session.execute(combined_query, {"tenant_id": tenant_uuid_str})
            result = result_obj.mappings().first()
            
            if result:
                summary_data = {
                    "earliest_date": result.earliest_date.isoformat() if result.earliest_date else None,
                    "latest_date": result.latest_date.isoformat() if result.latest_date else None,
                    "total_events": int(result.event_count)
                }
                logger.info(f"Data availability: {summary_data['total_events']} total events")
            else:
                summary_data = {
                    "earliest_date": None,
                    "latest_date": None,
                    "total_events": 0
                }
                logger.info("Data availability: No data found")
            
            return {
                "summary": summary_data,
            }

    async def get_tenant_jobs(self, tenant_id: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Get job history for a tenant - ULTRA-FAST PostgreSQL function only."""
        tenant_uuid_str = ensure_uuid_string(tenant_id)
        
        async with get_async_db_session(self.service_name, tenant_id=tenant_id) as session:
            # Call optimized PostgreSQL function (ULTRA FAST!)
            jobs_query = text("SELECT * FROM get_tenant_jobs_paginated(:tenant_id, :limit, :offset)")
            
            result = await session.execute(
                jobs_query,
                {
                    "tenant_id": tenant_uuid_str,
                    "limit": limit,
                    "offset": offset
                }
            )
            results = result.mappings().all()
            
            jobs = []
            total = 0
            
            for row in results:
                if total == 0:  # Get total from first row
                    total = int(row.total_count)
                
                # Build job data with proper type conversion
                job_data = {
                    "id": str(row.id),
                    "tenant_id": str(row.tenant_id),
                    "job_id": row.job_id,
                    "status": row.status,
                    "data_types": row.data_types,
                    "start_date": row.start_date.isoformat() if row.start_date else None,
                    "end_date": row.end_date.isoformat() if row.end_date else None,
                    "progress": row.progress,
                    "records_processed": row.records_processed,
                    "error_message": row.error_message,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "started_at": row.started_at.isoformat() if row.started_at else None,
                    "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                }
                jobs.append(job_data)
            
            logger.info(f"Job history: {len(jobs)} jobs returned, {total} total")
            
            return {
                "jobs": jobs,
                "total": total
            }