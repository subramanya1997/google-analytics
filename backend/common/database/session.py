"""
Common database session management.
"""
from __future__ import annotations
import os
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

def create_sqlalchemy_url(database_name: str = None) -> URL:
    """Create SQLAlchemy URL from environment variables."""
    url = URL.create(
        drivername="postgresql+pg8000",
        username=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST"),
        port=int(os.getenv("POSTGRES_PORT")),
        database=database_name or os.getenv("POSTGRES_DATABASE"),
    )
    return url


def database_exists(database_name: str) -> bool:
    """Check if a database exists."""
    try:
        # Connect to postgres database (default) to check if target database exists
        postgres_url = create_sqlalchemy_url("postgres")
        engine = create_engine(postgres_url)
        
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :database_name"),
                {"database_name": database_name}
            )
            return result.fetchone() is not None
    except Exception as e:
        logger.error(f"Error checking if database exists: {e}")
        return False


def create_database(database_name: str) -> bool:
    """Create a database if it doesn't exist."""
    try:
        if database_exists(database_name):
            logger.info(f"Database '{database_name}' already exists.")
            return True
            
        logger.info(f"Creating database '{database_name}'...")
        
        # Connect to postgres database (default) to create the target database
        postgres_url = create_sqlalchemy_url("postgres")
        engine = create_engine(postgres_url, isolation_level="AUTOCOMMIT")
        
        with engine.connect() as connection:
            # Use text() to properly escape the database name
            connection.execute(text(f'CREATE DATABASE "{database_name}"'))
            logger.info(f"Database '{database_name}' created successfully.")
            return True
            
    except Exception as e:
        logger.error(f"Error creating database '{database_name}': {e}")
        return False


def ensure_database_exists() -> bool:
    """Ensure the configured database exists, creating it if necessary."""
    database_name = os.getenv("POSTGRES_DATABASE")
    if not database_name:
        logger.error("POSTGRES_DATABASE environment variable is not set")
        return False
        
    return create_database(database_name)


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
