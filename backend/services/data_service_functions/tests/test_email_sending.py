"""
Test script for Email Queue Messaging

This script sends messages directly to the Azure Storage Queue to trigger
email sending jobs. It tests the queue-based architecture where:
1. This script sends a message to 'email-jobs' queue
2. Azure Functions Queue Trigger picks up the message and processes it
3. Check Azure Functions logs or database to see job progress

Note: Email mappings must be configured in the database (branch_email_mappings table).

Usage:
    python test_email_sending.py \\
      --tenant-id YOUR_TENANT_ID \\
      --connection-string "DefaultEndpointsProtocol=https;AccountName=..." \\
      --report-date 2025-12-23 \\
      --branch-codes D01,D02
    
    # Or for all branches:
    python test_email_sending.py \\
      --tenant-id YOUR_TENANT_ID \\
      --connection-string "..." \\
      --report-date 2025-12-23
"""

import argparse
import json
import os
import sys
from datetime import datetime, date, timedelta
from typing import List, Optional

from azure.storage.queue import QueueClient
from dotenv import load_dotenv
import asyncio

# Add parent directory to path to import shared modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.database import create_repository

# Load environment variables from .env file
load_dotenv()


class EmailQueueTester:
    """Test client for sending email messages to Azure Storage Queue."""
    
    def __init__(self, connection_string: str, tenant_id: str):
        """
        Initialize queue test client.
        
        Args:
            connection_string: Azure Storage connection string
            tenant_id: Tenant UUID to test with
        """
        self.connection_string = connection_string
        self.tenant_id = tenant_id
        self.queue_name = "email-jobs"
        self.repo = create_repository(tenant_id)
    
    async def send_email_message(
        self,
        job_id: str,
        report_date: date,
        branch_codes: Optional[List[str]] = None
    ) -> bool:
        """
        Send an email job message to the queue.
        
        Args:
            job_id: Unique job ID
            report_date: Date for the report
            branch_codes: Optional list of branch codes (None = all branches)
            
        Returns:
            True if message was sent successfully, False otherwise
        """
        branch_info = f"{len(branch_codes)} branches" if branch_codes else "all branches"
        
        print(f"\n📝 Step 1: Creating email job record in database...")
        print(f"   Job ID: {job_id}")
        print(f"   Tenant ID: {self.tenant_id}")
        print(f"   Report Date: {report_date}")
        print(f"   Target: {branch_info}")
        
        try:
            # Step 1: Create email job record in database (just like FastAPI does)
            await self.repo.create_email_job({
                "job_id": job_id,
                "tenant_id": self.tenant_id,
                "status": "queued",
                "report_date": report_date,
                "target_branches": branch_codes or []
            })
            print(f"✅ Email job record created in database")
            
        except Exception as e:
            print(f"\n❌ Failed to create email job in database: {e}")
            print(f"   Error type: {type(e).__name__}")
            return False
        
        # Step 2: Send message to queue
        message = {
            "job_id": job_id,
            "tenant_id": self.tenant_id,
            "report_date": report_date.isoformat(),
            "branch_codes": branch_codes
        }
        
        print(f"\n📤 Step 2: Sending message to '{self.queue_name}' queue...")
        
        try:
            # Connect to queue
            queue_client = QueueClient.from_connection_string(
                self.connection_string,
                self.queue_name
            )
            
            # Send message
            message_json = json.dumps(message)
            queue_client.send_message(message_json)
            
            print(f"✅ Message sent to queue successfully!")
            print(f"   Queue: {self.queue_name}")
            print(f"   Message: {message_json}")
            print(f"\n📊 What happens next:")
            print(f"   1. Azure Functions Queue Trigger will pick up this message")
            print(f"   2. It will generate and send email reports (2-5 minutes)")
            print(f"   3. Job status will be updated from 'queued' → 'processing' → 'completed'")
            print(f"   4. Check Azure Functions logs to see progress")
            print(f"   5. Query 'email_sending_jobs' table for job status")
            print(f"   6. Check 'email_send_history' for individual email results")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Failed to send message to queue: {e}")
            print(f"   Error type: {type(e).__name__}")
            print(f"\n⚠️  Note: Email job record was created in DB but message wasn't queued.")
            print(f"   You may need to manually update job status or delete the record.")
            return False


def main():
    """Main test function."""
    parser = argparse.ArgumentParser(
        description="Test email sending by sending messages to Azure Storage Queue",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Send email job to queue for all branches (reads connection string from .env)
  python test_email_sending.py \\
    --tenant-id "123e4567-e89b-12d3-a456-426614174000" \\
    --report-date 2025-12-23
  
  # Send for specific branches
  python test_email_sending.py \\
    --tenant-id "123e4567-e89b-12d3-a456-426614174000" \\
    --report-date 2025-12-23 \\
    --branch-codes D01,D02,D03
  
  # Or explicitly provide connection string
  python test_email_sending.py \\
    --tenant-id "123e4567-e89b-12d3-a456-426614174000" \\
    --connection-string "DefaultEndpointsProtocol=https;..." \\
    --report-date 2025-12-23

Note:
  - Automatically reads AZURE_STORAGE_CONNECTION_STRING from .env file
  - Email mappings must be configured in 'branch_email_mappings' table
  - Report date defaults to yesterday if not provided
        """
    )
    
    parser.add_argument(
        "--tenant-id",
        required=True,
        help="Tenant ID (UUID)"
    )
    
    parser.add_argument(
        "--connection-string",
        default=None,
        help="Azure Storage connection string (optional: reads from .env file or AZURE_STORAGE_CONNECTION_STRING env var)"
    )
    
    parser.add_argument(
        "--report-date",
        default=None,
        help="Report date (YYYY-MM-DD). Default: yesterday"
    )
    
    parser.add_argument(
        "--branch-codes",
        default=None,
        help="Comma-separated branch codes (e.g., D01,D02). Default: all branches"
    )
    
    parser.add_argument(
        "--job-id",
        default=None,
        help="Custom job ID (optional, will be generated if not provided)"
    )
    
    args = parser.parse_args()
    
    # Get connection string (automatically loads from .env file)
    connection_string = args.connection_string or os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    if not connection_string:
        print("❌ Error: Azure Storage connection string is required!")
        print("\n   Option 1 (Recommended): Add to .env file:")
        print("      AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;...")
        print("\n   Option 2: Pass via command line:")
        print("      --connection-string \"DefaultEndpointsProtocol=https;...\"")
        print("\n   Get it from: Azure Portal → Storage Account → Access keys → Connection string")
        return 1
    
    # Generate job ID if not provided
    import uuid
    job_id = args.job_id or f"email_job_{uuid.uuid4().hex[:12]}"
    
    # Parse report date
    if args.report_date:
        try:
            report_date = datetime.strptime(args.report_date, "%Y-%m-%d").date()
        except ValueError:
            print(f"❌ Invalid date format: {args.report_date}. Use YYYY-MM-DD")
            sys.exit(1)
    else:
        # Default to yesterday
        report_date = date.today() - timedelta(days=1)
    
    # Parse branch codes
    branch_codes = None
    if args.branch_codes:
        branch_codes = [code.strip() for code in args.branch_codes.split(",")]
    
    print("=" * 80)
    print("Email Sending Queue Test".center(80))
    print("=" * 80)
    print(f"Tenant ID: {args.tenant_id}")
    print(f"Job ID: {job_id}")
    print(f"Report Date: {report_date.strftime('%Y-%m-%d')}")
    if branch_codes:
        print(f"Target Branches: {', '.join(branch_codes)}")
    else:
        print(f"Target Branches: All configured branches")
    print(f"Queue: email-jobs")
    print("=" * 80)
    
    print("\n⚠️  Prerequisites:")
    print("   - Email mappings configured in 'branch_email_mappings' table")
    print("   - SMTP configuration in 'tenants' table (smtp_config column)")
    print("   - Branch codes must exist in your database")
    
    # Initialize tester
    tester = EmailQueueTester(connection_string, args.tenant_id)
    
    # Send message to queue (async operation)
    success = asyncio.run(tester.send_email_message(
        job_id=job_id,
        report_date=report_date,
        branch_codes=branch_codes
    ))
    
    if success:
        print("\n" + "=" * 80)
        print("✅ Message sent to queue successfully!")
        print("\n📝 Next Steps:")
        print("   1. Check Azure Functions logs:")
        print("      Azure Portal → Function App → Log stream")
        print(f"\n   2. Check job status in database:")
        print(f"      SELECT * FROM email_sending_jobs WHERE job_id = '{job_id}';")
        print(f"\n   3. Check email send history:")
        print(f"      SELECT * FROM email_send_history WHERE job_id = '{job_id}';")
        print("\n   4. Monitor queue:")
        print("      Azure Portal → Storage Account → Queues → email-jobs")
        print("=" * 80)
        return 0
    else:
        print("\n❌ Failed to send message to queue")
        return 1


if __name__ == "__main__":
    main()

