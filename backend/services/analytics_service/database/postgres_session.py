# Use common database session management
from common.database import get_engine, SessionLocal, create_sqlalchemy_url

# Re-export for backward compatibility
__all__ = ["get_engine", "SessionLocal", "create_sqlalchemy_url"]


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
