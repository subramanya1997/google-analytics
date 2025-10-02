"""
Data Ingestion Service - Business Logic for Multi-Source Analytics Pipeline.

This module implements the core business logic for data ingestion operations
in the Google Analytics Intelligence System. It orchestrates the complete
data pipeline from multiple sources (BigQuery, SFTP) through transformation
to database storage with comprehensive job management and error handling.

Key Features:
- **Multi-Source Integration**: BigQuery (GA4) + SFTP (user/location data)
- **Asynchronous Processing**: Background job execution with status tracking
- **Thread Pool Optimization**: Heavy operations in dedicated thread pools
- **Error Recovery**: Graceful handling of individual data type failures
- **Progress Monitoring**: Real-time job status and record count tracking
- **Data Quality**: Comprehensive validation and transformation pipelines

Data Pipeline Architecture:
1. **Job Creation**: Initialize job record with queued status
2. **Multi-Source Extraction**: Parallel processing of BigQuery events and SFTP files
3. **Data Transformation**: Normalization, validation, and type conversion
4. **Database Storage**: Batch operations with transaction management
5. **Status Tracking**: Progress updates and completion notification

Processing Strategies:
- **Events**: Date-range based extraction from BigQuery with 6 event types
- **Users**: Excel file processing from SFTP with multi-strategy parsing
- **Locations**: Facility data processing with comprehensive cleaning
- **Error Isolation**: Individual data type failures don't stop others
- **Resource Management**: Thread pools prevent blocking of async operations

The service provides the complete business logic layer between the API
endpoints and the data access layer, handling orchestration, error
management, and performance optimization for large-scale data processing.
"""

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
    """
    Core service for multi-source analytics data ingestion and processing.
    
    This service orchestrates the complete data ingestion pipeline from multiple
    external sources through transformation to database storage. It manages job
    lifecycle, handles errors gracefully, and provides real-time status tracking
    for complex, long-running data processing operations.
    
    **Architecture Overview:**
    - Async/await for I/O-bound operations (API calls, database)
    - Thread pool executor for CPU-bound operations (data processing)
    - Multi-source integration with tenant-specific configurations
    - Comprehensive error handling with job status management
    - Performance optimization through parallel processing
    
    **Data Sources:**
    1. **BigQuery**: GA4 event data with 6 event types
    2. **SFTP**: User profiles and location data from Excel files
    
    **Key Capabilities:**
    - Job creation and lifecycle management
    - Multi-source data extraction and processing
    - Data transformation and validation
    - Error recovery and status tracking
    - Performance monitoring and optimization
    
    Attributes:
        repo: Database repository for all persistence operations
        _executor: Thread pool for heavy synchronous operations
        
    """

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

            # Process events from BigQuery
            if "events" in request.data_types:
                try:
                    logger.info(f"Processing events for job {job_id}")
                    event_results = await self._process_events_async(tenant_id, request)
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

    async def _process_events_async(
        self, tenant_id: str, request: CreateIngestionJobRequest
    ) -> Dict[str, int]:
        """Process all event types from BigQuery asynchronously."""
        try:
            # Initialize BigQuery client using tenant configuration from database
            bigquery_client = await get_tenant_bigquery_client(tenant_id)

            if not bigquery_client:
                raise ValueError(
                    f"BigQuery configuration not found for tenant {tenant_id}"
                )

            # Get all events for date range - run sync operation in thread pool
            loop = asyncio.get_event_loop()
            events_by_type = await loop.run_in_executor(
                self._executor,
                bigquery_client.get_date_range_events,
                request.start_date.isoformat(),
                request.end_date.isoformat()
            )

            results = {}

            # Process each event type
            for event_type, events_data in events_by_type.items():
                try:
                    if events_data:
                        # Use async method directly
                        count = await self.repo.replace_event_data(
                            tenant_id,
                            event_type,
                            request.start_date,
                            request.end_date,
                            events_data,
                        )
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


    async def _process_users(self, tenant_id: str) -> int:
        """Process users from SFTP."""
        try:
            # Create a fresh Azure SFTP client using tenant configuration from database
            sftp_client = await get_tenant_sftp_client(tenant_id)

            if not sftp_client:
                logger.warning(f"SFTP configuration not found for tenant {tenant_id}, skipping user processing")
                return 0

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
                        elif isinstance(value, pd.Timestamp):
                            # Convert pandas Timestamp to Python datetime
                            cleaned_record[key] = value.to_pydatetime()
                        else:
                            cleaned_record[key] = value
                    cleaned_users.append(cleaned_record)

                # Use async database operation directly
                count = await self.repo.upsert_users(tenant_id, cleaned_users)
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
                sftp_client = await get_tenant_sftp_client(tenant_id)
                if sftp_client:
                    logger.info(
                        f"Attempting to get locations from SFTP for tenant {tenant_id}"
                    )
                    locations_data = await sftp_client.get_latest_locations_data()
                else:
                    logger.warning(
                        f"SFTP configuration not found for tenant {tenant_id}, skipping location processing"
                    )
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
                        elif isinstance(value, pd.Timestamp):
                            # Convert pandas Timestamp to Python datetime
                            cleaned_record[key] = value.to_pydatetime()
                        else:
                            cleaned_record[key] = value
                    cleaned_locations.append(cleaned_record)
                
                # Use async database operation directly
                count = await self.repo.upsert_locations(tenant_id, cleaned_locations)
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