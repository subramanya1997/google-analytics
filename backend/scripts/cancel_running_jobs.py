"""
Script to cancel all running/queued ingestion jobs and mark them as failed.
Use this to clean up stuck jobs and stop background threads.

Usage:
    cd backend
    python -m scripts.cancel_running_jobs
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy import text

from common.database import get_async_db_session


async def cancel_all_running_jobs():
    """Cancel all jobs that are in 'queued' or 'processing' status."""
    
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
                logger.info(f"  - {job.job_id} (status: {job.status}, created: {job.created_at})")
            
            # Ask for confirmation
            print("\n⚠️  This will mark all these jobs as FAILED. Continue? (yes/no): ", end="")
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
                update_query, 
                {"completed_at": datetime.now()}
            )
            await session.commit()
            
            updated_jobs = result.fetchall()
            logger.success(f"✅ Successfully cancelled {len(updated_jobs)} jobs")
            
            for job in updated_jobs:
                logger.info(f"  - Cancelled: {job.job_id}")
                
    except Exception as e:
        logger.error(f"Error cancelling jobs: {e}")
        raise


async def kill_background_threads():
    """Display instructions for killing background threads."""
    
    logger.info("\n" + "="*60)
    logger.info("To kill background worker threads, run these commands:")
    logger.info("="*60)
    
    print("\n1. Find data service processes:")
    print("   ps aux | grep 'data_service'")
    
    print("\n2. Kill the data service (this will stop all background threads):")
    print("   pkill -f 'data_service'")
    print("   # OR if using make:")
    print("   make stop-data-service")
    
    print("\n3. Restart the service when ready:")
    print("   make run-data-service")
    
    print("\n" + "="*60)


async def main():
    """Main function."""
    logger.info("🛑 Cancel Running Jobs Script")
    logger.info("="*60)
    
    # Cancel jobs in database
    await cancel_all_running_jobs()
    
    # Show thread killing instructions
    await kill_background_threads()
    
    logger.info("\n✅ Done! Jobs have been cancelled in the database.")
    logger.info("⚠️  Remember to stop/restart the data service to kill threads.")


if __name__ == "__main__":
    asyncio.run(main())

