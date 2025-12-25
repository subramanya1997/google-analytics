"""
Base declarative class for all ORM models.

This module provides the base SQLAlchemy declarative class that all ORM models
should inherit from. It includes common fields (created_at, updated_at) and
automatic table name generation.

Features:
    - Automatic timestamp tracking (created_at, updated_at)
    - Automatic table name generation from class name
    - Timezone-aware timestamps
    - Server-side default values for timestamps

Usage:
    ```python
    from common.database import Base
    from sqlalchemy.orm import Mapped, mapped_column
    from sqlalchemy import String
    
    class User(Base):
        id: Mapped[str] = mapped_column(String(50), primary_key=True)
        name: Mapped[str] = mapped_column(String(100))
        
        # created_at and updated_at are automatically included
    ```

Note:
    - Table names are automatically generated as lowercase class names
    - Timestamps use PostgreSQL TIMESTAMP WITH TIME ZONE
    - Server defaults ensure timestamps are set even if not provided in Python
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import TIMESTAMP, text
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column


class Base(DeclarativeBase):
    """
    Base declarative class for all SQLAlchemy ORM models.

    This class provides common functionality for all database models, including:
    - Automatic timestamp tracking (created_at, updated_at)
    - Automatic table name generation
    - Type-safe column definitions using SQLAlchemy 2.0 style

    Attributes:
        created_at (Mapped[datetime]): Timestamp when the record was created.
            Automatically set by the database server using NOW().
        updated_at (Mapped[datetime]): Timestamp when the record was last updated.
            Automatically set by the database server using NOW().

    Table Naming:
        Table names are automatically generated from the class name by converting
        to lowercase. For example:
        - User -> "user"
        - ProcessingJobs -> "processingjobs"
        - AddToCart -> "addtocart"

    Example:
        ```python
        from common.database import Base
        from sqlalchemy.orm import Mapped, mapped_column
        from sqlalchemy import String, Integer
        from sqlalchemy.dialects.postgresql import UUID
        
        class Product(Base):
            id: Mapped[str] = mapped_column(
                UUID(as_uuid=False), 
                primary_key=True,
                server_default=text("gen_random_uuid()")
            )
            name: Mapped[str] = mapped_column(String(255))
            price: Mapped[float] = mapped_column(Integer)
            
            # created_at and updated_at are automatically available
        ```

    Note:
        - All models inheriting from this class will have created_at and updated_at fields
        - Timestamps are timezone-aware (TIMESTAMP WITH TIME ZONE)
        - Table names follow snake_case convention (lowercase class name)
        - This uses SQLAlchemy 2.0 declarative style with Mapped type hints
    """

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("NOW()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("NOW()")
    )

    @declared_attr.directive
    def __tablename__(cls) -> str:  # type: ignore[override]
        """
        Generate table name from class name.

        Automatically converts the class name to lowercase for use as the table name.
        This ensures consistent naming conventions across all models.

        Returns:
            Lowercase version of the class name.

        Example:
            ```python
            class User(Base):
                pass
            # Table name: "user"
            
            class ProcessingJobs(Base):
                pass
            # Table name: "processingjobs"
            ```
        """
        return cls.__name__.lower()
