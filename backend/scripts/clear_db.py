import os
import sys
import asyncio
from sqlalchemy import text, inspect
from sqlalchemy.ext.asyncio import create_async_engine
from loguru import logger

# Add the project's root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.database.session import create_sqlalchemy_url
from common.database.tenant_provisioning import drop_tenant_database

# Define paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "..", "database")
TABLES_DIR = os.path.join(DB_DIR, "tables")
FUNCTIONS_DIR = os.path.join(DB_DIR, "functions")

# Define the correct order for table creation (from init_db.py)
# We'll reverse this for deletion to respect dependencies
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

async def drop_all_functions(connection):
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
            await connection.execute(text(drop_sql))
            logger.info(f"Successfully dropped function: public.{function_name}")
        except Exception as e:
            logger.error(f"Error dropping function public.{function_name}: {e}")
            # Continue with other functions

async def drop_all_tables(connection):
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
            await connection.execute(text(drop_sql))
            logger.info(f"Successfully dropped table: public.{table_name}")
        except Exception as e:
            logger.error(f"Error dropping table public.{table_name}: {e}")
            # Continue with other tables

async def list_remaining_objects(connection):
    """List any remaining tables and functions after cleanup."""
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

async def list_tenant_databases():
    """List all tenant databases by connecting to postgres database."""
    # Use same pattern as tenant_provisioning.py - connect to postgres database
    postgres_url = create_sqlalchemy_url("postgres", async_driver=True)
    engine = create_async_engine(postgres_url)
    
    try:
        async with engine.connect() as connection:
            # List all databases that match tenant database pattern (google-analytics-*)
            # Excluding system databases
            result = await connection.execute(text("""
                SELECT datname 
                FROM pg_database 
                WHERE datistemplate = false 
                AND datname NOT IN ('postgres', 'template0', 'template1')
                AND datname LIKE 'google-analytics-%'
                ORDER BY datname
            """))
            databases = [row[0] for row in result]
            return databases
    finally:
        await engine.dispose()

async def clear_tenant_database(db_name: str):
    """Clear all tables and functions from a specific tenant database."""
    logger.info(f"Clearing tenant database: {db_name}")
    
    try:
        # Create engine for this specific database (same pattern as tenant_provisioning.py)
        url = create_sqlalchemy_url(db_name, async_driver=True)
        engine = create_async_engine(url, echo=False)
    except Exception as e:
        logger.error(f"Failed to get database engine for {db_name}: {e}")
        return False

    try:
        async with engine.begin() as connection:
            # First drop all functions (they may depend on tables)
            await drop_all_functions(connection)
            
            # Then drop all tables
            await drop_all_tables(connection)
            
            logger.info(f"Database cleanup completed successfully for {db_name}.")
            
            # List any remaining objects
            await list_remaining_objects(connection)
            
        return True
    except Exception as e:
        logger.error(f"Database cleanup failed for {db_name}. Error: {e}")
        return False
    finally:
        await engine.dispose()

def extract_tenant_id_from_db_name(db_name: str) -> str:
    """Extract tenant_id from database name (google-analytics-{tenant_id})."""
    prefix = "google-analytics-"
    if db_name.startswith(prefix):
        return db_name[len(prefix):]
    return db_name

async def main():
    """Main function to list tenants and clear/delete selected databases."""
    logger.info("Starting multi-tenant database cleanup...")
    
    # List all tenant databases
    try:
        tenant_databases = await list_tenant_databases()
    except Exception as e:
        logger.error(f"Failed to list tenant databases: {e}")
        return
    
    if not tenant_databases:
        logger.info("No tenant databases found.")
        return
    
    # Display tenant databases
    logger.info(f"\nFound {len(tenant_databases)} tenant database(s):")
    for idx, db_name in enumerate(tenant_databases, 1):
        print(f"  {idx}. {db_name}")
    
    # Ask user which databases to operate on
    print("\nSelect databases:")
    print("  - Enter database numbers separated by commas (e.g., 1,3,5)")
    print("  - Enter 'all' to select all databases")
    print("  - Enter 'cancel' to exit")
    
    selection = input("\nSelect databases: ").strip().lower()
    
    if selection == 'cancel':
        logger.info("Database cleanup cancelled.")
        return
    
    # Determine which databases to operate on
    databases_selected = []
    
    if selection == 'all':
        databases_selected = tenant_databases
    else:
        try:
            indices = [int(idx.strip()) for idx in selection.split(',')]
            for idx in indices:
                if 1 <= idx <= len(tenant_databases):
                    databases_selected.append(tenant_databases[idx - 1])
                else:
                    logger.warning(f"Invalid index: {idx}")
        except ValueError:
            logger.error("Invalid input. Please enter numbers separated by commas.")
            return
    
    if not databases_selected:
        logger.info("No databases selected.")
        return
    
    # Ask for operation type
    print("\nOperation type:")
    print("  1. CLEAR - Drop all tables and functions (keeps database)")
    print("  2. DELETE - Completely delete the database(s)")
    
    operation = input("\nSelect operation (1 or 2): ").strip()
    
    if operation == '2':
        # DELETE entire database
        logger.info(f"\nYou are about to PERMANENTLY DELETE {len(databases_selected)} database(s):")
        for db in databases_selected:
            print(f"  - {db}")
        
        print("\n⚠️  WARNING: This action cannot be undone!")
        response = input("\nType 'DELETE' to confirm: ").strip()
        if response != 'DELETE':
            logger.info("Database deletion cancelled.")
            return
        
        # Delete selected databases
        success_count = 0
        failed_count = 0
        
        for db_name in databases_selected:
            logger.info(f"\n{'='*60}")
            logger.info(f"Deleting: {db_name}")
            logger.info(f"{'='*60}")
            
            tenant_id = extract_tenant_id_from_db_name(db_name)
            success = drop_tenant_database(tenant_id)
            if success:
                success_count += 1
                logger.info(f"Successfully deleted database: {db_name}")
            else:
                failed_count += 1
                logger.error(f"Failed to delete database: {db_name}")
        
        # Summary
        logger.info(f"\n{'='*60}")
        logger.info(f"Deletion Summary:")
        logger.info(f"  Successfully deleted: {success_count} database(s)")
        if failed_count > 0:
            logger.error(f"  Failed: {failed_count} database(s)")
            logger.info("  Note: For Cloud SQL, you may need to use the Google Cloud Console or gcloud CLI.")
        logger.info(f"{'='*60}")
        
    else:
        # CLEAR tables/functions (keep database)
        logger.info(f"\nYou are about to CLEAR all tables and functions from {len(databases_selected)} database(s):")
        for db in databases_selected:
            print(f"  - {db}")
        
        response = input("\nAre you sure you want to proceed? (yes/no): ").lower().strip()
        if response not in ['yes', 'y']:
            logger.info("Database cleanup cancelled.")
            return
        
        # Clear selected databases
        success_count = 0
        failed_count = 0
        
        for db_name in databases_selected:
            logger.info(f"\n{'='*60}")
            logger.info(f"Clearing: {db_name}")
            logger.info(f"{'='*60}")
            
            success = await clear_tenant_database(db_name)
            if success:
                success_count += 1
            else:
                failed_count += 1
        
        # Summary
        logger.info(f"\n{'='*60}")
        logger.info(f"Cleanup Summary:")
        logger.info(f"  Successfully cleared: {success_count} database(s)")
        if failed_count > 0:
            logger.info(f"  Failed: {failed_count} database(s)")
        logger.info(f"{'='*60}")

if __name__ == "__main__":
    # Configure logger
    logger.add(sys.stderr, format="{time} {level} {message}", filter="my_module", level="INFO")
    logger.add("logs/clear_db.log", rotation="500 MB")  # For logging to a file

    asyncio.run(main())
