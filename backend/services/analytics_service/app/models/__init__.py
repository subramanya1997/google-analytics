"""
Response models for analytics service API endpoints.
"""

from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class LocationResponse(BaseModel):
    """Response model for location data."""
    locationId: str
    locationName: str
    city: Optional[str] = None
    state: Optional[str] = None


class DashboardStatsResponse(BaseModel):
    """Response model for dashboard statistics."""
    totalRevenue: str
    totalPurchases: int
    totalVisitors: int
    uniqueUsers: int
    abandonedCarts: int
    totalSearches: int
    failedSearches: int
    conversionRate: float


class ChartDataPoint(BaseModel):
    """Chart data point model."""
    date: str
    value: float
    label: Optional[str] = None


class LocationStatsResponse(BaseModel):
    """Location statistics response model."""
    locationId: str
    locationName: str
    revenue: float
    visitors: int
    purchases: int


class TaskStatusResponse(BaseModel):
    """Task status response model."""
    taskId: str
    taskType: str
    completed: bool
    notes: str
    completedAt: Optional[str] = None
    completedBy: Optional[str] = None


class TaskStatusRequest(BaseModel):
    """Task status request model."""
    taskId: str
    taskType: str


class TaskStatusUpdateRequest(BaseModel):
    """Task status update request model."""
    completed: bool
    notes: Optional[str] = ""
    completedBy: Optional[str] = ""


class TaskListRequest(BaseModel):
    """Task list request model."""
    taskType: Optional[str] = None
    completed: Optional[bool] = None


class PagedResponse(BaseModel):
    """Generic paged response model."""
    data: List[Dict[str, Any]]
    total: int
    page: int
    limit: int
    has_more: bool
