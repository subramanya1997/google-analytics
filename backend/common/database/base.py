"""
Base declarative class for all ORM models.
"""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase, declared_attr

from datetime import datetime
from sqlalchemy import TIMESTAMP, text
from sqlalchemy.orm import Mapped, mapped_column

class Base(DeclarativeBase):
    """Base declarative class for all ORM models."""

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    @declared_attr.directive
    def __tablename__(cls) -> str:  # type: ignore[override]
        return cls.__name__.lower()
