import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from typing import Any, Dict

import pandas as pd
from loguru import logger

from services.data_service.api.v1.models import CreateIngestionJobRequest
from services.data_service.clients.tenant_client_factory import (
    get_tenant_sftp_client,
    get_tenant_bigquery_client,
)
from services.data_service.database.sqlalchemy_repository import SqlAlchemyRepository


class IngestionService:
    """Service for handling analytics data ingestion jobs."""

    def __init__(self):
        self.repo = SqlAlchemyRepository()
        # Thread pool for heavy synchronous operations
        self._executor = ThreadPoolExecutor(
            max_workers=2,  # Limit concurrent heavy operations
            thread_name_prefix="ingestion-worker"
        )
    
    def __del__(self):
        """Cleanup thread pool on destruction."""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)

    async def create_job(
        self, job_id: str, tenant_id: str, request: CreateIngestionJobRequest
    ) -> Dict[str, Any]:
        """Create a new ingestion job."""
        try:
            job_data = {
                "job_id": job_id,
                "tenant_id": tenant_id,  # Repository will handle UUID conversion
                "status": "queued",
                "data_types": request.data_types,
                "start_date": request.start_date,  # Pass as date object, not string
                "end_date": request.end_date,  # Pass as date object, not string
            }

            job = await self.repo.create_processing_job(job_data)
            logger.info(f"Created processing job {job_id}")
            return job

        except Exception as e:
            logger.error(f"Error creating processing job {job_id}: {e}")
            raise

    async def run_job(
        self, job_id: str, tenant_id: str, request: CreateIngestionJobRequest
    ) -> Dict[str, Any]:
        """Run the data ingestion job."""
        try:
            # Update job status to processing
            await self.repo.update_job_status(job_id, "processing", started_at=datetime.now())

            results = {
                "purchase": 0,
                "add_to_cart": 0,
                "page_view": 0,
                "view_search_results": 0,
                "no_search_results": 0,
                "view_item": 0,
                "users_processed": 0,
                "locations_processed": 0,
            }

            # Process events from BigQuery in thread pool to avoid blocking
            if "events" in request.data_types:
                try:
                    logger.info(f"Processing events for job {job_id}")
                    # Run the synchronous event processing in a thread pool
                    loop = asyncio.get_event_loop()
                    event_results = await loop.run_in_executor(
                        self._executor, 
                        self._process_events_sync, 
                        tenant_id, 
                        request
                    )
                    results.update(event_results)

                except Exception as e:
                    logger.error(f"Error processing events: {e}")
                    raise

            # Process users from SFTP
            if "users" in request.data_types:
                try:
                    logger.info(f"Processing users for job {job_id}")
                    users_count = await self._process_users(tenant_id)
                    results["users_processed"] = users_count

                except Exception as e:
                    logger.error(f"Error processing users: {e}")
                    raise

            # Process locations from SFTP
            if "locations" in request.data_types:
                try:
                    logger.info(f"Processing locations for job {job_id}")
                    locations_count = await self._process_locations(tenant_id)
                    results["locations_processed"] = locations_count

                except Exception as e:
                    logger.error(f"Error processing locations: {e}")
                    raise

            # Update job status to completed
            await self.repo.update_job_status(
                job_id,
                "completed",
                completed_at=datetime.now(),
                records_processed=results,
            )

            logger.info(f"Completed processing job {job_id}: {results}")
            return results

        except Exception as e:
            # Update job status to failed
            await self.repo.update_job_status(
                job_id, "failed", completed_at=datetime.now(), error_message=str(e)
            )
            logger.error(f"Failed processing job {job_id}: {e}")
            raise

    def _process_events_sync(
        self, tenant_id: str, request: CreateIngestionJobRequest
    ) -> Dict[str, int]:
        """Process all event types from BigQuery (runs in thread pool)."""
        try:
            # Create a new repository instance for this thread to avoid connection sharing
            thread_repo = SqlAlchemyRepository()
            
            # Initialize BigQuery client using tenant configuration from database
            bigquery_client = get_tenant_bigquery_client(tenant_id)

            if not bigquery_client:
                raise ValueError(
                    f"BigQuery configuration not found for tenant {tenant_id}"
                )

            # Get all events for date range
            events_by_type = bigquery_client.get_date_range_events(
                request.start_date.isoformat(), request.end_date.isoformat()
            )

            results = {}

            # Process each event type
            for event_type, events_data in events_by_type.items():
                try:
                    if events_data:
                        # Need to run async method in sync context
                        count = asyncio.run(thread_repo.replace_event_data(
                            tenant_id,
                            event_type,
                            request.start_date,
                            request.end_date,
                            events_data,
                        ))
                        results[event_type] = count
                        logger.info(f"Processed {count} {event_type} events")
                    else:
                        results[event_type] = 0
                        logger.info(f"No {event_type} events found")

                except Exception as e:
                    logger.error(f"Error processing {event_type} events: {e}")
                    results[event_type] = 0

            return results

        except Exception as e:
            logger.error(f"Error processing BigQuery events: {e}")
            raise

    def _upsert_users_sync(self, tenant_id: str, users_data: list) -> int:
        """Synchronous user upsert operation (runs in thread pool)."""
        # Create a new repository instance for this thread
        thread_repo = SqlAlchemyRepository()
        return asyncio.run(thread_repo.upsert_users(tenant_id, users_data))
    
    def _upsert_locations_sync(self, tenant_id: str, locations_data: list) -> int:
        """Synchronous location upsert operation (runs in thread pool)."""
        # Create a new repository instance for this thread
        thread_repo = SqlAlchemyRepository()
        return asyncio.run(thread_repo.upsert_locations(tenant_id, locations_data))

    async def _process_users(self, tenant_id: str) -> int:
        """Process users from SFTP."""
        try:
            # Create a fresh Azure SFTP client using tenant configuration from database
            sftp_client = get_tenant_sftp_client(tenant_id)

            if not sftp_client:
                raise ValueError(f"SFTP configuration not found for tenant {tenant_id}")

            # Get users data (Azure client handles connections internally)
            users_data = await sftp_client.get_latest_users_data()

            if users_data is not None and len(users_data) > 0:
                # Clean the data: replace NaN values with None
                import numpy as np

                users_data = users_data.replace({np.nan: None})

                # Convert DataFrame to list of dictionaries
                users_list = users_data.to_dict("records")

                # Clean the records for JSON compatibility
                cleaned_users = []
                for record in users_list:
                    cleaned_record = {}
                    for key, value in record.items():
                        if (
                            pd.isna(value)
                            if hasattr(pd, "isna")
                            else (value is None or str(value) == "nan")
                        ):
                            cleaned_record[key] = None
                        else:
                            cleaned_record[key] = value
                    cleaned_users.append(cleaned_record)

                # Run the database operation in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                count = await loop.run_in_executor(
                    self._executor,
                    self._upsert_users_sync,
                    tenant_id,
                    cleaned_users
                )
                logger.info(f"Processed {count} users from SFTP")
                return count
            else:
                logger.info("No users data found")
                return 0

        except Exception as e:
            logger.error(f"Error processing users: {e}")
            raise

    async def _process_locations(self, tenant_id: str) -> int:
        """Process locations from SFTP using tenant configuration, with local fallback."""
        try:
            from pathlib import Path

            import pandas as pd

            locations_data = None

            # First try to get from SFTP using tenant configuration
            try:
                sftp_client = get_tenant_sftp_client(tenant_id)
                if sftp_client:
                    logger.info(
                        f"Attempting to get locations from SFTP for tenant {tenant_id}"
                    )
                    locations_data = await sftp_client.get_latest_locations_data()
            except Exception as e:
                logger.warning(
                    f"Failed to get locations from SFTP for tenant {tenant_id}: {e}"
                )

            # Fallback to local file if SFTP failed or no data
                # Successfully got data from SFTP - process it
            if locations_data is not None and len(locations_data) > 0:
                # Clean the data: replace NaN values with None
                import numpy as np
                
                locations_data = locations_data.replace({np.nan: None})
                
                # Convert DataFrame to list of dictionaries
                locations_list = locations_data.to_dict("records")
                
                # Clean the records for JSON compatibility
                cleaned_locations = []
                for record in locations_list:
                    cleaned_record = {}
                    for key, value in record.items():
                        if (
                            pd.isna(value)
                            if hasattr(pd, "isna")
                            else (value is None or str(value) == "nan")
                        ):
                            cleaned_record[key] = None
                        else:
                            cleaned_record[key] = value
                    cleaned_locations.append(cleaned_record)
                
                # Run the database operation in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                count = await loop.run_in_executor(
                    self._executor,
                    self._upsert_locations_sync,
                    tenant_id,
                    cleaned_locations
                )
                logger.info(f"Processed {count} locations from SFTP")
                return count
            else:
                logger.info("No locations data received from SFTP")
                return 0

        except Exception as e:
            logger.error(f"Error processing locations: {e}")
            raise

    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status."""
        job = await self.repo.get_job_by_id(job_id)
        if not job:
            raise Exception(f"Job {job_id} not found")
        return job

    async def get_tenant_summary(
        self, tenant_id: str, start_date: date = None, end_date: date = None
    ) -> Dict[str, Any]:
        """Get analytics summary for a tenant."""
        return await self.repo.get_analytics_summary(tenant_id, start_date, end_date)

    async def get_data_availability(self, tenant_id: str) -> Dict[str, Any]:
        """Get the date range of available data for a tenant."""
        return await self.repo.get_data_availability(tenant_id)

    async def get_data_availability_with_breakdown(self, tenant_id: str) -> Dict[str, Any]:
        """Get both data availability summary and detailed breakdown in one call."""
        return await self.repo.get_data_availability_with_breakdown(tenant_id)

    async def get_tenant_jobs(self, tenant_id: str, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """Get job history for a tenant."""
        return await self.repo.get_tenant_jobs(tenant_id, limit, offset)