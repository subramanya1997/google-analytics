"""
Common ORM models for all backend services.

This module provides SQLAlchemy ORM models that represent database tables used
across all backend services. Models are organized into two categories:

1. Control Models: System-level tables for job tracking and processing
   - ProcessingJobs: Tracks data ingestion and processing jobs

2. Event Models: User behavior and analytics event tables
   - PageView: Page view events
   - AddToCart: Add to cart events
   - Purchase: Purchase/transaction events
   - ViewItem: Product view events
   - ViewSearchResults: Search result view events
   - NoSearchResults: No search results events

All models inherit from common.database.Base, which provides:
- Automatic created_at and updated_at timestamps
- Automatic table name generation

Usage:
    ```python
    from common.models import PageView, Purchase, ProcessingJobs
    
    # Query events
    page_views = session.query(PageView).filter_by(tenant_id="tenant-123").all()
    
    # Create new event
    purchase = Purchase(
        tenant_id="tenant-123",
        event_date=date.today(),
        user_pseudo_id="user-456",
        ecommerce_purchase_revenue=Decimal("99.99")
    )
    session.add(purchase)
    ```
"""

# Import all models to make them available
from .control import ProcessingJobs
from .events import (
    AddToCart,
    NoSearchResults,
    PageView,
    Purchase,
    ViewItem,
    ViewSearchResults,
)

__all__ = [
    "AddToCart",
    "NoSearchResults",
    "PageView",
    # Data processing models (SQLAlchemy ORM)
    "ProcessingJobs",
    # Event models (SQLAlchemy ORM)
    "Purchase",
    "ViewItem",
    "ViewSearchResults",
]
