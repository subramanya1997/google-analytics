"""
Data Service Database Layer Package.

This package contains the database access layer for the data ingestion service,
implementing the Repository pattern for clean separation between business logic
and data persistence. It provides comprehensive multi-tenant data management
with performance optimization and data integrity guarantees.

Key Components:
- SqlAlchemyRepository: Complete data access layer with async operations
- Multi-tenant isolation with UUID-based tenant identification
- Event data management with batch processing capabilities
- Dimension management with upsert operations
- Job tracking and status management
- Analytics queries with PostgreSQL function optimization

The database layer handles all aspects of data persistence for the Google
Analytics Intelligence System with proper transaction management, error
handling, and performance optimization for large-scale analytics workloads.
"""
