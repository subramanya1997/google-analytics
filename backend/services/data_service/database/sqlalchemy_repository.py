from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import delete, func, select, literal_column, union_all, text
from sqlalchemy.dialects.postgresql import insert

from common.models import (
    AddToCart,
    Locations,
    NoSearchResults,
    PageView,
    ProcessingJobs,
    Purchase,
    Users,
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
        async with get_async_db_session(self.service_name) as session:
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

    async def update_job_status(self, job_id: str, status: str, **kwargs) -> bool:
        async with get_async_db_session(self.service_name) as session:
            update_data = {"status": status}
            update_data.update(kwargs)
            stmt = (
                ProcessingJobs.__table__.update()
                .where(ProcessingJobs.__table__.c.job_id == job_id)
                .values(**update_data)
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0

    async def get_job_by_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        async with get_async_db_session(self.service_name) as session:
            stmt = select(ProcessingJobs.__table__).where(
                ProcessingJobs.__table__.c.job_id == job_id
            )
            result = await session.execute(stmt)
            row = result.mappings().first()
            return dict(row) if row else None

    # ---------- Events ----------
    async def replace_event_data(
        self,
        tenant_id: str,
        event_type: str,
        start_date: date,
        end_date: date,
        events_data: List[Dict[str, Any]],
    ) -> int:
        table = EVENT_TABLES[event_type]
        tenant_uuid_str = ensure_uuid_string(tenant_id)
        async with get_async_db_session(self.service_name) as session:
            # delete date range
            del_stmt = delete(table).where(
                table.c.tenant_id == tenant_uuid_str,
                table.c.event_date.between(start_date, end_date),
            )
            delete_result = await session.execute(del_stmt)
            deleted_count = delete_result.rowcount or 0
            logger.info(
                f"Deleted {deleted_count} existing {event_type} events for tenant {tenant_id} from {start_date} to {end_date}"
            )

            if not events_data:
                await session.commit()
                return 0

            # normalize event_date, coerce types, filter to known columns
            # Optimized for performance with large datasets
            normalized: List[Dict[str, Any]] = []
            table_cols = set(c.name for c in table.c)
            decimal_fields = {
                "purchase": {"ecommerce_purchase_revenue"},
                "add_to_cart": {"first_item_price"},
                "view_item": {"first_item_price"},
            }.get(event_type, set())
            
            # Pre-check if we need JSON parsing (only once, not per record)
            has_json_fields = "items_json" in table_cols or "raw_data" in table_cols

            for ev in events_data:
                ev_copy: Dict[str, Any] = {}
                # keep only known columns
                for k, v in ev.items():
                    if k not in table_cols:
                        continue
                    # JSON fields: parse string to python (only if needed)
                    if has_json_fields and k in ("items_json", "raw_data") and isinstance(v, str):
                        try:
                            v = json.loads(v)
                        except Exception:
                            pass
                    # Decimal fields: coerce via Decimal
                    if k in decimal_fields and v is not None:
                        try:
                            v = Decimal(str(v))
                        except Exception:
                            pass
                    ev_copy[k] = v
                    
                # Date conversion - optimized
                ev_date = ev_copy.get("event_date")
                if isinstance(ev_date, str) and len(ev_date) == 8 and ev_date.isdigit():
                    ev_copy["event_date"] = date(
                        int(ev_date[:4]), int(ev_date[4:6]), int(ev_date[6:8])
                    )
                # Ensure tenant_id is properly formatted as UUID string
                ev_copy["tenant_id"] = tenant_uuid_str
                normalized.append(ev_copy)

            # Batch inserts to avoid PostgreSQL parameter limit (32,767)
            total = len(normalized)
            
            if total == 0:
                logger.info(f"No {event_type} events to insert")
                return 0
            
            # Safe batch size: 32,767 params ÷ ~19 columns ≈ 1,724 max, use 1,500 for safety
            batch_size = 1500
            logger.info(f"Inserting {total} {event_type} events in batches of {batch_size}")
            
            for i in range(0, total, batch_size):
                batch = normalized[i : i + batch_size]
                ins = table.insert().values(batch)
                await session.execute(ins)
                logger.debug(f"Inserted batch {i//batch_size + 1}: {len(batch)} {event_type} events")
            
            await session.commit()
            
            logger.info(
                f"Successfully inserted {total} {event_type} events for tenant {tenant_id}"
            )
            return total

    # ---------- Dimensions ----------
    async def upsert_users(self, tenant_id: str, users_data: List[Dict[str, Any]]) -> int:
        if not users_data:
            return 0
        table = Users.__table__
        total = 0
        batch_size = 500
        logger.info(f"Upserting {len(users_data)} users for tenant {tenant_id}")
        async with get_async_db_session(self.service_name) as session:
            # add tenant_id to each
            rows = []
            for u in users_data:
                r = dict(u)
                # ensure UUID type for tenant_id
                r["tenant_id"] = ensure_uuid_string(tenant_id)
                rows.append(r)

            for i in range(0, len(rows), batch_size):
                batch = rows[i : i + batch_size]
                stmt = insert(table).values(batch)
                excluded = stmt.excluded
                # update all columns except immutable keys
                update_map = {
                    c.name: getattr(excluded, c.name)
                    for c in table.c
                    if c.name not in ("id", "tenant_id", "user_id", "created_at")
                }
                # always bump updated_at
                update_map["updated_at"] = func.now()
                upsert_stmt = stmt.on_conflict_do_update(
                    index_elements=[table.c.tenant_id, table.c.user_id], set_=update_map
                )
                result = await session.execute(upsert_stmt)
                batch_count = result.rowcount or 0
                total += batch_count
                logger.debug(f"Upserted batch {i//batch_size + 1}: {batch_count} users")
            await session.commit()
            logger.info(f"Successfully upserted {total} users for tenant {tenant_id}")
            return total

    async def upsert_locations(
        self, tenant_id: str, locations_data: List[Dict[str, Any]]
    ) -> int:
        if not locations_data:
            return 0
        table = Locations.__table__
        total = 0
        batch_size = 500
        logger.info(f"Upserting {len(locations_data)} locations for tenant {tenant_id}")
        async with get_async_db_session(self.service_name) as session:
            rows = []
            for loc in locations_data:
                r = dict(loc)
                # ensure UUID type for tenant_id
                r["tenant_id"] = ensure_uuid_string(tenant_id)
                # ensure warehouse_id is string (it's the unique field in the model)
                if "warehouse_id" in r and r["warehouse_id"] is not None:
                    r["warehouse_id"] = str(r["warehouse_id"])
                rows.append(r)

            for i in range(0, len(rows), batch_size):
                batch = rows[i : i + batch_size]
                stmt = insert(table).values(batch)
                excluded = stmt.excluded
                update_map = {
                    c.name: getattr(excluded, c.name)
                    for c in table.c
                    if c.name not in ("id", "tenant_id", "warehouse_id", "created_at")
                }
                update_map["updated_at"] = func.now()
                upsert_stmt = stmt.on_conflict_do_update(
                    index_elements=[table.c.tenant_id, table.c.warehouse_id],
                    set_=update_map,
                )
                result = await session.execute(upsert_stmt)
                batch_count = result.rowcount or 0
                total += batch_count
                logger.debug(
                    f"Upserted batch {i//batch_size + 1}: {batch_count} locations"
                )
            await session.commit()
            logger.info(
                f"Successfully upserted {total} locations for tenant {tenant_id}"
            )
            return total

    # ---------- Analytics helpers ----------
    async def get_analytics_summary(
        self,
        tenant_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, int]:
        summary: Dict[str, int] = {}

        # Convert tenant_id to proper UUID string
        tenant_uuid_str = ensure_uuid_string(tenant_id)

        async with get_async_db_session(self.service_name) as session:
            for key, table in EVENT_TABLES.items():
                conds = [table.c.tenant_id == tenant_uuid_str]
                if start_date and end_date:
                    conds.append(table.c.event_date.between(start_date, end_date))
                count_stmt = select(func.count()).select_from(table).where(*conds)
                result = await session.execute(count_stmt)
                summary[key] = result.scalar_one()

            # users
            u = Users.__table__
            user_result = await session.execute(
                select(func.count())
                .select_from(u)
                .where(u.c.tenant_id == tenant_uuid_str)
            )
            summary["users"] = user_result.scalar_one()

            # locations
            l = Locations.__table__
            location_result = await session.execute(
                select(func.count())
                .select_from(l)
                .where(l.c.tenant_id == tenant_uuid_str)
            )
            summary["locations"] = location_result.scalar_one()

        return summary

    async def get_data_availability(self, tenant_id: str) -> Dict[str, Any]:
        """Get the date range of available data for a tenant."""
        tenant_uuid_str = ensure_uuid_string(tenant_id)
        
        async with get_async_db_session(self.service_name) as session:
            results = {}
            earliest_date = None
            latest_date = None
            total_events = 0
            
            for event_type, table in EVENT_TABLES.items():
                # Get date range for this event type
                date_query = (
                    select(
                        func.min(table.c.event_date).label("earliest"),
                        func.max(table.c.event_date).label("latest"),
                        func.count().label("count")
                    )
                    .select_from(table)
                    .where(table.c.tenant_id == tenant_uuid_str)
                )
                
                result_obj = await session.execute(date_query)
                result = result_obj.fetchone()
                
                if result and result.count > 0:
                    if earliest_date is None or (result.earliest and result.earliest < earliest_date):
                        earliest_date = result.earliest
                    if latest_date is None or (result.latest and result.latest > latest_date):
                        latest_date = result.latest
                    total_events += result.count
            
            return {
                "earliest_date": earliest_date.isoformat() if earliest_date else None,
                "latest_date": latest_date.isoformat() if latest_date else None,
                "total_events": total_events
            }

    async def get_data_availability_with_breakdown(self, tenant_id: str) -> Dict[str, Any]:
        """Get data availability summary using optimized function."""
        tenant_uuid_str = ensure_uuid_string(tenant_id)
        
        async with get_async_db_session(self.service_name) as session:
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
        
        async with get_async_db_session(self.service_name) as session:
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