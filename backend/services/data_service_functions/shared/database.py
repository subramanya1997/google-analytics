"""
Database session management for Azure Functions.

This module provides per-request database connections without connection pooling,
suitable for the stateless nature of Azure Functions.

IMPORTANT: Uses tenant-specific databases for SOC2 compliance.
Each tenant has their own database: google-analytics-{tenant_id}
"""

import os
import uuid
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from datetime import date, datetime
from decimal import Decimal
import json

from sqlalchemy import create_engine, text, delete, func, select
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.dialects.postgresql import insert
from loguru import logger
from dotenv import load_dotenv

load_dotenv()


def ensure_uuid_string(tenant_id: str) -> str:
    """Convert tenant_id to a consistent UUID string format."""
    try:
        uuid_obj = uuid.UUID(tenant_id)
        return str(uuid_obj)
    except ValueError:
        import hashlib
        tenant_uuid = uuid.UUID(bytes=hashlib.md5(tenant_id.encode()).digest()[:16])
        return str(tenant_uuid)


def get_tenant_database_name(tenant_id: str) -> str:
    """
    Get the database name for a tenant.
    
    Each tenant has their own isolated database for SOC2 compliance.
    Format: google-analytics-{tenant_id}
    
    Args:
        tenant_id: The tenant ID (UUID string)
        
    Returns:
        Database name in format: google-analytics-{tenant_id}
    """
    # Ensure tenant_id is a valid UUID string
    tenant_uuid_str = ensure_uuid_string(tenant_id)
    return f"google-analytics-{tenant_uuid_str}"


def create_sqlalchemy_url(tenant_id: str = None, async_driver: bool = False) -> URL:
    """
    Create SQLAlchemy URL from environment variables.
    
    Args:
        tenant_id: The tenant ID for tenant-specific database connection.
                   If None, falls back to POSTGRES_DATABASE env var (for admin ops).
        async_driver: Whether to use async driver (asyncpg) or sync driver (psycopg2)
    
    Returns:
        SQLAlchemy URL object
    """
    driver = "postgresql+asyncpg" if async_driver else "postgresql+psycopg2"
    
    # Determine database name
    if tenant_id:
        database_name = get_tenant_database_name(tenant_id)
    else:
        # Fallback to env var for backwards compatibility or admin operations
        database_name = os.getenv("POSTGRES_DATABASE")
        if not database_name:
            raise ValueError(
                "Either tenant_id must be provided or POSTGRES_DATABASE env var must be set. "
                "Tenant-specific databases are required for SOC2 compliance."
            )
    
    url = URL.create(
        drivername=driver,
        username=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        database=database_name,
    )
    return url


def get_sync_engine(tenant_id: str = None):
    """Get a fresh sync database engine (no pooling for serverless)."""
    url = create_sqlalchemy_url(tenant_id=tenant_id, async_driver=False)
    
    engine = create_engine(
        url,
        pool_pre_ping=True,
        pool_size=1,
        max_overflow=0,
        echo=os.getenv("DATABASE_ECHO", "false").lower() == "true",
    )
    return engine


def get_async_engine(tenant_id: str = None):
    """
    Get a fresh async database engine (no pooling for serverless).
    
    Args:
        tenant_id: The tenant ID for tenant-specific database connection.
    """
    url = create_sqlalchemy_url(tenant_id=tenant_id, async_driver=True)
    
    async_engine = create_async_engine(
        url,
        pool_pre_ping=True,
        pool_size=1,
        max_overflow=0,
        echo=os.getenv("DATABASE_ECHO", "false").lower() == "true",
    )
    return async_engine


@asynccontextmanager
async def get_db_session(tenant_id: str = None):
    """
    Async context manager for database sessions.
    Creates a fresh connection per invocation (serverless pattern).
    
    Args:
        tenant_id: The tenant ID for tenant-specific database connection.
                   Required for tenant data operations.
    """
    engine = get_async_engine(tenant_id=tenant_id)
    session_maker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False
    )
    session = session_maker()
    try:
        yield session
    except Exception as e:
        await session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        await session.close()
        await engine.dispose()


class FunctionsRepository:
    """
    Data-access layer for Azure Functions.
    Designed for stateless per-request connections.
    
    Each tenant has their own isolated database (google-analytics-{tenant_id})
    for SOC2 compliance and data isolation.
    """

    def __init__(self, tenant_id: str):
        """
        Initialize repository for a specific tenant.
        
        Args:
            tenant_id: The tenant ID - used to connect to the correct database.
        """
        self.tenant_id = ensure_uuid_string(tenant_id)

    async def create_processing_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new processing job."""
        async with get_db_session(tenant_id=self.tenant_id) as session:
            if "tenant_id" in job_data:
                job_data["tenant_id"] = ensure_uuid_string(job_data["tenant_id"])

            # Convert data_types to JSON string for JSONB column (matches data_service)
            data_types = job_data.get("data_types", [])
            data_types_json = json.dumps(data_types)
            
            # progress and records_processed are NOT NULL in schema
            # SQLAlchemy ORM uses default=dict, but raw SQL needs explicit values
            progress_json = json.dumps(job_data.get("progress", {}))
            records_processed_json = json.dumps(job_data.get("records_processed", {}))

            stmt = text("""
                INSERT INTO processing_jobs (
                    job_id, tenant_id, status, data_types, 
                    start_date, end_date, progress, records_processed, created_at
                )
                VALUES (
                    :job_id, :tenant_id, :status, CAST(:data_types AS jsonb), 
                    :start_date, :end_date, CAST(:progress AS jsonb), CAST(:records_processed AS jsonb), NOW()
                )
                RETURNING *
            """)
            
            result = await session.execute(stmt, {
                "job_id": job_data["job_id"],
                "tenant_id": job_data["tenant_id"],
                "status": job_data["status"],
                "data_types": data_types_json,
                "start_date": job_data["start_date"],
                "end_date": job_data["end_date"],
                "progress": progress_json,
                "records_processed": records_processed_json,
            })
            await session.commit()
            row = result.mappings().first()
            return dict(row) if row else {}

    async def update_job_status(self, job_id: str, status: str, **kwargs) -> bool:
        """Update job status with optional additional fields."""
        async with get_db_session(tenant_id=self.tenant_id) as session:
            # Build dynamic update
            set_clauses = ["status = :status"]
            params = {"job_id": job_id, "status": status}
            
            if "started_at" in kwargs:
                set_clauses.append("started_at = :started_at")
                params["started_at"] = kwargs["started_at"]
            
            if "completed_at" in kwargs:
                set_clauses.append("completed_at = :completed_at")
                params["completed_at"] = kwargs["completed_at"]
            
            if "error_message" in kwargs:
                set_clauses.append("error_message = :error_message")
                params["error_message"] = kwargs["error_message"]
            
            if "progress" in kwargs:
                set_clauses.append("progress = CAST(:progress AS jsonb)")
                params["progress"] = json.dumps(kwargs["progress"]) if kwargs["progress"] else None
            
            if "records_processed" in kwargs:
                set_clauses.append("records_processed = CAST(:records_processed AS jsonb)")
                params["records_processed"] = json.dumps(kwargs["records_processed"]) if kwargs["records_processed"] else None

            stmt = text(f"""
                UPDATE processing_jobs 
                SET {', '.join(set_clauses)}
                WHERE job_id = :job_id
            """)
            
            result = await session.execute(stmt, params)
            await session.commit()
            return result.rowcount > 0

    async def replace_event_data(
        self,
        tenant_id: str,
        event_type: str,
        start_date: date,
        end_date: date,
        events_data: List[Dict[str, Any]],
    ) -> int:
        """Replace event data for a date range."""
        tenant_uuid_str = ensure_uuid_string(tenant_id)
        
        async with get_db_session(tenant_id=self.tenant_id) as session:
            # Delete existing data
            del_stmt = text(f"""
                DELETE FROM {event_type}
                WHERE tenant_id = :tenant_id
                AND event_date BETWEEN :start_date AND :end_date
            """)
            
            delete_result = await session.execute(del_stmt, {
                "tenant_id": tenant_uuid_str,
                "start_date": start_date,
                "end_date": end_date
            })
            deleted_count = delete_result.rowcount or 0
            logger.info(f"Deleted {deleted_count} existing {event_type} events")

            if not events_data:
                await session.commit()
                return 0

            # Insert in batches
            total = len(events_data)
            batch_size = 500
            
            for i in range(0, total, batch_size):
                batch = events_data[i:i + batch_size]
                
                # Normalize each record
                normalized_batch = []
                for ev in batch:
                    ev_copy = dict(ev)
                    ev_copy["tenant_id"] = tenant_uuid_str
                    
                    # Handle date conversion
                    if isinstance(ev_copy.get("event_date"), str):
                        ev_date = ev_copy["event_date"]
                        if len(ev_date) == 8 and ev_date.isdigit():
                            ev_copy["event_date"] = date(
                                int(ev_date[:4]), int(ev_date[4:6]), int(ev_date[6:8])
                            )
                    
                    normalized_batch.append(ev_copy)
                
                # Build insert statement dynamically based on first record
                if normalized_batch:
                    columns = list(normalized_batch[0].keys())
                    placeholders = ", ".join([f":{col}" for col in columns])
                    columns_str = ", ".join(columns)
                    
                    insert_stmt = text(f"""
                        INSERT INTO {event_type} ({columns_str})
                        VALUES ({placeholders})
                    """)
                    
                    for record in normalized_batch:
                        await session.execute(insert_stmt, record)
            
            await session.commit()
            logger.info(f"Inserted {total} {event_type} events")
            return total

    async def upsert_users(self, tenant_id: str, users_data: List[Dict[str, Any]]) -> int:
        """Upsert users data in batches for performance."""
        if not users_data:
            return 0
        
        tenant_uuid_str = ensure_uuid_string(tenant_id)
        batch_size = 500
        total = 0
        errors = 0
        
        # Prepare all rows with tenant_id
        rows = []
        for user in users_data:
            user["tenant_id"] = tenant_uuid_str
            rows.append(user)
        
        # Process each batch in a SEPARATE session to isolate failures
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            # Build multi-row VALUES clause for batch insert
            values_clauses = []
            params = {}
            
            for idx, user in enumerate(batch):
                prefix = f"u{idx}_"
                values_clauses.append(f"""(
                    :{prefix}tenant_id, :{prefix}user_id, :{prefix}user_name, 
                    :{prefix}first_name, :{prefix}middle_name, :{prefix}last_name,
                    :{prefix}job_title, :{prefix}user_erp_id, :{prefix}email, 
                    :{prefix}office_phone, :{prefix}cell_phone, :{prefix}fax,
                    :{prefix}address1, :{prefix}address2, :{prefix}address3, 
                    :{prefix}city, :{prefix}state, :{prefix}country, :{prefix}zip,
                    :{prefix}warehouse_code, :{prefix}registered_date, :{prefix}last_login_date,
                    :{prefix}cimm_buying_company_id, :{prefix}buying_company_name, :{prefix}buying_company_erp_id,
                    :{prefix}role_name, :{prefix}site_name, true, NOW()
                )""")
                
                # Add all user fields with prefix
                for key, value in user.items():
                    params[f"{prefix}{key}"] = value
            
            stmt = text(f"""
                INSERT INTO users (tenant_id, user_id, user_name, first_name, middle_name, last_name,
                    job_title, user_erp_id, email, office_phone, cell_phone, fax,
                    address1, address2, address3, city, state, country, zip,
                    warehouse_code, registered_date, last_login_date,
                    cimm_buying_company_id, buying_company_name, buying_company_erp_id,
                    role_name, site_name, is_active, updated_at)
                VALUES {', '.join(values_clauses)}
                ON CONFLICT (tenant_id, user_id) DO UPDATE SET
                    user_name = EXCLUDED.user_name,
                    first_name = EXCLUDED.first_name,
                    middle_name = EXCLUDED.middle_name,
                    last_name = EXCLUDED.last_name,
                    job_title = EXCLUDED.job_title,
                    email = EXCLUDED.email,
                    is_active = EXCLUDED.is_active,
                    updated_at = NOW()
            """)
            
            try:
                # Use separate session per batch to isolate failures
                async with get_db_session(tenant_id=self.tenant_id) as session:
                    result = await session.execute(stmt, params)
                    await session.commit()
                    batch_count = result.rowcount or len(batch)
                    total += batch_count
                    logger.debug(f"Upserted user batch {batch_num}: {batch_count} rows")
            except Exception as e:
                errors += 1
                logger.warning(f"Error upserting user batch {batch_num}: {e}")
                # Continue with next batch instead of failing completely
        
        logger.info(f"Upserted {total} users ({errors} batch errors)")
        return total, errors  # Return tuple (count, errors)

    async def upsert_locations(self, tenant_id: str, locations_data: List[Dict[str, Any]]) -> int:
        """Upsert locations data in batches for performance."""
        if not locations_data:
            return 0
        
        tenant_uuid_str = ensure_uuid_string(tenant_id)
        batch_size = 500
        total = 0
        errors = 0
        
        # Prepare all rows with tenant_id
        rows = []
        for loc in locations_data:
            loc["tenant_id"] = tenant_uuid_str
            if loc.get("warehouse_id"):
                loc["warehouse_id"] = str(loc["warehouse_id"])
            rows.append(loc)
        
        # Process each batch in a SEPARATE session to isolate failures
        for i in range(0, len(rows), batch_size):
            batch = rows[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            # Build multi-row VALUES clause for batch insert
            values_clauses = []
            params = {}
            
            for idx, loc in enumerate(batch):
                prefix = f"l{idx}_"
                values_clauses.append(f"""(
                    :{prefix}tenant_id, :{prefix}warehouse_id, :{prefix}warehouse_code, :{prefix}warehouse_name,
                    :{prefix}city, :{prefix}state, :{prefix}country, 
                    :{prefix}address1, :{prefix}address2, :{prefix}zip, true, NOW()
                )""")
                
                # Add all location fields with prefix
                for key, value in loc.items():
                    params[f"{prefix}{key}"] = value
            
            stmt = text(f"""
                INSERT INTO locations (tenant_id, warehouse_id, warehouse_code, warehouse_name,
                    city, state, country, address1, address2, zip, is_active, updated_at)
                VALUES {', '.join(values_clauses)}
                ON CONFLICT (tenant_id, warehouse_id) DO UPDATE SET
                    warehouse_code = EXCLUDED.warehouse_code,
                    warehouse_name = EXCLUDED.warehouse_name,
                    city = EXCLUDED.city,
                    state = EXCLUDED.state,
                    country = EXCLUDED.country,
                    address1 = EXCLUDED.address1,
                    address2 = EXCLUDED.address2,
                    zip = EXCLUDED.zip,
                    is_active = EXCLUDED.is_active,
                    updated_at = NOW()
            """)
            
            try:
                # Use separate session per batch to isolate failures
                async with get_db_session(tenant_id=self.tenant_id) as session:
                    result = await session.execute(stmt, params)
                    await session.commit()
                    batch_count = result.rowcount or len(batch)
                    total += batch_count
                    logger.debug(f"Upserted location batch {batch_num}: {batch_count} rows")
            except Exception as e:
                errors += 1
                logger.warning(f"Error upserting location batch {batch_num}: {e}")
                # Continue with next batch instead of failing completely
        
        logger.info(f"Upserted {total} locations ({errors} batch errors)")
        return total, errors  # Return tuple (count, errors)

    async def get_tenant_service_status(self, tenant_id: str) -> Dict[str, Dict[str, Any]]:
        """Get service status for a tenant."""
        async with get_db_session(tenant_id=self.tenant_id) as session:
            # Query tenant_config with explicit tenant_id for consistency with data_service
            stmt = text("""
                SELECT bigquery_enabled, sftp_enabled, bigquery_validation_error, sftp_validation_error,
                       bigquery_project_id, sftp_config
                FROM tenant_config
                WHERE id = :tenant_id AND is_active = true
            """)
            result = await session.execute(stmt, {"tenant_id": tenant_id})
            row = result.mappings().first()
            
            if not row:
                return {
                    "bigquery": {"enabled": False, "error": "Tenant config not found"},
                    "sftp": {"enabled": False, "error": "Tenant config not found"}
                }
            
            # Check BigQuery status
            bigquery_enabled = row.get("bigquery_enabled", False) and row.get("bigquery_project_id")
            bigquery_error = row.get("bigquery_validation_error") or (None if bigquery_enabled else "BigQuery not configured")
            
            # Check SFTP status
            sftp_enabled = row.get("sftp_enabled", False) and row.get("sftp_config")
            sftp_error = row.get("sftp_validation_error") or (None if sftp_enabled else "SFTP not configured")
            
            return {
                "bigquery": {
                    "enabled": bool(bigquery_enabled),
                    "error": bigquery_error
                },
                "sftp": {
                    "enabled": bool(sftp_enabled),
                    "error": sftp_error
                }
            }

    async def get_tenant_bigquery_config(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get BigQuery config for a tenant."""
        async with get_db_session(tenant_id=self.tenant_id) as session:
            # Query tenant_config with explicit tenant_id for consistency with data_service
            stmt = text("""
                SELECT bigquery_project_id, bigquery_dataset_id, bigquery_credentials, bigquery_enabled
                FROM tenant_config
                WHERE id = :tenant_id AND is_active = true
            """)
            result = await session.execute(stmt, {"tenant_id": tenant_id})
            row = result.mappings().first()
            
            if row and row.get("bigquery_enabled") and row.get("bigquery_project_id"):
                # Parse credentials JSON if needed (matches data_service pattern)
                credentials = row.get("bigquery_credentials")
                if isinstance(credentials, str):
                    credentials = json.loads(credentials)
                
                return {
                    "project_id": row["bigquery_project_id"],
                    "dataset_id": row["bigquery_dataset_id"],
                    "service_account": credentials  # Use "service_account" key to match BigQueryClient expectations
                }
            return None

    async def get_tenant_sftp_config(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get SFTP config for a tenant."""
        async with get_db_session(tenant_id=self.tenant_id) as session:
            # Query tenant_config with explicit tenant_id for consistency with data_service
            stmt = text("""
                SELECT sftp_config, sftp_enabled
                FROM tenant_config
                WHERE id = :tenant_id AND is_active = true
            """)
            result = await session.execute(stmt, {"tenant_id": tenant_id})
            row = result.mappings().first()
            
            if row and row.get("sftp_enabled") and row.get("sftp_config"):
                config = row["sftp_config"]
                if isinstance(config, str):
                    return json.loads(config)
                return config
            return None

    # ======================================
    # EMAIL JOB METHODS
    # ======================================

    async def create_email_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new email sending job."""
        async with get_db_session(tenant_id=self.tenant_id) as session:
            tenant_uuid_str = ensure_uuid_string(job_data["tenant_id"])
            
            stmt = text("""
                INSERT INTO email_sending_jobs (
                    tenant_id, job_id, status, report_date, target_branches
                ) VALUES (
                    :tenant_id, :job_id, :status, :report_date, :target_branches
                )
                RETURNING id, job_id, status
            """)
            
            result = await session.execute(stmt, {
                "tenant_id": tenant_uuid_str,
                "job_id": job_data["job_id"],
                "status": job_data["status"],
                "report_date": job_data["report_date"],
                "target_branches": job_data.get("target_branches", [])
            })
            row = result.mappings().first()
            await session.commit()
            
            return {
                "id": str(row["id"]) if row else None,
                "job_id": row["job_id"] if row else None,
                "status": row["status"] if row else None
            }

    async def update_email_job_status(
        self, job_id: str, status: str, updates: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update email job status and other fields."""
        async with get_db_session(tenant_id=self.tenant_id) as session:
            set_clauses = ["status = :status", "updated_at = NOW()"]
            params = {"job_id": job_id, "status": status}
            
            if updates:
                for key, value in updates.items():
                    if key in ["started_at", "completed_at", "total_emails", 
                             "emails_sent", "emails_failed", "error_message"]:
                        set_clauses.append(f"{key} = :{key}")
                        params[key] = value
            
            stmt = text(f"""
                UPDATE email_sending_jobs 
                SET {', '.join(set_clauses)}
                WHERE job_id = :job_id
            """)
            
            result = await session.execute(stmt, params)
            await session.commit()
            return result.rowcount > 0

    # ======================================
    # EMAIL CONFIG & MAPPINGS METHODS
    # ======================================

    async def get_email_config(self, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get email configuration for a tenant."""
        async with get_db_session(tenant_id=self.tenant_id) as session:
            # Each tenant database has a single-row tenant_config table
            stmt = text("""
                SELECT email_config, smtp_enabled
                FROM tenant_config
                LIMIT 1
            """)
            result = await session.execute(stmt)
            row = result.mappings().first()
            
            if row and row.get("smtp_enabled") and row.get("email_config"):
                config = row["email_config"]
                if isinstance(config, str):
                    return json.loads(config)
                return config
            return None

    async def get_smtp_service_status(self, tenant_id: str) -> Dict[str, Any]:
        """Check if SMTP is configured for tenant."""
        email_config = await self.get_email_config(tenant_id)
        
        if not email_config:
            return {"enabled": False, "error": "SMTP not configured"}
        
        # Check required fields
        required_fields = ["server", "from_address"]
        missing = [f for f in required_fields if not email_config.get(f)]
        
        if missing:
            return {"enabled": False, "error": f"Missing SMTP config: {', '.join(missing)}"}
        
        return {"enabled": True, "error": None}

    async def get_branch_email_mappings(
        self, tenant_id: str, branch_code: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get branch email mappings for a tenant."""
        tenant_uuid_str = ensure_uuid_string(tenant_id)
        
        async with get_db_session(tenant_id=self.tenant_id) as session:
            query = """
                SELECT id, branch_code, branch_name, sales_rep_email, 
                       sales_rep_name, is_enabled, created_at, updated_at
                FROM branch_email_mappings
                WHERE tenant_id = :tenant_id
            """
            params = {"tenant_id": tenant_uuid_str}
            
            if branch_code:
                query += " AND branch_code = :branch_code"
                params["branch_code"] = branch_code
            
            query += " ORDER BY branch_code, sales_rep_email"
            
            result = await session.execute(text(query), params)
            rows = result.mappings().all()
            
            mappings = []
            for row in rows:
                mappings.append({
                    "id": str(row["id"]),
                    "branch_code": row["branch_code"],
                    "branch_name": row["branch_name"],
                    "sales_rep_email": row["sales_rep_email"],
                    "sales_rep_name": row["sales_rep_name"],
                    "is_enabled": row["is_enabled"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"]
                })
            
            return mappings

    # ======================================
    # EMAIL HISTORY METHODS
    # ======================================

    async def log_email_send_history(self, history_data: Dict[str, Any]) -> None:
        """Log email send history record."""
        tenant_uuid_str = ensure_uuid_string(history_data["tenant_id"])
        
        async with get_db_session(tenant_id=self.tenant_id) as session:
            stmt = text("""
                INSERT INTO email_send_history (
                    tenant_id, job_id, branch_code, sales_rep_email,
                    sales_rep_name, subject, report_date, status,
                    smtp_response, error_message
                ) VALUES (
                    :tenant_id, :job_id, :branch_code, :sales_rep_email,
                    :sales_rep_name, :subject, :report_date, :status,
                    :smtp_response, :error_message
                )
            """)
            
            await session.execute(stmt, {
                "tenant_id": tenant_uuid_str,
                "job_id": history_data.get("job_id"),
                "branch_code": history_data["branch_code"],
                "sales_rep_email": history_data["sales_rep_email"],
                "sales_rep_name": history_data.get("sales_rep_name"),
                "subject": history_data["subject"],
                "report_date": history_data["report_date"],
                "status": history_data["status"],
                "smtp_response": history_data.get("smtp_response"),
                "error_message": history_data.get("error_message")
            })
            await session.commit()

    # ======================================
    # LOCATION METHODS
    # ======================================

    async def get_location_by_code(self, tenant_id: str, branch_code: str) -> Optional[Dict[str, Any]]:
        """Get location info by branch/warehouse code."""
        tenant_uuid_str = ensure_uuid_string(tenant_id)
        
        async with get_db_session(tenant_id=self.tenant_id) as session:
            stmt = text("""
                SELECT warehouse_id, warehouse_code, warehouse_name, city, state, country
                FROM locations
                WHERE tenant_id = :tenant_id AND warehouse_code = :branch_code
                LIMIT 1
            """)
            
            result = await session.execute(stmt, {
                "tenant_id": tenant_uuid_str,
                "branch_code": branch_code
            })
            row = result.mappings().first()
            
            if row:
                return {
                    "warehouse_id": row["warehouse_id"],
                    "warehouse_code": row["warehouse_code"],
                    "warehouse_name": row["warehouse_name"],
                    "city": row["city"],
                    "state": row["state"],
                    "country": row["country"]
                }
            return None

    # Analytics task query methods
    async def get_purchase_tasks(
        self,
        tenant_id: str,
        page: int,
        limit: int,
        query: Optional[str] = None,
        location_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get purchase analysis tasks with pagination and filtering."""
        try:
            async with get_db_session(tenant_id=self.tenant_id) as session:
                # Use the existing RPC function from functions.sql
                result = await session.execute(
                    text("""
                        SELECT get_purchase_tasks(:p_tenant_id, :p_page, :p_limit, :p_query, :p_location_id, :p_start_date, :p_end_date)
                    """),
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
                tasks = result.scalar()

                return tasks or {
                    "data": [],
                    "total": 0,
                    "page": page,
                    "limit": limit,
                    "has_more": False,
                }

        except Exception as e:
            logger.error(f"Error fetching purchase tasks: {e}")
            return {"data": [], "total": 0, "page": page, "limit": limit, "has_more": False}

    async def get_cart_abandonment_tasks(
        self,
        tenant_id: str,
        page: int,
        limit: int,
        query: Optional[str] = None,
        location_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get cart abandonment tasks using the RPC function."""
        try:
            async with get_db_session(tenant_id=self.tenant_id) as session:
                result = await session.execute(
                    text("""
                        SELECT get_cart_abandonment_tasks(:p_tenant_id, :p_page, :p_limit, :p_query, :p_location_id, :p_start_date, :p_end_date)
                    """),
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
                tasks = result.scalar()

                return tasks or {
                    "data": [],
                    "total": 0,
                    "page": page,
                    "limit": limit,
                    "has_more": False,
                }

        except Exception as e:
            logger.error(f"Error fetching cart abandonment tasks: {e}")
            return {"data": [], "total": 0, "page": page, "limit": limit, "has_more": False}

    async def get_search_analysis_tasks(
        self,
        tenant_id: str,
        page: int,
        limit: int,
        query: Optional[str] = None,
        location_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        include_converted: bool = False,
    ) -> Dict[str, Any]:
        """Get search analysis tasks using the RPC function."""
        try:
            async with get_db_session(tenant_id=self.tenant_id) as session:
                result = await session.execute(
                    text("""
                        SELECT get_search_analysis_tasks(:p_tenant_id, :p_page, :p_limit, :p_query, :p_location_id, :p_start_date, :p_end_date, :p_include_converted)
                    """),
                    {
                        "p_tenant_id": tenant_id,
                        "p_page": page,
                        "p_limit": limit,
                        "p_query": query,
                        "p_location_id": location_id,
                        "p_start_date": start_date,
                        "p_end_date": end_date,
                        "p_include_converted": include_converted,
                    },
                )
                tasks = result.scalar()

                return tasks or {
                    "data": [],
                    "total": 0,
                    "page": page,
                    "limit": limit,
                    "has_more": False,
                }

        except Exception as e:
            logger.error(f"Error fetching search analysis tasks: {e}")
            return {"data": [], "total": 0, "page": page, "limit": limit, "has_more": False}

    async def get_repeat_visit_tasks(
        self,
        tenant_id: str,
        page: int,
        limit: int,
        query: Optional[str] = None,
        location_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get repeat visit tasks using the RPC function."""
        try:
            async with get_db_session(tenant_id=self.tenant_id) as session:
                result = await session.execute(
                    text("""
                        SELECT get_repeat_visit_tasks(:p_tenant_id, :p_page, :p_limit, :p_query, :p_location_id, :p_start_date, :p_end_date)
                    """),
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
                tasks = result.scalar()

                return tasks or {
                    "data": [],
                    "total": 0,
                    "page": page,
                    "limit": limit,
                    "has_more": False,
                }

        except Exception as e:
            logger.error(f"Error fetching repeat visit tasks: {e}")
            return {"data": [], "total": 0, "page": page, "limit": limit, "has_more": False}


def create_repository(tenant_id: str) -> FunctionsRepository:
    """
    Factory function to create a repository instance for a specific tenant.
    
    Args:
        tenant_id: The tenant ID - determines which database to connect to.
                   Each tenant has their own database: google-analytics-{tenant_id}
    
    Returns:
        FunctionsRepository instance configured for the tenant's database.
    """
    return FunctionsRepository(tenant_id)

