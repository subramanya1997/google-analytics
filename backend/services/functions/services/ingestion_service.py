"""
Data ingestion service for Azure Functions.

Adapted from the FastAPI data_service for use in serverless Azure Functions.
Handles BigQuery event and user extraction, and SFTP location downloads.
"""

import asyncio
from datetime import datetime
import logging
from typing import Any
import numpy as np
from clients import get_tenant_bigquery_client, get_tenant_bigquery_config, get_tenant_sftp_client
import pandas as pd
from shared.database import create_repository
from shared.models import CreateIngestionJobRequest

logger = logging.getLogger(__name__)


class IngestionService:
    """
    Service for handling analytics data ingestion jobs from BigQuery and SFTP.

    This service orchestrates the complete data ingestion workflow, including:
    - BigQuery event extraction (purchases, cart events, page views, searches, etc.)
    - SFTP user data downloads and processing
    - SFTP location data downloads and processing
    - Database updates with proper tenant isolation

    Each tenant has their own isolated database (google-analytics-{tenant_id})
    for SOC2 compliance and data isolation. The service handles job status
    tracking, error handling, and timeout management.

    Attributes:
        tenant_id: The tenant identifier used for database routing.
        repo: Repository instance for database operations.

    Example:
        >>> service = IngestionService("550e8400-e29b-41d4-a716-446655440000")
        >>> await service.run_job_safe(job_id, tenant_id, request)
    """

    def __init__(self, tenant_id: str) -> None:
        """
        Initialize ingestion service for a specific tenant.

        Creates a repository instance configured for the tenant's isolated database.
        The tenant_id determines which database connection to use, ensuring
        complete data isolation between tenants.

        Args:
            tenant_id: The tenant ID (UUID string) that determines which database
                      to connect to. Format: google-analytics-{tenant_id}.

        Raises:
            ValueError: If tenant_id is invalid or database connection fails.
        """
        self.tenant_id = tenant_id
        self.repo = create_repository(tenant_id)

    async def run_job_safe(
        self, job_id: str, tenant_id: str, request: CreateIngestionJobRequest
    ) -> None:
        """
        Execute ingestion job with comprehensive error handling and timeout protection.

        This wrapper function ensures job status is always updated in the database,
        even when unexpected failures occur. It implements a 30-minute timeout
        to prevent jobs from running indefinitely and consuming resources.

        The function catches all exceptions, logs them appropriately, and updates
        the job status to "failed" with a descriptive error message. This ensures
        the FastAPI service can track job completion status reliably.

        Args:
            job_id: Unique identifier for the ingestion job.
            tenant_id: Tenant ID for database routing and isolation.
            request: Ingestion job request containing date range and data types.

        Returns:
            None: Function completes asynchronously. Job status is persisted to database.

        Raises:
            asyncio.TimeoutError: If job execution exceeds 30 minutes.
            Exception: Any exceptions from run_job are caught and logged.

        Note:
            - Timeout is set to 1800 seconds (30 minutes)
            - Job status is always updated, even on timeout or failure
            - Error messages are sanitized and stored in database
            - Network/DNS errors are detected and reported with helpful messages

        Example:
            >>> request = CreateIngestionJobRequest(
            ...     start_date=date(2024, 1, 1),
            ...     end_date=date(2024, 1, 7),
            ...     data_types=["events", "users"]
            ... )
            >>> await service.run_job_safe("job_123", tenant_id, request)
        """
        try:
            # Set a 30-minute timeout for medium date ranges
            await asyncio.wait_for(
                self.run_job(job_id, tenant_id, request),
                timeout=1800,  # 30 minutes
            )
        except asyncio.TimeoutError:
            logger.error(f"Job {job_id} timed out after 30 minutes")
            try:
                await self.repo.update_job_status(
                    job_id,
                    "failed",
                    completed_at=datetime.now(),
                    error_message="Job timed out after 30 minutes",
                )
            except Exception as update_error:
                logger.error(
                    f"Failed to update job status after timeout: {update_error}"
                )
        except Exception as e:
            error_msg = str(e)
            logger.exception(f"Job failed: {error_msg}")

            if not error_msg or error_msg == "":
                error_msg = f"Job failed unexpectedly. Please contact administrator with job ID: {job_id}"

            try:
                await self.repo.update_job_status(
                    job_id,
                    "failed",
                    completed_at=datetime.now(),
                    error_message=error_msg,
                )
            except Exception as update_error:
                logger.error(f"Failed to update job status: {update_error}")

    async def run_job(
        self, job_id: str, tenant_id: str, request: CreateIngestionJobRequest
    ) -> dict[str, Any]:
        """
        Execute the complete data ingestion job workflow.

        This method orchestrates the ingestion of multiple data types:
        1. Events from BigQuery (purchase, add_to_cart, page_view, etc.)
        2. Users from SFTP (Excel file download and processing)
        3. Locations from SFTP (Excel file download and processing)

        The method updates job status throughout execution and handles partial
        failures gracefully. If one data type fails, others can still succeed,
        with warnings tracked in the results.

        Args:
            job_id: Unique identifier for tracking this job.
            tenant_id: Tenant ID for multi-tenant isolation.
            request: Ingestion request specifying date range and data types to process.

        Returns:
            dict[str, Any]: Results dictionary containing:
                - Event type counts (purchase, add_to_cart, page_view, etc.)
                - users_processed: Number of users successfully processed
                - locations_processed: Number of locations successfully processed
                - warnings: List of warning messages for partial failures

        Raises:
            ValueError: If BigQuery configuration is missing for events processing.
            Exception: Various exceptions for network, authentication, or file errors.
                      Error messages are enhanced with context for debugging.

        Note:
            - Job status is updated to "processing" at start
            - Progress is tracked per data type (events, users, locations)
            - Partial failures result in warnings, not complete failure
            - Job status is updated to "completed" or "failed" at end
            - All database operations use tenant-specific connections

        Example:
            >>> request = CreateIngestionJobRequest(
            ...     start_date=date(2024, 1, 1),
            ...     end_date=date(2024, 1, 7),
            ...     data_types=["events", "users"]
            ... )
            >>> results = await service.run_job("job_123", tenant_id, request)
            >>> results["purchase"]
            150
            >>> results["users_processed"]
            500
        """
        try:
            # Update job status to processing
            await self.repo.update_job_status(
                job_id, "processing", started_at=datetime.now()
            )

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
                    await self.repo.update_job_status(
                        job_id, "processing", progress={"current": "events"}
                    )
                    event_results, event_warnings = await self._process_events_async(tenant_id, request)
                    results.update(event_results)
                    warnings.extend(event_warnings)

                except Exception as e:
                    logger.error(
                        f"Failed to extract events from BigQuery: {e}", exc_info=True
                    )
                    root_cause = str(e)
                    if (
                        "nodename nor servname" in root_cause
                        or "gaierror" in root_cause
                    ):
                        msg = "Failed to extract events from BigQuery - Network/DNS error. Please check BigQuery configuration and network connectivity."
                        raise Exception(
                            msg
                        ) from e
                    if (
                        "credentials" in root_cause.lower()
                        or "authentication" in root_cause.lower()
                    ):
                        msg = "Failed to extract events from BigQuery - Authentication error. Please check service account credentials."
                        raise Exception(
                            msg
                        ) from e
                    msg = f"Failed to extract events from BigQuery - {type(e).__name__}: {e!s}"
                    raise Exception(
                        msg
                    ) from e

            # Process users from BigQuery (or SFTP fallback)
            if "users" in request.data_types:
                try:
                    logger.info(f"Processing users for job {job_id}")
                    await self.repo.update_job_status(
                        job_id, "processing", progress={"current": "users"}
                    )
                    users_count, users_errors = await self._process_users(tenant_id)
                    results["users_processed"] = users_count
                    if users_errors > 0:
                        warnings.append(
                            f"Users: {users_errors} batch errors during upsert"
                        )

                except Exception as e:
                    logger.error(
                        f"Failed to process users: {e}", exc_info=True
                    )
                    root_cause = str(e)
                    if (
                        "nodename nor servname" in root_cause
                        or "gaierror" in root_cause
                    ):
                        msg = "Failed to process users - Network/DNS error. Please check BigQuery/SFTP configuration and network connectivity."
                        raise Exception(msg) from e
                    if (
                        "credentials" in root_cause.lower()
                        or "authentication" in root_cause.lower()
                        or "permission denied" in root_cause.lower()
                    ):
                        msg = "Failed to process users - Authentication error. Please check service account or SFTP credentials."
                        raise Exception(msg) from e
                    msg = f"Failed to process users - {type(e).__name__}: {e!s}"
                    raise Exception(msg) from e

            # Process locations from SFTP
            if "locations" in request.data_types:
                try:
                    logger.info(f"Processing locations for job {job_id}")
                    await self.repo.update_job_status(
                        job_id, "processing", progress={"current": "locations"}
                    )
                    locations_count, locations_errors = await self._process_locations(
                        tenant_id
                    )
                    results["locations_processed"] = locations_count
                    if locations_errors > 0:
                        warnings.append(
                            f"Locations: {locations_errors} batch errors during upsert"
                        )

                except Exception as e:
                    logger.error(
                        f"Failed to download/process locations: {e}", exc_info=True
                    )
                    root_cause = str(e)
                    if (
                        "nodename nor servname" in root_cause
                        or "gaierror" in root_cause
                    ):
                        msg = "Failed to download locations data from SFTP - Network/DNS error. Please verify SFTP hostname in tenant configuration."
                        raise Exception(
                            msg
                        ) from e
                    if (
                        "authentication" in root_cause.lower()
                        or "permission denied" in root_cause.lower()
                    ):
                        msg = "Failed to download locations data from SFTP - Authentication error. Please check SFTP credentials."
                        raise Exception(
                            msg
                        ) from e
                    if (
                        "no such file" in root_cause.lower()
                        or "file not found" in root_cause.lower()
                    ):
                        msg = "Failed to download locations data from SFTP - File not found. Please verify the file exists on the server."
                        raise Exception(
                            msg
                        ) from e
                    msg = f"Failed to download locations data from SFTP - {type(e).__name__}: {e!s}"
                    raise Exception(
                        msg
                    ) from e

            if warnings:
                logger.warning(f"Job {job_id} completed with warnings: {warnings}")
                results["warnings"] = warnings

            final_status = "completed_with_warnings" if warnings else "completed"
            await self.repo.update_job_status(
                job_id,
                final_status,
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
    ) -> tuple[dict[str, int], list[str]]:
        """
        Extract and process all event types from BigQuery for the specified date range.

        This method queries BigQuery for GA4 events across multiple event types:
        - purchase: Completed purchase transactions
        - add_to_cart: Items added to shopping cart
        - page_view: Page view events
        - view_search_results: Successful search queries
        - no_search_results: Failed search queries
        - view_item: Product detail page views

        Events are extracted in parallel where possible and then inserted into
        the tenant's database, replacing any existing data for the date range.

        Args:
            tenant_id: Tenant ID for BigQuery configuration lookup and database routing.
            request: Ingestion request containing start_date, end_date, and data_types.

        Returns:
            dict[str, int]: Dictionary mapping event type names to record counts.
                          Example: {"purchase": 150, "add_to_cart": 300, ...}

        Raises:
            ValueError: If BigQuery configuration is not found for the tenant.
            Exception: Various BigQuery errors (network, authentication, query errors)
                      with enhanced error messages for debugging.

        Note:
            - Uses tenant-specific BigQuery credentials from database
            - Events are extracted for the entire date range in one query per type
            - Existing events for the date range are deleted before insertion
            - Each event type is processed independently (failures don't cascade)
            - Raw event data is preserved in JSON format for future analysis

        Example:
            >>> request = CreateIngestionJobRequest(
            ...     start_date=date(2024, 1, 1),
            ...     end_date=date(2024, 1, 7),
            ...     data_types=["events"]
            ... )
            >>> results = await service._process_events_async(tenant_id, request)
            >>> results["purchase"]
            150
        """
        try:
            logger.info(f"Fetching BigQuery configuration for tenant {tenant_id}")
            bigquery_client = await get_tenant_bigquery_client(tenant_id)

            if not bigquery_client:
                msg = f"BigQuery configuration not found for tenant {tenant_id}"
                raise ValueError(
                    msg
                )

            # Get all events for date range
            logger.info(
                f"Starting BigQuery extraction for {request.start_date} to {request.end_date}"
            )
            events_by_type = bigquery_client.get_date_range_events(
                request.start_date.isoformat(), request.end_date.isoformat()
            )

            # Reclassify mistagged search events: the GA4 implementation fires
            # no_search_results for ALL searches on /searchPage.action regardless
            # of outcome. We use page title to distinguish genuinely failed searches
            # from successful ones that were mistagged.
            events_by_type = self._reclassify_search_events(events_by_type)

            results: dict[str, int] = {}
            event_warnings: list[str] = []

            async def _insert_event_type_safe(
                et: str, data: list[dict[str, Any]]
            ) -> tuple[str, int, str | None]:
                try:
                    if data:
                        count = await self.repo.replace_event_data(
                            tenant_id,
                            et,
                            request.start_date,
                            request.end_date,
                            data,
                        )
                        logger.info(f"Processed {count} {et} events")
                        return et, count, None
                    logger.info(f"No {et} events found")
                    return et, 0, None
                except Exception as e:
                    logger.error(f"Failed to insert {et} events: {e}")
                    return et, 0, str(e)

            tasks = [
                _insert_event_type_safe(et, data)
                for et, data in events_by_type.items()
            ]

            for coro in asyncio.as_completed(tasks):
                event_type, count, error = await coro
                results[event_type] = count
                if error:
                    event_warnings.append(f"{event_type}: {error}")

            return results, event_warnings

        except Exception as e:
            logger.error(f"Error processing BigQuery events: {e}")
            raise

    @staticmethod
    def _reclassify_search_events(
        events_by_type: dict[str, list[dict[str, Any]]]
    ) -> dict[str, list[dict[str, Any]]]:
        """Reclassify mistagged no_search_results events into view_search_results.

        The GA4 implementation on the site fires ``no_search_results`` for all
        searches on ``/searchPage.action``, regardless of whether results were
        found.  Events whose page title does NOT contain "No Results Found" are
        actually successful searches and belong in ``view_search_results``.

        For reclassified events the ``param_no_search_results_term`` key is
        renamed to ``param_search_term`` so the record matches the
        ``view_search_results`` table schema.
        """
        NO_RESULTS_MARKER = "No Results Found"

        no_search = events_by_type.get("no_search_results", [])
        if not no_search:
            return events_by_type

        genuinely_failed: list[dict[str, Any]] = []
        reclassified: list[dict[str, Any]] = []

        for event in no_search:
            title = event.get("param_page_title") or ""
            if NO_RESULTS_MARKER in title:
                genuinely_failed.append(event)
            else:
                converted = dict(event)
                converted["param_search_term"] = converted.pop(
                    "param_no_search_results_term", None
                )
                reclassified.append(converted)

        events_by_type["no_search_results"] = genuinely_failed

        existing_vsr = events_by_type.get("view_search_results", [])
        events_by_type["view_search_results"] = existing_vsr + reclassified

        if reclassified:
            logger.info(
                f"Reclassified {len(reclassified)} mistagged no_search_results "
                f"events as view_search_results (genuinely failed: {len(genuinely_failed)})"
            )

        return events_by_type

    async def _process_users(self, tenant_id: str) -> tuple[int, int]:
        """
        Extract user data from BigQuery and upsert into the users table.

        Requires `bigquery_user_table` to be configured in tenant_config.

        Args:
            tenant_id: Tenant ID for configuration lookup and database routing.

        Returns:
            tuple[int, int]: (count of users processed, count of batch errors)
        """
        try:
            bq_config = await get_tenant_bigquery_config(tenant_id)
            user_table = bq_config.get("user_table") if bq_config else None

            if not user_table:
                logger.warning(
                    f"No bigquery_user_table configured for tenant {tenant_id}, skipping user processing"
                )
                return 0, 0

            logger.info(f"Extracting users from BigQuery table: {user_table}")
            bigquery_client = await get_tenant_bigquery_client(tenant_id)
            if not bigquery_client:
                msg = f"BigQuery client could not be created for tenant {tenant_id}"
                raise ValueError(msg)

            users_list = bigquery_client.extract_users(user_table)

            if users_list:
                count, errors = await self.repo.upsert_users(tenant_id, users_list)
                logger.info(
                    f"Processed {count} users from BigQuery ({errors} batch errors)"
                )
                return count, errors

            logger.info("No users found in BigQuery table")
            return 0, 0

        except Exception as e:
            logger.error(f"Error processing users: {e}")
            raise

    async def _process_locations(self, tenant_id: str) -> tuple[int, int]:
        """
        Download and process location/warehouse data from SFTP server.

        This method downloads the locations Excel file from the configured SFTP server,
        parses it using pandas, normalizes column names to match the database schema,
        and performs batch upserts into the tenant's locations table.

        The method handles various Excel file formats and column name variations,
        ensuring compatibility with different source systems. Location data is cleaned
        and validated before insertion.

        Args:
            tenant_id: Tenant ID for SFTP configuration lookup and database routing.

        Returns:
            tuple[int, int]: A tuple containing:
                - count: Number of locations successfully processed
                - errors: Number of batch upsert errors encountered

        Raises:
            ValueError: If SFTP configuration is missing or Excel file cannot be read.
            Exception: Network errors, authentication failures, or file format issues
                      with enhanced error messages for debugging.

        Note:
            - SFTP connection is created fresh for each operation (stateless)
            - Excel file is downloaded to temporary file and cleaned up after processing
            - Multiple parsing strategies are attempted for file format compatibility
            - Data is processed in batches of 500 records for performance
            - Batch failures are logged but don't stop processing
            - Warehouse ID is required and records without it are filtered out
            - String fields are normalized and NaN values converted to None

        Example:
            >>> count, errors = await service._process_locations(tenant_id)
            >>> print(f"Processed {count} locations with {errors} errors")
            Processed 25 locations with 0 errors
        """
        try:
            logger.info(f"Fetching SFTP configuration for tenant {tenant_id}")
            sftp_client = await get_tenant_sftp_client(tenant_id)

            if not sftp_client:
                logger.warning(
                    f"SFTP configuration not found for tenant {tenant_id}, skipping location processing"
                )
                return 0, 0

            logger.info(
                f"Connecting to SFTP to download locations data for tenant {tenant_id}"
            )
            locations_data = sftp_client._get_locations_data_sync()

            if locations_data is not None and len(locations_data) > 0:

                locations_data = locations_data.replace({np.nan: None})

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
                            cleaned_record[key] = value.to_pydatetime()
                        else:
                            cleaned_record[key] = value
                    cleaned_locations.append(cleaned_record)

                count, errors = await self.repo.upsert_locations(
                    tenant_id, cleaned_locations
                )
                logger.info(
                    f"Processed {count} locations from SFTP ({errors} batch errors)"
                )
                return count, errors
            logger.info("No locations data received from SFTP")
            return 0, 0

        except Exception as e:
            logger.error(f"Error processing locations: {e}")
            raise
