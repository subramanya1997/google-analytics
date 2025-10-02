"""
Event models - User behavior and transaction events.

This module defines database models for storing Google Analytics events representing
user interactions and e-commerce transactions. These models capture detailed event
data from Google Analytics 4 including user properties, event parameters, device
information, and geographic data.

All event models share common patterns:
- Tenant isolation (tenant_id field)
- Event metadata (date, timestamp, user identification)
- Google Analytics parameters (ga_session_id, page information)
- Device and geographic context
- Raw data preservation for debugging and future analysis

Event Types Supported:
- Purchase: E-commerce transaction completion events
- AddToCart: Product addition to shopping cart events  
- PageView: Page navigation and view events
- ViewSearchResults: Search result page views with search terms
- NoSearchResults: Failed search attempts with zero results
- ViewItem: Individual product or item page views

Each model includes JSONB fields for flexible data storage:
- items_json: Structured product/item data
- raw_data: Complete original event data from Google Analytics

"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import DECIMAL, Date, String, Text, Integer
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import text

from common.database import Base


class Purchase(Base):
    """E-commerce purchase completion events with transaction details and purchased items."""
    __tablename__ = "purchase"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    event_date: Mapped[date] = mapped_column(Date)
    event_timestamp: Mapped[Optional[str]] = mapped_column(String(50))
    user_pseudo_id: Mapped[Optional[str]] = mapped_column(String(255))
    user_prop_webuserid: Mapped[Optional[str]] = mapped_column(String(100))
    user_prop_default_branch_id: Mapped[Optional[str]] = mapped_column(String(100))
    param_ga_session_id: Mapped[Optional[str]] = mapped_column(String(100))
    param_transaction_id: Mapped[Optional[str]] = mapped_column(String(100))
    param_page_title: Mapped[Optional[str]] = mapped_column(String(500))
    param_page_location: Mapped[Optional[str]] = mapped_column(Text)
    ecommerce_purchase_revenue: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(15, 2))
    items_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    device_category: Mapped[Optional[str]] = mapped_column(String(50))
    device_operating_system: Mapped[Optional[str]] = mapped_column(String(50))
    geo_country: Mapped[Optional[str]] = mapped_column(String(100))
    geo_city: Mapped[Optional[str]] = mapped_column(String(100))
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB)


class AddToCart(Base):
    """Shopping cart addition events with product details and user context."""
    __tablename__ = "add_to_cart"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    event_date: Mapped[date] = mapped_column(Date)
    event_timestamp: Mapped[Optional[str]] = mapped_column(String(50))
    user_pseudo_id: Mapped[Optional[str]] = mapped_column(String(255))
    user_prop_webuserid: Mapped[Optional[str]] = mapped_column(String(100))
    user_prop_default_branch_id: Mapped[Optional[str]] = mapped_column(String(100))
    param_ga_session_id: Mapped[Optional[str]] = mapped_column(String(100))
    param_page_title: Mapped[Optional[str]] = mapped_column(String(500))
    param_page_location: Mapped[Optional[str]] = mapped_column(Text)
    first_item_item_id: Mapped[Optional[str]] = mapped_column(String(255))
    first_item_item_name: Mapped[Optional[str]] = mapped_column(String(500))
    first_item_item_category: Mapped[Optional[str]] = mapped_column(String(255))
    first_item_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 2))
    first_item_quantity: Mapped[Optional[int]] = mapped_column(Integer)
    items_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    device_category: Mapped[Optional[str]] = mapped_column(String(50))
    device_operating_system: Mapped[Optional[str]] = mapped_column(String(50))
    geo_country: Mapped[Optional[str]] = mapped_column(String(100))
    geo_city: Mapped[Optional[str]] = mapped_column(String(100))
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB)


class PageView(Base):
    """Page navigation and view events with referrer and device information."""
    __tablename__ = "page_view"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    event_date: Mapped[date] = mapped_column(Date)
    event_timestamp: Mapped[Optional[str]] = mapped_column(String(50))
    user_pseudo_id: Mapped[Optional[str]] = mapped_column(String(255))
    user_prop_webuserid: Mapped[Optional[str]] = mapped_column(String(100))
    user_prop_default_branch_id: Mapped[Optional[str]] = mapped_column(String(100))
    param_ga_session_id: Mapped[Optional[str]] = mapped_column(String(100))
    param_page_title: Mapped[Optional[str]] = mapped_column(String(500))
    param_page_location: Mapped[Optional[str]] = mapped_column(Text)
    param_page_referrer: Mapped[Optional[str]] = mapped_column(Text)
    device_category: Mapped[Optional[str]] = mapped_column(String(50))
    device_operating_system: Mapped[Optional[str]] = mapped_column(String(50))
    geo_country: Mapped[Optional[str]] = mapped_column(String(100))
    geo_city: Mapped[Optional[str]] = mapped_column(String(100))
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB)


class ViewSearchResults(Base):
    """Search result page views with search terms and context."""
    __tablename__ = "view_search_results"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    event_date: Mapped[date] = mapped_column(Date)
    event_timestamp: Mapped[Optional[str]] = mapped_column(String(50))
    user_pseudo_id: Mapped[Optional[str]] = mapped_column(String(255))
    user_prop_webuserid: Mapped[Optional[str]] = mapped_column(String(100))
    user_prop_default_branch_id: Mapped[Optional[str]] = mapped_column(String(100))
    param_ga_session_id: Mapped[Optional[str]] = mapped_column(String(100))
    param_search_term: Mapped[Optional[str]] = mapped_column(String(500))
    param_page_title: Mapped[Optional[str]] = mapped_column(String(500))
    param_page_location: Mapped[Optional[str]] = mapped_column(Text)
    device_category: Mapped[Optional[str]] = mapped_column(String(50))
    device_operating_system: Mapped[Optional[str]] = mapped_column(String(50))
    geo_country: Mapped[Optional[str]] = mapped_column(String(100))
    geo_city: Mapped[Optional[str]] = mapped_column(String(100))
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB)


class NoSearchResults(Base):
    """Failed search attempts that returned zero results."""
    __tablename__ = "no_search_results"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    event_date: Mapped[date] = mapped_column(Date)
    event_timestamp: Mapped[Optional[str]] = mapped_column(String(50))
    user_pseudo_id: Mapped[Optional[str]] = mapped_column(String(255))
    user_prop_webuserid: Mapped[Optional[str]] = mapped_column(String(100))
    user_prop_default_branch_id: Mapped[Optional[str]] = mapped_column(String(100))
    param_ga_session_id: Mapped[Optional[str]] = mapped_column(String(100))
    param_no_search_results_term: Mapped[Optional[str]] = mapped_column(String(500))
    param_page_title: Mapped[Optional[str]] = mapped_column(String(500))
    param_page_location: Mapped[Optional[str]] = mapped_column(Text)
    device_category: Mapped[Optional[str]] = mapped_column(String(50))
    device_operating_system: Mapped[Optional[str]] = mapped_column(String(50))
    geo_country: Mapped[Optional[str]] = mapped_column(String(100))
    geo_city: Mapped[Optional[str]] = mapped_column(String(100))
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB)


class ViewItem(Base):
    """Individual product or item page view events with item details."""
    __tablename__ = "view_item"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    event_date: Mapped[date] = mapped_column(Date)
    event_timestamp: Mapped[Optional[str]] = mapped_column(String(50))
    user_pseudo_id: Mapped[Optional[str]] = mapped_column(String(255))
    user_prop_webuserid: Mapped[Optional[str]] = mapped_column(String(100))
    user_prop_default_branch_id: Mapped[Optional[str]] = mapped_column(String(100))
    param_ga_session_id: Mapped[Optional[str]] = mapped_column(String(100))
    first_item_item_id: Mapped[Optional[str]] = mapped_column(String(255))
    first_item_item_name: Mapped[Optional[str]] = mapped_column(String(500))
    first_item_item_category: Mapped[Optional[str]] = mapped_column(String(255))
    first_item_price: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 2))
    param_page_title: Mapped[Optional[str]] = mapped_column(String(500))
    param_page_location: Mapped[Optional[str]] = mapped_column(Text)
    items_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    device_category: Mapped[Optional[str]] = mapped_column(String(50))
    device_operating_system: Mapped[Optional[str]] = mapped_column(String(50))
    geo_country: Mapped[Optional[str]] = mapped_column(String(100))
    geo_city: Mapped[Optional[str]] = mapped_column(String(100))
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB)