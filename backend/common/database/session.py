"""
Common database session management.
"""
from __future__ import annotations
import os

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker

from common.config import get_settings


def create_sqlalchemy_url(service_name: str = None) -> URL:
    """Create SQLAlchemy URL from environment variables."""
    # Use environment variables for main database connection
    # This is used by the auth service to store tenant configurations
    url = URL.create(
        drivername="postgresql+pg8000",
        username=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "pt9s>gdF#Y8SVIhX"),
        host=os.getenv("POSTGRES_HOST", "34.9.165.33"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DATABASE", "postgres"),
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
