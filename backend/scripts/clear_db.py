import os
import sys
from sqlalchemy import text, inspect
from loguru import logger

# Add the project's root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.database.session import get_engine

# Define paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "..", "database")
TABLES_DIR = os.path.join(DB_DIR, "tables")
FUNCTIONS_DIR = os.path.join(DB_DIR, "functions")

# Define the correct order for table creation (from init_db.py)
# We'll reverse this for deletion to respect dependencies
TABLE_CREATION_ORDER = [
    "tenants.sql",
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
    """Extract table name from SQL file by reading the CREATE TABLE statement."""
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
    """Extract function name from SQL file by reading the CREATE FUNCTION statement."""
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

def drop_all_functions(connection):
    """Drop all functions by reading function SQL files."""
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
            connection.execute(text(drop_sql))
            logger.info(f"Successfully dropped function: public.{function_name}")
        except Exception as e:
            logger.error(f"Error dropping function public.{function_name}: {e}")
            # Continue with other functions

def drop_all_tables(connection):
    """Drop all tables in reverse order of creation."""
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
            connection.execute(text(drop_sql))
            logger.info(f"Successfully dropped table: public.{table_name}")
        except Exception as e:
            logger.error(f"Error dropping table public.{table_name}: {e}")
            # Continue with other tables

def list_remaining_objects(connection):
    """List any remaining tables and functions after cleanup."""
    try:
        # List remaining tables
        inspector = inspect(connection)
        remaining_tables = inspector.get_table_names()
        if remaining_tables:
            logger.info(f"Remaining tables: {', '.join(remaining_tables)}")
        else:
            logger.info("No tables remaining in database.")
        
        # List remaining functions
        result = connection.execute(text("""
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

def main():
    """Main function to clear the database."""
    logger.info("Starting database cleanup...")
    
    # Confirm action
    response = input("This will DELETE ALL tables and functions from the database. Are you sure? (yes/no): ").lower().strip()
    if response not in ['yes', 'y']:
        logger.info("Database cleanup cancelled.")
        return
    
    try:
        engine = get_engine()
    except Exception as e:
        logger.error(f"Failed to get database engine: {e}")
        return

    with engine.connect() as connection:
        try:
            with connection.begin():  # Starts a transaction
                # First drop all functions (they may depend on tables)
                drop_all_functions(connection)
                
                # Then drop all tables
                drop_all_tables(connection)
                
            logger.info("Database cleanup completed successfully.")
            
            # List any remaining objects
            list_remaining_objects(connection)
            
        except Exception as e:
            logger.error(f"Database cleanup failed. Transaction rolled back. Error: {e}")

if __name__ == "__main__":
    # Configure logger
    logger.add(sys.stderr, format="{time} {level} {message}", filter="my_module", level="INFO")
    logger.add("clear_db.log", rotation="500 MB")  # For logging to a file

    main()
