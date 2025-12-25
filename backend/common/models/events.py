"""
Event models for user behavior and transaction tracking.

This module contains ORM models representing analytics events captured from
Google Analytics. These models store user interactions, transactions, and
behavioral data for analysis and reporting.

Event Types:
    - PageView: Page navigation events
    - AddToCart: Shopping cart addition events
    - Purchase: Transaction/purchase events
    - ViewItem: Product detail view events
    - ViewSearchResults: Search query and results view events
    - NoSearchResults: Search queries with no results

Common Fields:
    All event models share common fields:
    - tenant_id: Tenant identifier for multi-tenant isolation
    - event_date: Date of the event
    - event_timestamp: Precise timestamp of the event
    - user_pseudo_id: Google Analytics user identifier
    - user_prop_webuserid: Web user ID (if available)
    - user_prop_default_branch_id: User's default branch/store
    - param_ga_session_id: Google Analytics session identifier
    - device_category: Device type (desktop, mobile, tablet)
    - device_operating_system: OS information
    - geo_country: Country from IP geolocation
    - geo_city: City from IP geolocation
    - raw_data: Complete raw event data in JSONB format

Usage:
    ```python
    from common.models import PageView, Purchase
    from datetime import date
    
    # Create a page view event
    page_view = PageView(
        tenant_id="tenant-123",
        event_date=date.today(),
        user_pseudo_id="user-456",
        param_page_title="Product Page",
        param_page_location="/products/item-123"
    )
    session.add(page_view)
    ```
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import DECIMAL, Date, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from common.database import Base


class Purchase(Base):
    """
    Model representing purchase/transaction events.

    This model stores completed purchase transactions with revenue, items,
    and transaction details. It's one of the most important event types for
    e-commerce analytics.

    Attributes:
        id (str): Unique event identifier (UUID). Primary key. Auto-generated.
        tenant_id (str): Tenant ID (UUID). Required for multi-tenant isolation.
        event_date (date): Date when the purchase occurred.
        event_timestamp (str | None): Precise timestamp of the purchase event.
        user_pseudo_id (str | None): Google Analytics user identifier.
        user_prop_webuserid (str | None): Web user ID if user is authenticated.
        user_prop_default_branch_id (str | None): User's default branch/store ID.
        param_ga_session_id (str | None): Google Analytics session identifier.
        param_transaction_id (str | None): Unique transaction identifier.
        param_page_title (str | None): Title of the page where purchase occurred.
        param_page_location (str | None): URL of the purchase page.
        ecommerce_purchase_revenue (Decimal | None): Total revenue for this purchase.
            Stored as DECIMAL(15, 2) for precision.
        items_json (dict | None): JSONB object containing purchased items array.
            Structure: [{"item_id": "...", "item_name": "...", "price": ..., "quantity": ...}]
        device_category (str | None): Device type: "desktop", "mobile", or "tablet".
        device_operating_system (str | None): Operating system name.
        geo_country (str | None): Country from IP geolocation.
        geo_city (str | None): City from IP geolocation.
        raw_data (dict | None): Complete raw event data in JSONB format.

    Table:
        purchase

    Example:
        ```python
        from common.models import Purchase
        from decimal import Decimal
        from datetime import date
        
        purchase = Purchase(
            tenant_id="tenant-123",
            event_date=date(2024, 1, 15),
            event_timestamp="1705276800000",
            user_pseudo_id="user-456",
            param_transaction_id="txn-789",
            param_page_title="Order Confirmation",
            ecommerce_purchase_revenue=Decimal("99.99"),
            items_json=[
                {
                    "item_id": "prod-123",
                    "item_name": "Product Name",
                    "price": 99.99,
                    "quantity": 1
                }
            ],
            device_category="desktop",
            geo_country="United States"
        )
        ```

    Note:
        - Revenue is stored as Decimal for financial precision
        - Transaction ID should be unique per purchase
        - Items JSON contains full product details
    """
    __tablename__ = "purchase"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    event_date: Mapped[date] = mapped_column(Date)
    event_timestamp: Mapped[str | None] = mapped_column(String(50))
    user_pseudo_id: Mapped[str | None] = mapped_column(String(255))
    user_prop_webuserid: Mapped[str | None] = mapped_column(String(100))
    user_prop_default_branch_id: Mapped[str | None] = mapped_column(String(100))
    param_ga_session_id: Mapped[str | None] = mapped_column(String(100))
    param_transaction_id: Mapped[str | None] = mapped_column(String(100))
    param_page_title: Mapped[str | None] = mapped_column(String(500))
    param_page_location: Mapped[str | None] = mapped_column(Text)
    ecommerce_purchase_revenue: Mapped[Decimal | None] = mapped_column(DECIMAL(15, 2))
    items_json: Mapped[dict | None] = mapped_column(JSONB)
    device_category: Mapped[str | None] = mapped_column(String(50))
    device_operating_system: Mapped[str | None] = mapped_column(String(50))
    geo_country: Mapped[str | None] = mapped_column(String(100))
    geo_city: Mapped[str | None] = mapped_column(String(100))
    raw_data: Mapped[dict | None] = mapped_column(JSONB)


class AddToCart(Base):
    """
    Model representing add-to-cart events.

    This model tracks when users add items to their shopping cart. It's useful
    for analyzing cart abandonment and product interest.

    Attributes:
        id (str): Unique event identifier (UUID). Primary key. Auto-generated.
        tenant_id (str): Tenant ID (UUID). Required for multi-tenant isolation.
        event_date (date): Date when the item was added to cart.
        event_timestamp (str | None): Precise timestamp of the event.
        user_pseudo_id (str | None): Google Analytics user identifier.
        user_prop_webuserid (str | None): Web user ID if user is authenticated.
        user_prop_default_branch_id (str | None): User's default branch/store ID.
        param_ga_session_id (str | None): Google Analytics session identifier.
        param_page_title (str | None): Title of the page where add-to-cart occurred.
        param_page_location (str | None): URL of the page.
        first_item_item_id (str | None): Item ID of the first item added.
        first_item_item_name (str | None): Name of the first item added.
        first_item_item_category (str | None): Category of the first item.
        first_item_price (Decimal | None): Price of the first item (DECIMAL(10, 2)).
        first_item_quantity (int | None): Quantity of the first item added.
        items_json (dict | None): JSONB object containing all items added to cart.
        device_category (str | None): Device type: "desktop", "mobile", or "tablet".
        device_operating_system (str | None): Operating system name.
        geo_country (str | None): Country from IP geolocation.
        geo_city (str | None): City from IP geolocation.
        raw_data (dict | None): Complete raw event data in JSONB format.

    Table:
        add_to_cart

    Note:
        - First item fields provide quick access to primary item without parsing JSON
        - Items JSON contains full details of all items added in this event
    """
    __tablename__ = "add_to_cart"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    event_date: Mapped[date] = mapped_column(Date)
    event_timestamp: Mapped[str | None] = mapped_column(String(50))
    user_pseudo_id: Mapped[str | None] = mapped_column(String(255))
    user_prop_webuserid: Mapped[str | None] = mapped_column(String(100))
    user_prop_default_branch_id: Mapped[str | None] = mapped_column(String(100))
    param_ga_session_id: Mapped[str | None] = mapped_column(String(100))
    param_page_title: Mapped[str | None] = mapped_column(String(500))
    param_page_location: Mapped[str | None] = mapped_column(Text)
    first_item_item_id: Mapped[str | None] = mapped_column(String(255))
    first_item_item_name: Mapped[str | None] = mapped_column(String(500))
    first_item_item_category: Mapped[str | None] = mapped_column(String(255))
    first_item_price: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 2))
    first_item_quantity: Mapped[int | None] = mapped_column(Integer)
    items_json: Mapped[dict | None] = mapped_column(JSONB)
    device_category: Mapped[str | None] = mapped_column(String(50))
    device_operating_system: Mapped[str | None] = mapped_column(String(50))
    geo_country: Mapped[str | None] = mapped_column(String(100))
    geo_city: Mapped[str | None] = mapped_column(String(100))
    raw_data: Mapped[dict | None] = mapped_column(JSONB)


class PageView(Base):
    """
    Model representing page view events.

    This model tracks page navigation events, which are the most common type of
    analytics event. It captures page visits, referrers, and user context.

    Attributes:
        id (str): Unique event identifier (UUID). Primary key. Auto-generated.
        tenant_id (str): Tenant ID (UUID). Required for multi-tenant isolation.
        event_date (date): Date when the page was viewed.
        event_timestamp (str | None): Precise timestamp of the page view.
        user_pseudo_id (str | None): Google Analytics user identifier.
        user_prop_webuserid (str | None): Web user ID if user is authenticated.
        user_prop_default_branch_id (str | None): User's default branch/store ID.
        param_ga_session_id (str | None): Google Analytics session identifier.
        param_page_title (str | None): Title of the viewed page.
        param_page_location (str | None): Full URL of the viewed page.
        param_page_referrer (str | None): URL of the referring page (if any).
        device_category (str | None): Device type: "desktop", "mobile", or "tablet".
        device_operating_system (str | None): Operating system name.
        geo_country (str | None): Country from IP geolocation.
        geo_city (str | None): City from IP geolocation.
        raw_data (dict | None): Complete raw event data in JSONB format.

    Table:
        page_view

    Note:
        - Page referrer helps track traffic sources
        - This is typically the highest-volume event type
    """
    __tablename__ = "page_view"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    event_date: Mapped[date] = mapped_column(Date)
    event_timestamp: Mapped[str | None] = mapped_column(String(50))
    user_pseudo_id: Mapped[str | None] = mapped_column(String(255))
    user_prop_webuserid: Mapped[str | None] = mapped_column(String(100))
    user_prop_default_branch_id: Mapped[str | None] = mapped_column(String(100))
    param_ga_session_id: Mapped[str | None] = mapped_column(String(100))
    param_page_title: Mapped[str | None] = mapped_column(String(500))
    param_page_location: Mapped[str | None] = mapped_column(Text)
    param_page_referrer: Mapped[str | None] = mapped_column(Text)
    device_category: Mapped[str | None] = mapped_column(String(50))
    device_operating_system: Mapped[str | None] = mapped_column(String(50))
    geo_country: Mapped[str | None] = mapped_column(String(100))
    geo_city: Mapped[str | None] = mapped_column(String(100))
    raw_data: Mapped[dict | None] = mapped_column(JSONB)


class ViewSearchResults(Base):
    """
    Model representing search result view events.

    This model tracks when users view search results, including the search term
    and result page information. Useful for analyzing search behavior and
    search effectiveness.

    Attributes:
        id (str): Unique event identifier (UUID). Primary key. Auto-generated.
        tenant_id (str): Tenant ID (UUID). Required for multi-tenant isolation.
        event_date (date): Date when search results were viewed.
        event_timestamp (str | None): Precise timestamp of the event.
        user_pseudo_id (str | None): Google Analytics user identifier.
        user_prop_webuserid (str | None): Web user ID if user is authenticated.
        user_prop_default_branch_id (str | None): User's default branch/store ID.
        param_ga_session_id (str | None): Google Analytics session identifier.
        param_search_term (str | None): The search query entered by the user.
        param_page_title (str | None): Title of the search results page.
        param_page_location (str | None): URL of the search results page.
        device_category (str | None): Device type: "desktop", "mobile", or "tablet".
        device_operating_system (str | None): Operating system name.
        geo_country (str | None): Country from IP geolocation.
        geo_city (str | None): City from IP geolocation.
        raw_data (dict | None): Complete raw event data in JSONB format.

    Table:
        view_search_results

    Note:
        - Search term is crucial for understanding user intent
        - Often analyzed alongside NoSearchResults for search quality metrics
    """
    __tablename__ = "view_search_results"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    event_date: Mapped[date] = mapped_column(Date)
    event_timestamp: Mapped[str | None] = mapped_column(String(50))
    user_pseudo_id: Mapped[str | None] = mapped_column(String(255))
    user_prop_webuserid: Mapped[str | None] = mapped_column(String(100))
    user_prop_default_branch_id: Mapped[str | None] = mapped_column(String(100))
    param_ga_session_id: Mapped[str | None] = mapped_column(String(100))
    param_search_term: Mapped[str | None] = mapped_column(String(500))
    param_page_title: Mapped[str | None] = mapped_column(String(500))
    param_page_location: Mapped[str | None] = mapped_column(Text)
    device_category: Mapped[str | None] = mapped_column(String(50))
    device_operating_system: Mapped[str | None] = mapped_column(String(50))
    geo_country: Mapped[str | None] = mapped_column(String(100))
    geo_city: Mapped[str | None] = mapped_column(String(100))
    raw_data: Mapped[dict | None] = mapped_column(JSONB)


class NoSearchResults(Base):
    """
    Model representing search queries that returned no results.

    This model tracks failed search attempts, which are important for identifying
    gaps in product catalog, improving search functionality, and understanding
    user intent.

    Attributes:
        id (str): Unique event identifier (UUID). Primary key. Auto-generated.
        tenant_id (str): Tenant ID (UUID). Required for multi-tenant isolation.
        event_date (date): Date when the search with no results occurred.
        event_timestamp (str | None): Precise timestamp of the event.
        user_pseudo_id (str | None): Google Analytics user identifier.
        user_prop_webuserid (str | None): Web user ID if user is authenticated.
        user_prop_default_branch_id (str | None): User's default branch/store ID.
        param_ga_session_id (str | None): Google Analytics session identifier.
        param_no_search_results_term (str | None): The search query that returned no results.
        param_page_title (str | None): Title of the page where search occurred.
        param_page_location (str | None): URL of the search page.
        device_category (str | None): Device type: "desktop", "mobile", or "tablet".
        device_operating_system (str | None): Operating system name.
        geo_country (str | None): Country from IP geolocation.
        geo_city (str | None): City from IP geolocation.
        raw_data (dict | None): Complete raw event data in JSONB format.

    Table:
        no_search_results

    Note:
        - Critical for identifying search quality issues
        - Can be used to suggest product additions or search improvements
    """
    __tablename__ = "no_search_results"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    event_date: Mapped[date] = mapped_column(Date)
    event_timestamp: Mapped[str | None] = mapped_column(String(50))
    user_pseudo_id: Mapped[str | None] = mapped_column(String(255))
    user_prop_webuserid: Mapped[str | None] = mapped_column(String(100))
    user_prop_default_branch_id: Mapped[str | None] = mapped_column(String(100))
    param_ga_session_id: Mapped[str | None] = mapped_column(String(100))
    param_no_search_results_term: Mapped[str | None] = mapped_column(String(500))
    param_page_title: Mapped[str | None] = mapped_column(String(500))
    param_page_location: Mapped[str | None] = mapped_column(Text)
    device_category: Mapped[str | None] = mapped_column(String(50))
    device_operating_system: Mapped[str | None] = mapped_column(String(50))
    geo_country: Mapped[str | None] = mapped_column(String(100))
    geo_city: Mapped[str | None] = mapped_column(String(100))
    raw_data: Mapped[dict | None] = mapped_column(JSONB)


class ViewItem(Base):
    """
    Model representing product/item detail view events.

    This model tracks when users view individual product/item pages. It's useful
    for analyzing product interest, popular items, and user browsing behavior.

    Attributes:
        id (str): Unique event identifier (UUID). Primary key. Auto-generated.
        tenant_id (str): Tenant ID (UUID). Required for multi-tenant isolation.
        event_date (date): Date when the item was viewed.
        event_timestamp (str | None): Precise timestamp of the event.
        user_pseudo_id (str | None): Google Analytics user identifier.
        user_prop_webuserid (str | None): Web user ID if user is authenticated.
        user_prop_default_branch_id (str | None): User's default branch/store ID.
        param_ga_session_id (str | None): Google Analytics session identifier.
        first_item_item_id (str | None): Item ID of the viewed item.
        first_item_item_name (str | None): Name of the viewed item.
        first_item_item_category (str | None): Category of the viewed item.
        first_item_price (Decimal | None): Price of the viewed item (DECIMAL(10, 2)).
        param_page_title (str | None): Title of the item detail page.
        param_page_location (str | None): URL of the item detail page.
        items_json (dict | None): JSONB object containing item details.
        device_category (str | None): Device type: "desktop", "mobile", or "tablet".
        device_operating_system (str | None): Operating system name.
        geo_country (str | None): Country from IP geolocation.
        geo_city (str | None): City from IP geolocation.
        raw_data (dict | None): Complete raw event data in JSONB format.

    Table:
        view_item

    Note:
        - First item fields provide quick access without parsing JSON
        - Often analyzed alongside Purchase events for conversion funnel analysis
    """
    __tablename__ = "view_item"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    event_date: Mapped[date] = mapped_column(Date)
    event_timestamp: Mapped[str | None] = mapped_column(String(50))
    user_pseudo_id: Mapped[str | None] = mapped_column(String(255))
    user_prop_webuserid: Mapped[str | None] = mapped_column(String(100))
    user_prop_default_branch_id: Mapped[str | None] = mapped_column(String(100))
    param_ga_session_id: Mapped[str | None] = mapped_column(String(100))
    first_item_item_id: Mapped[str | None] = mapped_column(String(255))
    first_item_item_name: Mapped[str | None] = mapped_column(String(500))
    first_item_item_category: Mapped[str | None] = mapped_column(String(255))
    first_item_price: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 2))
    param_page_title: Mapped[str | None] = mapped_column(String(500))
    param_page_location: Mapped[str | None] = mapped_column(Text)
    items_json: Mapped[dict | None] = mapped_column(JSONB)
    device_category: Mapped[str | None] = mapped_column(String(50))
    device_operating_system: Mapped[str | None] = mapped_column(String(50))
    geo_country: Mapped[str | None] = mapped_column(String(100))
    geo_city: Mapped[str | None] = mapped_column(String(100))
    raw_data: Mapped[dict | None] = mapped_column(JSONB)
