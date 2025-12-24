#!/usr/bin/env python3
"""
Test script for data ingestion endpoint.

Tests the Azure Functions data ingestion API for a specific tenant
with a date range of the last 7 days.

Usage:
    python test_ingestion.py --tenant-id <tenant-uuid> [--base-url <url>]
    
Example:
    python test_ingestion.py --tenant-id "123e4567-e89b-12d3-a456-426614174000" --base-url "https://func-data-ingestion-prod.azurewebsites.net"
"""

import argparse
import json
import time
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
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of an ingestion job.
        
        Args:
            job_id: Job ID to check
            
        Returns:
            Job status dictionary or None if failed
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/jobs/{job_id}",
                headers=self.headers,
                timeout=60  # Increased for Azure Functions cold start
            )
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(f"✗ Job {job_id} not found")
            else:
                print(f"✗ Failed to get job status: {e}")
            return None
            
        except requests.exceptions.Timeout as e:
            # Return special marker for timeout (can be retried)
            return {"_error": "timeout", "_message": str(e)}
            
        except requests.exceptions.ConnectionError as e:
            # Return special marker for connection error (can be retried)
            return {"_error": "connection", "_message": str(e)}
            
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
            return None
    
    def poll_job_status(
        self,
        job_id: str,
        max_wait_time: int = 1800,
        poll_interval: int = 5
    ) -> Optional[Dict[str, Any]]:
        """
        Poll job status until completion or timeout.
        
        Args:
            job_id: Job ID to poll
            max_wait_time: Maximum time to wait in seconds (default: 30 minutes)
            poll_interval: Seconds between polls (default: 5 seconds)
            
        Returns:
            Final job status dictionary or None if failed
        """
        print(f"\n⏳ Polling job status (max wait: {max_wait_time}s, interval: {poll_interval}s)...")
        
        start_time = time.time()
        last_status = None
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while True:
            elapsed = time.time() - start_time
            
            if elapsed > max_wait_time:
                print(f"\n⏱️  Timeout reached ({max_wait_time}s)")
                return last_status
            
            status = self.get_job_status(job_id)
            
            # Handle transient errors (timeouts, connection issues)
            if status and status.get("_error"):
                consecutive_errors += 1
                error_type = status.get("_error")
                print(f"   [{elapsed:.0f}s] ⚠️  {error_type} error (retry {consecutive_errors}/{max_consecutive_errors})")
                
                if consecutive_errors >= max_consecutive_errors:
                    print(f"\n✗ Too many consecutive errors, giving up")
                    return None
                    
                time.sleep(poll_interval)
                continue
            
            if not status:
                return None
            
            # Reset error counter on successful request
            consecutive_errors = 0
            
            current_status = status.get('status', 'unknown')
            progress = status.get('progress', {})
            records = status.get('records_processed', {})
            error = status.get('error_message')
            
            # Print status update if changed
            if current_status != last_status:
                print(f"\n   [{elapsed:.0f}s] Status: {current_status}")
                if progress:
                    print(f"      Progress: {json.dumps(progress)}")
                if records:
                    print(f"      Records: {json.dumps(records)}")
                if error:
                    print(f"      Error: {error}")
            
            last_status = current_status
            
            # Check if job is complete
            if current_status in ['completed', 'failed']:
                print(f"\n✓ Job finished with status: {current_status}")
                if current_status == 'completed':
                    print(f"   Completed at: {status.get('completed_at', 'N/A')}")
                    if records:
                        print(f"   Records processed:")
                        for event_type, count in records.items():
                            print(f"      - {event_type}: {count}")
                else:
                    print(f"   Error: {error or 'Unknown error'}")
                
                return status
            
            # Wait before next poll
            time.sleep(poll_interval)
    
    def get_data_availability(self) -> Optional[Dict[str, Any]]:
        """Get data availability summary for the tenant."""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/data-availability",
                headers=self.headers,
                timeout=60  # Increased for Azure Functions cold start
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"✗ Failed to get data availability: {e}")
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
  
  # Test with Azure Functions URL
  python test_ingestion.py \\
    --tenant-id "123e4567-e89b-12d3-a456-426614174000" \\
    --base-url "https://func-data-ingestion-prod.azurewebsites.net"
  
  # Test only events (skip users/locations)
  python test_ingestion.py \\
    --tenant-id "123e4567-e89b-12d3-a456-426614174000" \\
    --data-types events
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
    
    parser.add_argument(
        "--no-poll",
        action="store_true",
        help="Don't poll for job completion (just start the job)"
    )
    
    parser.add_argument(
        "--max-wait",
        type=int,
        default=1800,
        help="Maximum time to wait for job completion in seconds (default: 1800 = 30 minutes)"
    )
    
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=5,
        help="Seconds between status polls (default: 5)"
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
    
    # Check data availability before
    print("\n📊 Checking current data availability...")
    availability = tester.get_data_availability()
    if availability:
        summary = availability.get('summary', {})
        print(f"   Earliest date: {summary.get('earliest_date', 'N/A')}")
        print(f"   Latest date: {summary.get('latest_date', 'N/A')}")
        print(f"   Total events: {summary.get('total_events', 0):,}")
    
    # Start ingestion job
    job_result = tester.start_ingestion_job(
        start_date=start_date,
        end_date=end_date,
        data_types=args.data_types
    )
    
    if not job_result:
        print("\n❌ Failed to start ingestion job")
        return 1
    
    job_id = job_result.get('job_id')
    
    if args.no_poll:
        print(f"\n✓ Job started. Use the following to check status:")
        print(f"   curl -H 'X-Tenant-Id: {args.tenant_id}' {args.base_url}/api/v1/jobs/{job_id}")
        return 0
    
    # Poll for completion
    final_status = tester.poll_job_status(
        job_id=job_id,
        max_wait_time=args.max_wait,
        poll_interval=args.poll_interval
    )
    
    if not final_status:
        print("\n❌ Failed to get final job status")
        return 1
    
    # Check data availability after
    print("\n📊 Checking data availability after ingestion...")
    availability_after = tester.get_data_availability()
    if availability_after:
        summary_after = availability_after.get('summary', {})
        print(f"   Earliest date: {summary_after.get('earliest_date', 'N/A')}")
        print(f"   Latest date: {summary_after.get('latest_date', 'N/A')}")
        print(f"   Total events: {summary_after.get('total_events', 0):,}")
    
    # Summary
    print("\n" + "=" * 70)
    if final_status.get('status') == 'completed':
        print("✅ Test completed successfully!")
    else:
        print("❌ Test completed with errors")
    print("=" * 70)
    
    return 0 if final_status.get('status') == 'completed' else 1


if __name__ == "__main__":
    exit(main())

