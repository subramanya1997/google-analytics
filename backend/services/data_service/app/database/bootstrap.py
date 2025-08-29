from __future__ import annotations

from sqlalchemy import text

from app.database.sqlalchemy_session import get_engine
from app.database.table_schemas import TABLE_SCHEMAS


def run_bootstrap() -> None:
    engine = get_engine()
    with engine.begin() as conn:
        # Ensure pgcrypto for gen_random_uuid()
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto;"))

        # Create tables
        for name, sql in TABLE_SCHEMAS.items():
            conn.execute(text(sql))


def drop_all() -> None:
    """Drop all analytics tables defined in TABLE_SCHEMAS (CASCADE)."""
    engine = get_engine()
    with engine.begin() as conn:
        for name in TABLE_SCHEMAS.keys():
            conn.execute(text(f"DROP TABLE IF EXISTS {name} CASCADE;"))


def reset_and_bootstrap() -> None:
    """Convenience helper to drop then recreate everything."""
    drop_all()
    run_bootstrap()


if __name__ == "__main__":
    run_bootstrap()


