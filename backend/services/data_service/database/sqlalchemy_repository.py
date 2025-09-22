"""
SQLAlchemy Repository for Multi-Tenant Analytics Data Management.

This module provides a comprehensive data access layer for the Google Analytics
Intelligence System using SQLAlchemy ORM. It handles all database operations
including event data storage, dimension management, job tracking, and analytics
queries with proper multi-tenant isolation and performance optimization.

Key Features:
- **Multi-Tenant Data Isolation**: Tenant-scoped operations with UUID handling
- **Event Data Management**: Batch processing for 6 GA4 event types
- **Dimension Management**: User and location data with upsert operations
- **Job Tracking**: Processing job lifecycle and status management
- **Analytics Queries**: Data availability and summary statistics
- **Performance Optimization**: Batch operations, PostgreSQL functions
- **Data Integrity**: Transaction management and error handling

Database Architecture:
- **Event Tables**: Time-series event data with tenant isolation
- **Dimension Tables**: Reference data (users, locations) with SCD Type 1
- **Control Tables**: Job processing and system metadata
- **Multi-Tenant Design**: UUID-based tenant isolation across all tables

Supported Operations:
1. **Event Processing**: Batch insert/replace with type coercion
2. **Dimension Updates**: Upsert operations with conflict resolution
3. **Job Management**: Status tracking and progress monitoring
4. **Analytics**: Data availability and summary reporting
5. **Performance**: Optimized PostgreSQL functions for complex queries

The repository implements the Repository pattern to abstract database
operations and provide a clean interface for the service layer while
maintaining high performance and data consistency.
"""

from __future__ import annotations

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
    """
    Convert tenant_id to consistent UUID string format for database storage.
    
    Ensures all tenant identifiers are stored as valid UUID strings in the
    database, handling both valid UUID inputs and string inputs that need
    to be converted to UUID format using deterministic hashing.
    
    Args:
        tenant_id: Input tenant identifier (UUID string or arbitrary string)
        
    Returns:
        str: Valid UUID string representation for database storage
        
    Conversion Logic:
        - Valid UUID strings: Validated and returned as-is
        - Invalid UUID strings: Converted using MD5 hash for deterministic UUIDs
        - Ensures consistent tenant identification across all database operations
        
    Multi-Tenant Security:
        Provides consistent tenant identification for proper data isolation
        and prevents tenant ID spoofing through deterministic conversion.
    """
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
"""
Event table mapping for dynamic table access in batch operations.

Maps event type names to their corresponding SQLAlchemy table objects,
enabling generic event processing across all supported GA4 event types
without code duplication.
"""


class SqlAlchemyRepository:
    """
    Multi-tenant analytics data repository with comprehensive database operations.
    
    This repository provides the complete data access layer for the Google Analytics
    Intelligence System, handling all database operations with proper multi-tenant
    isolation, performance optimization, and data integrity management.
    
    Key Capabilities:
    - **Event Data Processing**: Batch insert/replace operations for GA4 events
    - **Dimension Management**: User and location data with upsert logic
    - **Job Tracking**: Processing job lifecycle and status management
    - **Analytics Queries**: Data availability and summary statistics
    - **Multi-Tenant Security**: UUID-based tenant isolation
    - **Performance Optimization**: Batch operations and PostgreSQL functions
    
    Database Design:
    - Uses async SQLAlchemy for non-blocking operations
    - Implements proper transaction management
    - Handles data type conversions and validation
    - Provides comprehensive error handling and logging
    
    Attributes:
        service_name: Service identifier for database session management
        
    """

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
        """
        Replace event data for tenant and date range with comprehensive processing.
        
        This is the primary method for event data ingestion, providing atomic
        replace operations that delete existing data for the date range and
        insert new events with proper data transformation and validation.
        
        **Atomic Replace Operation:**
        1. Delete existing events for tenant/event_type/date_range
        2. Transform and validate new event data
        3. Batch insert new events (1000 records per batch)
        4. Commit transaction atomically
        
        **Data Transformation:**
        - Converts string dates (YYYYMMDD) to date objects
        - Handles JSON field parsing (items_json, raw_data)
        - Performs decimal conversion for revenue fields
        - Filters columns to match database schema
        - Ensures proper tenant UUID formatting
        
        Args:
            tenant_id: Unique tenant identifier for data isolation
            event_type: GA4 event type (purchase, add_to_cart, page_view, etc.)
            start_date: Beginning of date range to replace (inclusive)
            end_date: End of date range to replace (inclusive)
            events_data: List of event dictionaries from BigQuery extraction
            
        Returns:
            int: Number of new event records successfully inserted
            
        **Multi-Tenant Security:**
        All operations are scoped to the specified tenant, ensuring
        proper data isolation and preventing cross-tenant contamination.
        
        Raises:
            Exception: Database transaction failures, data validation errors

        """
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
            normalized: List[Dict[str, Any]] = []
            table_cols = set(c.name for c in table.c)
            decimal_fields = {
                "purchase": {"ecommerce_purchase_revenue"},
                "add_to_cart": {"first_item_price"},
                "view_item": {"first_item_price"},
            }.get(event_type, set())

            for ev in events_data:
                ev_copy: Dict[str, Any] = {}
                # keep only known columns
                for k, v in ev.items():
                    if k not in table_cols:
                        continue
                    # JSON fields: parse string to python
                    if k in ("items_json", "raw_data") and isinstance(v, str):
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
                ev_date = ev_copy.get("event_date")
                if isinstance(ev_date, str) and len(ev_date) == 8 and ev_date.isdigit():
                    ev_copy["event_date"] = date(
                        int(ev_date[:4]), int(ev_date[4:6]), int(ev_date[6:8])
                    )
                # Ensure tenant_id is properly formatted as UUID string
                ev_copy["tenant_id"] = tenant_uuid_str
                normalized.append(ev_copy)

            batch_size = 1000
            total = 0
            logger.info(
                f"Inserting {len(normalized)} new {event_type} events in batches of {batch_size}"
            )
            for i in range(0, len(normalized), batch_size):
                batch = normalized[i : i + batch_size]
                ins = table.insert().values(batch)
                result = await session.execute(ins)
                batch_count = result.rowcount or 0
                total += batch_count
                logger.debug(
                    f"Inserted batch {i//batch_size + 1}: {batch_count} {event_type} events"
                )

            await session.commit()
            logger.info(
                f"Successfully inserted {total} new {event_type} events for tenant {tenant_id}"
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