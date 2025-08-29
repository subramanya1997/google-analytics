from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, String, TIMESTAMP, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

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


