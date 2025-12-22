"""
Tenant database provisioning for SOC2 compliance.

This module handles the creation and initialization of tenant-specific databases
to ensure complete data isolation between tenants.
"""

import os
from typing import Optional
from sqlalchemy import text, create_engine
from sqlalchemy.ext.asyncio import create_async_engine
from loguru import logger

from common.database.session import create_sqlalchemy_url

# Define paths to SQL files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "..", "..", "database")
TABLES_DIR = os.path.join(DB_DIR, "tables")
FUNCTIONS_DIR = os.path.join(DB_DIR, "functions")

# Define the correct order for table creation to respect dependencies
TABLE_CREATION_ORDER = [
    "tenant_config.sql",
    "branch_email_mappings.sql",
    "email_sending_jobs.sql",
    "email_send_history.sql",
    "users.sql",
    "locations.sql",
    "processing_jobs.sql",
    "page_view.sql",
    "add_to_cart.sql",
    "purchase.sql",
    "view_item.sql",
    "view_search_results.sql",
    "no_search_results.sql"
]


def get_tenant_database_name(tenant_id: str) -> str:
    """
    Generate the database name for a tenant.
    
    Args:
        tenant_id: The tenant ID
        
    Returns:
        Database name in format: google-analytics-{tenant_id}
    """
    return f"google-analytics-{tenant_id}"


def tenant_database_exists(tenant_id: str) -> bool:
    """
    Check if a tenant database exists.
    
    Args:
        tenant_id: The tenant ID
        
    Returns:
        True if database exists, False otherwise
    """
    try:
        db_name = get_tenant_database_name(tenant_id)
        # Connect to postgres database (default) to check if target database exists
        postgres_url = create_sqlalchemy_url("postgres")
        engine = create_engine(postgres_url)
        
        with engine.connect() as connection:
            result = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :database_name"),
                {"database_name": db_name}
            )
            exists = result.fetchone() is not None
            
        engine.dispose()
        return exists
        
    except Exception as e:
        logger.error(f"Error checking if tenant database exists for {tenant_id}: {e}")
        return False


def create_tenant_database(tenant_id: str) -> bool:
    """
    Create a new tenant-specific database.
    
    Args:
        tenant_id: The tenant ID
        
    Returns:
        True if successful, False otherwise
    """
    try:
        db_name = get_tenant_database_name(tenant_id)
        
        if tenant_database_exists(tenant_id):
            logger.info(f"Tenant database '{db_name}' already exists.")
            return True
            
        logger.info(f"Creating tenant database '{db_name}'...")
        
        # Connect to postgres database (default) to create the target database
        postgres_url = create_sqlalchemy_url("postgres")
        engine = create_engine(postgres_url, isolation_level="AUTOCOMMIT")
        
        with engine.connect() as connection:
            # Use text() to properly escape the database name
            connection.execute(text(f'CREATE DATABASE "{db_name}"'))
            logger.info(f"Tenant database '{db_name}' created successfully.")
            
        engine.dispose()
        return True
        
    except Exception as e:
        # Check if this is a "database already exists" error (PostgreSQL error code 42P04)
        # This can happen with concurrent tenant provisioning requests
        error_str = str(e)
        if "42P04" in error_str or "already exists" in error_str.lower():
            logger.info(f"Tenant database '{db_name}' already exists (concurrent creation detected).")
            return True
        logger.error(f"Error creating tenant database for {tenant_id}: {e}")
        return False


async def is_schema_initialized(tenant_id: str) -> bool:
    """
    Check if the tenant database already has tables initialized.
    
    We check for the existence of the tenant_config table as an indicator
    that the schema has been initialized.
    
    Args:
        tenant_id: The tenant ID
        
    Returns:
        True if schema is initialized, False otherwise
    """
    try:
        db_name = get_tenant_database_name(tenant_id)
        
        # Check if database exists first
        if not tenant_database_exists(tenant_id):
            return False
        
        # Create async engine for the tenant database
        url = create_sqlalchemy_url(db_name, async_driver=True)
        async_engine = create_async_engine(url, echo=False)
        
        try:
            async with async_engine.connect() as connection:
                # Check if tenant_config table exists
                result = await connection.execute(
                    text("""
                        SELECT EXISTS (
                            SELECT 1 
                            FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = 'tenant_config'
                        )
                    """)
                )
                exists = result.scalar()
                
                if exists:
                    logger.info(f"Schema already initialized for tenant database '{db_name}'")
                
                return exists
        finally:
            await async_engine.dispose()
            
    except Exception as e:
        logger.error(f"Error checking if schema is initialized for tenant {tenant_id}: {e}")
        return False


async def initialize_tenant_schema(tenant_id: str) -> bool:
    """
    Initialize the schema (tables and functions) for a tenant database.
    
    Args:
        tenant_id: The tenant ID
        
    Returns:
        True if successful, False otherwise
    """
    try:
        db_name = get_tenant_database_name(tenant_id)
        logger.info(f"Initializing schema for tenant database '{db_name}'...")
        
        # Create async engine for the tenant database
        url = create_sqlalchemy_url(db_name, async_driver=True)
        async_engine = create_async_engine(url, echo=False)
        
        sql_files_to_execute = []
        
        # Get tables in the specified order
        logger.info(f"Looking for table SQL files in: {TABLES_DIR}")
        
        try:
            all_table_files = {f for f in os.listdir(TABLES_DIR) if f.endswith(".sql")}
        except FileNotFoundError:
            logger.error(f"Directory not found: {TABLES_DIR}")
            await async_engine.dispose()
            return False
        
        # Add files in the specified order
        for filename in TABLE_CREATION_ORDER:
            if filename in all_table_files:
                sql_files_to_execute.append(os.path.join(TABLES_DIR, filename))
                all_table_files.remove(filename)
            else:
                logger.warning(f"Specified table file not found, skipping: {filename}")
                
        # Add any remaining files that were not in the ordered list
        if all_table_files:
            logger.info(f"Adding remaining table files: {', '.join(sorted(list(all_table_files)))}")
            for filename in sorted(list(all_table_files)):
                sql_files_to_execute.append(os.path.join(TABLES_DIR, filename))
        
        # Get functions (order is less critical for functions)
        logger.info(f"Looking for function SQL files in: {FUNCTIONS_DIR}")
        try:
            for filename in sorted(os.listdir(FUNCTIONS_DIR)):
                if filename.endswith(".sql"):
                    sql_files_to_execute.append(os.path.join(FUNCTIONS_DIR, filename))
        except FileNotFoundError:
            logger.error(f"Directory not found: {FUNCTIONS_DIR}")
            await async_engine.dispose()
            return False
        
        if not sql_files_to_execute:
            logger.warning("No SQL files found to execute.")
            await async_engine.dispose()
            return False
        
        async with async_engine.begin() as connection:
            try:
                for filepath in sql_files_to_execute:
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            sql_content = f.read()
                            if sql_content.strip():
                                logger.info(f"Executing {os.path.basename(filepath)}...")
                                
                                # Check if this is a function file or contains dollar-quoted strings (DO blocks, functions)
                                if '$function$' in sql_content or '$body$' in sql_content or '$$' in sql_content or 'CREATE OR REPLACE FUNCTION' in sql_content.upper():
                                    # For files with dollar-quoted strings, use raw asyncpg connection for script execution
                                    # This bypasses SQLAlchemy's prepared statement handling which doesn't support multiple commands
                                    logger.debug(f"Executing file with dollar-quoted strings {os.path.basename(filepath)} using raw connection")
                                    raw_conn = await connection.get_raw_connection()
                                    await raw_conn.driver_connection.execute(sql_content)
                                else:
                                    # Split SQL content by semicolons to handle multiple statements
                                    statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
                                    
                                    for i, statement in enumerate(statements):
                                        if statement:
                                            logger.debug(f"Executing statement {i+1}/{len(statements)} from {os.path.basename(filepath)}")
                                            await connection.execute(text(statement))
                                
                                logger.info(f"Successfully executed {os.path.basename(filepath)}.")
                            else:
                                logger.warning(f"Skipping empty file: {os.path.basename(filepath)}")
                    
                    except Exception as e:
                        logger.error(f"Error executing file {filepath}: {e}")
                        raise  # This will trigger the rollback of the transaction
                
                logger.info(f"Schema initialization completed successfully for tenant database '{db_name}'.")
                
            except Exception as e:
                logger.error(f"Schema initialization failed for tenant database '{db_name}'. Transaction rolled back. Error: {e}")
                raise
        
        await async_engine.dispose()
        return True
        
    except Exception as e:
        logger.error(f"Error initializing schema for tenant {tenant_id}: {e}")
        return False


def drop_tenant_database(tenant_id: str) -> bool:
    """
    Drop a tenant database (use with caution - for rollback scenarios).
    
    Args:
        tenant_id: The tenant ID
        
    Returns:
        True if successful, False otherwise
    """
    try:
        db_name = get_tenant_database_name(tenant_id)
        
        if not tenant_database_exists(tenant_id):
            logger.info(f"Tenant database '{db_name}' does not exist, nothing to drop.")
            return True
            
        logger.warning(f"Dropping tenant database '{db_name}'...")
        
        # Connect to postgres database (default) to drop the target database
        postgres_url = create_sqlalchemy_url("postgres")
        engine = create_engine(postgres_url, isolation_level="AUTOCOMMIT")
        
        with engine.connect() as connection:
            # Terminate all connections to the database first
            connection.execute(text(f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = :database_name
                AND pid <> pg_backend_pid()
            """), {"database_name": db_name})
            
            # Drop the database
            connection.execute(text(f'DROP DATABASE "{db_name}"'))
            logger.info(f"Tenant database '{db_name}' dropped successfully.")
            
        engine.dispose()
        return True
        
    except Exception as e:
        logger.error(f"Error dropping tenant database for {tenant_id}: {e}")
        return False


async def provision_tenant_database(tenant_id: str, force_recreate: bool = False) -> bool:
    """
    Provision a complete tenant-specific database with all tables and functions.
    
    This is the main entry point for tenant database provisioning. It will:
    1. Create the tenant database
    2. Initialize all tables in the correct order
    3. Create all database functions
    4. Rollback (drop database) if any step fails
    
    Args:
        tenant_id: The tenant ID
        force_recreate: If True, drop and recreate the database if it exists
        
    Returns:
        True if provisioning was successful, False otherwise
    """
    try:
        db_name = get_tenant_database_name(tenant_id)
        logger.info(f"Starting provisioning for tenant database '{db_name}'...")
        
        # Check if database already exists
        if tenant_database_exists(tenant_id):
            if force_recreate:
                logger.warning(f"Force recreate requested, dropping existing database '{db_name}'...")
                if not drop_tenant_database(tenant_id):
                    logger.error(f"Failed to drop existing database for tenant {tenant_id}")
                    return False
            elif await is_schema_initialized(tenant_id):
                logger.info(f"Tenant database '{db_name}' already exists and is initialized. Skipping.")
                return True
            else:
                logger.info(f"Tenant database '{db_name}' exists but schema not initialized. Proceeding...")
        
        # Create the database if it doesn't exist
        if not tenant_database_exists(tenant_id):
            if not create_tenant_database(tenant_id):
                logger.error(f"Failed to create database for tenant {tenant_id}")
                return False
        
        # Initialize the schema
        if not await initialize_tenant_schema(tenant_id):
            logger.error(f"Failed to initialize schema for tenant {tenant_id}")
            drop_tenant_database(tenant_id)
            return False
        
        logger.info(f"Successfully provisioned tenant database '{db_name}'")
        return True
        
    except Exception as e:
        logger.error(f"Unexpected error during provisioning for tenant {tenant_id}: {e}")
        try:
            drop_tenant_database(tenant_id)
        except Exception:
            pass
        return False

