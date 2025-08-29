from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


def create_sqlalchemy_url() -> URL:
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


def get_engine():
    url = create_sqlalchemy_url()
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
    )


SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)


