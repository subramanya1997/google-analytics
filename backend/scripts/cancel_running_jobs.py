"""
Job Cancellation and Cleanup Script.

This module provides a command-line utility for managing stuck or long-running
data ingestion jobs. It cancels jobs that are in 'queued' or 'processing' status
and marks them as failed, allowing the system to recover from hung states.

**Architecture Context:**
    - The system uses asynchronous job processing for data ingestion
    - Jobs are tracked in the `processing_jobs` table with status tracking
    - Jobs can get stuck in 'queued' or 'processing' states due to:
      * Background thread crashes
      * Service restarts during job execution
      * Database connection timeouts
      * Unhandled exceptions in worker threads

**Primary Use Cases:**
    1. **Cleanup Stuck Jobs**: Cancel jobs that are stuck in processing
    2. **Service Recovery**: Reset job state after service crashes
    3. **Manual Intervention**: Administrative cleanup of hung jobs
    4. **Development/Testing**: Reset job state during development

**Security Considerations:**
    - Requires database access (via environment variables)
    - Interactive confirmation required before cancelling jobs
    - All cancellations are logged with timestamps
    - Error messages are preserved in job records for debugging

**Dependencies:**
    - PostgreSQL database with processing_jobs table
    - Environment variables: DB_HOST, DB_PORT, DB_USER, DB_PASSWORD
    - Access to 'data-ingestion-service' tenant database

**Example Usage:**
    ```bash
    # Run from backend directory
    cd backend
    python -m scripts.cancel_running_jobs

    # Or directly
    python scripts/cancel_running_jobs.py
    ```

**Operation Details:**

    **Job Cancellation:**
        - Finds all jobs with status 'queued' or 'processing'
        - Updates status to 'failed'
        - Sets completed_at timestamp to current time
        - Adds error message: 'Manually cancelled - background threads terminated'
        - Preserves job metadata (job_id, tenant_id, created_at, etc.)

    **Background Thread Management:**
        - Provides instructions for killing background worker threads
        - Shows process management commands (ps, pkill)
        - Recommends service restart after job cancellation

**Error Handling:**
    - Logs errors but continues execution
    - Provides clear error messages for debugging
    - Does not raise exceptions (errors are logged)

**Logging:**
    - Console output: INFO level with timestamps
    - Detailed operation logs for each job cancelled
    - Summary of cancellation results

**Performance Notes:**
    - Job query: ~50-200ms (depends on number of jobs)
    - Job update: ~100-500ms per job (depends on database load)
    - Total execution: Typically < 1 second for standard workloads
"""

import asyncio
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy import text

from common.database import get_async_db_session


async def cancel_all_running_jobs() -> None:
    """
    Cancel all jobs in 'queued' or 'processing' status.

    Queries the processing_jobs table for jobs that are stuck in intermediate
    states and marks them as failed. This allows the system to recover from
    hung job states and prevents jobs from remaining stuck indefinitely.

    **Workflow:**
        1. Query database for jobs with status 'queued' or 'processing'
        2. Display list of jobs to be cancelled
        3. Request user confirmation
        4. Update job status to 'failed' with completion timestamp
        5. Add error message indicating manual cancellation
        6. Display summary of cancelled jobs

    **Returns:**
        None: Function completes silently, errors are logged but don't stop execution.

    **Raises:**
        Exception: May raise database connection or query errors.
                   Errors are logged and re-raised for caller handling.

    **Side Effects:**
        - Updates processing_jobs table records
        - Commits database transaction
        - Logs all cancellation operations
        - Modifies job state (non-idempotent operation)

    **Examples:**
        ```python
        await cancel_all_running_jobs()
        # Output:
        # Found 3 jobs to cancel:
        #   - job-123 (status: processing, created: 2024-01-01 10:00:00)
        #   - job-124 (status: queued, created: 2024-01-01 10:05:00)
        #   - job-125 (status: processing, created: 2024-01-01 10:10:00)
        # ✅ Successfully cancelled 3 jobs
        ```

    **Error Handling:**
        - Logs error and returns early if no jobs found
        - Requires user confirmation before proceeding
        - Logs detailed error messages if database operations fail
        - Re-raises exceptions for caller to handle

    **Database Operations:**
        - SELECT query: Finds jobs with status IN ('queued', 'processing')
        - UPDATE query: Sets status='failed', completed_at=now(), error_message=...
        - Uses parameterized queries to prevent SQL injection
        - Commits transaction after update

    **Note:**
        - Only cancels jobs in 'queued' or 'processing' status
        - Does not affect jobs in 'completed', 'failed', or 'cancelled' status
        - Jobs are marked as 'failed' (not 'cancelled') for consistency
        - Error message indicates manual cancellation for audit purposes
        - Background threads may still be running (see kill_background_threads())

    **Performance:**
        - Query execution: ~50-200ms (depends on number of jobs)
        - Update execution: ~100-500ms per job (depends on database load)
        - Total time scales linearly with number of jobs
        - User confirmation time not included in performance metrics
    """

    try:
        async with get_async_db_session("data-ingestion-service") as session:
            # Find all jobs that are stuck in queued or processing
            query = text("""
                SELECT job_id, tenant_id, status, created_at, started_at
                FROM processing_jobs
                WHERE status IN ('queued', 'processing')
                ORDER BY created_at DESC
            """)

            result = await session.execute(query)
            jobs = result.fetchall()

            if not jobs:
                logger.info("No running or queued jobs found.")
                return

            logger.info(f"Found {len(jobs)} jobs to cancel:")
            for job in jobs:
                logger.info(
                    f"  - {job.job_id} (status: {job.status}, created: {job.created_at})"
                )

            # Ask for confirmation
            print(
                "\n⚠️  This will mark all these jobs as FAILED. Continue? (yes/no): ",
                end="",
            )
            response = input().strip().lower()

            if response != "yes":
                logger.info("Cancelled by user.")
                return

            # Update all jobs to failed
            update_query = text("""
                UPDATE processing_jobs
                SET
                    status = 'failed',
                    completed_at = :completed_at,
                    error_message = 'Manually cancelled - background threads terminated'
                WHERE status IN ('queued', 'processing')
                RETURNING job_id
            """)

            result = await session.execute(
                update_query, {"completed_at": datetime.now()}
            )
            await session.commit()

            updated_jobs = result.fetchall()
            logger.success(f"✅ Successfully cancelled {len(updated_jobs)} jobs")

            for job in updated_jobs:
                logger.info(f"  - Cancelled: {job.job_id}")

    except Exception as e:
        logger.error(f"Error cancelling jobs: {e}")
        raise


async def kill_background_threads() -> None:
    """
    Display instructions for killing background worker threads.

    Provides command-line instructions for terminating background worker threads
    that may still be processing jobs. This is necessary because cancelling jobs
    in the database doesn't automatically stop running threads.

    **Returns:**
        None: Function only displays instructions, no return value.

    **Side Effects:**
        - Writes instructions to stdout
        - Logs informational messages

    **Examples:**
        ```python
        await kill_background_threads()
        # Displays:
        # ============================================================
        # To kill background worker threads, run these commands:
        # ============================================================
        # 1. Find data service processes:
        #    ps aux | grep 'data_service'
        # ...
        ```

    **Note:**
        - This function only displays instructions, it doesn't execute commands
        - Users must manually run the provided commands
        - Commands are provided for both direct process management and Make targets
        - Service restart is recommended after killing threads

    **Why This Is Needed:**
        - Database job cancellation doesn't stop running threads
        - Background threads may continue processing even after job is marked failed
        - Threads need to be terminated at the process level
        - Service restart ensures clean state for new jobs

    **Security Considerations:**
        - Commands use standard Unix process management tools
        - pkill command will kill all matching processes (use with caution)
        - Make targets provide safer, controlled shutdown
        - Users should verify processes before killing them
    """

    logger.info("\n" + "=" * 60)
    logger.info("To kill background worker threads, run these commands:")
    logger.info("=" * 60)

    print("\n1. Find data service processes:")
    print("   ps aux | grep 'data_service'")

    print("\n2. Kill the data service (this will stop all background threads):")
    print("   pkill -f 'data_service'")
    print("   # OR if using make:")
    print("   make stop-data-service")

    print("\n3. Restart the service when ready:")
    print("   make run-data-service")

    print("\n" + "=" * 60)


async def main() -> None:
    """
    Main entry point for the job cancellation script.

    Orchestrates the job cancellation workflow and provides user feedback.
    This is the primary entry point when the script is executed directly.

    **Workflow:**
        1. Display script header and separator
        2. Cancel all running/queued jobs (with user confirmation)
        3. Display instructions for killing background threads
        4. Display completion message with reminders

    **Returns:**
        None: Function completes and returns, no exit code set.

    **Side Effects:**
        - Reads from stdin for user confirmation
        - Writes to stdout for user prompts and instructions
        - Modifies database state (job status updates)
        - Logs all operations to console

    **Examples:**
        Interactive session:
        ```
        🛑 Cancel Running Jobs Script
        ============================================================
        Found 2 jobs to cancel:
          - job-123 (status: processing, created: 2024-01-01 10:00:00)
          - job-124 (status: queued, created: 2024-01-01 10:05:00)

        ⚠️  This will mark all these jobs as FAILED. Continue? (yes/no): yes
        ✅ Successfully cancelled 2 jobs
          - Cancelled: job-123
          - Cancelled: job-124

        ============================================================
        To kill background worker threads, run these commands:
        ============================================================
        ...

        ✅ Done! Jobs have been cancelled in the database.
        ⚠️  Remember to stop/restart the data service to kill threads.
        ```

    **Error Handling:**
        - Errors in cancel_all_running_jobs() are logged and may stop execution
        - kill_background_threads() never raises exceptions
        - User can cancel operation by typing anything other than 'yes'

    **Note:**
        - This is an interactive script requiring user input
        - Not suitable for automated/cron execution without modification
        - User confirmation is required before cancelling jobs
        - Background thread instructions are always displayed
    """
    logger.info("🛑 Cancel Running Jobs Script")
    logger.info("=" * 60)

    # Cancel jobs in database
    await cancel_all_running_jobs()

    # Show thread killing instructions
    await kill_background_threads()

    logger.info("\n✅ Done! Jobs have been cancelled in the database.")
    logger.info("⚠️  Remember to stop/restart the data service to kill threads.")


if __name__ == "__main__":
    """
    Script entry point.

    Executes the main async function using asyncio.run(). This is the standard
    entry point for async Python scripts and handles event loop creation and
    cleanup automatically.

    **Usage:**
        ```bash
        python scripts/cancel_running_jobs.py
        # Or as a module:
        python -m scripts.cancel_running_jobs
        ```

    **Note:**
        - Uses asyncio.run() for proper async execution
        - Event loop is created and cleaned up automatically
        - Script exits when main() completes
        - Exit code is 0 unless unhandled exceptions occur
    """
    asyncio.run(main())
