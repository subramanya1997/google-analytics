"""
Common database session management.
"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker

from common.config import get_settings


def create_sqlalchemy_url(service_name: str = None) -> URL:
    """Create SQLAlchemy URL from configuration."""
    settings = get_settings(service_name)
    cfg = settings.get_postgres_config()
    url = URL.create(
        drivername="postgresql+pg8000",
        username=cfg.get("user"),
        password=cfg.get("password"),
        host=cfg.get("host"),
        port=int(cfg.get("port", 5432)),
        database=cfg.get("database", "postgres"),
    )
    return url


def get_engine(service_name: str = None):
    """Get database engine with connection pooling."""
    settings = get_settings(service_name)
    url = create_sqlalchemy_url(service_name)
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
    )


SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
