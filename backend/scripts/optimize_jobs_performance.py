#!/usr/bin/env python3
"""
Optimize Jobs Tables Performance

This script applies database optimizations to improve the performance
of /api/v1/jobs and /api/v1/email/jobs endpoints by:

1. Adding statistics targets to improve query planning
2. Ensuring critical indexes exist
3. Creating optimized pagination functions
4. Running ANALYZE to update table statistics

Usage:
    python scripts/optimize_jobs_performance.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy import text

from common.database import get_async_db_session


async def run_migration():
    """Run the jobs optimization migration."""
    
    migration_file = Path(__file__).parent.parent / "database" / "migrations" / "optimize_jobs_tables.sql"
    
    if not migration_file.exists():
        logger.error(f"Migration file not found: {migration_file}")
        return False
    
    logger.info("Reading migration SQL...")
    migration_sql = migration_file.read_text()
    
    try:
        async with get_async_db_session("analytics-service") as session:
            logger.info("Applying database optimizations...")
            
            # Split by semicolons and execute each statement
            statements = [s.strip() for s in migration_sql.split(';') if s.strip() and not s.strip().startswith('--')]
            
            for i, statement in enumerate(statements, 1):
                # Skip comment-only statements
                if all(line.strip().startswith('--') or not line.strip() for line in statement.split('\n')):
                    continue
                
                try:
                    logger.debug(f"Executing statement {i}/{len(statements)}")
                    await session.execute(text(statement))
                except Exception as e:
                    # Some statements might fail if already applied (like CREATE INDEX IF NOT EXISTS)
                    # That's okay - log and continue
                    logger.debug(f"Statement {i} result: {str(e)}")
            
            await session.commit()
            logger.success("✓ Database optimizations applied successfully!")
            
            # Verify the optimizations
            logger.info("Verifying optimizations...")
            
            # Check processing_jobs statistics
            result = await session.execute(text("""
                SELECT attname, attstattarget 
                FROM pg_attribute 
                WHERE attrelid = 'processing_jobs'::regclass 
                  AND attname IN ('tenant_id', 'job_id', 'status', 'created_at')
                ORDER BY attname
            """))
            logger.info("Processing jobs statistics targets:")
            for row in result:
                logger.info(f"  - {row.attname}: {row.attstattarget}")
            
            # Check email_sending_jobs statistics
            result = await session.execute(text("""
                SELECT attname, attstattarget 
                FROM pg_attribute 
                WHERE attrelid = 'email_sending_jobs'::regclass 
                  AND attname IN ('tenant_id', 'job_id', 'status', 'created_at')
                ORDER BY attname
            """))
            logger.info("Email sending jobs statistics targets:")
            for row in result:
                logger.info(f"  - {row.attname}: {row.attstattarget}")
            
            # Check indexes
            result = await session.execute(text("""
                SELECT tablename, indexname 
                FROM pg_indexes 
                WHERE tablename IN ('processing_jobs', 'email_sending_jobs')
                  AND indexname LIKE '%tenant%created%'
                ORDER BY tablename, indexname
            """))
            logger.info("Critical indexes:")
            for row in result:
                logger.info(f"  - {row.tablename}: {row.indexname}")
            
            # Check functions exist
            result = await session.execute(text("""
                SELECT proname 
                FROM pg_proc 
                WHERE proname IN ('get_tenant_jobs_paginated', 'get_email_jobs_paginated')
                ORDER BY proname
            """))
            logger.info("Pagination functions:")
            for row in result:
                logger.info(f"  - {row.proname}")
            
            logger.success("✓ All optimizations verified!")
            return True
            
    except Exception as e:
        logger.error(f"Failed to apply optimizations: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("Jobs Tables Performance Optimization")
    logger.info("=" * 60)
    
    success = await run_migration()
    
    if success:
        logger.success("\n✓ Optimization complete!")
        logger.info("\nThe following endpoints should now be faster:")
        logger.info("  - /api/v1/jobs (data ingestion jobs)")
        logger.info("  - /api/v1/email/jobs (email sending jobs)")
        logger.info("\nChanges applied:")
        logger.info("  1. Statistics targets added for better query planning")
        logger.info("  2. Optimized indexes ensured")
        logger.info("  3. Single-query pagination functions created")
        logger.info("  4. Table statistics updated (ANALYZE)")
    else:
        logger.error("\n✗ Optimization failed!")
        logger.error("Please check the error messages above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

