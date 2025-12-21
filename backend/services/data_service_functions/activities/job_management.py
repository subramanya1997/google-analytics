"""
Activity functions for job management operations.

This module contains activity functions for creating and updating
ingestion job records in the database.
"""

import logging
from datetime import datetime
from typing import Dict, Any

from loguru import logger


async def create_job(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a new processing job in the database.
    
    Args:
        job_data: Dictionary containing job information
        
    Returns:
        Created job record
    """
    from shared.database import create_repository
    
    logger.info(f"Creating job {job_data.get('job_id')}")
    
    try:
        repo = create_repository()
        job = await repo.create_processing_job(job_data)
        logger.info(f"Created job {job_data.get('job_id')}")
        return job
    except Exception as e:
        logger.error(f"Error creating job: {e}")
        raise


async def update_job_status(
    job_id: str,
    status: str,
    started_at: datetime = None,
    completed_at: datetime = None,
    error_message: str = None,
    progress: Dict[str, Any] = None,
    records_processed: Dict[str, int] = None
) -> bool:
    """
    Update job status in the database.
    
    Args:
        job_id: The job identifier
        status: New status value
        started_at: When the job started processing
        completed_at: When the job completed
        error_message: Error message if failed
        progress: Progress information
        records_processed: Record counts by type
        
    Returns:
        True if update was successful
    """
    from shared.database import create_repository
    
    logger.info(f"Updating job {job_id} status to {status}")
    
    try:
        repo = create_repository()
        
        kwargs = {}
        if started_at:
            kwargs["started_at"] = started_at
        if completed_at:
            kwargs["completed_at"] = completed_at
        if error_message:
            kwargs["error_message"] = error_message
        if progress:
            kwargs["progress"] = progress
        if records_processed:
            kwargs["records_processed"] = records_processed
        
        result = await repo.update_job_status(job_id, status, **kwargs)
        logger.info(f"Updated job {job_id} status to {status}")
        return result
    except Exception as e:
        logger.error(f"Error updating job status: {e}")
        raise


def create_job_activity(input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Wrapper function for activity trigger.
    """
    import asyncio
    return asyncio.run(create_job(input))


def update_job_status_activity(input: Dict[str, Any]) -> bool:
    """
    Wrapper function for activity trigger.
    """
    import asyncio
    
    started_at = None
    completed_at = None
    
    if input.get("started_at"):
        started_at = datetime.fromisoformat(input["started_at"])
    if input.get("completed_at"):
        completed_at = datetime.fromisoformat(input["completed_at"])
    
    return asyncio.run(update_job_status(
        job_id=input["job_id"],
        status=input["status"],
        started_at=started_at,
        completed_at=completed_at,
        error_message=input.get("error_message"),
        progress=input.get("progress"),
        records_processed=input.get("records_processed")
    ))

