"""
Base declarative class for all ORM models.

This module provides the foundational SQLAlchemy declarative base class that all
database models inherit from. It includes common fields and automatic table naming
conventions to ensure consistency across all database entities in the Google Analytics
Intelligence System.

Key Features:
- Automatic timestamp tracking (created_at, updated_at)
- Automatic table naming based on class name
- Timezone-aware datetime fields
- PostgreSQL-specific optimizations

"""
from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase, declared_attr

from datetime import datetime
from sqlalchemy import TIMESTAMP, text
from sqlalchemy.orm import Mapped, mapped_column

class Base(DeclarativeBase):
    """
    Base declarative class for all SQLAlchemy ORM models.
    
    Provides common functionality and fields that all database entities should have,
    including automatic timestamp tracking and table naming conventions. All model
    classes in the system should inherit from this base class to ensure consistency.
    
    Attributes:
        created_at: Timestamp when the record was created, automatically set by database
        updated_at: Timestamp when the record was last modified, automatically set by database
    
    Table Naming:
        Table names are automatically generated from the class name converted to lowercase.
        For example, a class named 'UserProfile' becomes table 'userprofile'.
        
    Timezone Handling:
        All timestamp fields are timezone-aware using PostgreSQL's TIMESTAMP with timezone.
        The database server default 'NOW()' ensures consistent timestamp generation.
        
    """

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), 
        server_default=text("NOW()"),
        doc="Timestamp when the record was created"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), 
        server_default=text("NOW()"),
        doc="Timestamp when the record was last updated"
    )

    @declared_attr.directive
    def __tablename__(cls) -> str:  # type: ignore[override]
        """
        Generate table name from class name.
        
        Automatically converts the class name to lowercase to create the database
        table name. This ensures consistent naming conventions across all tables.
        
        Returns:
            Lowercase version of the class name
            
        Example:
            UserProfile -> "userprofile"
            ProductCategory -> "productcategory"
        """
        return cls.__name__.lower()
