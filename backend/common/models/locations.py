"""
Location management models.

This module defines location/warehouse entities with detailed address information,
contact details, and operational metadata for multi-tenant location tracking.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from common.database import Base

class Locations(Base):
    """Location/warehouse model with comprehensive address and contact information."""
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

    __table_args__ = (
        UniqueConstraint("tenant_id", "warehouse_id", name="uq_locations_tenant_warehouse"),
    )