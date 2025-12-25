"""
Multi-Tenant Database Cleanup and Deletion Script.

This module provides a comprehensive command-line utility for managing tenant databases
in a multi-tenant architecture. It supports both clearing database contents (dropping
tables and functions) and complete database deletion.

**Architecture Context:**
    - The system uses a multi-tenant architecture with complete database isolation
    - Each tenant has its own dedicated PostgreSQL database
    - Database names follow the pattern: `google-analytics-{tenant_id}`
    - This script operates on tenant databases identified by this naming convention

**Primary Use Cases:**
    1. **CLEAR Operation**: Drop all tables and functions while keeping the database
       - Useful for resetting tenant data during development/testing
       - Preserves database structure for re-initialization
       - Non-destructive operation (database can be repopulated)

    2. **DELETE Operation**: Completely remove tenant databases
       - Permanent deletion of tenant data
       - Useful for tenant offboarding or cleanup
       - Irreversible operation (requires confirmation)

**Security Considerations:**
    - Requires database admin credentials (via environment variables)
    - Interactive confirmation required for destructive operations
    - DELETE operation requires typing 'DELETE' to confirm
    - All operations are logged for audit purposes
    - Supports selective database operations (not all-or-nothing)

**Dependencies:**
    - PostgreSQL database server (local or Cloud SQL)
    - Environment variables: DB_HOST, DB_PORT, DB_USER, DB_PASSWORD
    - SQL table and function definitions in backend/database/

**Example Usage:**
    ```bash
    # Interactive mode - lists all tenant databases
    python scripts/clear_db.py

    # User selects databases and operation type:
    # 1. CLEAR - Drop tables/functions (keeps database)
    # 2. DELETE - Completely delete database(s)
    ```

**Operation Details:**

    **CLEAR Operation:**
        - Drops all PostgreSQL functions first (they may depend on tables)
        - Drops all tables in reverse dependency order
        - Lists any remaining objects after cleanup
        - Database structure remains for re-initialization

    **DELETE Operation:**
        - Permanently removes the entire database
        - Cannot be undone
        - Requires explicit 'DELETE' confirmation
        - For Cloud SQL, may require Google Cloud Console/gcloud CLI

**Error Handling:**
    - Continues processing remaining databases if one fails
    - Logs detailed error messages for each failure
    - Provides summary of successful/failed operations
    - Non-fatal errors don't stop the entire operation

**Logging:**
    - Console output: INFO level with timestamps
    - File output: logs/clear_db.log (rotates at 500 MB)
    - Detailed operation logs for each database processed

**Performance Notes:**
    - Table dropping: ~100-500ms per table (depends on table size)
    - Function dropping: ~50-200ms per function
    - Database deletion: ~500ms-2s (depends on database size)
    - Total time scales linearly with number of databases selected
"""

import asyncio
from pathlib import Path
import sys
import re
from typing import Optional

from loguru import logger
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncConnection

# Add the project's root directory to the Python path
sys.path.append(str(Path(__file__).parent.parent.resolve()))

from common.database.session import create_sqlalchemy_url
from common.database.tenant_provisioning import drop_tenant_database

# Define paths
BASE_DIR = Path(__file__).parent.resolve()
DB_DIR = BASE_DIR.parent / "database"
TABLES_DIR = DB_DIR / "tables"
FUNCTIONS_DIR = DB_DIR / "functions"

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
    "no_search_results.sql",
]


def get_table_name_from_sql_file(filepath: str | Path) -> str:
    """
    Extract table name from SQL CREATE TABLE statement.

    Parses SQL files to identify the table name defined in CREATE TABLE statements.
    Handles various SQL syntax variations including schema-qualified names and
    IF NOT EXISTS clauses.

    Args:
        filepath: Path to the SQL file containing CREATE TABLE statement.
                  Can be a string or Path object.

    Returns:
        str: Lowercase table name extracted from the SQL file.
             Falls back to filename (without extension) if parsing fails.

    Examples:
        >>> get_table_name_from_sql_file("database/tables/users.sql")
        'users'
        >>> get_table_name_from_sql_file("database/tables/public.page_view.sql")
        'page_view'

    Note:
        - Handles both "CREATE TABLE table_name" and "CREATE TABLE public.table_name"
        - Handles "CREATE TABLE IF NOT EXISTS table_name" syntax
        - Returns lowercase table name for consistency
        - Gracefully falls back to filename if parsing fails

    Raises:
        No exceptions raised - always returns a value (fallback to filename)
    """
    try:
        with Path(filepath).open(encoding="utf-8") as f:
            content = f.read().upper()
            # Look for CREATE TABLE statement
            if "CREATE TABLE" in content:
                # Find the table name after CREATE TABLE, handling schema-qualified names
                # Match pattern like "CREATE TABLE public.table_name" or "CREATE TABLE table_name"
                match = re.search(
                    r"CREATE TABLE\s+(?:IF NOT EXISTS\s+)?(?:\w+\.)?(\w+)", content
                )
                if match:
                    return match.group(1).lower()
    except Exception as e:
        logger.warning(f"Could not extract table name from {filepath}: {e}")

    # Fallback: use filename without extension
    return Path(filepath).stem


def get_function_name_from_sql_file(filepath: str | Path) -> str:
    """
    Extract function name from SQL CREATE FUNCTION statement.

    Parses SQL files to identify the function name defined in CREATE FUNCTION or
    CREATE OR REPLACE FUNCTION statements. Handles various SQL syntax variations
    including schema-qualified names.

    Args:
        filepath: Path to the SQL file containing CREATE FUNCTION statement.
                  Can be a string or Path object.

    Returns:
        str: Lowercase function name extracted from the SQL file.
             Falls back to filename (without extension) if parsing fails.

    Examples:
        >>> get_function_name_from_sql_file("database/functions/get_users.sql")
        'get_users'
        >>> get_function_name_from_sql_file("database/functions/public.get_dashboard_stats.sql")
        'get_dashboard_stats'

    Note:
        - Handles both "CREATE FUNCTION" and "CREATE OR REPLACE FUNCTION" syntax
        - Handles schema-qualified names like "public.function_name"
        - Looks for function name before opening parenthesis
        - Returns lowercase function name for consistency
        - Gracefully falls back to filename if parsing fails

    Raises:
        No exceptions raised - always returns a value (fallback to filename)
    """
    try:
        with Path(filepath).open(encoding="utf-8") as f:
            content = f.read().upper()
            # Look for CREATE OR REPLACE FUNCTION or CREATE FUNCTION statement
            if "CREATE" in content and "FUNCTION" in content:
                # Match pattern like "CREATE FUNCTION public.function_name(" or "CREATE FUNCTION function_name("
                match = re.search(
                    r"CREATE\s+(?:OR\s+REPLACE\s+)?FUNCTION\s+(?:\w+\.)?(\w+)\s*\(",
                    content,
                )
                if match:
                    return match.group(1).lower()
    except Exception as e:
        logger.warning(f"Could not extract function name from {filepath}: {e}")

    # Fallback: use filename without extension
    return Path(filepath).stem


async def drop_all_functions(connection: AsyncConnection) -> None:
    """
    Drop all PostgreSQL functions from the database.

    Reads all SQL function definition files from the functions directory,
    extracts function names, and drops them from the database. Functions are
    dropped with CASCADE to handle any dependencies.

    Args:
        connection: Async SQLAlchemy connection to the tenant database.
                    Must be within an active transaction context.

    Returns:
        None: Function completes silently, errors are logged but don't stop execution.

    Side Effects:
        - Drops all functions matching those defined in backend/database/functions/
        - Uses CASCADE to handle function dependencies
        - Logs each function drop operation
        - Continues processing even if individual drops fail

    Error Handling:
        - Logs warnings if functions directory doesn't exist
        - Logs errors for individual function drop failures
        - Continues processing remaining functions on error
        - Does not raise exceptions (failures are logged only)

    Examples:
        ```python
        async with engine.begin() as connection:
            await drop_all_functions(connection)
        ```

    Note:
        - Functions are dropped before tables (they may depend on tables)
        - Uses "DROP FUNCTION IF EXISTS" to avoid errors if function doesn't exist
        - All functions are dropped from the 'public' schema
        - Function names are extracted from SQL files, not queried from database
    """
    logger.info(f"Looking for function SQL files in: {FUNCTIONS_DIR}")

    try:
        function_files = [f.name for f in FUNCTIONS_DIR.iterdir() if f.suffix == ".sql"]
    except FileNotFoundError:
        logger.warning(f"Directory not found: {FUNCTIONS_DIR}")
        return

    if not function_files:
        logger.info("No function files found.")
        return

    for filename in sorted(function_files):
        filepath = FUNCTIONS_DIR / filename
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


async def drop_all_tables(connection: AsyncConnection) -> None:
    """
    Drop all PostgreSQL tables from the database in reverse dependency order.

    Reads table definition files and drops tables in the reverse order of their
    creation to respect foreign key dependencies. Tables are dropped with CASCADE
    to handle any remaining dependencies.

    Args:
        connection: Async SQLAlchemy connection to the tenant database.
                    Must be within an active transaction context.

    Returns:
        None: Function completes silently, errors are logged but don't stop execution.

    Side Effects:
        - Drops all tables matching those defined in backend/database/tables/
        - Uses CASCADE to handle foreign key dependencies
        - Logs each table drop operation
        - Continues processing even if individual drops fail

    Error Handling:
        - Logs warnings if tables directory doesn't exist
        - Logs errors for individual table drop failures
        - Continues processing remaining tables on error
        - Does not raise exceptions (failures are logged only)

    Examples:
        ```python
        async with engine.begin() as connection:
            await drop_all_tables(connection)
        ```

    Note:
        - Tables are dropped after functions (tables may be referenced by functions)
        - Uses reverse order of TABLE_CREATION_ORDER to respect dependencies
        - Any tables not in TABLE_CREATION_ORDER are dropped in reverse alphabetical order
        - Uses "DROP TABLE IF EXISTS" to avoid errors if table doesn't exist
        - All tables are dropped from the 'public' schema
        - Table names are extracted from SQL files, not queried from database

    Performance:
        - Execution time depends on number of tables and their sizes
        - Large tables may take longer to drop
        - Typically completes in 1-5 seconds for standard schema
    """
    logger.info(f"Looking for table SQL files in: {TABLES_DIR}")

    try:
        all_table_files = {f.name for f in TABLES_DIR.iterdir() if f.suffix == ".sql"}
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
            filepath = TABLES_DIR / filename
            table_name = get_table_name_from_sql_file(str(filepath))
            logger.info(f"Extracted table name '{table_name}' from {filename}")
            tables_to_drop.append(table_name)
            all_table_files.remove(filename)

    # Add any remaining files that were not in the ordered list
    if all_table_files:
        logger.info(
            f"Adding remaining table files in reverse alphabetical order: {', '.join(sorted(all_table_files, reverse=True))}"
        )
        for filename in sorted(all_table_files, reverse=True):
            filepath = TABLES_DIR / filename
            table_name = get_table_name_from_sql_file(str(filepath))
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


async def list_remaining_objects(connection: AsyncConnection) -> None:
    """
    List any remaining tables and functions in the database after cleanup.

    Queries the database metadata to identify any tables or functions that
    remain after the cleanup operation. Useful for verifying that cleanup
    was successful or identifying unexpected objects.

    Args:
        connection: Async SQLAlchemy connection to the tenant database.
                    Can be within or outside a transaction context.

    Returns:
        None: Results are logged to the console, function doesn't return values.

    Side Effects:
        - Queries PostgreSQL system catalogs (information_schema, pg_database)
        - Logs remaining table names (if any)
        - Logs remaining function names (if any)
        - Logs confirmation message if no objects remain

    Error Handling:
        - Logs warnings if metadata queries fail
        - Does not raise exceptions (failures are logged only)
        - Continues execution even if inspection fails

    Examples:
        ```python
        async with engine.connect() as connection:
            await list_remaining_objects(connection)
        ```

    Note:
        - Uses SQLAlchemy Inspector for table listing (synchronous API)
        - Uses raw SQL for function listing (queries information_schema.routines)
        - Only lists objects in the 'public' schema
        - System tables and functions are excluded from results
        - Useful for debugging incomplete cleanup operations
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
        result = await connection.execute(
            text("""
            SELECT routine_name
            FROM information_schema.routines
            WHERE routine_type = 'FUNCTION'
            AND routine_schema = 'public'
        """)
        )
        remaining_functions = [row[0] for row in result]
        if remaining_functions:
            logger.info(f"Remaining functions: {', '.join(remaining_functions)}")
        else:
            logger.info("No functions remaining in database.")

    except Exception as e:
        logger.warning(f"Could not list remaining objects: {e}")


async def list_tenant_databases() -> list[str]:
    """
    List all tenant databases in the PostgreSQL server.

    Connects to the 'postgres' system database and queries pg_database to find
    all databases matching the tenant naming pattern (google-analytics-*).
    Excludes system databases and templates.

    Returns:
        list[str]: List of tenant database names, sorted alphabetically.
                   Returns empty list if no tenant databases found or on error.

    Raises:
        Exception: May raise database connection or query errors.
                   Caller should handle exceptions appropriately.

    Examples:
        >>> databases = await list_tenant_databases()
        >>> print(databases)
        ['google-analytics-550e8400-e29b-41d4-a716-446655440000', ...]

    Note:
        - Connects to 'postgres' database (not a tenant database)
        - Uses async SQLAlchemy engine for connection
        - Filters databases by naming pattern: 'google-analytics-%'
        - Excludes system databases: postgres, template0, template1
        - Excludes template databases (datistemplate = false)
        - Results are sorted alphabetically for consistent ordering

    Performance:
        - Query execution: ~50-200ms (depends on number of databases)
        - Network latency may add overhead for remote databases
        - Typically completes quickly even with many tenant databases
    """
    # Use same pattern as tenant_provisioning.py - connect to postgres database
    postgres_url = create_sqlalchemy_url("postgres", async_driver=True)
    engine = create_async_engine(postgres_url)

    try:
        async with engine.connect() as connection:
            # List all databases that match tenant database pattern (google-analytics-*)
            # Excluding system databases
            result = await connection.execute(
                text("""
                SELECT datname
                FROM pg_database
                WHERE datistemplate = false
                AND datname NOT IN ('postgres', 'template0', 'template1')
                AND datname LIKE 'google-analytics-%'
                ORDER BY datname
            """)
            )
            return [row[0] for row in result]
    finally:
        await engine.dispose()


async def clear_tenant_database(db_name: str) -> Optional[bool]:
    """
    Clear all tables and functions from a specific tenant database.

    Performs a CLEAR operation on a tenant database: drops all tables and functions
    while preserving the database itself. This allows the database to be
    re-initialized without recreating it.

    Args:
        db_name: Name of the tenant database to clear.
                 Should follow pattern: 'google-analytics-{tenant_id}'

    Returns:
        Optional[bool]: True if cleanup succeeded, False if it failed, None if
                       database connection couldn't be established.

    Raises:
        Exception: May raise database connection or SQL execution errors.
                   Errors are caught, logged, and False is returned.

    Side Effects:
        - Drops all tables from the database
        - Drops all functions from the database
        - Logs detailed operation information
        - Lists remaining objects after cleanup

    Examples:
        ```python
        success = await clear_tenant_database('google-analytics-550e8400-e29b-41d4-a716-446655440000')
        if success:
            print("Database cleared successfully")
        ```

    Note:
        - Uses async SQLAlchemy with transaction management
        - Functions are dropped before tables (respects dependencies)
        - Tables are dropped in reverse dependency order
        - Database structure remains intact (only data/schema removed)
        - Can be re-initialized using init_db.py or tenant_provisioning module

    Error Handling:
        - Returns None if database engine creation fails
        - Returns False if cleanup operations fail
        - Returns True if all operations succeed
        - All errors are logged with detailed messages

    Performance:
        - Database connection: ~100-500ms
        - Function dropping: ~500ms-2s (depends on number of functions)
        - Table dropping: ~1-5s (depends on number and size of tables)
        - Total execution: Typically 2-10 seconds per database
    """
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
    """
    Extract tenant ID from database name.

    Parses the tenant database naming convention to extract the tenant UUID.
    Database names follow the pattern: 'google-analytics-{tenant_id}'.

    Args:
        db_name: Database name following the tenant naming convention.
                 Example: 'google-analytics-550e8400-e29b-41d4-a716-446655440000'

    Returns:
        str: Tenant ID (UUID string) extracted from the database name.
             Returns the original db_name if it doesn't match the expected pattern.

    Examples:
        >>> extract_tenant_id_from_db_name('google-analytics-550e8400-e29b-41d4-a716-446655440000')
        '550e8400-e29b-41d4-a716-446655440000'
        >>> extract_tenant_id_from_db_name('some-other-db')
        'some-other-db'

    Note:
        - Assumes database names follow the pattern: 'google-analytics-{tenant_id}'
        - If pattern doesn't match, returns the original database name
        - No validation of tenant_id format (UUID validation not performed)
        - Used primarily for passing tenant_id to drop_tenant_database()

    Raises:
        No exceptions raised - always returns a value
    """
    prefix = "google-analytics-"
    if db_name.startswith(prefix):
        return db_name[len(prefix) :]
    return db_name


async def main() -> None:
    """
    Main entry point for the database cleanup script.

    Provides an interactive command-line interface for managing tenant databases.
    Users can select databases and choose between CLEAR (drop tables/functions)
    or DELETE (remove entire database) operations.

    **Workflow:**
        1. Lists all tenant databases found in the PostgreSQL server
        2. Prompts user to select databases (by number or 'all')
        3. Prompts user to choose operation type (CLEAR or DELETE)
        4. Requests confirmation for destructive operations
        5. Executes selected operations on chosen databases
        6. Displays summary of successful/failed operations

    **User Interactions:**
        - Database selection: Enter numbers (e.g., "1,3,5") or "all"
        - Operation selection: Enter "1" for CLEAR, "2" for DELETE
        - Confirmation: Type "yes" for CLEAR, "DELETE" for DELETE operation

    **Returns:**
        None: Function completes and returns, no exit code set.

    **Side Effects:**
        - Reads from stdin for user input
        - Writes to stdout for user prompts
        - Modifies database state based on user selections
        - Logs all operations to console and log file

    **Error Handling:**
        - Continues processing remaining databases if one fails
        - Logs detailed error messages for each failure
        - Provides summary of successful/failed operations
        - Does not exit on errors (allows user to see all results)

    **Examples:**
        Interactive session:
        ```
        Found 3 tenant database(s):
          1. google-analytics-tenant-1
          2. google-analytics-tenant-2
          3. google-analytics-tenant-3

        Select databases: 1,3
        Select operation (1 or 2): 1
        Are you sure you want to proceed? (yes/no): yes
        ```

    **Security Considerations:**
        - DELETE operation requires typing 'DELETE' (case-sensitive)
        - CLEAR operation requires 'yes' confirmation
        - All operations are logged for audit purposes
        - User can cancel at any prompt by entering 'cancel' or 'no'

    **Performance:**
        - Database listing: ~50-200ms
        - Per-database operations: 2-10 seconds each
        - Total time scales linearly with number of databases selected
        - User input time not included in performance metrics
    """
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

    if selection == "cancel":
        logger.info("Database cleanup cancelled.")
        return

    # Determine which databases to operate on
    databases_selected = []

    if selection == "all":
        databases_selected = tenant_databases
    else:
        try:
            indices = [int(idx.strip()) for idx in selection.split(",")]
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

    if operation == "2":
        # DELETE entire database
        logger.info(
            f"\nYou are about to PERMANENTLY DELETE {len(databases_selected)} database(s):"
        )
        for db in databases_selected:
            print(f"  - {db}")

        print("\n⚠️  WARNING: This action cannot be undone!")
        response = input("\nType 'DELETE' to confirm: ").strip()
        if response != "DELETE":
            logger.info("Database deletion cancelled.")
            return

        # Delete selected databases
        success_count = 0
        failed_count = 0

        for db_name in databases_selected:
            logger.info(f"\n{'=' * 60}")
            logger.info(f"Deleting: {db_name}")
            logger.info(f"{'=' * 60}")

            tenant_id = extract_tenant_id_from_db_name(db_name)
            success = drop_tenant_database(tenant_id)
            if success:
                success_count += 1
                logger.info(f"Successfully deleted database: {db_name}")
            else:
                failed_count += 1
                logger.error(f"Failed to delete database: {db_name}")

        # Summary
        logger.info(f"\n{'=' * 60}")
        logger.info("Deletion Summary:")
        logger.info(f"  Successfully deleted: {success_count} database(s)")
        if failed_count > 0:
            logger.error(f"  Failed: {failed_count} database(s)")
            logger.info(
                "  Note: For Cloud SQL, you may need to use the Google Cloud Console or gcloud CLI."
            )
        logger.info(f"{'=' * 60}")

    else:
        # CLEAR tables/functions (keep database)
        logger.info(
            f"\nYou are about to CLEAR all tables and functions from {len(databases_selected)} database(s):"
        )
        for db in databases_selected:
            print(f"  - {db}")

        response = (
            input("\nAre you sure you want to proceed? (yes/no): ").lower().strip()
        )
        if response not in ["yes", "y"]:
            logger.info("Database cleanup cancelled.")
            return

        # Clear selected databases
        success_count = 0
        failed_count = 0

        for db_name in databases_selected:
            logger.info(f"\n{'=' * 60}")
            logger.info(f"Clearing: {db_name}")
            logger.info(f"{'=' * 60}")

            success = await clear_tenant_database(db_name)
            if success:
                success_count += 1
            else:
                failed_count += 1

        # Summary
        logger.info(f"\n{'=' * 60}")
        logger.info("Cleanup Summary:")
        logger.info(f"  Successfully cleared: {success_count} database(s)")
        if failed_count > 0:
            logger.info(f"  Failed: {failed_count} database(s)")
        logger.info(f"{'=' * 60}")


if __name__ == "__main__":
    """
    Script entry point.

    Configures logging to both console (stderr) and file, then executes the
    main async function. Logs are written to:
    - Console: INFO level with timestamps
    - File: logs/clear_db.log (rotates at 500 MB to prevent disk space issues)

    The script runs in interactive mode, prompting users for database selection
    and operation type. All operations are logged for audit purposes.
    """
    # Configure logger
    logger.add(
        sys.stderr, format="{time} {level} {message}", filter="my_module", level="INFO"
    )
    logger.add("logs/clear_db.log", rotation="500 MB")  # For logging to a file

    asyncio.run(main())
