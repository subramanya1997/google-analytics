#!/usr/bin/env python3
"""
Test script for data ingestion endpoint.

Tests the Azure Functions data ingestion API (synchronous processing).
The ingestion endpoint runs synchronously and returns when complete.

Usage:
    python test_ingestion.py --tenant-id <tenant-uuid> [--base-url <url>]
    
Example:
    python test_ingestion.py --tenant-id "123e4567-e89b-12d3-a456-426614174000" \
      --base-url "https://gadataingestion.azurewebsites.net"
"""

import argparse
from datetime import date, timedelta
from typing import Optional, Dict, Any

import requests


class IngestionTester:
    """Test client for data ingestion API."""
    
    def __init__(self, base_url: str, tenant_id: str):
        """
        Initialize test client.
        
        Args:
            base_url: Base URL of the Azure Functions app (without trailing slash)
            tenant_id: Tenant UUID to test with
        """
        self.base_url = base_url.rstrip('/')
        self.tenant_id = tenant_id
        self.headers = {
            "X-Tenant-Id": tenant_id,
            "Content-Type": "application/json"
        }
    
    def health_check(self) -> bool:
        """Check if the service is healthy."""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/health",
                timeout=30  # Increased for Azure Functions cold start
            )
            response.raise_for_status()
            data = response.json()
            print(f"✓ Health check passed: {data.get('status', 'unknown')}")
            return True
        except Exception as e:
            print(f"✗ Health check failed: {e}")
            return False
    
    def start_ingestion_job(
        self,
        start_date: date,
        end_date: date,
        data_types: list = None
    ) -> Optional[Dict[str, Any]]:
        """
        Start a data ingestion job.
        
        Args:
            start_date: Start date for ingestion (inclusive)
            end_date: End date for ingestion (inclusive)
            data_types: List of data types to ingest. Default: ["events", "users", "locations"]
            
        Returns:
            Job response dictionary or None if failed
        """
        if data_types is None:
            data_types = ["events", "users", "locations"]
        
        payload = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "data_types": data_types
        }
        
        print(f"\n📤 Starting ingestion job...")
        print(f"   Tenant ID: {self.tenant_id}")
        print(f"   Date range: {start_date} to {end_date}")
        print(f"   Data types: {', '.join(data_types)}")
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/ingest",
                headers=self.headers,
                json=payload,
                timeout=600  # 10 minutes - job now runs synchronously
            )
            response.raise_for_status()
            result = response.json()
            
            print(f"✓ Job created successfully!")
            print(f"   Job ID: {result.get('job_id')}")
            print(f"   Status: {result.get('status')}")
            print(f"   Message: {result.get('message', 'N/A')}")
            
            return result
            
        except requests.exceptions.HTTPError as e:
            error_msg = "Unknown error"
            try:
                error_data = e.response.json()
                error_msg = error_data.get('error', str(e))
            except:
                error_msg = str(e)
            
            print(f"✗ Failed to create job: {error_msg}")
            print(f"   Status code: {e.response.status_code}")
            return None
            
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
            return None
    


def main():
    """Main test function."""
    parser = argparse.ArgumentParser(
        description="Test data ingestion API for a tenant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with default localhost URL
  python test_ingestion.py --tenant-id "123e4567-e89b-12d3-a456-426614174000"
  
  # Test with production Azure Functions URL
  python test_ingestion.py \\
    --tenant-id "123e4567-e89b-12d3-a456-426614174000" \\
    --base-url "https://gadataingestion.azurewebsites.net"
  
  # Test only events (skip users/locations)
  python test_ingestion.py \\
    --tenant-id "123e4567-e89b-12d3-a456-426614174000" \\
    --data-types events \\
    --days 3
        """
    )
    
    parser.add_argument(
        "--tenant-id",
        required=True,
        help="Tenant UUID to test with"
    )
    
    parser.add_argument(
        "--base-url",
        default="http://localhost:7071",
        help="Base URL of Azure Functions app (default: http://localhost:7071)"
    )
    
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to go back from today (default: 7)"
    )
    
    parser.add_argument(
        "--data-types",
        nargs="+",
        choices=["events", "users", "locations"],
        default=["events", "users", "locations"],
        help="Data types to ingest (default: all)"
    )
    
    args = parser.parse_args()
    
    # Calculate date range (last N days)
    today = date.today()
    start_date = today - timedelta(days=args.days)
    end_date = today
    
    print("=" * 70)
    print("Data Ingestion API Test")
    print("=" * 70)
    print(f"Base URL: {args.base_url}")
    print(f"Tenant ID: {args.tenant_id}")
    print(f"Date Range: {start_date} to {end_date} ({args.days} days)")
    print(f"Data Types: {', '.join(args.data_types)}")
    print("=" * 70)
    
    # Initialize tester
    tester = IngestionTester(args.base_url, args.tenant_id)
    
    # Health check
    if not tester.health_check():
        print("\n⚠️  Health check failed. Continuing anyway...")
    
    # Start ingestion job (runs synchronously - returns when complete)
    print("\n⚠️  Note: Ingestion runs synchronously. This may take several minutes...")
    print(f"   Expected time: 30 seconds to 10 minutes depending on data volume")
    
    job_result = tester.start_ingestion_job(
        start_date=start_date,
        end_date=end_date,
        data_types=args.data_types
    )
    
    if not job_result:
        print("\n❌ Ingestion job failed")
        return 1
    
    # Display results
    job_status = job_result.get('status')
    records = job_result.get('records_processed', {})
    error_msg = job_result.get('error_message')
    
    print("\n" + "=" * 70)
    print(f"Job Status: {job_status}")
    
    if records:
        print(f"\nRecords Processed:")
        for data_type, count in records.items():
            print(f"  - {data_type}: {count:,}")
    
    if error_msg:
        print(f"\nError: {error_msg}")
    
    print("=" * 70)
    
    if job_status in ['completed', 'completed_with_warnings']:
        print("\n✅ Test completed successfully!")
        if job_status == 'completed_with_warnings':
            print("⚠️  Some records failed to process. Check error_message for details.")
        return 0
    else:
        print("\n❌ Test completed with errors")
        return 1


if __name__ == "__main__":
    exit(main())

