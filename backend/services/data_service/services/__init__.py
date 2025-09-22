"""
Data Service Business Logic Package.

This package contains the core business logic services for the data ingestion
system. The services orchestrate complex data processing workflows, manage
job lifecycles, and coordinate between external data sources and database
storage with comprehensive error handling and performance optimization.

Available Services:
- IngestionService: Multi-source data ingestion and processing pipeline

Key Features:
- Multi-source data integration (BigQuery + SFTP)
- Asynchronous job processing with status tracking
- Thread pool optimization for heavy operations
- Comprehensive error handling and recovery
- Real-time progress monitoring
- Performance optimization for large datasets

The services layer provides the complete business logic implementation
for the data ingestion API, handling orchestration, validation, and
coordination between all system components.
"""

from .ingestion_service import IngestionService

__all__ = ["IngestionService"]
