"""
Response models for analytics service API endpoints.
"""

from typing import Optional

from pydantic import BaseModel


class TaskStatusResponse(BaseModel):
    """Task status response model."""

    taskId: str
    taskType: str
    completed: bool
    notes: str
    completedAt: Optional[str] = None
    completedBy: Optional[str] = None


class TaskStatusUpdateRequest(BaseModel):
    """Task status update request model."""

    completed: bool
    notes: Optional[str] = ""
    completedBy: Optional[str] = ""
