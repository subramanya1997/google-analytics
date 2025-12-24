"""
Service modules for Azure Functions.
"""

from .ingestion_service import IngestionService
from .email_service import EmailService

__all__ = [
    "IngestionService",
    "EmailService",
]

