"""
Durable Functions Orchestrator for Data Ingestion.

This module defines the orchestrator function that coordinates the
ingestion of events, users, and locations data. The actual orchestrator
is registered in function_app.py.

This module provides the orchestrator logic that can be tested independently.
"""

import logging
from typing import Dict, Any, List, Tuple


def create_ingestion_tasks(
    context,
    job_id: str,
    tenant_id: str,
    start_date: str,
    end_date: str,
    data_types: List[str]
) -> List[Tuple[str, Any]]:
    """
    Create activity tasks for the ingestion job.
    
    Args:
        context: Durable Functions orchestration context
        job_id: The job identifier
        tenant_id: The tenant identifier
        start_date: Start date in ISO format
        end_date: End date in ISO format
        data_types: List of data types to process
        
    Returns:
        List of (key, task) tuples for fan-out processing
    """
    tasks = []
    
    if "events" in data_types:
        # Fan-out: process all 6 event types in parallel
        event_types = [
            "purchase",
            "add_to_cart", 
            "page_view",
            "view_search_results",
            "no_search_results",
            "view_item"
        ]
        
        for event_type in event_types:
            task = context.call_activity("process_events_activity", {
                "job_id": job_id,
                "tenant_id": tenant_id,
                "start_date": start_date,
                "end_date": end_date,
                "event_type": event_type
            })
            tasks.append((event_type, task))
    
    if "users" in data_types:
        task = context.call_activity("process_users_activity", {
            "job_id": job_id,
            "tenant_id": tenant_id
        })
        tasks.append(("users_processed", task))
    
    if "locations" in data_types:
        task = context.call_activity("process_locations_activity", {
            "job_id": job_id,
            "tenant_id": tenant_id
        })
        tasks.append(("locations_processed", task))
    
    return tasks


def collect_results(tasks: List[Tuple[str, Any]]) -> Dict[str, int]:
    """
    Collect results from completed tasks.
    
    This is a helper for the orchestrator to format results.
    Note: In actual orchestrator, you need to yield each task.
    """
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
    
    return results


# The actual orchestrator function is defined in function_app.py
# using the @app.orchestration_trigger decorator.
# 
# This module provides supporting functions that can be tested
# and reused.

def orchestrator_function(context):
    """
    Main orchestrator function logic.
    
    This is imported and used by the function_app.py orchestrator.
    The actual decorator-based registration happens there.
    
    Orchestration flow:
    1. Update job status to "processing"
    2. Fan-out: Start all data processing activities in parallel
    3. Fan-in: Wait for all activities to complete
    4. Update job status to "completed" with results
    
    Error handling:
    - Individual activity failures are caught and logged
    - Overall orchestration failure updates job status to "failed"
    """
    # Get input
    input_data = context.get_input()
    job_id = input_data["job_id"]
    tenant_id = input_data["tenant_id"]
    start_date = input_data["start_date"]
    end_date = input_data["end_date"]
    data_types = input_data["data_types"]
    
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
    
    try:
        # Update job status to processing
        yield context.call_activity("update_job_status_activity", {
            "job_id": job_id,
            "status": "processing",
            "started_at": context.current_utc_datetime.isoformat()
        })
        
        # Create parallel tasks
        tasks = create_ingestion_tasks(
            context, job_id, tenant_id, start_date, end_date, data_types
        )
        
        # Fan-in: wait for all tasks to complete
        for key, task in tasks:
            try:
                count = yield task
                results[key] = count or 0
            except Exception as e:
                logging.error(f"Activity {key} failed: {e}")
                results[key] = 0
        
        # Update job status to completed
        yield context.call_activity("update_job_status_activity", {
            "job_id": job_id,
            "status": "completed",
            "completed_at": context.current_utc_datetime.isoformat(),
            "records_processed": results
        })
        
        return results
        
    except Exception as e:
        # Update job status to failed
        yield context.call_activity("update_job_status_activity", {
            "job_id": job_id,
            "status": "failed",
            "completed_at": context.current_utc_datetime.isoformat(),
            "error_message": str(e)
        })
        raise

