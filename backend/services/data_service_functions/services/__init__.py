"""
Service modules for Azure Functions.
"""

from .email_service import EmailService
from .ingestion_service import IngestionService

__all__ = [
    "EmailService",
    "IngestionService",
]
