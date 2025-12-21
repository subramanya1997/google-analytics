"""
Activity function for processing users from SFTP.

This module contains the activity function logic that is registered
in the main function_app.py. It can be imported and tested independently.
"""

import logging
from typing import Dict, Any

import pandas as pd
import numpy as np
from loguru import logger


async def process_users(job_id: str, tenant_id: str) -> int:
    """
    Process users from SFTP.
    
    Args:
        job_id: The job identifier
        tenant_id: The tenant identifier
        
    Returns:
        Number of users processed
    """
    from clients import get_tenant_sftp_client
    from shared.database import create_repository
    
    logger.info(f"Processing users for job {job_id}")
    
    try:
        sftp_client = await get_tenant_sftp_client(tenant_id)
        if not sftp_client:
            logger.warning(f"SFTP not configured for tenant {tenant_id}")
            return 0
        
        # Get users data (synchronous method)
        users_data = sftp_client._get_users_data_sync()
        
        if users_data is not None and len(users_data) > 0:
            # Clean data - replace NaN with None
            users_data = users_data.replace({np.nan: None})
            users_list = users_data.to_dict("records")
            
            # Clean records for JSON compatibility
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
            
            repo = create_repository()
            count = await repo.upsert_users(tenant_id, cleaned_users)
            logger.info(f"Processed {count} users")
            return count
        
        logger.info("No users data found")
        return 0
        
    except Exception as e:
        logger.error(f"Error processing users: {e}")
        raise


def process_users_activity(input: Dict[str, Any]) -> int:
    """
    Wrapper function for activity trigger.
    This is called by the Azure Functions runtime.
    """
    import asyncio
    
    return asyncio.run(process_users(
        job_id=input["job_id"],
        tenant_id=input["tenant_id"]
    ))

