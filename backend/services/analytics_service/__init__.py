"""
Analytics Service Package.

This package provides comprehensive analytics capabilities for the Google Analytics
platform, including dashboard statistics, task management, location analytics,
and automated report distribution.

Key Features:
- Multi-tenant analytics data processing and visualization
- Sales task management (purchase follow-ups, cart abandonment, search analysis)
- Automated branch report generation and email distribution
- Location-based analytics and filtering
- Real-time dashboard statistics and metrics
- Comprehensive email configuration and delivery tracking

Architecture:
- FastAPI-based REST API with multi-version support
- PostgreSQL database integration with optimized RPC functions  
- Background task processing for email operations
- Jinja2 template-based HTML report generation
- Multi-tenant data isolation and security

Production Configuration:
- Environment-based configuration management
- Structured logging with Loguru
- Database connection pooling and health monitoring
- CORS middleware for cross-origin requests
- Comprehensive error handling and monitoring

Environment Variables:
- Analytics service configuration through common settings
- Database connection parameters
- Email server configuration for SMTP delivery
- Template directory paths for report generation
"""

from services.analytics_service.main import app

__all__ = ["app"]
