"""
Data Service Client Package.

This package contains all client implementations for external data source
integration in the data ingestion service. The clients provide secure,
multi-tenant access to various data sources with comprehensive error
handling and data transformation capabilities.

Available Clients:
- BigQueryClient: Google Analytics 4 data extraction from BigQuery
- SFTPClient: User and location data processing from SFTP sources

Key Features:
- Multi-tenant authentication and configuration
- Robust error handling and recovery
- Comprehensive data transformation
- Performance optimization for large datasets
- Azure Blob Storage SFTP compatibility
- GA4 nested data structure handling

The clients are designed to work together in the data ingestion pipeline,
with the factory pattern providing consistent instantiation and configuration
management across all tenant-specific data sources.
"""

from .bigquery_client import BigQueryClient
from .sftp_client import SFTPClient

__all__ = ["BigQueryClient", "SFTPClient"]
