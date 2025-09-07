#!/usr/bin/env python3
"""
Test script to send a single branch report via email
"""

import sys
import os
import glob
from send_branch_reports import BranchReportEmailer
import json

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_send_report.py <branch_code>")
        print("Example: python test_send_report.py D01")
        sys.exit(1)
    
    branch_code = sys.argv[1]
    
    # Load configurations
    smtp_config_path = "configs/smtp_config.json"
    branch_mapping_path = "configs/branch_email_mapping.json"
    
    if not os.path.exists(smtp_config_path):
        print(f"Error: SMTP config not found at {smtp_config_path}")
        print("Please copy configs/smtp_config.json.example and configure it")
        sys.exit(1)
    
    # Find the latest report for this branch
    report_pattern = f"branch_reports/{branch_code}_report_*.html"
    reports = glob.glob(report_pattern)
    
    if not reports:
        print(f"No reports found for branch {branch_code}")
        print("Available branches:")
        all_reports = glob.glob("branch_reports/D*_report_*.html")
        branches = set()
        for report in all_reports:
            branch = os.path.basename(report).split('_')[0]
            if branch != 'D':  # Skip D_All
                branches.add(branch)
        for branch in sorted(branches):
            print(f"  - {branch}")
        sys.exit(1)
    
    # Get the most recent report
    latest_report = max(reports)
    print(f"Found report: {latest_report}")
    
    # Load SMTP config
    with open(smtp_config_path, 'r') as f:
        smtp_config = json.load(f)
    
    # Create emailer
    emailer = BranchReportEmailer(smtp_config, branch_mapping_path)
    
    # Check if branch has email mapping
    if branch_code not in emailer.branch_mapping:
        print(f"No email mapping found for branch {branch_code}")
        print("Please add the branch to configs/branch_email_mapping.json")
        sys.exit(1)
    
    branch_info = emailer.branch_mapping[branch_code]
    print(f"Sending to: {branch_info['email']} ({branch_info.get('name', 'Unknown')})")
    if branch_info.get('cc'):
        print(f"CC: {branch_info['cc']}")
    
    # Send the email
    success = emailer.send_branch_report(branch_code, latest_report)
    
    if success:
        print("✓ Email sent successfully!")
    else:
        print("✗ Failed to send email")
        print("Check your SMTP configuration and credentials")


if __name__ == "__main__":
    main() 