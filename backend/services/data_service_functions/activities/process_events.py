"""
Activity function for processing events from BigQuery.

This module contains the activity function logic that is registered
in the main function_app.py. It can be imported and tested independently.
"""

import logging
from datetime import date
from typing import Dict, Any

from loguru import logger


async def process_events(
    job_id: str,
    tenant_id: str,
    start_date: str,
    end_date: str,
    event_type: str
) -> int:
    """
    Process events from BigQuery for a specific event type.
    
    Args:
        job_id: The job identifier
        tenant_id: The tenant identifier
        start_date: Start date in ISO format
        end_date: End date in ISO format
        event_type: Type of event to process
        
    Returns:
        Number of events processed
    """
    from clients import get_tenant_bigquery_client
    from shared.database import create_repository
    
    start_dt = date.fromisoformat(start_date)
    end_dt = date.fromisoformat(end_date)
    
    logger.info(f"Processing {event_type} events for job {job_id}")
    
    try:
        # Get BigQuery client
        bigquery_client = await get_tenant_bigquery_client(tenant_id)
        if not bigquery_client:
            raise ValueError(f"BigQuery configuration not found for tenant {tenant_id}")
        
        # Map event types to extractor methods
        extractor_map = {
            "purchase": bigquery_client._extract_purchase_events,
            "add_to_cart": bigquery_client._extract_add_to_cart_events,
            "page_view": bigquery_client._extract_page_view_events,
            "view_search_results": bigquery_client._extract_view_search_results_events,
            "no_search_results": bigquery_client._extract_no_search_results_events,
            "view_item": bigquery_client._extract_view_item_events,
        }
        
        extractor = extractor_map.get(event_type)
        if not extractor:
            raise ValueError(f"Unknown event type: {event_type}")
        
        # Extract events (synchronous call - no thread pool in serverless)
        events_data = extractor(start_date, end_date)
        
        if events_data:
            repo = create_repository()
            count = await repo.replace_event_data(
                tenant_id, event_type, start_dt, end_dt, events_data
            )
            logger.info(f"Processed {count} {event_type} events")
            return count
        
        logger.info(f"No {event_type} events found")
        return 0
        
    except Exception as e:
        logger.error(f"Error processing {event_type} events: {e}")
        raise


def process_events_activity(input: Dict[str, Any]) -> int:
    """
    Wrapper function for activity trigger.
    This is called by the Azure Functions runtime.
    """
    import asyncio
    
    return asyncio.run(process_events(
        job_id=input["job_id"],
        tenant_id=input["tenant_id"],
        start_date=input["start_date"],
        end_date=input["end_date"],
        event_type=input["event_type"]
    ))

