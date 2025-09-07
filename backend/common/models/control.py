from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from sqlalchemy import TIMESTAMP, Date, String, Text, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, declared_attr

from common.database import Base


class ProcessingJobs(Base):
    __tablename__ = "processing_jobs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    tenant_id: Mapped[str] = mapped_column(UUID(as_uuid=False))
    job_id: Mapped[str] = mapped_column(String(255), unique=True)
    status: Mapped[str] = mapped_column(String(50))
    data_types: Mapped[dict] = mapped_column(JSONB)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    progress: Mapped[dict] = mapped_column(JSONB, default=dict)
    records_processed: Mapped[dict] = mapped_column(JSONB, default=dict)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True))