"""
Business Logic Services for Analytics Service.

This package contains core business logic services for the analytics system,
including email distribution, report generation, and template rendering services.

Provides high-level service abstractions that coordinate database operations,
external integrations, and presentation logic for analytics functionality.
"""

from .email_service import EmailService
from .report_service import ReportService
from .template_service import TemplateService

__all__ = ["EmailService", "ReportService", "TemplateService"]
