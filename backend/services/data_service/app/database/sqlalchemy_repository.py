from __future__ import annotations

from datetime import date
from decimal import Decimal
import json
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from loguru import logger

from services.data_service.app.database.sqlalchemy_session import get_engine
from common.models import (
    Purchase, AddToCart, PageView, ViewSearchResults, NoSearchResults, ViewItem,
    Users, Locations, ProcessingJobs
)


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

    def __init__(self, engine: Optional[Engine] = None):
        self.engine: Engine = engine or get_engine()

    # ---------- Job operations ----------
    def create_processing_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        with Session(self.engine) as session:
            # Ensure tenant_id is properly formatted for UUID column
            if 'tenant_id' in job_data:
                job_data['tenant_id'] = ensure_uuid_string(job_data['tenant_id'])
            
            stmt = (
                insert(ProcessingJobs.__table__)
                .values(job_data)
                .returning(*ProcessingJobs.__table__.columns)
            )
            result = session.execute(stmt)
            session.commit()
            row = result.mappings().first()
            return dict(row) if row else {}

    def update_job_status(self, job_id: str, status: str, **kwargs) -> bool:
        with Session(self.engine) as session:
            update_data = {"status": status}
            update_data.update(kwargs)
            stmt = (
                ProcessingJobs.__table__.update()
                .where(ProcessingJobs.__table__.c.job_id == job_id)
                .values(**update_data)
            )
            result = session.execute(stmt)
            session.commit()
            return result.rowcount > 0

    def get_job_by_id(self, job_id: str) -> Optional[Dict[str, Any]]:
        with Session(self.engine) as session:
            stmt = select(ProcessingJobs.__table__).where(
                ProcessingJobs.__table__.c.job_id == job_id
            )
            row = session.execute(stmt).mappings().first()
            return dict(row) if row else None

    # ---------- Events ----------
    def replace_event_data(
        self,
        tenant_id: str,
        event_type: str,
        start_date: date,
        end_date: date,
        events_data: List[Dict[str, Any]],
    ) -> int:
        table = EVENT_TABLES[event_type]
        tenant_uuid_str = ensure_uuid_string(tenant_id)
        with Session(self.engine) as session:
            # delete date range
            del_stmt = delete(table).where(
                table.c.tenant_id == tenant_uuid_str,
                table.c.event_date.between(start_date, end_date),
            )
            delete_result = session.execute(del_stmt)
            deleted_count = delete_result.rowcount or 0
            logger.info(f"Deleted {deleted_count} existing {event_type} events for tenant {tenant_id} from {start_date} to {end_date}")

            if not events_data:
                session.commit()
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
            logger.info(f"Inserting {len(normalized)} new {event_type} events in batches of {batch_size}")
            for i in range(0, len(normalized), batch_size):
                batch = normalized[i : i + batch_size]
                ins = table.insert().values(batch)
                result = session.execute(ins)
                batch_count = result.rowcount or 0
                total += batch_count
                logger.debug(f"Inserted batch {i//batch_size + 1}: {batch_count} {event_type} events")

            session.commit()
            logger.info(f"Successfully inserted {total} new {event_type} events for tenant {tenant_id}")
            return total

    # ---------- Dimensions ----------
    def upsert_users(self, tenant_id: str, users_data: List[Dict[str, Any]]) -> int:
        if not users_data:
            return 0
        table = Users.__table__
        total = 0
        batch_size = 500
        logger.info(f"Upserting {len(users_data)} users for tenant {tenant_id}")
        with Session(self.engine) as session:
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
                result = session.execute(upsert_stmt)
                batch_count = result.rowcount or 0
                total += batch_count
                logger.debug(f"Upserted batch {i//batch_size + 1}: {batch_count} users")
            session.commit()
            logger.info(f"Successfully upserted {total} users for tenant {tenant_id}")
            return total

    def upsert_locations(self, tenant_id: str, locations_data: List[Dict[str, Any]]) -> int:
        if not locations_data:
            return 0
        table = Locations.__table__
        total = 0
        batch_size = 500
        logger.info(f"Upserting {len(locations_data)} locations for tenant {tenant_id}")
        with Session(self.engine) as session:
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
                    index_elements=[table.c.tenant_id, table.c.warehouse_id], set_=update_map
                )
                result = session.execute(upsert_stmt)
                batch_count = result.rowcount or 0
                total += batch_count
                logger.debug(f"Upserted batch {i//batch_size + 1}: {batch_count} locations")
            session.commit()
            logger.info(f"Successfully upserted {total} locations for tenant {tenant_id}")
            return total

    # ---------- Analytics helpers ----------
    def get_analytics_summary(
        self, tenant_id: str, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> Dict[str, int]:
        summary: Dict[str, int] = {}
        
        # Convert tenant_id to proper UUID string
        tenant_uuid_str = ensure_uuid_string(tenant_id)
        
        with Session(self.engine) as session:
            for key, table in EVENT_TABLES.items():
                conds = [table.c.tenant_id == tenant_uuid_str]
                if start_date and end_date:
                    conds.append(table.c.event_date.between(start_date, end_date))
                count_stmt = select(func.count()).select_from(table).where(*conds)
                summary[key] = session.execute(count_stmt).scalar_one()

            # users
            u = Users.__table__
            summary["users"] = session.execute(
                select(func.count()).select_from(u).where(u.c.tenant_id == tenant_uuid_str)
            ).scalar_one()

            # locations
            l = Locations.__table__
            summary["locations"] = session.execute(
                select(func.count()).select_from(l).where(l.c.tenant_id == tenant_uuid_str)
            ).scalar_one()

        return summary


