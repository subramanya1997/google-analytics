"""
Email service for Azure Functions.

Adapted from the FastAPI analytics_service for use in serverless Azure Functions.
Handles sending branch reports via SMTP.
"""

import builtins
import contextlib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from collections import defaultdict
import smtplib
from typing import Any

from loguru import logger
from shared.database import create_repository

from services.report_service import ReportService


class EmailService:
    """
    Service for handling email report generation and SMTP delivery.

    This service orchestrates the complete email workflow, including:
    - Email job creation and status tracking
    - Branch report generation with analytics data
    - HTML template rendering
    - SMTP email delivery to configured recipients
    - Email send history logging for compliance

    Each tenant has their own isolated database (google-analytics-{tenant_id})
    and SMTP configuration for SOC2 compliance. The service supports sending
    reports to individual branches or all branches based on configuration.

    Attributes:
        tenant_id: The tenant identifier used for database routing.
        repo: Repository instance for database operations.
        report_service: Service for generating HTML reports.

    Example:
        >>> service = EmailService("550e8400-e29b-41d4-a716-446655440000")
        >>> result = await service.process_email_job(tenant_id, job_id, report_date)
    """

    def __init__(self, tenant_id: str) -> None:
        """
        Initialize email service for a specific tenant.

        Creates repository and report service instances configured for the
        tenant's isolated database and configuration.

        Args:
            tenant_id: The tenant ID (UUID string) that determines which database
                      and SMTP configuration to use.

        Raises:
            ValueError: If tenant_id is invalid or database connection fails.
        """
        self.tenant_id = tenant_id
        self.repo = create_repository(tenant_id)
        self.report_service = ReportService(tenant_id)


    async def process_email_job(
        self,
        tenant_id: str,
        job_id: str,
        report_date,
        branch_codes: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Process email sending job by generating and sending branch reports.

        This method orchestrates the complete email workflow:
        1. Validates email configuration and branch mappings
        2. Generates HTML reports for each branch using analytics data
        3. Sends emails via SMTP to configured sales representatives
        4. Logs email send history for each attempt
        5. Updates job status with completion metrics

        The method handles partial failures gracefully - if some emails fail,
        others can still succeed, and the job status reflects this.

        Args:
            tenant_id: Tenant ID for database routing and configuration lookup.
            job_id: Unique identifier for tracking this email job.
            report_date: Date for which to generate analytics reports.
            branch_codes: Optional list of branch codes to process.
                        If None, processes all configured branches.

        Returns:
            dict[str, Any]: Job result summary containing:
                - job_id: The job identifier
                - status: Final job status ("completed", "completed_with_errors", "failed")
                - total_emails: Total number of emails attempted
                - emails_sent: Number of successfully sent emails
                - emails_failed: Number of failed email attempts

        Raises:
            Exception: If email configuration is missing, no branch mappings found,
                      or critical errors occur during processing.

        Note:
            - Job status is updated to "processing" at start
            - Each branch report is generated independently
            - Individual email failures are logged but don't stop the job
            - Job status reflects overall success/failure state
            - Email send history is logged for compliance auditing
            - SMTP connection is created fresh for each email (stateless)

        Example:
            >>> result = await service.process_email_job(
            ...     tenant_id,
            ...     "email_abc123",
            ...     date(2024, 1, 14),
            ...     branch_codes=["BR001"]
            ... )
            >>> result["status"]
            'completed'
            >>> result["emails_sent"]
            1
        """
        try:
            logger.info(f"Starting email job {job_id} for tenant {tenant_id}")

            # Update job status to processing
            await self.repo.update_email_job_status(
                job_id, "processing", {"started_at": datetime.now()}
            )

            # Get email configuration
            email_config = await self.repo.get_email_config(tenant_id)

            if not email_config:
                msg = "Email configuration not found for tenant"
                raise Exception(msg)

            # Get ALL branch email mappings
            all_mappings = await self.repo.get_branch_email_mappings(tenant_id, None)

            if not all_mappings:
                msg = "No branch email mappings configured"
                raise Exception(msg)

            # Filter mappings by requested branches if specified
            if branch_codes:
                filtered_mappings = [
                    m for m in all_mappings if m["branch_code"] in branch_codes
                ]
            else:
                filtered_mappings = all_mappings

            if not filtered_mappings:
                msg = "No branches found to send reports to"
                raise Exception(msg)

            # Send individual branch reports
            total_emails = 0
            emails_sent = 0
            emails_failed = 0

            # Group mappings by branch


            mappings_by_branch = defaultdict(list)
            for mapping in filtered_mappings:
                mappings_by_branch[mapping["branch_code"]].append(mapping)

            logger.info(
                f"Generating individual branch reports for {len(mappings_by_branch)} branches"
            )

            # Send individual reports for each branch
            for branch_code, branch_mappings in mappings_by_branch.items():
                for mapping in branch_mappings:
                    if mapping.get("is_enabled", True):
                        total_emails += 1

                        try:
                            # Generate full branch report with analytics
                            branch_report_html = (
                                await self.report_service.generate_branch_report(
                                    tenant_id, branch_code, report_date
                                )
                            )

                            await self._send_branch_email(
                                email_config,
                                mapping,
                                branch_report_html,
                                report_date,
                                branch_code,
                                job_id,
                                tenant_id,
                            )
                            emails_sent += 1
                            logger.info(
                                f"Sent branch report to {mapping['sales_rep_email']} for branch: {branch_code}"
                            )

                        except Exception as email_error:
                            emails_failed += 1
                            logger.error(
                                f"Failed to send branch email to {mapping['sales_rep_email']} for branch {branch_code}: {email_error}"
                            )

                            # Log failed email
                            error_subject = f"Daily Branch Sales Report - {report_date.strftime('%Y-%m-%d')} - {branch_code}"

                            await self.repo.log_email_send_history(
                                {
                                    "tenant_id": tenant_id,
                                    "job_id": job_id,
                                    "branch_code": branch_code,
                                    "sales_rep_email": mapping["sales_rep_email"],
                                    "sales_rep_name": mapping.get("sales_rep_name"),
                                    "subject": error_subject,
                                    "report_date": report_date,
                                    "status": "failed",
                                    "error_message": str(email_error),
                                }
                            )

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
                "emails_failed": emails_failed,
            }

            await self.repo.update_email_job_status(
                job_id, final_status, completion_data
            )

            logger.info(
                f"Email job {job_id} finished with status '{final_status}': {emails_sent}/{total_emails} sent successfully"
            )

            return {
                "job_id": job_id,
                "status": final_status,
                "total_emails": total_emails,
                "emails_sent": emails_sent,
                "emails_failed": emails_failed,
            }

        except Exception as e:
            logger.error(f"Email job {job_id} failed: {e}")

            # Update job failure status
            await self.repo.update_email_job_status(
                job_id,
                "failed",
                {"completed_at": datetime.now(), "error_message": str(e)},
            )
            raise

    async def _send_branch_email(
        self,
        email_config: dict[str, Any],
        mapping: dict[str, Any],
        branch_report_html: str,
        report_date,
        branch_code: str,
        job_id: str,
        tenant_id: str,
    ) -> None:
        """
        Send individual branch report email via SMTP.

        This method creates an HTML email message, connects to the SMTP server
        using tenant-specific configuration, and sends the branch analytics
        report to the configured sales representative. The email send attempt
        is logged to the database for audit purposes.

        Args:
            email_config: SMTP server configuration dictionary containing:
                - server: SMTP server hostname
                - port: SMTP server port (default: 587)
                - username: SMTP authentication username (optional)
                - password: SMTP authentication password (optional)
                - from_address: Sender email address
                - use_ssl: Boolean for SSL connection (default: False)
                - use_tls: Boolean for STARTTLS (default: True)
            mapping: Branch email mapping dictionary containing:
                - sales_rep_email: Recipient email address
                - sales_rep_name: Recipient name (optional)
                - branch_code: Branch identifier
                - is_enabled: Whether this mapping is active
            branch_report_html: Complete HTML content of the branch report.
            report_date: Date for which the report was generated.
            branch_code: Branch/warehouse code for the report.
            job_id: Email job identifier for tracking and logging.
            tenant_id: Tenant ID for database logging.

        Returns:
            None: Email is sent synchronously. Results are logged to database.

        Raises:
            smtplib.SMTPException: If SMTP server connection or send fails.
            Exception: Various SMTP-related errors (authentication, network, etc.)

        Note:
            - SMTP connection is created fresh for each email (stateless)
            - Supports both SSL (port 465) and STARTTLS (port 587) connections
            - Email subject format: "Daily Branch Sales Report - {date} - {branch_code}"
            - Email send history is logged with status "sent" or "failed"
            - SMTP response is captured and stored for debugging
            - Connection is properly closed even on errors

        Example:
            >>> await service._send_branch_email(
            ...     email_config,
            ...     {"sales_rep_email": "rep@example.com", ...},
            ...     "<html>...</html>",
            ...     date(2024, 1, 14),
            ...     "BR001",
            ...     "email_abc123",
            ...     tenant_id
            ... )
        """
        # Create email message
        msg = MIMEMultipart("related")

        # Email headers for individual branch report
        subject = f"Daily Branch Sales Report - {report_date.strftime('%Y-%m-%d')} - {branch_code}"

        msg["From"] = email_config.get("from_address")
        msg["To"] = mapping["sales_rep_email"]
        msg["Subject"] = subject

        # Attach HTML content
        msg.attach(MIMEText(branch_report_html, "html"))

        # Send via SMTP
        smtp_server = None
        try:
            # Get port as integer
            port = email_config.get("port", 587)
            if isinstance(port, str):
                port = int(port)

            # Create SMTP connection
            if email_config.get("use_ssl", False):
                smtp_server = smtplib.SMTP_SSL(
                    email_config["server"], port if port in [465, 995] else 465
                )
            else:
                smtp_server = smtplib.SMTP(email_config["server"], port)

                if email_config.get("use_tls", True):
                    smtp_server.starttls()

            # Login if credentials provided
            if email_config.get("username") and email_config.get("password"):
                smtp_server.login(email_config["username"], email_config["password"])

            # Send email
            smtp_response = smtp_server.send_message(msg)

            # Log successful send
            await self.repo.log_email_send_history(
                {
                    "tenant_id": tenant_id,
                    "job_id": job_id,
                    "branch_code": branch_code,
                    "sales_rep_email": mapping["sales_rep_email"],
                    "sales_rep_name": mapping.get("sales_rep_name"),
                    "subject": subject,
                    "report_date": report_date,
                    "status": "sent",
                    "smtp_response": str(smtp_response) if smtp_response else "OK",
                    "error_message": None,
                }
            )

        finally:
            if smtp_server:
                with contextlib.suppress(builtins.BaseException):
                    smtp_server.quit()
