"""
Common database session management.
"""
from __future__ import annotations
import os
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

def create_sqlalchemy_url() -> URL:
    """Create SQLAlchemy URL from environment variables."""
    url = URL.create(
        drivername="postgresql+pg8000",
        username=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST"),
        port=int(os.getenv("POSTGRES_PORT")),
        database=os.getenv("POSTGRES_DATABASE"),
    )
    return url


def get_engine(service_name: str = None):
    """Get database engine with connection pooling."""
    url = create_sqlalchemy_url()
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=int(os.getenv("DATABASE_POOL_SIZE", 10)),
        max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", 5)),
    )


SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
