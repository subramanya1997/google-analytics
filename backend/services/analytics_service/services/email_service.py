"""
Email service for sending branch reports
"""

import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List
from uuid import uuid4
from datetime import datetime

from fastapi import BackgroundTasks
from loguru import logger

from services.analytics_service.api.v1.models import SendReportsRequest
from services.analytics_service.database.postgres_client import AnalyticsPostgresClient
from services.analytics_service.services.report_service import ReportService
from services.analytics_service.utils import run_sync_in_executor


class EmailService:
    """Service for handling email operations."""

    def __init__(self, db_client: AnalyticsPostgresClient):
        """Initialize email service."""
        self.db_client = db_client
        self.report_service = ReportService(db_client)

    async def create_send_reports_job(
        self, 
        tenant_id: str, 
        request: SendReportsRequest,
        background_tasks: BackgroundTasks
    ) -> str:
        """
        Create a background job to send reports via email.
        
        Args:
            tenant_id: Tenant ID
            request: Send reports request
            background_tasks: FastAPI background tasks
            
        Returns:
            Job ID for tracking
        """
        job_id = f"email_{uuid4().hex[:12]}"
        
        # Create job record in database
        job_data = {
            "job_id": job_id,
            "tenant_id": tenant_id,
            "status": "queued",
            "report_date": request.report_date,
            "target_branches": request.branch_codes or [],
        }
        
        await run_sync_in_executor(self.db_client.create_email_job, job_data)
        
        # Schedule background task
        background_tasks.add_task(
            self._process_email_job,
            tenant_id,
            job_id,
            request
        )
        
        return job_id

    async def _process_email_job(
        self, 
        tenant_id: str, 
        job_id: str,
        request: SendReportsRequest
    ) -> None:
        """
        Process email sending job in background.
        
        Args:
            tenant_id: Tenant ID
            job_id: Job ID
            request: Send reports request
        """
        try:
            logger.info(f"Starting email job {job_id} for tenant {tenant_id}")
            
            # Update job status to processing
            await asyncio.get_event_loop().run_in_executor(
                None, 
                self.db_client.update_email_job_status,
                job_id,
                "processing",
                {"started_at": datetime.now()}
            )

            # Get email configuration
            email_config = await asyncio.get_event_loop().run_in_executor(
                None, self.db_client.get_email_config, tenant_id
            )
            
            if not email_config:
                raise Exception("Email configuration not found for tenant")

            # Get branch email mappings
            if request.branch_codes:
                # Send to specific branches
                target_branches = request.branch_codes
            else:
                # Send to all branches with mappings
                all_mappings = await asyncio.get_event_loop().run_in_executor(
                    None, self.db_client.get_branch_email_mappings, tenant_id, None
                )
                target_branches = list(set(mapping["branch_code"] for mapping in all_mappings))

            if not target_branches:
                raise Exception("No branches found to send reports to")

            # Send personalized combined reports
            total_emails = 0
            emails_sent = 0
            emails_failed = 0
            
            logger.info(f"Generating personalized combined reports for branches: {target_branches}")
            
            try:
                # Group branches by recipient email
                recipient_branches = {}
                for branch_code in target_branches:
                    branch_mappings = await asyncio.get_event_loop().run_in_executor(
                        None, self.db_client.get_branch_email_mappings, tenant_id, branch_code
                    )
                    
                    for mapping in branch_mappings:
                        if mapping.get("is_enabled", True):
                            recipient_key = mapping["sales_rep_email"]
                            if recipient_key not in recipient_branches:
                                recipient_branches[recipient_key] = {
                                    "mapping": mapping,
                                    "branches": []
                                }
                            recipient_branches[recipient_key]["branches"].append(branch_code)
                
                # Generate and send personalized combined report for each recipient
                for recipient_email, recipient_data in recipient_branches.items():
                    mapping = recipient_data["mapping"]
                    recipient_specific_branches = recipient_data["branches"]
                    
                    total_emails += 1
                    
                    try:
                        # Generate combined report with only branches this recipient handles
                        personalized_report_html = await self.report_service.generate_combined_report(
                            tenant_id, request.report_date, recipient_specific_branches
                        )
                        
                        await self._send_combined_email(
                            email_config,
                            mapping,
                            personalized_report_html,
                            request.report_date,
                            recipient_specific_branches,
                            job_id,
                            tenant_id
                        )
                        emails_sent += 1
                        logger.info(f"Sent personalized combined report to {recipient_email} for branches: {recipient_specific_branches}")
                        
                    except Exception as email_error:
                        emails_failed += 1
                        logger.error(f"Failed to send personalized combined email to {recipient_email}: {email_error}")
                        
                        # Log failed email
                        error_branch_count = len(recipient_specific_branches)
                        error_branch_text = "branch" if error_branch_count == 1 else "branches"
                        error_subject = f"Daily Branch Sales Report - {request.report_date.strftime('%Y-%m-%d')} ({error_branch_count} {error_branch_text})"
                        
                        await asyncio.get_event_loop().run_in_executor(
                            None, 
                            self.db_client.log_email_send_history,
                            {
                                "tenant_id": tenant_id,
                                "job_id": job_id,
                                "branch_code": ", ".join(recipient_specific_branches),
                                "sales_rep_email": mapping["sales_rep_email"],
                                "sales_rep_name": mapping.get("sales_rep_name"),
                                "subject": error_subject,
                                "report_date": request.report_date,
                                "status": "failed",
                                "error_message": str(email_error)
                            }
                        )
            
            except Exception as combined_error:
                logger.error(f"Error generating personalized combined reports: {combined_error}")

            # Update job completion status
            completion_data = {
                "status": "completed",
                "completed_at": datetime.now(),
                "total_emails": total_emails,
                "emails_sent": emails_sent,
                "emails_failed": emails_failed
            }
            
            await asyncio.get_event_loop().run_in_executor(
                None, 
                self.db_client.update_email_job_status,
                job_id,
                "completed",
                completion_data
            )
            
            logger.info(f"Completed email job {job_id}: {emails_sent}/{total_emails} sent successfully")

        except Exception as e:
            logger.error(f"Email job {job_id} failed: {e}")
            
            # Update job failure status
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.db_client.update_email_job_status,
                job_id,
                "failed", 
                {
                    "completed_at": datetime.now(),
                    "error_message": str(e)
                }
            )


    async def _send_combined_email(
        self,
        email_config: Dict[str, Any],
        mapping: Dict[str, Any],
        combined_report_html: str,
        report_date,
        branch_codes: List[str],
        job_id: str,
        tenant_id: str
    ) -> None:
        """
        Send combined email with multiple branches.
        
        Args:
            email_config: SMTP configuration
            mapping: Email recipient mapping
            combined_report_html: Generated combined HTML report
            report_date: Date of the report
            branch_codes: List of branch codes included in the report
            job_id: Job ID for tracking
            tenant_id: Tenant ID
        """
        # Create email message
        msg = MIMEMultipart('related')
        
        # Email headers for combined report
        branch_count = len(branch_codes)
        branch_text = "branch" if branch_count == 1 else "branches"
        subject = f"Daily Branch Sales Report - {report_date.strftime('%Y-%m-%d')} ({branch_count} {branch_text})"
        
        msg['From'] = email_config.get('from_address')
        msg['To'] = mapping['sales_rep_email']
        msg['Subject'] = subject
        
        # Attach HTML content
        msg.attach(MIMEText(combined_report_html, 'html'))
        
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
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.db_client.log_email_send_history,
                {
                    "tenant_id": tenant_id,
                    "job_id": job_id,
                    "branch_code": ", ".join(branch_codes),  # Multiple branches in one record
                    "sales_rep_email": mapping["sales_rep_email"],
                    "sales_rep_name": mapping.get("sales_rep_name"),
                    "subject": subject,
                    "report_date": report_date,
                    "status": "sent",
                    "smtp_response": str(smtp_response) if smtp_response else "OK",
                    "error_message": None  # No error for successful sends
                }
            )
            
        finally:
            if smtp_server:
                try:
                    smtp_server.quit()
                except:
                    pass
