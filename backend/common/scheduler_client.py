"""
Scheduler Client for interacting with the Cronicle scheduler service.

This module provides a client interface for managing scheduled jobs through the Cronicle
scheduler API. It handles authentication, request/response processing, and provides
methods for creating, updating, executing, and querying scheduled jobs.

The scheduler is used to automate recurring tasks such as:
    - Daily data ingestion from BigQuery
    - Scheduled email notifications
    - Periodic analytics report generation

Architecture:
    The SchedulerClient uses Bearer token authentication (JWT) and communicates with
    the scheduler service via REST API. All requests include proper error handling
    and logging for debugging and monitoring.

Example:
    ```python
    from common.scheduler_client import create_scheduler_client
    
    client = create_scheduler_client("https://scheduler.example.com/api")
    
    # Create a scheduled job
    result = client.create_schedule(
        auth_token="jwt_token",
        job_name="daily-data-ingestion",
        app_name="data-service",
        url="https://api.example.com/data/ingest",
        method="POST",
        cron_exp="0 2 * * *",  # Daily at 2 AM
        headers={"X-Custom-Header": "value"},
        body={"tenant_id": "123"}
    )
    ```

Error Handling:
    All methods raise requests.exceptions.RequestException on failure, which should be
    caught and handled appropriately by calling code.
"""

from typing import Any

from loguru import logger
import requests


class SchedulerClient:
    """
    Client for managing scheduled jobs via the Cronicle scheduler API.
    
    This class provides a high-level interface for interacting with the Cronicle
    scheduler service. It handles HTTP communication, authentication, and provides
    methods for CRUD operations on scheduled jobs.
    
    Attributes:
        scheduler_url (str): Base URL for the scheduler API endpoint.
    
    Thread Safety:
        This class is not thread-safe. Each thread should create its own instance
        or use proper synchronization mechanisms.
    
    Example:
        ```python
        client = SchedulerClient("https://scheduler.example.com/api")
        
        # Create a new scheduled job
        result = client.create_schedule(
            auth_token="jwt_token",
            job_name="my-job",
            app_name="my-app",
            url="https://api.example.com/endpoint",
            method="POST",
            cron_exp="0 * * * *"
        )
        ```
    """

    def __init__(self, scheduler_url: str) -> None:
        """
        Initialize the scheduler client.

        Args:
            scheduler_url: Base URL for the scheduler API endpoint. This should be
                obtained from service settings (e.g., BaseServiceSettings.SCHEDULER_API_URL).
                The URL should not include trailing slashes.

        Raises:
            ValueError: If scheduler_url is empty or None.

        Example:
            ```python
            from common.config import get_settings
            
            settings = get_settings("analytics-service")
            client = SchedulerClient(settings.SCHEDULER_API_URL)
            ```
        """
        if not scheduler_url:
            raise ValueError("scheduler_url cannot be empty")
        self.scheduler_url = scheduler_url.rstrip("/")

    def _make_request(
        self,
        method: str,
        auth_token: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Make an authenticated HTTP request to the scheduler API.

        This is an internal method that handles the low-level HTTP communication
        with the scheduler service. It sets up authentication headers, handles
        errors, and logs request/response details.

        Args:
            method: HTTP method to use. Must be one of: "GET", "POST", "PUT".
            auth_token: JWT authentication token obtained from user session.
                This token is included in the Authorization header as a Bearer token.
            params: Optional dictionary of query parameters to include in the request URL.
            json_data: Optional dictionary of data to send as JSON in the request body.
                Only used for POST and PUT requests.

        Returns:
            Dictionary containing the parsed JSON response from the scheduler API.
            The structure depends on the specific endpoint called.

        Raises:
            requests.exceptions.HTTPError: If the HTTP request returns a non-2xx status code.
            requests.exceptions.ConnectionError: If a connection error occurs.
            requests.exceptions.Timeout: If the request times out (30 second timeout).
            requests.exceptions.RequestException: For other request-related errors.

        Note:
            All errors are logged with detailed information including status codes
            and error messages for debugging purposes.

        Example:
            ```python
            response = client._make_request(
                method="GET",
                auth_token="jwt_token",
                params={"job_name": "my-job"}
            )
            ```
        """
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
        }

        response = requests.request(
            method=method,
            url=self.scheduler_url,
            headers=headers,
            params=params,
            json=json_data,
            timeout=30,
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
        status: str = "active",
        headers: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a new scheduled job in the Cronicle scheduler.

        This method registers a new recurring job that will be executed according to
        the provided cron expression. The job will make an HTTP request to the
        specified URL when triggered.

        Args:
            auth_token: JWT authentication token from the user session. Required
                for authorization.
            job_name: Unique name identifier for the job. This should be descriptive
                and follow a consistent naming convention (e.g., "daily-data-ingestion").
            app_name: Name of the application or service that owns this job. Used for
                grouping and filtering jobs (e.g., "analytics-service", "data-service").
            url: Full URL endpoint that will be called when the job executes. Must be
                a valid HTTP/HTTPS URL.
            method: HTTP method to use when calling the URL. Must be either "GET" or
                "POST". Case-insensitive, will be converted to uppercase.
            cron_exp: Cron expression defining the schedule. Format: "minute hour day month weekday".
                Examples:
                    - "0 2 * * *" - Daily at 2:00 AM
                    - "0 */6 * * *" - Every 6 hours
                    - "0 8 * * 1" - Every Monday at 8:00 AM
            status: Initial status of the job. Defaults to "active". Other possible
                values: "inactive", "paused". Only "active" jobs will be executed.
            headers: Optional dictionary of HTTP headers to include in the job request.
                Useful for authentication, custom headers, etc. Defaults to empty dict.
            body: Optional dictionary of data to send in the request body. Only used
                when method is "POST". Defaults to empty dict.

        Returns:
            Dictionary containing the scheduler API response with the following structure:
            {
                "message": str,  # Success message
                "event_id": {
                    "code": int,  # Status code (0 indicates success)
                    "id": str     # Unique event ID assigned by scheduler
                }
            }

        Raises:
            requests.exceptions.RequestException: If the API request fails or returns
                an error status code.
            ValueError: If required parameters are missing or invalid.

        Example:
            ```python
            result = client.create_schedule(
                auth_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                job_name="daily-analytics-report",
                app_name="analytics-service",
                url="https://api.example.com/analytics/generate-report",
                method="POST",
                cron_exp="0 8 * * *",  # Daily at 8 AM
                headers={"X-API-Key": "secret-key"},
                body={"report_type": "daily", "tenant_id": "123"}
            )
            event_id = result["event_id"]["id"]
            ```

        Note:
            The event_id returned in the response should be stored for future reference
            when updating or executing the job.
        """
        job_config = {
            "job_name": job_name,
            "app_name": app_name,
            "url": url,
            "method": method.upper(),
            "cron_exp": cron_exp,
            "status": status,
            "header": headers or {},
            "body": body or {},
        }

        return self._make_request("POST", auth_token, json_data=job_config)

    def update_schedule(
        self,
        auth_token: str,
        job_name: str | None = None,
        app_name: str | None = None,
        event_id: str | None = None,
        url: str | None = None,
        method: str | None = None,
        cron_exp: str | None = None,
        status: str | None = None,
        headers: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Update an existing scheduled job in the Cronicle scheduler.

        This method allows partial updates to a scheduled job. Only provided
        parameters will be updated; unspecified parameters remain unchanged.

        Args:
            auth_token: JWT authentication token from the user session. Required
                for authorization.
            job_name: Name of the job to update. Must be provided along with app_name
                if event_id is not provided. If event_id is provided, this can be used
                to update the job name itself.
            app_name: Name of the application. Must be provided along with job_name
                if event_id is not provided. If event_id is provided, this can be used
                to update the app name.
            event_id: Unique event ID assigned by the scheduler when the job was created.
                If provided, this is the preferred method for identifying the job.
                Mutually exclusive with job_name/app_name combination.
            url: New URL endpoint to call when the job executes. If None, URL remains unchanged.
            method: New HTTP method to use. Must be "GET" or "POST" if provided.
                Case-insensitive, will be converted to uppercase. If None, method remains unchanged.
            cron_exp: New cron expression for scheduling. If None, schedule remains unchanged.
            status: New status for the job. Valid values: "active", "inactive", "paused".
                If None, status remains unchanged.
            headers: New dictionary of HTTP headers. If None, headers remain unchanged.
                If provided, replaces all existing headers.
            body: New dictionary of body data. If None, body remains unchanged.
                If provided, replaces all existing body data.

        Returns:
            Dictionary containing the scheduler API response with status information:
            {
                "message": str,  # Success or error message
                "status_code": int  # HTTP status code
            }

        Raises:
            ValueError: If neither event_id nor both job_name and app_name are provided.
            requests.exceptions.RequestException: If the API request fails or the job
                is not found.

        Example:
            ```python
            # Update using event_id (preferred)
            result = client.update_schedule(
                auth_token="jwt_token",
                event_id="emgrkv74x44",
                cron_exp="0 9 * * *",  # Change schedule to 9 AM
                status="active"
            )
            
            # Update using job_name and app_name
            result = client.update_schedule(
                auth_token="jwt_token",
                job_name="daily-report",
                app_name="analytics-service",
                url="https://new-url.example.com/endpoint"
            )
            ```

        Note:
            - Either event_id OR both job_name and app_name must be provided to identify the job.
            - When updating by event_id, you can optionally update job_name and app_name as well.
            - Partial updates are supported - only provide the fields you want to change.
        """
        params = {}
        if event_id:
            params["event_id"] = event_id
        elif job_name and app_name:
            params["job_name"] = job_name
            params["app_name"] = app_name
        else:
            msg = "Must provide either event_id or both job_name and app_name"
            raise ValueError(
                msg
            )

        job_config = {}
        if url is not None:
            job_config["url"] = url
        if method is not None:
            job_config["method"] = method.upper()
        if cron_exp is not None:
            job_config["cron_exp"] = cron_exp
        if status is not None:
            job_config["status"] = status
        if headers is not None:
            job_config["header"] = headers
        if body is not None:
            job_config["body"] = body

        # Include job_name and app_name in body if updating by event_id
        if event_id and job_name:
            job_config["job_name"] = job_name
        if event_id and app_name:
            job_config["app_name"] = app_name

        return self._make_request(
            "PUT", auth_token, params=params, json_data=job_config
        )

    def execute_schedule(
        self,
        auth_token: str,
        job_name: str | None = None,
        app_name: str | None = None,
        event_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Manually trigger execution of a scheduled job immediately.

        This method allows on-demand execution of a scheduled job without waiting
        for its next scheduled time. Useful for testing, manual triggers, or
        immediate execution needs.

        Args:
            auth_token: JWT authentication token from the user session. Required
                for authorization.
            job_name: Name of the job to execute. Must be provided along with app_name
                if event_id is not provided.
            app_name: Name of the application. Must be provided along with job_name
                if event_id is not provided.
            event_id: Unique event ID assigned by the scheduler. If provided, this is
                the preferred method for identifying the job. Mutually exclusive with
                job_name/app_name combination.

        Returns:
            Dictionary containing the scheduler API response with execution details:
            {
                "message": str,  # Success or error message
                "execution_id": str,  # Unique ID for this execution instance
                "status": str,  # Execution status
                ...
            }

        Raises:
            ValueError: If neither event_id nor both job_name and app_name are provided.
            requests.exceptions.RequestException: If the API request fails or the job
                is not found.

        Example:
            ```python
            # Execute using event_id (preferred)
            result = client.execute_schedule(
                auth_token="jwt_token",
                event_id="emgrkv74x44"
            )
            
            # Execute using job_name and app_name
            result = client.execute_schedule(
                auth_token="jwt_token",
                job_name="daily-report",
                app_name="analytics-service"
            )
            ```

        Note:
            - Manual execution does not affect the job's scheduled execution times.
            - The job will still run at its next scheduled time unless paused or deleted.
            - Execution is asynchronous - the method returns immediately, but the job
              may take time to complete.
        """
        params = {}
        if event_id:
            params["event_id"] = event_id
        elif job_name and app_name:
            params["job_name"] = job_name
            params["app_name"] = app_name
        else:
            msg = "Must provide either event_id or both job_name and app_name"
            raise ValueError(
                msg
            )

        return self._make_request("POST", auth_token, params=params)

    def get_schedules(
        self,
        auth_token: str,
        job_name: str | None = None,
        app_name: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """
        Retrieve scheduled job details from the Cronicle scheduler.

        This method queries the scheduler for scheduled jobs, with optional filtering
        by job name or app name. Useful for listing jobs, checking job status, or
        retrieving job configurations.

        Args:
            auth_token: JWT authentication token from the user session. Required
                for authorization.
            job_name: Optional filter to return only jobs matching this exact name.
                If None, all jobs are returned (subject to other filters).
            app_name: Optional filter to return only jobs belonging to this application.
                If None, all apps are included (subject to other filters).
            limit: Optional maximum number of results to return. If None, all matching
                jobs are returned. Useful for pagination or limiting large result sets.

        Returns:
            Dictionary containing the scheduler API response with the following structure:
            {
                "message": str,  # Success message
                "scheduler_details": [
                    {
                        "scheduler_name": str,  # Scheduler instance name
                        "app_name": str,  # Application name
                        "job_name": str,  # Job name
                        "status": str,  # Job status ("active", "inactive", "paused")
                        "event_id": str,  # Unique event ID
                        "url": str,  # Target URL
                        "method": str,  # HTTP method
                        "cron_exp": str,  # Cron expression
                        "response_list": list  # Execution history/responses
                    },
                    ...
                ]
            }

        Raises:
            requests.exceptions.RequestException: If the API request fails.

        Example:
            ```python
            # Get all schedules for an app
            result = client.get_schedules(
                auth_token="jwt_token",
                app_name="analytics-service"
            )
            
            # Get a specific job
            result = client.get_schedules(
                auth_token="jwt_token",
                job_name="daily-report",
                app_name="analytics-service"
            )
            
            # Get first 10 schedules
            result = client.get_schedules(
                auth_token="jwt_token",
                limit=10
            )
            
            # Process results
            for job in result["scheduler_details"]:
                print(f"Job: {job['job_name']}, Status: {job['status']}")
            ```

        Note:
            - Filters can be combined (e.g., filter by both job_name and app_name).
            - Results are ordered by creation time (newest first).
            - The response_list contains execution history and may be large for frequently
              executed jobs.
        """
        params = {}
        if job_name:
            params["job_name"] = job_name
        if app_name:
            params["app_name"] = app_name
        if limit:
            params["limit"] = str(limit)

        return self._make_request("GET", auth_token, params=params)


def create_scheduler_client(scheduler_url: str) -> SchedulerClient:
    """
    Factory function to create a SchedulerClient instance.

    This is a convenience function that creates and returns a configured
    SchedulerClient instance. It's the recommended way to instantiate the client
    as it provides a consistent interface and makes testing easier.

    Args:
        scheduler_url: Base URL for the scheduler API endpoint. Typically obtained
            from service settings (e.g., BaseServiceSettings.SCHEDULER_API_URL).
            Should not include trailing slashes.

    Returns:
        Configured SchedulerClient instance ready to use.

    Raises:
        ValueError: If scheduler_url is empty or None.

    Example:
        ```python
        from common.config import get_settings
        from common.scheduler_client import create_scheduler_client
        
        settings = get_settings("analytics-service")
        client = create_scheduler_client(settings.SCHEDULER_API_URL)
        
        # Use the client
        result = client.create_schedule(...)
        ```

    Note:
        This factory function is preferred over direct instantiation as it provides
        a consistent interface and makes it easier to swap implementations or add
        additional configuration in the future.
    """
    return SchedulerClient(scheduler_url)
