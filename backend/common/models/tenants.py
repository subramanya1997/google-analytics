"""
Control and analytics models - Tenants and Task tracking.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from common.database import Base

class Tenants(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(String(255))
    domain: Mapped[Optional[str]] = mapped_column(String(255))
    bigquery_project_id: Mapped[Optional[str]] = mapped_column(String(255))
    bigquery_dataset_id: Mapped[Optional[str]] = mapped_column(String(255))
    bigquery_credentials: Mapped[Optional[dict]] = mapped_column(JSONB)
    postgres_config: Mapped[Optional[dict]] = mapped_column(JSONB)
    sftp_config: Mapped[Optional[dict]] = mapped_column(JSONB)
    email_schedule: Mapped[Optional[str]] = mapped_column(String(255))
    data_ingestion_schedule: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint("domain", name="uq_tenants_domain"),
    )