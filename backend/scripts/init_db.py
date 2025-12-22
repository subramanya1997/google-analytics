import os
import sys
import asyncio
from sqlalchemy import text
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

# Add the project's root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.database import provision_tenant_database

# Paths no longer needed - provisioning handled by tenant_provisioning.py

async def main():
    """
    DEPRECATED: Master database concept removed for SOC2 compliance.
    
    Tenant databases are automatically created during OAuth authentication.
    
    This script is kept for manual tenant database creation if needed.
    Usage: python init_db.py <tenant_id>
    
    Example: python init_db.py 550e8400-e29b-41d4-a716-446655440000
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
    
    tenant_id = sys.argv[1]
    logger.info(f"Manually provisioning database for tenant: {tenant_id}")
    
    try:
        success = await provision_tenant_database(tenant_id, force_recreate=False)
        
        if success:
            logger.info(f"✓ Successfully provisioned database for tenant {tenant_id}")
            from common.database.tenant_provisioning import get_tenant_database_name
            db_name = get_tenant_database_name(tenant_id)
            logger.info(f"✓ Database name: {db_name}")
        else:
            logger.error(f"✗ Failed to provision database for tenant {tenant_id}")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"✗ Error during provisioning: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Configure logger
    logger.add(sys.stderr, format="{time} {level} {message}", filter="my_module", level="INFO")
    logger.add("logs/init_db.log", rotation="500 MB") # For logging to a file

    asyncio.run(main())
