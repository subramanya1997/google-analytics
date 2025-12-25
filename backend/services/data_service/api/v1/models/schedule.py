"""
Schedule API Models

This module defines Pydantic models for schedule management endpoints in the
Data Ingestion Service API. These models handle request validation and serialization
for creating, updating, and querying scheduled ingestion jobs.

Models:
    - ScheduleRequest: Request model for schedule upsert operations

The models ensure proper validation of cron expressions and schedule status
values before they are sent to the external scheduler service.
"""

from pydantic import BaseModel


class ScheduleRequest(BaseModel):
    """
    Request model for creating or updating a scheduled ingestion job.

    This model represents the input for schedule upsert operations, allowing
    clients to configure cron expressions and schedule status. All fields are
    optional, with defaults provided by the service configuration.

    Attributes:
        cron_expression: Optional cron expression for job scheduling.
                        If not provided, uses DATA_INGESTION_CRON env var default.
                        Format: "minute hour day month weekday"
                        Example: "0 2 * * *" (2 AM daily)
        status: Optional schedule status ("active" or "inactive").
               If not provided, defaults to "active" for new schedules.
               Existing schedules maintain their current status if not specified.

    Validation:
        - Cron expression format is validated by the scheduler service
        - Status must be "active" or "inactive" (validated by scheduler)

    Example:
        ```python
        # Create schedule with custom cron expression
        request = ScheduleRequest(
            cron_expression="0 3 * * *",  # 3 AM daily
            status="active"
        )
        
        # Update existing schedule status only
        request = ScheduleRequest(status="inactive")
        ```

    See Also:
        - services.data_service.api.v1.endpoints.schedule: Schedule endpoints
        - common.scheduler_client: Scheduler service integration
    """

    cron_expression: str | None = None
    status: str | None = None
