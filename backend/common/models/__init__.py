"""
Common ORM models for all backend services.

This module provides a comprehensive set of SQLAlchemy ORM models for the Google
Analytics Intelligence System, supporting multi-tenant analytics data management
and processing control.

Model Categories:

Control Models:
- ProcessingJobs: Data processing job tracking with progress monitoring

Dimension Models:
- Tenants: Multi-tenant configuration and service settings
- Users: User profile and organizational information  
- Locations: Warehouse and location management

Event Models:
- Purchase: E-commerce transaction events
- AddToCart: Shopping cart interaction events
- PageView: Website navigation events
- ViewSearchResults: Search interaction events
- NoSearchResults: Failed search tracking
- ViewItem: Product view events

All models inherit from the common Base class providing:
- Automatic UUID primary keys
- Created/updated timestamp tracking
- Consistent table naming conventions
- PostgreSQL-specific optimizations
"""

# Import all models to make them available
# TaskTracking import removed - functionality not needed
from .tenants import Tenants
from .users import Users
from .locations import Locations
from .events import Purchase, AddToCart, PageView, ViewSearchResults, NoSearchResults, ViewItem
from .control import ProcessingJobs

__all__ = [
    # Control/Analytics models (SQLAlchemy ORM)
    "Tenants",
    
    # Dimension models (SQLAlchemy ORM)
    "Users", "Locations",
    
    # Event models (SQLAlchemy ORM)
    "Purchase", "AddToCart", "PageView", "ViewSearchResults", "NoSearchResults", "ViewItem",
    
    # Data processing models (SQLAlchemy ORM)
    "ProcessingJobs",
]
