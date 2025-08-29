#!/usr/bin/env python3
"""
Database initialization script.
Drops all existing tables and recreates them from SQLAlchemy models.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add the app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import MetaData, text
from sqlalchemy.orm import Session
from loguru import logger

from app.database.sqlalchemy_session import get_engine
from app.models.orm.base import Base

# Import all models to register them with Base.metadata
from app.models.orm.control import Tenants, ProcessingJobs, TaskTracking
from app.models.orm.dimensions import Users, Locations
from app.models.orm.events import (
    Purchase,
    AddToCart,
    PageView,
    ViewSearchResults,
    NoSearchResults,
    ViewItem,
)


def drop_all_tables(engine):
    """Drop all tables in the database."""
    logger.warning("Dropping all existing tables...")
    
    with engine.begin() as conn:
        # Get all table names in the public schema
        result = conn.execute(text("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
        """))
        
        tables = [row[0] for row in result]
        
        # Drop each table with CASCADE to handle foreign key constraints
        for table in tables:
            logger.info(f"Dropping table: {table}")
            conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
        
        logger.info("All tables dropped successfully")


def create_all_tables(engine):
    """Create all tables from SQLAlchemy models."""
    logger.info("Creating all tables from models...")
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    logger.info("All tables created successfully")


def verify_tables(engine):
    """Verify that all expected tables exist."""
    expected_tables = [
        # Control tables
        "tenants",
        "processing_jobs",
        
        # Dimension tables
        "users",
        "locations",
        
        # Event tables
        "purchase",
        "add_to_cart",
        "page_view",
        "view_search_results",
        "no_search_results",
        "view_item",
    ]
    
    with engine.begin() as conn:
        result = conn.execute(text("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename
        """))
        
        existing_tables = [row[0] for row in result]
        
        logger.info(f"Found {len(existing_tables)} tables in database:")
        for table in existing_tables:
            status = "✓" if table in expected_tables else "?"
            logger.info(f"  {status} {table}")
        
        missing_tables = set(expected_tables) - set(existing_tables)
        if missing_tables:
            logger.warning(f"Missing expected tables: {missing_tables}")
        
        extra_tables = set(existing_tables) - set(expected_tables)
        if extra_tables:
            logger.info(f"Additional tables found: {extra_tables}")
    
    return len(missing_tables) == 0


def print_table_schemas(engine):
    """Print the schema of all tables for verification."""
    logger.info("\nTable Schemas:")
    logger.info("=" * 80)
    
    with engine.begin() as conn:
        # Get all tables
        tables_result = conn.execute(text("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename
        """))
        
        for table_row in tables_result:
            table_name = table_row[0]
            logger.info(f"\nTable: {table_name}")
            logger.info("-" * 40)
            
            # Get column information
            columns_result = conn.execute(text(f"""
                SELECT 
                    column_name,
                    data_type,
                    character_maximum_length,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = 'public' 
                AND table_name = '{table_name}'
                ORDER BY ordinal_position
            """))
            
            for col in columns_result:
                col_name, data_type, max_length, nullable, default = col
                type_str = data_type
                if max_length:
                    type_str += f"({max_length})"
                nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
                default_str = f"DEFAULT {default}" if default else ""
                
                logger.info(f"  {col_name:30} {type_str:20} {nullable_str:10} {default_str}")
            
            # Get constraints
            constraints_result = conn.execute(text(f"""
                SELECT 
                    conname AS constraint_name,
                    contype AS constraint_type
                FROM pg_constraint
                WHERE conrelid = '{table_name}'::regclass
            """))
            
            constraints = list(constraints_result)
            if constraints:
                logger.info("\n  Constraints:")
                for constraint in constraints:
                    con_name, con_type = constraint
                    con_type_map = {
                        'p': 'PRIMARY KEY',
                        'u': 'UNIQUE',
                        'f': 'FOREIGN KEY',
                        'c': 'CHECK',
                    }
                    con_type_str = con_type_map.get(con_type, con_type)
                    logger.info(f"    - {con_name}: {con_type_str}")


def main():
    """Main execution function."""
    logger.info("Starting database initialization...")
    
    try:
        # Get database engine
        engine = get_engine()
        
        # Drop all existing tables
        drop_all_tables(engine)
        
        # Create all tables from models
        create_all_tables(engine)
        
        # Verify tables were created
        if verify_tables(engine):
            logger.success("Database initialization completed successfully!")
        else:
            logger.error("Database initialization completed with missing tables")
            sys.exit(1)
        
        # Print table schemas for verification
        print_table_schemas(engine)
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Add confirmation prompt for safety
    print("\n" + "=" * 80)
    print("WARNING: This will DROP ALL TABLES and recreate them from scratch!")
    print("All existing data will be PERMANENTLY DELETED!")
    print("=" * 80 + "\n")
    
    response = input("Are you sure you want to continue? Type 'yes' to proceed: ")
    
    if response.lower() == 'yes':
        main()
    else:
        print("Database initialization cancelled.")
        sys.exit(0)
