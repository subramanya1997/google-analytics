"""
Database Initialization Script for Google Analytics Intelligence System.

This script initializes the PostgreSQL database by creating all required tables
and functions from SQL files. It handles the complete database schema setup
with proper dependency ordering and error handling.

Key Features:
- Creates database if it doesn't exist
- Executes table creation in dependency order
- Creates all stored functions and procedures
- Handles both regular SQL statements and PostgreSQL functions
- Comprehensive error handling with transaction rollback
- Detailed logging of all operations

The script reads SQL files from two directories:
- database/tables/: Table creation scripts (executed in dependency order)
- database/functions/: Function/procedure creation scripts

Table Creation Order:
The script follows a specific order for table creation to respect foreign key
dependencies and constraints. Tables are created in the following sequence:
1. tenants (base tenant configuration)
2. branch_email_mappings (email configuration)
3. email_sending_jobs (email job tracking)
4. email_send_history (email history)
5. users (user profiles)
6. locations (warehouse/location data)
7. processing_jobs (data processing tracking)
8. Event tables (page_view, add_to_cart, purchase, etc.)

Usage:
    python scripts/init_db.py

Environment Variables Required:
    - POSTGRES_HOST: Database host
    - POSTGRES_PORT: Database port
    - POSTGRES_USER: Database username
    - POSTGRES_PASSWORD: Database password
    - POSTGRES_DATABASE: Target database name

"""
import os
import sys
import asyncio
from sqlalchemy import text
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# Add the project's root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.database.session import get_async_engine, ensure_database_exists

# Define paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "..", "database")
TABLES_DIR = os.path.join(DB_DIR, "tables")
FUNCTIONS_DIR = os.path.join(DB_DIR, "functions")

# Define the correct order for table creation to respect dependencies
TABLE_CREATION_ORDER = [
    "tenants.sql",
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

async def main():
    """
    Initialize the database with tables and functions from SQL files.
    
    This is the main entry point for database initialization. It performs the
    following operations in sequence:
    
    1. Ensures the target database exists (creates if necessary)
    2. Establishes async database connection
    3. Collects SQL files in dependency order (tables first, then functions)
    4. Executes all SQL files within a single transaction
    5. Handles both regular SQL statements and PostgreSQL functions
    
    The function uses a single transaction for all operations, ensuring that
    either all tables and functions are created successfully, or none are
    created if any error occurs (atomic operation).
    
    SQL File Processing:
        - Table files: Split by semicolons, execute each statement separately
        - Function files: Execute entire content as single statement (handles $$ quoting)
        - Empty files: Skipped with warning
        - File order: Tables in dependency order, then functions alphabetically

        
    Returns:
        None: Function doesn't return a value, uses logging for status reporting
    """
    logger.info("Starting database initialization...")
    
    # First, ensure the database exists
    logger.info("Ensuring database exists...")
    if not ensure_database_exists():
        logger.error("Failed to ensure database exists")
        return
    
    try:
        engine = get_async_engine()
    except Exception as e:
        logger.error(f"Failed to get database engine: {e}")
        return

    sql_files_to_execute = []

    # Get tables in the specified order
    logger.info(f"Looking for table SQL files in: {TABLES_DIR}")
    
    # Get all SQL files from the directory
    try:
        all_table_files = {f for f in os.listdir(TABLES_DIR) if f.endswith(".sql")}
    except FileNotFoundError:
        logger.error(f"Directory not found: {TABLES_DIR}")
        return

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
        return

    if not sql_files_to_execute:
        logger.warning("No SQL files found to execute.")
        return

    async with engine.begin() as connection:
        try:
            for filepath in sql_files_to_execute:
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        sql_content = f.read()
                        if sql_content.strip(): #  Ensure content is not empty
                            logger.info(f"Executing {os.path.basename(filepath)}...")
                            
                            # Check if this is a function file (contains dollar-quoted strings)
                            if '$function$' in sql_content or '$body$' in sql_content or 'CREATE OR REPLACE FUNCTION' in sql_content.upper():
                                # For function files, execute the entire content as one statement
                                logger.debug(f"Executing function file {os.path.basename(filepath)} as single statement")
                                await connection.execute(text(sql_content))
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
            logger.info("Database initialization completed successfully.")
        except Exception as e:
            logger.error(f"Database initialization failed. Transaction rolled back. Error: {e}")
            raise

if __name__ == "__main__":
    """
    Script entry point with logging configuration.
    
    Configures loguru logging to output to both stderr and a rotating log file,
    then runs the async main() function to initialize the database.
    
    Logging Configuration:
        - Console output: Timestamped messages at INFO level and above
        - File output: logs/init_db.log with 500MB rotation
        - Log levels: INFO for progress, DEBUG for details, ERROR for failures
    """
    # Configure logger
    logger.add(sys.stderr, format="{time} {level} {message}", filter="my_module", level="INFO")
    logger.add("logs/init_db.log", rotation="500 MB") # For logging to a file

    asyncio.run(main())
