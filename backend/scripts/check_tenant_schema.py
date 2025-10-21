"""
Diagnostic script to check tenant table schema and data.

This script checks:
1. If the tenants table exists
2. What columns are present in the tenants table
3. Current tenant data and service status
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy import text

from common.database import get_async_db_session


async def check_tenant_schema():
    """Check the tenant table schema and data."""
    try:
        logger.info("Connecting to database...")
        
        async with get_async_db_session("diagnostics") as session:
            # Check if tenants table exists
            logger.info("\n" + "="*60)
            logger.info("Checking if tenants table exists...")
            logger.info("="*60)
            
            result = await session.execute(
                text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'tenants'
                    )
                """)
            )
            table_exists = result.scalar()
            
            if not table_exists:
                logger.error("❌ Tenants table does NOT exist!")
                return
            
            logger.info("✅ Tenants table exists")
            
            # Get all columns in tenants table
            logger.info("\n" + "="*60)
            logger.info("Checking columns in tenants table...")
            logger.info("="*60)
            
            result = await session.execute(
                text("""
                    SELECT 
                        column_name,
                        data_type,
                        is_nullable,
                        column_default
                    FROM information_schema.columns 
                    WHERE table_name = 'tenants'
                    ORDER BY ordinal_position
                """)
            )
            columns = result.fetchall()
            
            logger.info(f"\nFound {len(columns)} columns:")
            logger.info("-" * 60)
            
            service_status_columns = [
                'bigquery_enabled', 'sftp_enabled', 'smtp_enabled',
                'bigquery_validation_error', 'sftp_validation_error', 'smtp_validation_error'
            ]
            
            found_service_columns = []
            
            for col in columns:
                col_name = col[0]
                col_type = col[1]
                nullable = col[2]
                default = col[3]
                
                # Highlight service status columns
                if col_name in service_status_columns:
                    logger.info(f"✅ {col_name:30s} | {col_type:15s} | Nullable: {nullable:3s} | Default: {default}")
                    found_service_columns.append(col_name)
                else:
                    logger.info(f"   {col_name:30s} | {col_type:15s} | Nullable: {nullable:3s} | Default: {default}")
            
            # Check which service columns are missing
            logger.info("\n" + "="*60)
            logger.info("Service Status Columns Check:")
            logger.info("="*60)
            
            for col in service_status_columns:
                if col in found_service_columns:
                    logger.info(f"✅ {col} - PRESENT")
                else:
                    logger.error(f"❌ {col} - MISSING")
            
            missing_columns = [col for col in service_status_columns if col not in found_service_columns]
            
            if missing_columns:
                logger.warning(f"\n⚠️  Missing columns detected: {missing_columns}")
                logger.warning("Run the migration script to add missing columns:")
                logger.warning("  python backend/scripts/add_service_status_columns.py")
            else:
                logger.info("\n✅ All service status columns are present!")
            
            # Get tenant count and data
            logger.info("\n" + "="*60)
            logger.info("Checking tenant data...")
            logger.info("="*60)
            
            result = await session.execute(text("SELECT COUNT(*) FROM tenants"))
            tenant_count = result.scalar()
            
            logger.info(f"\nTotal tenants: {tenant_count}")
            
            if tenant_count > 0:
                # Get tenant details with service status
                if not missing_columns:
                    query = text("""
                        SELECT 
                            id,
                            name,
                            is_active,
                            bigquery_enabled,
                            sftp_enabled,
                            smtp_enabled,
                            bigquery_validation_error,
                            sftp_validation_error,
                            smtp_validation_error
                        FROM tenants
                        ORDER BY created_at DESC
                        LIMIT 10
                    """)
                else:
                    # If columns are missing, just get basic info
                    query = text("""
                        SELECT 
                            id,
                            name,
                            is_active
                        FROM tenants
                        ORDER BY created_at DESC
                        LIMIT 10
                    """)
                
                result = await session.execute(query)
                tenants = result.fetchall()
                
                logger.info("\nTenant Details (showing up to 10):")
                logger.info("-" * 100)
                
                for tenant in tenants:
                    if not missing_columns:
                        tenant_id, name, is_active, bq_enabled, sftp_enabled, smtp_enabled, bq_error, sftp_error, smtp_error = tenant
                        
                        logger.info(f"\nTenant ID: {tenant_id}")
                        logger.info(f"  Name: {name}")
                        logger.info(f"  Active: {is_active}")
                        logger.info(f"  Services:")
                        logger.info(f"    BigQuery: {'✅ Enabled' if bq_enabled else '❌ Disabled'} {f'({bq_error})' if bq_error else ''}")
                        logger.info(f"    SFTP:     {'✅ Enabled' if sftp_enabled else '❌ Disabled'} {f'({sftp_error})' if sftp_error else ''}")
                        logger.info(f"    SMTP:     {'✅ Enabled' if smtp_enabled else '❌ Disabled'} {f'({smtp_error})' if smtp_error else ''}")
                    else:
                        tenant_id, name, is_active = tenant
                        logger.info(f"\nTenant ID: {tenant_id}")
                        logger.info(f"  Name: {name}")
                        logger.info(f"  Active: {is_active}")
                        logger.info(f"  Services: (columns not available)")
            else:
                logger.warning("\n⚠️  No tenants found in database")
            
            # Summary
            logger.info("\n" + "="*60)
            logger.info("SUMMARY")
            logger.info("="*60)
            
            if missing_columns:
                logger.error(f"❌ Database schema is INCOMPLETE - {len(missing_columns)} columns missing")
                logger.warning("\nAction Required:")
                logger.warning("  Run: python backend/scripts/add_service_status_columns.py")
            else:
                logger.info("✅ Database schema is COMPLETE - all service status columns present")
            
            if tenant_count == 0:
                logger.warning("⚠️  No tenants in database - authenticate to create tenant")
            
    except Exception as e:
        logger.error(f"Error checking tenant schema: {e}")
        import traceback
        logger.error(traceback.format_exc())


def main():
    """Run the schema check."""
    logger.info("Starting tenant schema diagnostics...")
    asyncio.run(check_tenant_schema())
    logger.info("\nDiagnostics complete!")


if __name__ == "__main__":
    main()

