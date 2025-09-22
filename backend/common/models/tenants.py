"""
Tenant management models.

This module defines the tenant model for multi-tenant system support, storing
tenant-specific configurations for BigQuery, PostgreSQL, SFTP, and other services.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from common.database import Base

class Tenants(Base):
    """
    Multi-tenant configuration model storing per-tenant service configurations.
    
    Manages tenant-specific settings including database connections, API credentials,
    and service configurations for BigQuery, PostgreSQL, and SFTP integrations.
    """
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(String(255))
    domain: Mapped[Optional[str]] = mapped_column(String(255))
    bigquery_project_id: Mapped[Optional[str]] = mapped_column(String(255))
    bigquery_dataset_id: Mapped[Optional[str]] = mapped_column(String(255))
    bigquery_credentials: Mapped[Optional[dict]] = mapped_column(JSONB)
    postgres_config: Mapped[Optional[dict]] = mapped_column(JSONB)
    sftp_config: Mapped[Optional[dict]] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint("domain", name="uq_tenants_domain"),
    )