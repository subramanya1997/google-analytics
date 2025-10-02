"""
Database Cleanup Script for Google Analytics Intelligence System.

This script provides a safe way to completely clear the PostgreSQL database by
dropping all tables and functions in the correct order to avoid dependency conflicts.
The script reverses the creation order used by init_db.py to ensure proper cleanup.

⚠️  WARNING: This script PERMANENTLY DELETES ALL DATA ⚠️
- Drops all tables and their data
- Drops all stored functions and procedures
- Cannot be undone once executed
- Requires explicit user confirmation

Key Features:
- Safe dependency-aware deletion order (reverse of creation order)
- Interactive confirmation to prevent accidental execution
- Comprehensive error handling with transaction rollback
- Detailed logging of all operations
- Post-cleanup verification and reporting
- Graceful handling of missing or dependent objects

Deletion Order:
Functions are dropped first (they may depend on tables), followed by tables
in reverse dependency order:
1. Functions: All stored procedures and functions
2. Event tables: (page_view, purchase, add_to_cart, etc.)
3. processing_jobs (data processing tracking)
4. locations (warehouse/location data)
5. users (user profiles) 
6. email_send_history (email history)
7. email_sending_jobs (email job tracking)
8. branch_email_mappings (email configuration)
9. tenants (base tenant configuration)

Usage:
    python scripts/clear_db.py

The script will prompt for confirmation before proceeding.

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
from sqlalchemy import text, inspect
from loguru import logger

# Add the project's root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.database.session import get_async_engine

# Define paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "..", "database")
TABLES_DIR = os.path.join(DB_DIR, "tables")
FUNCTIONS_DIR = os.path.join(DB_DIR, "functions")

# Define the correct order for table creation (from init_db.py)
# We'll reverse this for deletion to respect dependencies
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

def get_table_name_from_sql_file(filepath):
    """
    Extract table name from SQL file by parsing CREATE TABLE statement.
    
    Reads the SQL file and uses regex to find the table name in CREATE TABLE
    statements, handling various formats including schema-qualified names and
    IF NOT EXISTS clauses.
    
    Args:
        filepath: Path to the SQL file to parse
        
    Returns:
        str: Extracted table name in lowercase, or filename without extension if parsing fails
    
    Note:
        Falls back to using the filename (without .sql) if parsing fails.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().upper()
            # Look for CREATE TABLE statement
            if 'CREATE TABLE' in content:
                # Find the table name after CREATE TABLE, handling schema-qualified names
                import re
                # Match pattern like "CREATE TABLE public.table_name" or "CREATE TABLE table_name"
                match = re.search(r'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?(?:\w+\.)?(\w+)', content)
                if match:
                    return match.group(1).lower()
    except Exception as e:
        logger.warning(f"Could not extract table name from {filepath}: {e}")
    
    # Fallback: use filename without extension
    return os.path.splitext(os.path.basename(filepath))[0]

def get_function_name_from_sql_file(filepath):
    """
    Extract function name from SQL file by parsing CREATE FUNCTION statement.
    
    Reads the SQL file and uses regex to find the function name in CREATE FUNCTION
    or CREATE OR REPLACE FUNCTION statements, handling schema-qualified names.
    
    Args:
        filepath: Path to the SQL file to parse
        
    Returns:
        str: Extracted function name in lowercase, or filename without extension if parsing fails

    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().upper()
            # Look for CREATE OR REPLACE FUNCTION or CREATE FUNCTION statement
            if 'CREATE' in content and 'FUNCTION' in content:
                import re
                # Match pattern like "CREATE FUNCTION public.function_name(" or "CREATE FUNCTION function_name("
                match = re.search(r'CREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\s+(?:\w+\.)?(\w+)\s*\(', content)
                if match:
                    return match.group(1).lower()
    except Exception as e:
        logger.warning(f"Could not extract function name from {filepath}: {e}")
    
    # Fallback: use filename without extension
    return os.path.splitext(os.path.basename(filepath))[0]

async def drop_all_functions(connection):
    """
    Drop all stored functions and procedures from the database.
    
    Reads all SQL files from the functions directory, extracts function names,
    and drops them using CASCADE to handle any dependencies. Functions are
    dropped before tables as they may depend on table structures.
    
    Args:
        connection: Async SQLAlchemy connection within a transaction
        
    Process:
        1. Scans functions directory for .sql files
        2. Extracts function name from each file
        3. Drops each function with CASCADE and IF EXISTS
        4. Continues on errors to drop as many functions as possible
    """
    logger.info(f"Looking for function SQL files in: {FUNCTIONS_DIR}")
    
    try:
        function_files = [f for f in os.listdir(FUNCTIONS_DIR) if f.endswith(".sql")]
    except FileNotFoundError:
        logger.warning(f"Directory not found: {FUNCTIONS_DIR}")
        return
    
    if not function_files:
        logger.info("No function files found.")
        return
    
    for filename in sorted(function_files):
        filepath = os.path.join(FUNCTIONS_DIR, filename)
        function_name = get_function_name_from_sql_file(filepath)
        logger.info(f"Extracted function name '{function_name}' from {filename}")
        
        try:
            # Drop function if exists (include schema for clarity)
            drop_sql = f"DROP FUNCTION IF EXISTS public.{function_name} CASCADE;"
            logger.info(f"Dropping function: public.{function_name}")
            await connection.execute(text(drop_sql))
            logger.info(f"Successfully dropped function: public.{function_name}")
        except Exception as e:
            logger.error(f"Error dropping function public.{function_name}: {e}")
            # Continue with other functions

async def drop_all_tables(connection):
    """
    Drop all tables from the database in reverse dependency order.
    
    Reads table SQL files and drops tables in the reverse order of their
    creation sequence to respect foreign key dependencies and constraints.
    Uses the TABLE_CREATION_ORDER list in reverse to determine the safe
    deletion sequence.
    
    Args:
        connection: Async SQLAlchemy connection within a transaction
        
    Process:
        1. Scans tables directory for .sql files
        2. Orders files by reverse TABLE_CREATION_ORDER
        3. Adds any unordered files in reverse alphabetical order
        4. Drops each table with CASCADE and IF EXISTS
        5. Continues on errors to drop as many tables as possible
        
    Deletion Order (reverse of creation):
        - Event tables (no_search_results, view_search_results, etc.)
        - processing_jobs
        - locations, users
        - Email-related tables
        - tenants (base configuration)
    """
    logger.info(f"Looking for table SQL files in: {TABLES_DIR}")
    
    try:
        all_table_files = {f for f in os.listdir(TABLES_DIR) if f.endswith(".sql")}
    except FileNotFoundError:
        logger.warning(f"Directory not found: {TABLES_DIR}")
        return
    
    if not all_table_files:
        logger.info("No table files found.")
        return
    
    # Get tables in reverse order for deletion
    tables_to_drop = []
    
    # Add files in reverse order of creation
    for filename in reversed(TABLE_CREATION_ORDER):
        if filename in all_table_files:
            filepath = os.path.join(TABLES_DIR, filename)
            table_name = get_table_name_from_sql_file(filepath)
            logger.info(f"Extracted table name '{table_name}' from {filename}")
            tables_to_drop.append(table_name)
            all_table_files.remove(filename)
    
    # Add any remaining files that were not in the ordered list
    if all_table_files:
        logger.info(f"Adding remaining table files in reverse alphabetical order: {', '.join(sorted(list(all_table_files), reverse=True))}")
        for filename in sorted(list(all_table_files), reverse=True):
            filepath = os.path.join(TABLES_DIR, filename)
            table_name = get_table_name_from_sql_file(filepath)
            tables_to_drop.append(table_name)
    
    # Drop tables
    for table_name in tables_to_drop:
        try:
            drop_sql = f"DROP TABLE IF EXISTS public.{table_name} CASCADE;"
            logger.info(f"Dropping table: public.{table_name}")
            await connection.execute(text(drop_sql))
            logger.info(f"Successfully dropped table: public.{table_name}")
        except Exception as e:
            logger.error(f"Error dropping table public.{table_name}: {e}")
            # Continue with other tables

async def list_remaining_objects(connection):
    """
    List any database objects that remain after the cleanup process.
    
    Queries the database system catalogs to identify any tables or functions
    that weren't dropped during the cleanup process. This helps verify the
    completeness of the cleanup and identify any objects that may need
    manual attention.
    
    Args:
        connection: Async SQLAlchemy connection for querying system catalogs
        
    Queries:
        - information_schema.tables: Lists remaining tables in public schema
        - information_schema.routines: Lists remaining functions in public schema
        
    Output:
        - Logs remaining table names (INFO level)
        - Logs remaining function names (INFO level) 
        - Logs success messages if no objects remain
    
    """
    try:
        # List remaining tables
        inspector = inspect(connection.sync_connection)
        remaining_tables = inspector.get_table_names()
        if remaining_tables:
            logger.info(f"Remaining tables: {', '.join(remaining_tables)}")
        else:
            logger.info("No tables remaining in database.")
        
        # List remaining functions
        result = await connection.execute(text("""
            SELECT routine_name 
            FROM information_schema.routines 
            WHERE routine_type = 'FUNCTION' 
            AND routine_schema = 'public'
        """))
        remaining_functions = [row[0] for row in result]
        if remaining_functions:
            logger.info(f"Remaining functions: {', '.join(remaining_functions)}")
        else:
            logger.info("No functions remaining in database.")
            
    except Exception as e:
        logger.warning(f"Could not list remaining objects: {e}")

async def main():
    """
    Main function to safely clear the entire database.
    
    This is the primary entry point for database cleanup operations. It coordinates
    the complete deletion of all tables and functions while ensuring user consent
    and providing comprehensive error handling.
    
    Process Flow:
        1. Display warning and request user confirmation
        2. Exit safely if user does not confirm
        3. Establish async database connection
        4. Execute cleanup within single transaction:
           a. Drop all functions first (may depend on tables)
           b. Drop all tables in reverse dependency order
        5. Verify cleanup completion
        6. Report any remaining objects
        
    User Interaction:
        - Displays prominent warning about data deletion
        - Requires explicit 'yes' or 'y' confirmation to proceed
        - Any other input cancels the operation safely
        
    Transaction Safety:
        - All operations performed within single transaction
        - Any error triggers complete rollback
        - Database remains unchanged if any step fails
        
    Error Handling:
        - Database connection failures: Logged and script exits
        - SQL execution errors: Transaction rolled back automatically
        - Individual object errors: Logged but cleanup continues

    Returns:
        None: Function uses logging for status reporting
        
    Raises:
        Exception: Any database error that prevents cleanup
    """
    logger.info("Starting database cleanup...")
    
    # Confirm action
    response = input("This will DELETE ALL tables and functions from the database. Are you sure? (yes/no): ").lower().strip()
    if response not in ['yes', 'y']:
        logger.info("Database cleanup cancelled.")
        return
    
    try:
        engine = get_async_engine()
    except Exception as e:
        logger.error(f"Failed to get database engine: {e}")
        return

    async with engine.begin() as connection:
        try:
            # First drop all functions (they may depend on tables)
            await drop_all_functions(connection)
            
            # Then drop all tables
            await drop_all_tables(connection)
            
            logger.info("Database cleanup completed successfully.")
            
            # List any remaining objects
            await list_remaining_objects(connection)
            
        except Exception as e:
            logger.error(f"Database cleanup failed. Transaction rolled back. Error: {e}")
            raise

if __name__ == "__main__":
    """
    Script entry point with logging configuration and safety warnings.
    
    Configures comprehensive logging to both console and file, then executes
    the async main() function to perform database cleanup. The logging setup
    ensures all operations are recorded for audit and debugging purposes.
    
    Logging Configuration:
        - Console output: Timestamped messages at INFO level and above
        - File output: logs/clear_db.log with 500MB rotation
        - Captures all cleanup operations and errors
        
    Safety Note:
        This script permanently deletes all database contents. The main()
        function includes user confirmation prompts to prevent accidental
        execution.
    """
    # Configure logger
    logger.add(sys.stderr, format="{time} {level} {message}", filter="my_module", level="INFO")
    logger.add("logs/clear_db.log", rotation="500 MB")  # For logging to a file

    asyncio.run(main())
