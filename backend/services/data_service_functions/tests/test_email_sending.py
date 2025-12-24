"""
Test script for Azure Functions Email Service

This script tests the email sending functionality including:
- Health check
- Email report sending (synchronous)

Note: Email mappings are managed directly in the database.

Usage:
    python test_email_sending.py --tenant-id YOUR_TENANT_ID --report-date 2025-12-23 --branch-codes D01,D02
    
    # Or for all branches:
    python test_email_sending.py --tenant-id YOUR_TENANT_ID --report-date 2025-12-23
"""

import argparse
import json
import sys
import time
from datetime import datetime, date, timedelta
from typing import List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# Configuration
BASE_URL = "https://gadataingestion.azurewebsites.net/api/v1"
# For local testing: BASE_URL = "http://localhost:7071/api/v1"

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def create_session_with_retries() -> requests.Session:
    """Create a requests session with retry logic."""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}\n")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


def test_health_check(session: requests.Session, base_url: str) -> bool:
    """Test the health check endpoint."""
    print_header("Testing Health Check")
    
    try:
        response = session.get(
            f"{base_url}/health",
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"Health check passed")
            print_info(f"Status: {data.get('status')}")
            print_info(f"Version: {data.get('version')}")
            print_info(f"Timestamp: {data.get('timestamp')}")
            return True
        else:
            print_error(f"Health check failed: {response.status_code}")
            print_error(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Health check error: {e}")
        return False


def send_email_reports(
    session: requests.Session,
    base_url: str,
    tenant_id: str,
    report_date: date,
    branch_codes: Optional[List[str]] = None
) -> Optional[dict]:
    """Send email reports."""
    print_header("Sending Email Reports")
    
    branch_info = f"branches: {', '.join(branch_codes)}" if branch_codes else "all branches"
    print_info(f"Sending reports for {report_date.strftime('%Y-%m-%d')} to {branch_info}")
    print_warning("This may take several minutes depending on the number of branches...")
    
    try:
        payload = {
            "report_date": report_date.strftime("%Y-%m-%d"),
        }
        
        if branch_codes:
            payload["branch_codes"] = branch_codes
        
        start_time = time.time()
        
        response = session.post(
            f"{base_url}/email/send-reports",
            headers={
                "X-Tenant-Id": tenant_id,
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=600  # 10 minutes for synchronous processing
        )
        
        elapsed_time = time.time() - start_time
        
        if response.status_code in [200, 202]:
            data = response.json()
            job_id = data.get("job_id")
            status = data.get("status")
            
            print_success(f"Email job completed in {elapsed_time:.1f}s")
            print_info(f"Job ID: {job_id}")
            print_info(f"Status: {status}")
            print_info(f"Report Date: {data.get('report_date')}")
            
            # Show results
            total_emails = data.get("total_emails", 0)
            emails_sent = data.get("emails_sent", 0)
            emails_failed = data.get("emails_failed", 0)
            
            print(f"\n{Colors.BOLD}Results:{Colors.ENDC}")
            print(f"  Total Emails: {total_emails}")
            print(f"  {Colors.OKGREEN}✓ Sent: {emails_sent}{Colors.ENDC}")
            if emails_failed > 0:
                print(f"  {Colors.FAIL}✗ Failed: {emails_failed}{Colors.ENDC}")
            
            return data
        else:
            print_error(f"Failed to send emails: {response.status_code}")
            print_error(f"Response: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print_error("Request timed out after 10 minutes")
        print_info("The job may still be processing. Check job status separately.")
        return None
    except Exception as e:
        print_error(f"Error sending emails: {e}")
        return None


def main():
    """Main test function."""
    parser = argparse.ArgumentParser(description="Test Azure Functions Email Service")
    parser.add_argument(
        "--tenant-id",
        required=True,
        help="Tenant ID (UUID)"
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
        "--skip-health-check",
        action="store_true",
        help="Skip health check"
    )
    parser.add_argument(
        "--base-url",
        default=BASE_URL,
        help=f"Base URL for API (default: {BASE_URL})"
    )
    
    args = parser.parse_args()
    
    # Use the provided base URL
    base_url = args.base_url
    
    # Parse report date
    if args.report_date:
        try:
            report_date = datetime.strptime(args.report_date, "%Y-%m-%d").date()
        except ValueError:
            print_error(f"Invalid date format: {args.report_date}. Use YYYY-MM-DD")
            sys.exit(1)
    else:
        # Default to yesterday
        report_date = date.today() - timedelta(days=1)
    
    # Parse branch codes
    branch_codes = None
    if args.branch_codes:
        branch_codes = [code.strip() for code in args.branch_codes.split(",")]
    
    # Create session
    session = create_session_with_retries()
    
    print(f"\n{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"{Colors.BOLD}Azure Functions Email Service Test{Colors.ENDC}".center(80))
    print(f"{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"\n{Colors.BOLD}Configuration:{Colors.ENDC}")
    print(f"  Base URL: {base_url}")
    print(f"  Tenant ID: {args.tenant_id}")
    print(f"  Report Date: {report_date.strftime('%Y-%m-%d')}")
    if branch_codes:
        print(f"  Target Branches: {', '.join(branch_codes)}")
    else:
        print(f"  Target Branches: All configured branches")
    
    print(f"\n{Colors.BOLD}Note:{Colors.ENDC} Email mappings must be configured in the database.")
    print(f"  Table: branch_email_mappings")
    print(f"  Required: branch_code, sales_rep_email, is_enabled=true")
    
    # Run tests
    success = True
    
    # 1. Health check
    if not args.skip_health_check:
        if not test_health_check(session, base_url):
            print_warning("Health check failed, but continuing...")
    
    # 2. Send email reports (synchronous - returns when complete)
    result = send_email_reports(session, base_url, args.tenant_id, report_date, branch_codes)
    
    if not result:
        success = False
    
    # Final summary
    print_header("Test Summary")
    if success:
        print_success("All tests completed successfully!")
    else:
        print_error("Some tests failed. Check the output above for details.")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

