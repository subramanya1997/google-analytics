#!/usr/bin/env python3
"""
Send branch-wise reports to sales representatives via email
"""

import os
import json
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
import glob
from typing import Dict, List, Optional
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BranchReportEmailer:
    def __init__(self, smtp_config: Dict[str, str], branch_mapping_file: str):
        """Initialize email sender with SMTP configuration"""
        self.smtp_config = smtp_config
        self.branch_mapping = self.load_branch_mapping(branch_mapping_file)
        
    def load_branch_mapping(self, mapping_file: str) -> Dict[str, Dict[str, str]]:
        """Load branch to sales rep email mapping"""
        try:
            with open(mapping_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load branch mapping: {e}")
            return {}
    
    def connect_smtp(self) -> smtplib.SMTP:
        """Establish SMTP connection"""
        smtp = None
        try:
            # Create SMTP connection
            if self.smtp_config.get('use_tls', True):
                smtp = smtplib.SMTP(self.smtp_config['server'], self.smtp_config['port'])
                smtp.starttls()
            else:
                smtp = smtplib.SMTP_SSL(self.smtp_config['server'], self.smtp_config['port'])
            
            # Login if credentials provided
            if self.smtp_config.get('username') and self.smtp_config.get('password'):
                smtp.login(self.smtp_config['username'], self.smtp_config['password'])
            
            logger.info(f"Connected to SMTP server: {self.smtp_config['server']}")
            return smtp
            
        except Exception as e:
            logger.error(f"Failed to connect to SMTP server: {e}")
            if smtp:
                smtp.quit()
            raise
    
    def create_email_message(self, branch_code: str, report_path: str, 
                           recipient_info: Dict[str, str]) -> MIMEMultipart:
        """Create email message with HTML report as body"""
        msg = MIMEMultipart('related')
        
        # Email headers
        msg['From'] = self.smtp_config.get('from_address', 'noreply@company.com')
        msg['To'] = recipient_info['email']
        msg['Subject'] = f"Daily Sales Report - {recipient_info.get('branch_name', f'Branch {branch_code}')} - {datetime.now().strftime('%Y-%m-%d')}"
        
        # Add CC if specified
        if recipient_info.get('cc'):
            msg['Cc'] = recipient_info['cc']
        
        # Read the HTML report content
        if os.path.exists(report_path):
            with open(report_path, 'r', encoding='utf-8') as f:
                report_html = f.read()
            
            # The HTML report from generate_branch_wise_report.py already has all styling inline
            # Just send it as the email body
            msg.attach(MIMEText(report_html, 'html'))
        else:
            # Fallback if report doesn't exist
            fallback_html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; font-size: 14px; padding: 20px;">
                <h2>Report Not Found</h2>
                <p>The sales report for branch {branch_code} could not be found.</p>
                <p>Please contact the system administrator.</p>
            </body>
            </html>
            """
            msg.attach(MIMEText(fallback_html, 'html'))
        
        return msg
    
    def send_branch_report(self, branch_code: str, report_path: str, 
                          smtp_connection: Optional[smtplib.SMTP] = None) -> bool:
        """Send report for a specific branch"""
        # Check if branch has email mapping
        if branch_code not in self.branch_mapping:
            logger.warning(f"No email mapping found for branch {branch_code}")
            return False
        
        recipient_info = self.branch_mapping[branch_code]
        
        # Skip if email is not configured
        if not recipient_info.get('email'):
            logger.warning(f"No email address configured for branch {branch_code}")
            return False
        
        # Skip if explicitly disabled
        if not recipient_info.get('enabled', True):
            logger.info(f"Email sending disabled for branch {branch_code}")
            return False
        
        try:
            # Create email message
            msg = self.create_email_message(branch_code, report_path, recipient_info)
            
            # Send email
            if smtp_connection:
                smtp = smtp_connection
            else:
                smtp = self.connect_smtp()
            
            recipients = [recipient_info['email']]
            if recipient_info.get('cc'):
                recipients.extend(recipient_info['cc'].split(','))
            
            smtp.send_message(msg)
            logger.info(f"Successfully sent report for branch {branch_code} to {recipient_info['email']}")
            
            # Close connection if we created it
            if not smtp_connection:
                smtp.quit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email for branch {branch_code}: {e}")
            return False
    
    def send_all_branch_reports(self, report_dir: str, date_suffix: Optional[str] = None) -> Dict[str, bool]:
        """Send all branch reports found in the report directory"""
        results = {}
        
        # Determine report pattern
        if date_suffix:
            pattern = f"{report_dir}/D*_report_{date_suffix}.html"
        else:
            # Find the most recent reports
            all_reports = glob.glob(f"{report_dir}/D*_report_*.html")
            if not all_reports:
                logger.warning("No branch reports found")
                return results
            
            # Get the most recent date suffix
            dates = set()
            for report in all_reports:
                parts = os.path.basename(report).split('_')
                if len(parts) >= 3:
                    dates.add(parts[2].replace('.html', ''))
            
            if dates:
                date_suffix = max(dates)
                pattern = f"{report_dir}/D*_report_{date_suffix}.html"
            else:
                logger.error("Could not determine report date suffix")
                return results
        
        # Find all branch reports
        branch_reports = glob.glob(pattern)
        
        if not branch_reports:
            logger.warning(f"No reports found matching pattern: {pattern}")
            return results
        
        logger.info(f"Found {len(branch_reports)} branch reports to send")
        
        # Connect to SMTP once for all emails
        smtp = None
        try:
            smtp = self.connect_smtp()
            
            for report_path in branch_reports:
                # Extract branch code from filename (e.g., D01_report_20250629.html -> D01)
                filename = os.path.basename(report_path)
                branch_code = filename.split('_')[0]
                
                # Skip the combined "D_All" report
                if branch_code == 'D':
                    continue
                
                results[branch_code] = self.send_branch_report(branch_code, report_path, smtp)
            
        finally:
            if smtp:
                smtp.quit()
        
        # Summary
        successful = sum(1 for success in results.values() if success)
        logger.info(f"Email sending complete: {successful}/{len(results)} sent successfully")
        
        return results


def main():
    parser = argparse.ArgumentParser(description="Send branch reports via email")
    parser.add_argument("--smtp-config", default="configs/smtp_config.json", 
                       help="SMTP configuration file")
    parser.add_argument("--branch-mapping", default="configs/branch_email_mapping.json",
                       help="Branch to email mapping file")
    parser.add_argument("--report-dir", default="branch_reports",
                       help="Directory containing branch reports")
    parser.add_argument("--date-suffix", help="Specific date suffix (e.g., 20250629)")
    parser.add_argument("--branch", help="Send report for specific branch only")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be sent without sending")
    
    args = parser.parse_args()
    
    # Load SMTP configuration
    try:
        with open(args.smtp_config, 'r') as f:
            smtp_config = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load SMTP configuration: {e}")
        return 1
    
    # Initialize emailer
    emailer = BranchReportEmailer(smtp_config, args.branch_mapping)
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No emails will be sent")
        # Just show what would be sent
        if args.branch:
            if args.branch in emailer.branch_mapping:
                info = emailer.branch_mapping[args.branch]
                logger.info(f"Would send report for branch {args.branch} to {info.get('email')}")
            else:
                logger.warning(f"No mapping found for branch {args.branch}")
        else:
            for branch, info in emailer.branch_mapping.items():
                if info.get('enabled', True) and info.get('email'):
                    logger.info(f"Would send report for branch {branch} to {info.get('email')}")
        return 0
    
    # Send reports
    if args.branch:
        # Send single branch report
        pattern = f"{args.report_dir}/{args.branch}_report_*.html"
        reports = glob.glob(pattern)
        if reports:
            report_path = max(reports)  # Get most recent
            success = emailer.send_branch_report(args.branch, report_path)
            return 0 if success else 1
        else:
            logger.error(f"No report found for branch {args.branch}")
            return 1
    else:
        # Send all branch reports
        results = emailer.send_all_branch_reports(args.report_dir, args.date_suffix)
        return 0 if any(results.values()) else 1


if __name__ == "__main__":
    import sys
    sys.exit(main()) 