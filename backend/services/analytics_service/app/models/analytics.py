"""
Pydantic models for analytics service
"""
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field


# Request models
class DashboardStatsRequest(BaseModel):
    tenant_id: str = "default"
    location_id: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    granularity: str = "daily"
    timezone_offset: int = 0


class TaskListRequest(BaseModel):
    tenant_id: str = "default"
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=50, ge=1, le=1000)
    query: Optional[str] = None
    location_id: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class TaskStatusRequest(BaseModel):
    tenant_id: str = "default"
    task_id: str
    task_type: str


class TaskStatusUpdateRequest(BaseModel):
    tenant_id: str = "default"
    task_id: str
    task_type: str
    completed: bool
    notes: str = ""
    completed_by: str = ""


class SessionHistoryRequest(BaseModel):
    tenant_id: str = "default"
    session_id: str


class UserHistoryRequest(BaseModel):
    tenant_id: str = "default"
    user_id: str


# Response models
class LocationResponse(BaseModel):
    locationId: str
    locationName: str
    city: Optional[str] = None
    state: Optional[str] = None


class DashboardStatsResponse(BaseModel):
    totalRevenue: str
    purchases: int
    abandonedCarts: int
    failedSearches: int
    totalVisitors: int
    repeatVisits: int


class ChartDataPoint(BaseModel):
    date: str
    revenue: float
    purchases: int
    visitors: int


class LocationStatsResponse(BaseModel):
    locationId: str
    locationName: str
    revenue: float
    purchases: int
    visitors: int
    abandonedCarts: int
    repeatVisits: int


class ProductDetail(BaseModel):
    item_id: Optional[str] = None
    item_name: Optional[str] = None
    item_category: Optional[str] = None
    price: Optional[float] = None
    quantity: Optional[int] = None


class PurchaseTask(BaseModel):
    transaction_id: str
    event_date: str
    order_value: float
    page_location: str
    ga_session_id: str
    user_id: Optional[str] = None
    customer_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    products: List[ProductDetail] = []
    completed: bool = False


class CartAbandonmentTask(BaseModel):
    session_id: str
    event_date: str
    last_activity: str
    items_count: int
    total_value: Optional[float] = None
    user_id: Optional[str] = None
    customer_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    products: List[ProductDetail] = []
    completed: bool = False


class SearchAnalysisTask(BaseModel):
    session_id: str
    event_date: str
    search_term: str
    search_type: str  # 'no_results' or 'with_results'
    search_count: int
    user_id: Optional[str] = None
    customer_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    completed: bool = False


class PerformanceTask(BaseModel):
    session_id: str
    event_date: str
    bounce_type: str  # 'single_page' or 'quick_exit'
    page_views: int
    session_duration: Optional[float] = None
    user_id: Optional[str] = None
    customer_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    completed: bool = False


class RepeatVisitTask(BaseModel):
    product_url: str
    session_count: int
    last_view_date: str
    total_views: int
    user_id: Optional[str] = None
    customer_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    completed: bool = False


class TaskStatusResponse(BaseModel):
    taskId: str
    taskType: str
    completed: bool
    notes: str
    completedAt: Optional[str] = None
    completedBy: Optional[str] = None


class PagedResponse(BaseModel):
    data: List[Dict[str, Any]]
    total: int
    page: int
    limit: int
    has_more: bool


class SessionHistoryItem(BaseModel):
    title: str
    url: str
    event_timestamp: str
    event_date: str


class PurchaseHistoryItem(BaseModel):
    transaction_id: str
    event_date: str
    event_timestamp: str
    order_value: float
    items: List[Dict[str, Any]] = []


class CartActivityItem(BaseModel):
    event_timestamp: str
    event_date: str
    item_name: Optional[str] = None
    item_price: Optional[float] = None
    item_quantity: Optional[int] = None
    items: List[Dict[str, Any]] = []


class SearchHistoryItem(BaseModel):
    event_timestamp: str
    event_date: str
    search_term: str
    search_type: str


class SessionHistoryResponse(BaseModel):
    session_id: str
    user: Optional[Dict[str, Any]] = None
    page_views: List[SessionHistoryItem] = []
    purchases: List[PurchaseHistoryItem] = []
    cart_activity: List[CartActivityItem] = []
    searches: List[SearchHistoryItem] = []


class UserHistoryResponse(BaseModel):
    user_id: str
    user_info: Optional[Dict[str, Any]] = None
    sessions: List[Dict[str, Any]] = []
    total_sessions: int
    total_purchases: int
    total_revenue: float
