"""
Re-apply all SQL functions to existing tenant databases.

Safe to run on live databases since all functions use CREATE OR REPLACE FUNCTION.
Discovers all tenant databases (google-analytics-*) and applies every .sql file
from backend/database/functions/ to each one.

Usage:
    python scripts/migrate_functions.py              # apply to ALL tenant databases
    python scripts/migrate_functions.py <tenant_id>  # apply to one tenant only
"""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

sys.path.append(str(Path(__file__).parent.parent.resolve()))

from common.database.session import create_sqlalchemy_url
from common.database.tenant_provisioning import FUNCTIONS_DIR, get_tenant_database_name
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine


def discover_tenant_databases() -> list[str]:
    """Return all database names matching google-analytics-*."""
    postgres_url = create_sqlalchemy_url("postgres")
    engine = create_engine(postgres_url)
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT datname FROM pg_database WHERE datname LIKE 'google-analytics-%'")
        )
        db_names = [row[0] for row in result]
    engine.dispose()
    return db_names


async def apply_functions(db_name: str) -> bool:
    """Apply all function SQL files to a single database."""
    try:
        function_files = sorted(f for f in FUNCTIONS_DIR.iterdir() if f.suffix == ".sql")
        if not function_files:
            logger.warning("No function SQL files found.")
            return False

        url = create_sqlalchemy_url(db_name, async_driver=True)
        async_engine = create_async_engine(url, echo=False)

        async with async_engine.begin() as connection:
            for filepath in function_files:
                sql_content = filepath.read_text(encoding="utf-8").strip()
                if not sql_content:
                    continue
                logger.info(f"  [{db_name}] Applying {filepath.name}")
                raw_conn = await connection.get_raw_connection()
                await raw_conn.driver_connection.execute(sql_content)

        await async_engine.dispose()
        logger.info(f"  [{db_name}] All functions applied successfully.")
        return True

    except Exception as e:
        logger.error(f"  [{db_name}] Error applying functions: {e}")
        return False


async def main() -> None:
    single_tenant = sys.argv[1] if len(sys.argv) > 1 else None

    if single_tenant:
        db_names = [get_tenant_database_name(single_tenant)]
        logger.info(f"Targeting single tenant database: {db_names[0]}")
    else:
        db_names = discover_tenant_databases()
        logger.info(f"Discovered {len(db_names)} tenant database(s).")

    if not db_names:
        logger.warning("No tenant databases found.")
        return

    success_count = 0
    for db_name in db_names:
        logger.info(f"Migrating functions for {db_name}...")
        if await apply_functions(db_name):
            success_count += 1

    logger.info(f"Done. {success_count}/{len(db_names)} databases migrated successfully.")
    if success_count < len(db_names):
        sys.exit(1)


if __name__ == "__main__":
    logger.add(sys.stderr, format="{time} {level} {message}", level="INFO")
    asyncio.run(main())
