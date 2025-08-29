from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from sqlalchemy import DECIMAL, Date, String, TIMESTAMP, Text, Integer, Boolean, UniqueConstraint, JSON
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import text

from .base import Base


class Users(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    user_id: Mapped[Optional[str]] = mapped_column(String(100))
    user_name: Mapped[Optional[str]] = mapped_column(String(255))
    first_name: Mapped[Optional[str]] = mapped_column(String(255))
    middle_name: Mapped[Optional[str]] = mapped_column(String(255))
    last_name: Mapped[Optional[str]] = mapped_column(String(255))
    job_title: Mapped[Optional[str]] = mapped_column(String(255))
    user_erp_id: Mapped[Optional[str]] = mapped_column(String(100))
    fax: Mapped[Optional[str]] = mapped_column(String(50))
    address1: Mapped[Optional[str]] = mapped_column(String(255))
    address2: Mapped[Optional[str]] = mapped_column(String(255))
    address3: Mapped[Optional[str]] = mapped_column(String(255))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    state: Mapped[Optional[str]] = mapped_column(String(100))
    country: Mapped[Optional[str]] = mapped_column(String(100))
    office_phone: Mapped[Optional[str]] = mapped_column(String(50))
    cell_phone: Mapped[Optional[str]] = mapped_column(String(50))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    registered_date: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    zip: Mapped[Optional[str]] = mapped_column(String(20))
    warehouse_code: Mapped[Optional[str]] = mapped_column(String(100))
    last_login_date: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    cimm_buying_company_id: Mapped[Optional[str]] = mapped_column(String(100))
    buying_company_name: Mapped[Optional[str]] = mapped_column(String(255))
    buying_company_erp_id: Mapped[Optional[str]] = mapped_column(String(100))
    role_name: Mapped[Optional[str]] = mapped_column(String(100))
    site_name: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_users_tenant_user"),
    )


class Locations(Base):
    __tablename__ = "locations"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    warehouse_id: Mapped[Optional[str]] = mapped_column(String(100))
    warehouse_code: Mapped[Optional[str]] = mapped_column(String(100))
    warehouse_name: Mapped[Optional[str]] = mapped_column(String(255))
    address1: Mapped[Optional[str]] = mapped_column(String(255))
    address2: Mapped[Optional[str]] = mapped_column(String(255))
    address3: Mapped[Optional[str]] = mapped_column(String(255))
    country: Mapped[Optional[str]] = mapped_column(String(100))
    city: Mapped[Optional[str]] = mapped_column(String(100))
    state: Mapped[Optional[str]] = mapped_column(String(100))
    zip: Mapped[Optional[str]] = mapped_column(String(20))
    user_edited: Mapped[Optional[str]] = mapped_column(String(255))
    updated_datetime: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    phone_number: Mapped[Optional[str]] = mapped_column(String(50))
    keywords: Mapped[Optional[str]] = mapped_column(String(500))
    subset_id: Mapped[Optional[str]] = mapped_column(String(100))
    fax: Mapped[Optional[str]] = mapped_column(String(50))
    latitude: Mapped[Optional[str]] = mapped_column(String(50))
    longitude: Mapped[Optional[str]] = mapped_column(String(50))
    service_manager: Mapped[Optional[str]] = mapped_column(String(255))
    wfl_phase_id: Mapped[Optional[str]] = mapped_column(String(100))
    work_hour: Mapped[Optional[str]] = mapped_column(String(255))
    note: Mapped[Optional[str]] = mapped_column(String(1000))
    ac: Mapped[Optional[str]] = mapped_column(String(100))
    branch_location_id: Mapped[Optional[str]] = mapped_column(String(100))
    toll_free_number: Mapped[Optional[str]] = mapped_column(String(50))
    status: Mapped[Optional[str]] = mapped_column(String(50))
    cne_batch_id: Mapped[Optional[str]] = mapped_column(String(100))
    external_system_ref_id: Mapped[Optional[str]] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    __table_args__ = (
        UniqueConstraint("tenant_id", "warehouse_id", name="uq_locations_tenant_warehouse"),
    )


class Tenants(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(String(255))
    domain: Mapped[Optional[str]] = mapped_column(String(255))
    bigquery_project_id: Mapped[Optional[str]] = mapped_column(String(255))
    bigquery_dataset_id: Mapped[Optional[str]] = mapped_column(String(255))
    bigquery_credentials: Mapped[Optional[dict]] = mapped_column(JSON)
    sftp_config: Mapped[Optional[dict]] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))

    __table_args__ = (
        UniqueConstraint("domain", name="uq_tenants_domain"),
    )

class TaskTracking(Base):
    __tablename__ = "task_tracking"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    task_id: Mapped[str] = mapped_column(String(255))
    task_type: Mapped[str] = mapped_column(String(100))
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    completed_by: Mapped[Optional[str]] = mapped_column(String(255))
    completed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    __table_args__ = (
        UniqueConstraint("tenant_id", "task_id", "task_type", name="uq_task_tracking_tenant_task_type"),
    )


class Purchase(Base):
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
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))


class AddToCart(Base):
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
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))


class PageView(Base):
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
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))


class ViewSearchResults(Base):
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
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))


class NoSearchResults(Base):
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
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))


class ViewItem(Base):
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
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))