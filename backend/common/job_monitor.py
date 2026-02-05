"""
Job Status Monitor for background task monitoring.

This module provides a lightweight background task that runs periodically to monitor
job statuses across all tenants. It detects stuck jobs (processing for too long)
and updates their status to failed.

The monitor runs as an asyncio background task within the FastAPI process, checking:
- Data ingestion jobs (processing_jobs table)
- Email sending jobs (email_sending_jobs table)

Features:
    - Periodic polling every N seconds (configurable, default 5 minutes)
    - Detects jobs stuck in 'processing' status beyond timeout threshold
    - Updates stuck jobs to 'failed' status with descriptive error message
    - Azure Queue statistics logging for monitoring
    - Multi-tenant support (queries all tenant databases)

Usage:
    ```python
    from common.job_monitor import JobStatusMonitor
    
    monitor = JobStatusMonitor(
        azure_connection_string="...",
        interval_seconds=300,
        stuck_timeout_minutes=10
    )
    
    # Start monitoring (typically in FastAPI lifespan)
    await monitor.start()
    
    # Stop monitoring (on shutdown)
    await monitor.stop()
    ```
"""

import asyncio
from datetime import datetime, timedelta, timezone
import json
import os
from typing import Any

from azure.storage.queue.aio import QueueClient
from dotenv import load_dotenv
from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

load_dotenv()


def _create_sqlalchemy_url(database_name: str, async_driver: bool = False) -> URL:
    """Create SQLAlchemy URL for a specific database."""
    driver = "postgresql+asyncpg" if async_driver else "postgresql+pg8000"
    return URL.create(
        drivername=driver,
        username=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        database=database_name,
    )


class JobStatusMonitor:
    """
    Background monitor for detecting and handling stuck jobs.
    
    This class runs as an asyncio background task within the FastAPI process,
    periodically checking for jobs that have been stuck in 'processing' status
    for too long and marking them as failed.
    
    Attributes:
        azure_connection_string: Connection string for Azure Storage Queue.
        interval_seconds: Polling interval in seconds (default: 300 = 5 minutes).
        stuck_timeout_minutes: Minutes after which a processing job is considered stuck.
    """

    def __init__(
        self,
        azure_connection_string: str,
        interval_seconds: int = 300,
        stuck_timeout_minutes: int = 10,
    ) -> None:
        """
        Initialize the job status monitor.
        
        Args:
            azure_connection_string: Azure Storage connection string for queue access.
            interval_seconds: How often to check job statuses (default: 300 seconds).
            stuck_timeout_minutes: Minutes before a job is considered stuck (default: 10).
        """
        self.azure_connection_string = azure_connection_string
        self.interval_seconds = interval_seconds
        self.stuck_timeout_minutes = stuck_timeout_minutes
        self._running = False
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the background monitoring task."""
        if self._running:
            logger.warning("Job status monitor is already running")
            return
            
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            f"Job status monitor started (interval={self.interval_seconds}s, "
            f"stuck_timeout={self.stuck_timeout_minutes}min)"
        )

    async def stop(self) -> None:
        """Stop the background monitoring task."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Job status monitor stopped")

    async def _run_loop(self) -> None:
        """Main monitoring loop - runs until stopped."""
        # Wait a bit before first check to let the service fully start
        await asyncio.sleep(30)
        
        while self._running:
            try:
                await self._check_all_jobs()
            except Exception as e:
                logger.error(f"Job monitor error: {e}", exc_info=True)
            
            # Wait for next interval
            await asyncio.sleep(self.interval_seconds)

    async def _check_all_jobs(self) -> None:
        """Check job statuses across all tenants."""
        logger.debug("Starting job status check...")
        
        # Get queue statistics
        await self._log_queue_stats()
        
        # Get all tenant database names
        tenant_ids = await self._get_all_tenant_ids()
        
        if not tenant_ids:
            logger.debug("No tenant databases found")
            return
        
        total_stuck_ingestion = 0
        total_stuck_email = 0
        
        # Check each tenant database for stuck jobs
        for tenant_id in tenant_ids:
            try:
                # Check ingestion jobs
                stuck_ingestion = await self._get_stuck_jobs(tenant_id, "ingestion")
                for job in stuck_ingestion:
                    await self._mark_job_failed(
                        tenant_id=tenant_id,
                        job_id=job["job_id"],
                        job_type="ingestion",
                        error_message=f"Job timed out - no progress for {self.stuck_timeout_minutes} minutes",
                    )
                    total_stuck_ingestion += 1
                
                # Check email jobs
                stuck_email = await self._get_stuck_jobs(tenant_id, "email")
                for job in stuck_email:
                    await self._mark_job_failed(
                        tenant_id=tenant_id,
                        job_id=job["job_id"],
                        job_type="email",
                        error_message=f"Job timed out - no progress for {self.stuck_timeout_minutes} minutes",
                    )
                    total_stuck_email += 1
                    
            except Exception as e:
                logger.warning(f"Error checking jobs for tenant {tenant_id}: {e}")
                continue
        
        if total_stuck_ingestion > 0 or total_stuck_email > 0:
            logger.info(
                f"Job monitor: marked {total_stuck_ingestion} ingestion jobs "
                f"and {total_stuck_email} email jobs as failed (stuck)"
            )
        else:
            logger.debug("Job monitor: no stuck jobs found")

    async def _get_all_tenant_ids(self) -> list[str]:
        """Get all tenant IDs from existing tenant databases."""
        try:
            # Connect to postgres database to list all tenant databases
            postgres_url = _create_sqlalchemy_url("postgres")
            engine = create_engine(postgres_url)
            
            with engine.connect() as connection:
                result = connection.execute(
                    text("""
                        SELECT datname FROM pg_database 
                        WHERE datname LIKE 'google-analytics-%'
                        AND datistemplate = false
                    """)
                )
                databases = [row[0] for row in result.fetchall()]
            
            engine.dispose()
            
            # Extract tenant IDs from database names
            tenant_ids = []
            prefix = "google-analytics-"
            for db_name in databases:
                if db_name.startswith(prefix):
                    tenant_id = db_name[len(prefix):]
                    tenant_ids.append(tenant_id)
            
            return tenant_ids
            
        except Exception as e:
            logger.error(f"Error getting tenant list: {e}")
            return []

    async def _get_stuck_jobs(self, tenant_id: str, job_type: str) -> list[dict[str, Any]]:
        """
        Query database for jobs stuck in 'processing' status.
        
        Args:
            tenant_id: The tenant ID to query.
            job_type: Either 'ingestion' or 'email'.
            
        Returns:
            List of stuck job records.
        """
        table = "processing_jobs" if job_type == "ingestion" else "email_sending_jobs"
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=self.stuck_timeout_minutes)
        
        db_name = f"google-analytics-{tenant_id}"
        url = _create_sqlalchemy_url(db_name, async_driver=True)
        
        engine = create_async_engine(url, pool_size=1, max_overflow=0)
        session_maker = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        try:
            async with session_maker() as session:
                result = await session.execute(
                    text(f"""
                        SELECT job_id, tenant_id, status, updated_at
                        FROM {table}
                        WHERE status = 'processing'
                        AND updated_at < :cutoff
                    """),
                    {"cutoff": cutoff},
                )
                rows = result.mappings().all()
                return [dict(row) for row in rows]
        finally:
            await engine.dispose()

    async def _mark_job_failed(
        self,
        tenant_id: str,
        job_id: str,
        job_type: str,
        error_message: str,
    ) -> None:
        """
        Update a stuck job's status to 'failed'.
        
        Args:
            tenant_id: The tenant ID.
            job_id: The job ID to update.
            job_type: Either 'ingestion' or 'email'.
            error_message: Error message to store.
        """
        table = "processing_jobs" if job_type == "ingestion" else "email_sending_jobs"
        
        db_name = f"google-analytics-{tenant_id}"
        url = _create_sqlalchemy_url(db_name, async_driver=True)
        
        engine = create_async_engine(url, pool_size=1, max_overflow=0)
        session_maker = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        try:
            async with session_maker() as session:
                await session.execute(
                    text(f"""
                        UPDATE {table}
                        SET status = 'failed',
                            error_message = :error_message,
                            completed_at = NOW(),
                            updated_at = NOW()
                        WHERE job_id = :job_id
                    """),
                    {"job_id": job_id, "error_message": error_message},
                )
                await session.commit()
                logger.info(
                    f"Marked {job_type} job {job_id} as failed for tenant {tenant_id}: {error_message}"
                )
        except Exception as e:
            logger.error(f"Error marking job {job_id} as failed: {e}")
        finally:
            await engine.dispose()

    async def _log_queue_stats(self) -> None:
        """Log Azure Queue statistics for monitoring."""
        if not self.azure_connection_string:
            logger.debug("Azure connection string not configured, skipping queue stats")
            return
            
        queues = ["ingestion-jobs", "email-jobs"]
        
        for queue_name in queues:
            try:
                queue_client = QueueClient.from_connection_string(
                    self.azure_connection_string, queue_name
                )
                async with queue_client:
                    props = await queue_client.get_queue_properties()
                    count = props.approximate_message_count or 0
                    logger.debug(f"Queue '{queue_name}': ~{count} messages")
            except Exception as e:
                logger.debug(f"Could not get stats for queue '{queue_name}': {e}")


def create_job_monitor(
    azure_connection_string: str,
    interval_seconds: int = 300,
    stuck_timeout_minutes: int = 10,
) -> JobStatusMonitor:
    """
    Factory function to create a JobStatusMonitor instance.
    
    Args:
        azure_connection_string: Azure Storage connection string.
        interval_seconds: Polling interval in seconds (default: 300).
        stuck_timeout_minutes: Stuck job timeout in minutes (default: 10).
        
    Returns:
        Configured JobStatusMonitor instance.
    """
    return JobStatusMonitor(
        azure_connection_string=azure_connection_string,
        interval_seconds=interval_seconds,
        stuck_timeout_minutes=stuck_timeout_minutes,
    )
