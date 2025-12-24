"""
Data ingestion service for Azure Functions.

Adapted from the FastAPI data_service for use in serverless Azure Functions.
Handles BigQuery event extraction and SFTP user/location downloads.
"""

import asyncio
from datetime import date, datetime
from typing import Any, Dict, List

import pandas as pd
from loguru import logger

from clients import get_tenant_bigquery_client, get_tenant_sftp_client
from shared.database import create_repository
from shared.models import CreateIngestionJobRequest


class IngestionService:
    """
    Service for handling analytics data ingestion jobs.
    
    Each tenant has their own isolated database for SOC2 compliance.
    """

    def __init__(self, tenant_id: str):
        """
        Initialize ingestion service for a specific tenant.
        
        Args:
            tenant_id: The tenant ID - determines which database to connect to.
        """
        self.tenant_id = tenant_id
        self.repo = create_repository(tenant_id)

    async def run_job_safe(
        self, job_id: str, tenant_id: str, request: CreateIngestionJobRequest
    ) -> None:
        """
        Wrapper that ensures job status is always updated, even on unexpected failures.
        Includes timeout monitoring to prevent jobs from running indefinitely.
        """
        try:
            # Set a 30-minute timeout for medium date ranges
            await asyncio.wait_for(
                self.run_job(job_id, tenant_id, request),
                timeout=1800  # 30 minutes
            )
        except asyncio.TimeoutError:
            logger.error(f"Job {job_id} timed out after 30 minutes")
            try:
                await self.repo.update_job_status(
                    job_id, "failed",
                    completed_at=datetime.now(),
                    error_message="Job timed out after 30 minutes"
                )
            except Exception as update_error:
                logger.error(f"Failed to update job status after timeout: {update_error}")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Job failed: {error_msg}", exc_info=True)
            
            if not error_msg or error_msg == "":
                error_msg = f"Job failed unexpectedly. Please contact administrator with job ID: {job_id}"
            
            try:
                await self.repo.update_job_status(
                    job_id, "failed",
                    completed_at=datetime.now(),
                    error_message=error_msg
                )
            except Exception as update_error:
                logger.error(f"Failed to update job status: {update_error}")

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
            warnings = []  # Track partial failures

            # Process events from BigQuery
            if "events" in request.data_types:
                try:
                    logger.info(f"Processing events for job {job_id}")
                    await self.repo.update_job_status(job_id, "processing", progress={"current": "events"})
                    event_results = await self._process_events_async(tenant_id, request)
                    results.update(event_results)

                except Exception as e:
                    logger.error(f"Failed to extract events from BigQuery: {e}", exc_info=True)
                    root_cause = str(e)
                    if "nodename nor servname" in root_cause or "gaierror" in root_cause:
                        raise Exception("Failed to extract events from BigQuery - Network/DNS error. Please check BigQuery configuration and network connectivity.") from e
                    elif "credentials" in root_cause.lower() or "authentication" in root_cause.lower():
                        raise Exception("Failed to extract events from BigQuery - Authentication error. Please check service account credentials.") from e
                    else:
                        raise Exception(f"Failed to extract events from BigQuery - {type(e).__name__}: {str(e)}") from e

            # Process users from SFTP
            if "users" in request.data_types:
                try:
                    logger.info(f"Processing users for job {job_id}")
                    await self.repo.update_job_status(job_id, "processing", progress={"current": "users"})
                    users_count, users_errors = await self._process_users(tenant_id)
                    results["users_processed"] = users_count
                    if users_errors > 0:
                        warnings.append(f"Users: {users_errors} batch errors during upsert")

                except Exception as e:
                    logger.error(f"Failed to download/process users: {e}", exc_info=True)
                    root_cause = str(e)
                    if "nodename nor servname" in root_cause or "gaierror" in root_cause:
                        raise Exception("Failed to download users report from SFTP - Network/DNS error. Please verify SFTP hostname in tenant configuration.") from e
                    elif "authentication" in root_cause.lower() or "permission denied" in root_cause.lower():
                        raise Exception("Failed to download users report from SFTP - Authentication error. Please check SFTP credentials.") from e
                    elif "no such file" in root_cause.lower() or "file not found" in root_cause.lower():
                        raise Exception("Failed to download users report from SFTP - File not found. Please verify the file exists on the server.") from e
                    else:
                        raise Exception(f"Failed to download users report from SFTP - {type(e).__name__}: {str(e)}") from e

            # Process locations from SFTP
            if "locations" in request.data_types:
                try:
                    logger.info(f"Processing locations for job {job_id}")
                    await self.repo.update_job_status(job_id, "processing", progress={"current": "locations"})
                    locations_count, locations_errors = await self._process_locations(tenant_id)
                    results["locations_processed"] = locations_count
                    if locations_errors > 0:
                        warnings.append(f"Locations: {locations_errors} batch errors during upsert")

                except Exception as e:
                    logger.error(f"Failed to download/process locations: {e}", exc_info=True)
                    root_cause = str(e)
                    if "nodename nor servname" in root_cause or "gaierror" in root_cause:
                        raise Exception("Failed to download locations data from SFTP - Network/DNS error. Please verify SFTP hostname in tenant configuration.") from e
                    elif "authentication" in root_cause.lower() or "permission denied" in root_cause.lower():
                        raise Exception("Failed to download locations data from SFTP - Authentication error. Please check SFTP credentials.") from e
                    elif "no such file" in root_cause.lower() or "file not found" in root_cause.lower():
                        raise Exception("Failed to download locations data from SFTP - File not found. Please verify the file exists on the server.") from e
                    else:
                        raise Exception(f"Failed to download locations data from SFTP - {type(e).__name__}: {str(e)}") from e

            # Log any warnings but keep status as completed
            if warnings:
                logger.warning(f"Job {job_id} completed with warnings: {warnings}")
                results["warnings"] = warnings

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
        """Process all event types from BigQuery."""
        try:
            logger.info(f"Fetching BigQuery configuration for tenant {tenant_id}")
            bigquery_client = await get_tenant_bigquery_client(tenant_id)

            if not bigquery_client:
                raise ValueError(f"BigQuery configuration not found for tenant {tenant_id}")

            # Get all events for date range
            logger.info(f"Starting BigQuery extraction for {request.start_date} to {request.end_date}")
            events_by_type = bigquery_client.get_date_range_events(
                request.start_date.isoformat(),
                request.end_date.isoformat()
            )

            results = {}

            # Process each event type
            for event_type, events_data in events_by_type.items():
                try:
                    if events_data:
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

    async def _process_users(self, tenant_id: str) -> tuple:
        """Process users from SFTP. Returns (count, errors) tuple."""
        try:
            logger.info(f"Fetching SFTP configuration for tenant {tenant_id}")
            sftp_client = await get_tenant_sftp_client(tenant_id)

            if not sftp_client:
                logger.warning(f"SFTP configuration not found for tenant {tenant_id}, skipping user processing")
                return 0, 0

            # Get users data (synchronous method)
            logger.info("Connecting to SFTP to download users data")
            users_data = sftp_client._get_users_data_sync()

            if users_data is not None and len(users_data) > 0:
                import numpy as np
                users_data = users_data.replace({np.nan: None})

                users_list = users_data.to_dict("records")

                # Clean the records for JSON compatibility
                cleaned_users = []
                for record in users_list:
                    cleaned_record = {}
                    for key, value in record.items():
                        if pd.isna(value) if hasattr(pd, "isna") else (value is None or str(value) == "nan"):
                            cleaned_record[key] = None
                        elif isinstance(value, pd.Timestamp):
                            cleaned_record[key] = value.to_pydatetime()
                        else:
                            cleaned_record[key] = value
                    cleaned_users.append(cleaned_record)

                count, errors = await self.repo.upsert_users(tenant_id, cleaned_users)
                logger.info(f"Processed {count} users from SFTP ({errors} batch errors)")
                return count, errors
            else:
                logger.info("No users data found")
                return 0, 0

        except Exception as e:
            logger.error(f"Error processing users: {e}")
            raise

    async def _process_locations(self, tenant_id: str) -> tuple:
        """Process locations from SFTP. Returns (count, errors) tuple."""
        try:
            logger.info(f"Fetching SFTP configuration for tenant {tenant_id}")
            sftp_client = await get_tenant_sftp_client(tenant_id)
            
            if not sftp_client:
                logger.warning(f"SFTP configuration not found for tenant {tenant_id}, skipping location processing")
                return 0, 0

            logger.info(f"Connecting to SFTP to download locations data for tenant {tenant_id}")
            locations_data = sftp_client._get_locations_data_sync()

            if locations_data is not None and len(locations_data) > 0:
                import numpy as np
                locations_data = locations_data.replace({np.nan: None})

                locations_list = locations_data.to_dict("records")

                # Clean the records for JSON compatibility
                cleaned_locations = []
                for record in locations_list:
                    cleaned_record = {}
                    for key, value in record.items():
                        if pd.isna(value) if hasattr(pd, "isna") else (value is None or str(value) == "nan"):
                            cleaned_record[key] = None
                        elif isinstance(value, pd.Timestamp):
                            cleaned_record[key] = value.to_pydatetime()
                        else:
                            cleaned_record[key] = value
                    cleaned_locations.append(cleaned_record)

                count, errors = await self.repo.upsert_locations(tenant_id, cleaned_locations)
                logger.info(f"Processed {count} locations from SFTP ({errors} batch errors)")
                return count, errors
            else:
                logger.info("No locations data received from SFTP")
                return 0, 0

        except Exception as e:
            logger.error(f"Error processing locations: {e}")
            raise

