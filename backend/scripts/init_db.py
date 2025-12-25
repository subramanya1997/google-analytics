"""
Tenant Database Initialization Script.

This module provides a command-line utility for manually provisioning tenant-specific
databases in a multi-tenant architecture. It is primarily used for administrative
purposes and development/testing scenarios.

**Architecture Context:**
    - The system uses a multi-tenant architecture with complete database isolation
    - Each tenant has its own dedicated PostgreSQL database
    - Database names follow the pattern: `google-analytics-{tenant_id}`
    - This ensures SOC2 compliance through physical data isolation

**Primary Use Cases:**
    1. Manual tenant database provisioning during development
    2. Testing database initialization workflows
    3. Recovery scenarios where automatic provisioning failed
    4. Administrative database setup for new tenants

**Note:** In production, tenant databases are automatically created during OAuth
authentication. This script is kept for manual intervention scenarios.

**Security Considerations:**
    - Requires database admin credentials (via environment variables)
    - Validates tenant_id format before provisioning
    - Does not overwrite existing databases unless explicitly forced
    - All operations are logged for audit purposes

**Dependencies:**
    - PostgreSQL database server (local or Cloud SQL)
    - Environment variables: DB_HOST, DB_PORT, DB_USER, DB_PASSWORD
    - SQL table and function definitions in backend/database/

**Example Usage:**
    ```bash
    # Provision a single tenant database
    python scripts/init_db.py 550e8400-e29b-41d4-a716-446655440000

    # The script will:
    # 1. Create the database: google-analytics-550e8400-e29b-41d4-a716-446655440000
    # 2. Create all required tables in dependency order
    # 3. Create all required PostgreSQL functions
    # 4. Initialize tenant configuration
    ```

**Error Handling:**
    - Exits with code 0 on success
    - Exits with code 1 on failure (database connection, SQL errors, etc.)
    - All errors are logged to both console and logs/init_db.log

**Logging:**
    - Console output: INFO level with timestamps
    - File output: logs/init_db.log (rotates at 500 MB)
"""

import asyncio
from pathlib import Path
import sys

from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# Add the project's root directory to the Python path
sys.path.append(str(Path(__file__).parent.parent.resolve()))

from common.database import provision_tenant_database

# Paths no longer needed - provisioning handled by tenant_provisioning.py


async def main() -> None:
    """
    Main entry point for tenant database initialization.

    This function handles the command-line interface and orchestrates the tenant
    database provisioning process. It validates input, provides user feedback,
    and handles errors gracefully.

    **Workflow:**
        1. Display deprecation notice (automatic provisioning is preferred)
        2. Validate tenant_id argument from command line
        3. Call provision_tenant_database() to create database and schema
        4. Display success/failure status with database name
        5. Exit with appropriate status code

    **Command Line Arguments:**
        - tenant_id (required): UUID string identifying the tenant
          Format: UUID v4 (e.g., "550e8400-e29b-41d4-a716-446655440000")

    **Returns:**
        None: Function exits via sys.exit() on completion

    **Raises:**
        SystemExit: Exits with code 0 on success, code 1 on failure

    **Examples:**
        ```bash
        # Valid usage
        python init_db.py 550e8400-e29b-41d4-a716-446655440000

        # Missing tenant_id (shows usage instructions)
        python init_db.py
        ```

    **Side Effects:**
        - Creates new PostgreSQL database if it doesn't exist
        - Creates tables and functions in the tenant database
        - Writes log entries to console and log file
        - Modifies database state (non-idempotent unless database exists)

    **Error Scenarios:**
        - Missing tenant_id: Displays usage instructions, exits with code 0
        - Database connection failure: Logs error, exits with code 1
        - SQL execution errors: Logs error, exits with code 1
        - Invalid tenant_id format: Handled by provision_tenant_database()

    **Performance Notes:**
        - Database creation: ~100-500ms (depends on PostgreSQL server)
        - Table creation: ~1-5 seconds (13 tables with dependencies)
        - Function creation: ~500ms-2s (depends on function complexity)
        - Total execution time: Typically 2-10 seconds for new database
    """
    logger.warning("=" * 80)
    logger.warning("NOTICE: Master database concept has been removed.")
    logger.warning("Tenant databases are automatically created during authentication.")
    logger.warning("=" * 80)

    # Check if tenant_id provided as command line argument
    if len(sys.argv) < 2:
        logger.info("")
        logger.info("For manual tenant database creation, provide tenant_id:")
        logger.info(f"  python {sys.argv[0]} <tenant_id>")
        logger.info("")
        logger.info("Example:")
        logger.info(f"  python {sys.argv[0]} 550e8400-e29b-41d4-a716-446655440000")
        logger.info("")
        return

    tenant_id: str = sys.argv[1]
    logger.info(f"Manually provisioning database for tenant: {tenant_id}")

    try:
        success: bool = await provision_tenant_database(tenant_id, force_recreate=False)

        if success:
            logger.info(f"✓ Successfully provisioned database for tenant {tenant_id}")
            from common.database.tenant_provisioning import get_tenant_database_name

            db_name: str = get_tenant_database_name(tenant_id)
            logger.info(f"✓ Database name: {db_name}")
        else:
            logger.error(f"✗ Failed to provision database for tenant {tenant_id}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"✗ Error during provisioning: {e}")
        sys.exit(1)


if __name__ == "__main__":
    """
    Script entry point.

    Configures logging to both console (stderr) and file, then executes the
    main async function. Logs are written to:
    - Console: INFO level with timestamps
    - File: logs/init_db.log (rotates at 500 MB to prevent disk space issues)
    """
    # Configure logger
    logger.add(
        sys.stderr, format="{time} {level} {message}", filter="my_module", level="INFO"
    )
    logger.add("logs/init_db.log", rotation="500 MB")  # For logging to a file

    asyncio.run(main())
