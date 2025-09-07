# Use common database session management
from common.database import SessionLocal, create_sqlalchemy_url, get_engine

# Re-export for backward compatibility
__all__ = ["get_engine", "SessionLocal", "create_sqlalchemy_url"]
