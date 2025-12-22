"""
Control and analytics models - Tenant configuration (single-tenant-per-database model).
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, String, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from common.database import Base

class TenantConfig(Base):
    __tablename__ = "tenant_config"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(String(255))
    bigquery_project_id: Mapped[Optional[str]] = mapped_column(String(255))
    bigquery_dataset_id: Mapped[Optional[str]] = mapped_column(String(255))
    bigquery_credentials: Mapped[Optional[dict]] = mapped_column(JSONB)
    postgres_config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    sftp_config: Mapped[Optional[dict]] = mapped_column(JSONB)
    email_config: Mapped[Optional[dict]] = mapped_column(JSONB)
    bigquery_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sftp_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    smtp_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    bigquery_validation_error: Mapped[Optional[str]] = mapped_column(String)
    sftp_validation_error: Mapped[Optional[str]] = mapped_column(String)
    smtp_validation_error: Mapped[Optional[str]] = mapped_column(String)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)