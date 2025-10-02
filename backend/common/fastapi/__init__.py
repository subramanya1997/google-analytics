"""
Common FastAPI utilities and middleware.

This module provides FastAPI application factory and utilities for creating
consistent web applications across all backend services in the Google Analytics
Intelligence System.

The main export is create_fastapi_app, which creates FastAPI applications with:
- Standardized configuration and middleware
- Environment-aware CORS policies
- Request timing and monitoring
- Global error handling
- Health check endpoints
- API documentation setup

"""

from .app_factory import create_fastapi_app

__all__ = ["create_fastapi_app"]
