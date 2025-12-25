"""
Schedule API Models.
"""

from typing import Optional
from pydantic import BaseModel


class ScheduleRequest(BaseModel):
    """Request model for creating/updating schedule."""
    cron_expression: Optional[str] = None
    status: Optional[str] = None
