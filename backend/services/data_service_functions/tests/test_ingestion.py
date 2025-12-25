#!/usr/bin/env python3
"""
Test script for data ingestion queue messaging.

This script sends messages directly to the Azure Storage Queue to trigger
data ingestion jobs. It tests the queue-based architecture where:
1. This script sends a message to 'ingestion-jobs' queue
2. Azure Functions Queue Trigger picks up the message and processes it
3. Check Azure Functions logs or database to see job progress

Usage:
    python test_ingestion.py --tenant-id <tenant-uuid> --connection-string <conn-str>

Example:
    python test_ingestion.py \\
      --tenant-id "123e4567-e89b-12d3-a456-426614174000" \\
      --connection-string "DefaultEndpointsProtocol=https;AccountName=..."
"""

import argparse
import asyncio
from datetime import date, timedelta
import json
import os
from pathlib import Path
import sys

from azure.storage.queue import QueueClient
from dotenv import load_dotenv

# Add parent directory to path to import shared modules
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

from shared.database import create_repository

# Load environment variables from .env file
load_dotenv()


class IngestionQueueTester:
    """Test client for sending ingestion messages to Azure Storage Queue."""

    def __init__(self, connection_string: str, tenant_id: str):
        """
        Initialize queue test client.

        Args:
            connection_string: Azure Storage connection string
            tenant_id: Tenant UUID to test with
        """
        self.connection_string = connection_string
        self.tenant_id = tenant_id
        self.queue_name = "ingestion-jobs"
        self.repo = create_repository(tenant_id)

    async def send_ingestion_message(
        self, job_id: str, start_date: date, end_date: date, data_types: list | None = None
    ) -> bool:
        """
        Send an ingestion job message to the queue.

        Args:
            job_id: Unique job ID (will be generated if not provided)
            start_date: Start date for ingestion (inclusive)
            end_date: End date for ingestion (inclusive)
            data_types: List of data types to ingest. Default: ["events", "users", "locations"]

        Returns:
            True if message was sent successfully, False otherwise
        """
        if data_types is None:
            data_types = ["events", "users", "locations"]

        print("\n📝 Step 1: Creating job record in database...")
        print(f"   Job ID: {job_id}")
        print(f"   Tenant ID: {self.tenant_id}")
        print(f"   Date range: {start_date} to {end_date}")
        print(f"   Data types: {', '.join(data_types)}")

        try:
            # Step 1: Create job record in database (just like FastAPI does)
            await self.repo.create_processing_job(
                {
                    "job_id": job_id,
                    "tenant_id": self.tenant_id,
                    "status": "queued",
                    "data_types": data_types,
                    "start_date": start_date,
                    "end_date": end_date,
                }
            )
            print("✅ Job record created in database")

        except Exception as e:
            print(f"\n❌ Failed to create job in database: {e}")
            print(f"   Error type: {type(e).__name__}")
            return False

        # Step 2: Send message to queue
        message = {
            "job_id": job_id,
            "tenant_id": self.tenant_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "data_types": data_types,
        }

        print(f"\n📤 Step 2: Sending message to '{self.queue_name}' queue...")

        try:
            # Connect to queue
            queue_client = QueueClient.from_connection_string(
                self.connection_string, self.queue_name
            )

            # Send message
            message_json = json.dumps(message)
            queue_client.send_message(message_json)

            print("✅ Message sent to queue successfully!")
            print(f"   Queue: {self.queue_name}")
            print(f"   Message: {message_json}")
            print("\n📊 What happens next:")
            print("   1. Azure Functions Queue Trigger will pick up this message")
            print("   2. It will process the ingestion job (5-10 minutes)")
            print(
                "   3. Job status will be updated from 'queued' → 'processing' → 'completed'"
            )
            print("   4. Check Azure Functions logs to see progress")
            print("   5. Query the database 'processing_jobs' table for job status")

            return True

        except Exception as e:
            print(f"\n❌ Failed to send message to queue: {e}")
            print(f"   Error type: {type(e).__name__}")
            print("\n⚠️  Note: Job record was created in DB but message wasn't queued.")
            print("   You may need to manually update job status or delete the record.")
            return False


def main():
    """Main test function."""
    parser = argparse.ArgumentParser(
        description="Test data ingestion by sending messages to Azure Storage Queue",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Send ingestion job to queue (reads connection string from .env file)
  python test_ingestion.py \\
    --tenant-id "123e4567-e89b-12d3-a456-426614174000"

  # Test only events for last 3 days
  python test_ingestion.py \\
    --tenant-id "123e4567-e89b-12d3-a456-426614174000" \\
    --data-types events \\
    --days 3

  # Or explicitly provide connection string
  python test_ingestion.py \\
    --tenant-id "123e4567-e89b-12d3-a456-426614174000" \\
    --connection-string "DefaultEndpointsProtocol=https;AccountName=..."

Note:
  - Automatically reads AZURE_STORAGE_CONNECTION_STRING from .env file
  - Connection string is the same as AzureWebJobsStorage in Azure Functions
  - Get it from: Azure Portal → Storage Account → Access keys
        """,
    )

    parser.add_argument("--tenant-id", required=True, help="Tenant UUID to test with")

    parser.add_argument(
        "--connection-string",
        default=None,
        help="Azure Storage connection string (optional: reads from .env file or AZURE_STORAGE_CONNECTION_STRING env var)",
    )

    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to go back from today (default: 7)",
    )

    parser.add_argument(
        "--data-types",
        nargs="+",
        choices=["events", "users", "locations"],
        default=["events", "users", "locations"],
        help="Data types to ingest (default: all)",
    )

    parser.add_argument(
        "--job-id",
        default=None,
        help="Custom job ID (optional, will be generated if not provided)",
    )

    args = parser.parse_args()

    # Get connection string (automatically loads from .env file)
    connection_string = args.connection_string or os.environ.get(
        "AZURE_STORAGE_CONNECTION_STRING"
    )
    if not connection_string:
        print("❌ Error: Azure Storage connection string is required!")
        print("\n   Option 1 (Recommended): Add to .env file:")
        print(
            "      AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;..."
        )
        print("\n   Option 2: Pass via command line:")
        print('      --connection-string "DefaultEndpointsProtocol=https;..."')
        print(
            "\n   Get it from: Azure Portal → Storage Account → Access keys → Connection string"
        )
        return 1

    # Generate job ID if not provided
    import uuid

    job_id = args.job_id or f"job_{uuid.uuid4().hex[:12]}"

    # Calculate date range (last N days)
    today = date.today()
    start_date = today - timedelta(days=args.days)
    end_date = today

    print("=" * 80)
    print("Data Ingestion Queue Test".center(80))
    print("=" * 80)
    print(f"Tenant ID: {args.tenant_id}")
    print(f"Job ID: {job_id}")
    print(f"Date Range: {start_date} to {end_date} ({args.days} days)")
    print(f"Data Types: {', '.join(args.data_types)}")
    print("Queue: ingestion-jobs")
    print("=" * 80)

    # Initialize tester
    tester = IngestionQueueTester(connection_string, args.tenant_id)

    # Send message to queue (async operation)
    success = asyncio.run(
        tester.send_ingestion_message(
            job_id=job_id,
            start_date=start_date,
            end_date=end_date,
            data_types=args.data_types,
        )
    )

    if success:
        print("\n" + "=" * 80)
        print("✅ Message sent to queue successfully!")
        print("\n📝 Next Steps:")
        print("   1. Check Azure Functions logs:")
        print("      Azure Portal → Function App → Log stream")
        print("\n   2. Check job status in database:")
        print(f"      SELECT * FROM processing_jobs WHERE job_id = '{job_id}';")
        print("\n   3. Monitor queue:")
        print("      Azure Portal → Storage Account → Queues → ingestion-jobs")
        print("=" * 80)
        return 0
    print("\n❌ Failed to send message to queue")
    return 1


if __name__ == "__main__":
    sys.exit(main())
