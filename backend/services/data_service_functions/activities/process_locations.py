"""
Activity function for processing locations from SFTP.

This module contains the activity function logic that is registered
in the main function_app.py. It can be imported and tested independently.
"""

import logging
from typing import Dict, Any

import pandas as pd
import numpy as np
from loguru import logger


async def process_locations(job_id: str, tenant_id: str) -> int:
    """
    Process locations from SFTP.
    
    Args:
        job_id: The job identifier
        tenant_id: The tenant identifier
        
    Returns:
        Number of locations processed
    """
    from clients import get_tenant_sftp_client
    from shared.database import create_repository
    
    logger.info(f"Processing locations for job {job_id}")
    
    try:
        sftp_client = await get_tenant_sftp_client(tenant_id)
        if not sftp_client:
            logger.warning(f"SFTP not configured for tenant {tenant_id}")
            return 0
        
        # Get locations data (synchronous method)
        locations_data = sftp_client._get_locations_data_sync()
        
        if locations_data is not None and len(locations_data) > 0:
            # Clean data - replace NaN with None
            locations_data = locations_data.replace({np.nan: None})
            locations_list = locations_data.to_dict("records")
            
            # Clean records for JSON compatibility
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
            
            repo = create_repository()
            count = await repo.upsert_locations(tenant_id, cleaned_locations)
            logger.info(f"Processed {count} locations")
            return count
        
        logger.info("No locations data found")
        return 0
        
    except Exception as e:
        logger.error(f"Error processing locations: {e}")
        raise


def process_locations_activity(input: Dict[str, Any]) -> int:
    """
    Wrapper function for activity trigger.
    This is called by the Azure Functions runtime.
    """
    import asyncio
    
    return asyncio.run(process_locations(
        job_id=input["job_id"],
        tenant_id=input["tenant_id"]
    ))

