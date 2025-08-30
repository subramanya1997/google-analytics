"""
Control and analytics models - Tenants and Task tracking.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, String, TIMESTAMP, Text, UniqueConstraint, JSON, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from common.database import Base


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



