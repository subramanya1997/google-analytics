"""
User models - User entities.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Boolean, String, TIMESTAMP, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from common.database import Base


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

    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_users_tenant_user"),
    )