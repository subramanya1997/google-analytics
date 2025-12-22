"""
Scheduler Client for interacting with the Cronicle scheduler service.
"""
import os
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger


class SchedulerClient:
    """Client for managing scheduled jobs via the Cronicle scheduler API."""
    
    def __init__(self, scheduler_url: str):
        """
        Initialize the scheduler client.
        
        Args:
            scheduler_url: Base URL for the scheduler API (from service settings).
        """
        self.scheduler_url = scheduler_url
    
    def _make_request(
        self,
        method: str,
        auth_token: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make an authenticated request to the scheduler API.
        
        Args:
            method: HTTP method (GET, POST, PUT)
            auth_token: JWT token from user session
            params: Query parameters
            json_data: JSON body data
            
        Returns:
            Response JSON as dictionary
            
        Raises:
            requests.exceptions.RequestException: If the request fails
        """
        headers = {
            'Authorization': f'Bearer {auth_token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.request(
            method=method,
            url=self.scheduler_url,
            headers=headers,
            params=params,
            json=json_data,
            timeout=30
        )
        
        # Enhanced error handling with detailed logging
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP error from scheduler API: {http_err}")
            logger.error(f"Response status code: {response.status_code}")
            raise
        except requests.exceptions.RequestException as req_err:
            logger.error(f"Request exception: {req_err}")
            raise
    
    def create_schedule(
        self,
        auth_token: str,
        job_name: str,
        app_name: str,
        url: str,
        method: str,
        cron_exp: str,
        status: str = 'active',
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new scheduled job.
        
        Args:
            auth_token: JWT token from user session
            job_name: Name of the job
            app_name: Name of the application
            url: URL to be called when the job executes
            method: HTTP method (GET or POST)
            cron_exp: Cron expression for scheduling
            status: Job status (default: 'active')
            headers: Optional headers to include in the job request
            body: Optional body data for the job request
            
        Returns:
            Response containing event_id and status code
            
        Example response:
            {
                "message": "Schedule created successfully",
                "event_id": {
                    "code": 0,
                    "id": "emgrkv74x44"
                }
            }
        """
        job_config = {
            'job_name': job_name,
            'app_name': app_name,
            'url': url,
            'method': method.upper(),
            'cron_exp': cron_exp,
            'status': status,
            'header': headers or {},
            'body': body or {}
        }
        
        return self._make_request('POST', auth_token, json_data=job_config)
    
    def update_schedule(
        self,
        auth_token: str,
        job_name: Optional[str] = None,
        app_name: Optional[str] = None,
        event_id: Optional[str] = None,
        url: Optional[str] = None,
        method: Optional[str] = None,
        cron_exp: Optional[str] = None,
        status: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Update an existing scheduled job.
        
        Args:
            auth_token: JWT token from user session
            job_name: Name of the job (used with app_name if event_id not provided)
            app_name: Name of the application (used with job_name if event_id not provided)
            event_id: Unique event ID from scheduler
            url: Updated URL
            method: Updated HTTP method
            cron_exp: Updated cron expression
            status: Updated status
            headers: Updated headers
            body: Updated body data
            
        Returns:
            Response containing status code
            
        Note:
            Either provide event_id OR both job_name and app_name
        """
        params = {}
        if event_id:
            params['event_id'] = event_id
        elif job_name and app_name:
            params['job_name'] = job_name
            params['app_name'] = app_name
        else:
            raise ValueError("Must provide either event_id or both job_name and app_name")
        
        job_config = {}
        if url is not None:
            job_config['url'] = url
        if method is not None:
            job_config['method'] = method.upper()
        if cron_exp is not None:
            job_config['cron_exp'] = cron_exp
        if status is not None:
            job_config['status'] = status
        if headers is not None:
            job_config['header'] = headers
        if body is not None:
            job_config['body'] = body
            
        # Include job_name and app_name in body if updating by event_id
        if event_id and job_name:
            job_config['job_name'] = job_name
        if event_id and app_name:
            job_config['app_name'] = app_name
        
        return self._make_request('PUT', auth_token, params=params, json_data=job_config)
    
    def execute_schedule(
        self,
        auth_token: str,
        job_name: Optional[str] = None,
        app_name: Optional[str] = None,
        event_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute a scheduled job manually.
        
        Args:
            auth_token: JWT token from user session
            job_name: Name of the job (used with app_name if event_id not provided)
            app_name: Name of the application (used with job_name if event_id not provided)
            event_id: Unique event ID from scheduler
            
        Returns:
            Response containing job execution details
        """
        params = {}
        if event_id:
            params['event_id'] = event_id
        elif job_name and app_name:
            params['job_name'] = job_name
            params['app_name'] = app_name
        else:
            raise ValueError("Must provide either event_id or both job_name and app_name")
        
        return self._make_request('POST', auth_token, params=params)
    
    def get_schedules(
        self,
        auth_token: str,
        job_name: Optional[str] = None,
        app_name: Optional[str] = None,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Fetch schedule details.
        
        Args:
            auth_token: JWT token from user session
            job_name: Optional filter by job name
            app_name: Optional filter by app name
            limit: Optional limit on number of results
            
        Returns:
            Response containing list of scheduler details
            
        Example response:
            {
                "message": "Schedules fetched successfully",
                "scheduler_details": [
                    {
                        "scheduler_name": "...",
                        "app_name": "...",
                        "job_name": "...",
                        "status": "active",
                        "event_id": "...",
                        "response_list": [...]
                    }
                ]
            }
        """
        params = {}
        if job_name:
            params['job_name'] = job_name
        if app_name:
            params['app_name'] = app_name
        if limit:
            params['limit'] = str(limit)
        
        return self._make_request('GET', auth_token, params=params)


def create_scheduler_client(scheduler_url: str) -> SchedulerClient:
    """
    Factory function to create a SchedulerClient instance.
    
    Args:
        scheduler_url: Base URL for the scheduler API (from service settings).
        
    Returns:
        Configured SchedulerClient instance.
    """
    return SchedulerClient(scheduler_url)

