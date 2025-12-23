"""
Email service for Azure Functions.

Adapted from the FastAPI analytics_service for use in serverless Azure Functions.
Handles sending branch reports via SMTP.
"""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from loguru import logger

from shared.database import create_repository


class EmailService:
    """
    Service for handling email operations.
    
    Each tenant has their own isolated database for SOC2 compliance.
    """

    def __init__(self, tenant_id: str):
        """
        Initialize email service for a specific tenant.
        
        Args:
            tenant_id: The tenant ID - determines which database to connect to.
        """
        self.tenant_id = tenant_id
        self.repo = create_repository(tenant_id)

    async def create_and_process_email_job(
        self,
        tenant_id: str,
        report_date,
        branch_codes: Optional[List[str]] = None
    ) -> str:
        """
        Create an email job and process it.
        
        Args:
            tenant_id: Tenant ID
            report_date: Date for report generation
            branch_codes: Optional list of branch codes (None = all branches)
            
        Returns:
            Job ID for tracking
        """
        job_id = f"email_{uuid4().hex[:12]}"
        
        # Create job record in database
        job_data = {
            "job_id": job_id,
            "tenant_id": tenant_id,
            "status": "queued",
            "report_date": report_date,
            "target_branches": branch_codes or [],
        }
        
        await self.repo.create_email_job(job_data)
        
        return job_id

    async def process_email_job(
        self,
        tenant_id: str,
        job_id: str,
        report_date,
        branch_codes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Process email sending job.
        
        Args:
            tenant_id: Tenant ID
            job_id: Job ID
            report_date: Date for report generation
            branch_codes: Optional list of branch codes
            
        Returns:
            Job result summary
        """
        try:
            logger.info(f"Starting email job {job_id} for tenant {tenant_id}")
            
            # Update job status to processing
            await self.repo.update_email_job_status(
                job_id,
                "processing",
                {"started_at": datetime.now()}
            )

            # Get email configuration
            email_config = await self.repo.get_email_config(tenant_id)
            
            if not email_config:
                raise Exception("Email configuration not found for tenant")

            # Get ALL branch email mappings
            all_mappings = await self.repo.get_branch_email_mappings(tenant_id, None)
            
            if not all_mappings:
                raise Exception("No branch email mappings configured")
            
            # Filter mappings by requested branches if specified
            if branch_codes:
                filtered_mappings = [
                    m for m in all_mappings 
                    if m["branch_code"] in branch_codes
                ]
            else:
                filtered_mappings = all_mappings
            
            if not filtered_mappings:
                raise Exception("No branches found to send reports to")

            # Send individual branch reports
            total_emails = 0
            emails_sent = 0
            emails_failed = 0
            
            # Group mappings by branch
            from collections import defaultdict
            mappings_by_branch = defaultdict(list)
            for mapping in filtered_mappings:
                mappings_by_branch[mapping["branch_code"]].append(mapping)
            
            logger.info(f"Generating individual branch reports for {len(mappings_by_branch)} branches")
            
            # Send individual reports for each branch
            for branch_code, branch_mappings in mappings_by_branch.items():
                for mapping in branch_mappings:
                    if mapping.get("is_enabled", True):
                        total_emails += 1
                        
                        try:
                            # Generate simple branch report
                            branch_report_html = await self._generate_simple_branch_report(
                                tenant_id, branch_code, report_date
                            )
                            
                            await self._send_branch_email(
                                email_config,
                                mapping,
                                branch_report_html,
                                report_date,
                                branch_code,
                                job_id,
                                tenant_id
                            )
                            emails_sent += 1
                            logger.info(f"Sent branch report to {mapping['sales_rep_email']} for branch: {branch_code}")
                            
                        except Exception as email_error:
                            emails_failed += 1
                            logger.error(f"Failed to send branch email to {mapping['sales_rep_email']} for branch {branch_code}: {email_error}")
                            
                            # Log failed email
                            error_subject = f"Daily Branch Sales Report - {report_date.strftime('%Y-%m-%d')} - {branch_code}"
                            
                            await self.repo.log_email_send_history({
                                "tenant_id": tenant_id,
                                "job_id": job_id,
                                "branch_code": branch_code,
                                "sales_rep_email": mapping["sales_rep_email"],
                                "sales_rep_name": mapping.get("sales_rep_name"),
                                "subject": error_subject,
                                "report_date": report_date,
                                "status": "failed",
                                "error_message": str(email_error)
                            })

            # Update job completion status
            if emails_failed > 0 and emails_sent > 0:
                final_status = "completed_with_errors"
            elif emails_failed > 0 and emails_sent == 0:
                final_status = "failed"
            else:
                final_status = "completed"
            
            completion_data = {
                "completed_at": datetime.now(),
                "total_emails": total_emails,
                "emails_sent": emails_sent,
                "emails_failed": emails_failed
            }
            
            await self.repo.update_email_job_status(
                job_id,
                final_status,
                completion_data
            )
            
            logger.info(f"Email job {job_id} finished with status '{final_status}': {emails_sent}/{total_emails} sent successfully")
            
            return {
                "job_id": job_id,
                "status": final_status,
                "total_emails": total_emails,
                "emails_sent": emails_sent,
                "emails_failed": emails_failed
            }

        except Exception as e:
            logger.error(f"Email job {job_id} failed: {e}")
            
            # Update job failure status
            await self.repo.update_email_job_status(
                job_id,
                "failed", 
                {
                    "completed_at": datetime.now(),
                    "error_message": str(e)
                }
            )
            raise

    async def _generate_simple_branch_report(
        self, tenant_id: str, branch_code: str, report_date
    ) -> str:
        """
        Generate a simple HTML report for a branch.
        
        For full report generation, integrate with the analytics service's
        report_service and template_service.
        """
        date_str = report_date.strftime('%B %d, %Y')
        
        # Get location info
        location_info = await self.repo.get_location_by_code(tenant_id, branch_code)
        location_name = location_info.get("warehouse_name", branch_code) if location_info else branch_code
        city = location_info.get("city", "") if location_info else ""
        state = location_info.get("state", "") if location_info else ""
        
        location_display = f"{location_name}"
        if city or state:
            location_display += f" - {city}, {state}"
        
        # Generate simple report HTML
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sales Report - {location_display}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f8f9fa; }}
        .container {{ max-width: 900px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ border-bottom: 2px solid #dee2e6; padding-bottom: 15px; margin-bottom: 25px; }}
        .header h1 {{ margin: 0; color: #333; }}
        .header p {{ margin: 5px 0 0 0; color: #666; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; color: #666; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{location_display}</h1>
            <p>Daily Sales Report - {date_str}</p>
        </div>
        
        <div class="content">
            <p>This is your daily sales report for <strong>{branch_code}</strong>.</p>
            <p>Please log in to the Sales Intelligence dashboard for detailed analytics and actionable tasks.</p>
        </div>
        
        <div class="footer">
            <p>Report generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>This is an automated report from the Sales Intelligence System</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    async def _send_branch_email(
        self,
        email_config: Dict[str, Any],
        mapping: Dict[str, Any],
        branch_report_html: str,
        report_date,
        branch_code: str,
        job_id: str,
        tenant_id: str
    ) -> None:
        """
        Send individual branch email.
        
        Args:
            email_config: SMTP configuration
            mapping: Email recipient mapping
            branch_report_html: Generated branch HTML report
            report_date: Date of the report
            branch_code: Branch code for the report
            job_id: Job ID for tracking
            tenant_id: Tenant ID
        """
        # Create email message
        msg = MIMEMultipart('related')
        
        # Email headers for individual branch report
        subject = f"Daily Branch Sales Report - {report_date.strftime('%Y-%m-%d')} - {branch_code}"
        
        msg['From'] = email_config.get('from_address')
        msg['To'] = mapping['sales_rep_email']
        msg['Subject'] = subject
        
        # Attach HTML content
        msg.attach(MIMEText(branch_report_html, 'html'))
        
        # Send via SMTP
        smtp_server = None
        try:
            # Get port as integer
            port = email_config.get('port', 587)
            if isinstance(port, str):
                port = int(port)
            
            # Create SMTP connection
            if email_config.get('use_ssl', False):
                smtp_server = smtplib.SMTP_SSL(
                    email_config['server'], 
                    port if port in [465, 995] else 465
                )
            else:
                smtp_server = smtplib.SMTP(
                    email_config['server'],
                    port
                )
                
                if email_config.get('use_tls', True):
                    smtp_server.starttls()
            
            # Login if credentials provided
            if email_config.get('username') and email_config.get('password'):
                smtp_server.login(
                    email_config['username'],
                    email_config['password']
                )
            
            # Send email
            smtp_response = smtp_server.send_message(msg)
            
            # Log successful send
            await self.repo.log_email_send_history({
                "tenant_id": tenant_id,
                "job_id": job_id,
                "branch_code": branch_code,
                "sales_rep_email": mapping["sales_rep_email"],
                "sales_rep_name": mapping.get("sales_rep_name"),
                "subject": subject,
                "report_date": report_date,
                "status": "sent",
                "smtp_response": str(smtp_response) if smtp_response else "OK",
                "error_message": None
            })
            
        finally:
            if smtp_server:
                try:
                    smtp_server.quit()
                except:
                    pass

