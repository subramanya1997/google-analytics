"""
Report generation service for creating HTML branch reports.

Adapted for Azure Functions from the analytics_service.
"""

import asyncio
from datetime import date, datetime
from typing import Any

import logging

from services.template_service import TemplateService
from shared.database import create_repository
from shared.tasks_repository import TasksRepository

logger = logging.getLogger(__name__)


class ReportService:
    """
    Service for generating HTML branch analytics reports.

    This service aggregates analytics data from multiple sources and generates
    comprehensive HTML reports for individual branches. Reports include:
    - Purchase analysis tasks
    - Cart abandonment insights
    - Search analysis results
    - Repeat visit patterns
    - Revenue summaries

    Each tenant has their own isolated database for data retrieval and report
    generation. Reports are rendered using Jinja2 templates for consistency.

    Attributes:
        tenant_id: The tenant identifier used for database routing.
        repo: Repository instance for database operations.
        template_service: Service for HTML template rendering.

    Example:
        >>> service = ReportService("550e8400-e29b-41d4-a716-446655440000")
        >>> html = await service.generate_branch_report(tenant_id, "BR001", date(2024, 1, 14))
    """

    def __init__(self, tenant_id: str) -> None:
        """
        Initialize report service for a specific tenant.

        Creates repository and template service instances configured for the
        tenant's isolated database.

        Args:
            tenant_id: The tenant ID (UUID string) that determines which database
                      to connect to for data retrieval.

        Raises:
            ValueError: If tenant_id is invalid or database connection fails.
        """
        self.tenant_id = tenant_id
        self.repo = create_repository(tenant_id)
        self.tasks_repo = TasksRepository()
        self.template_service = TemplateService()

    async def generate_branch_report(
        self, tenant_id: str, branch_code: str, report_date: date
    ) -> str:
        """
        Generate comprehensive HTML analytics report for a specific branch.

        This method aggregates data from multiple analytics task sources and
        generates a complete HTML report including:
        - Branch location information
        - Purchase analysis with revenue calculations
        - Cart abandonment insights
        - Search analysis with no-results tracking
        - Repeat visit patterns
        - Summary statistics

        Data is fetched in parallel for performance, and errors in individual
        data sources are handled gracefully without failing the entire report.

        Args:
            tenant_id: Tenant ID for database routing and data isolation.
            branch_code: Branch/warehouse code to generate report for.
            report_date: Date for which to generate the analytics report.

        Returns:
            str: Complete HTML content of the branch report, ready for email delivery.

        Raises:
            Exception: If location information is not found for the branch code,
                     or if critical errors occur during data aggregation.

        Note:
            - Data is fetched in parallel using asyncio.gather for performance
            - Individual task failures are handled gracefully
            - Report includes summary statistics and detailed task lists
            - HTML is generated using Jinja2 templates for consistency
            - Report generation timestamp is included in the output

        Example:
            >>> html = await service.generate_branch_report(
            ...     tenant_id,
            ...     "BR001",
            ...     date(2024, 1, 14)
            ... )
            >>> len(html)
            50000
        """
        logger.info(f"Generating report for branch {branch_code} on {report_date}")

        # Convert date to string format
        date_str = report_date.strftime("%Y-%m-%d")

        # Get branch/location information
        location_info = await self._get_location_info(tenant_id, branch_code)

        if not location_info:
            msg = f"Location information not found for branch {branch_code}"
            raise Exception(msg)

        # Gather all task data in parallel
        try:
            tasks_data = await asyncio.gather(
                self._get_purchase_tasks_async(tenant_id, branch_code, date_str),
                self._get_cart_abandonment_tasks_async(
                    tenant_id, branch_code, date_str
                ),
                self._get_search_analysis_tasks_async(tenant_id, branch_code, date_str),
                self._get_repeat_visit_tasks_async(tenant_id, branch_code, date_str),
                return_exceptions=True,
            )

            # Process results with proper error handling
            purchase_tasks = self._safe_get_task_data(tasks_data[0], "purchase")
            cart_tasks = self._safe_get_task_data(tasks_data[1], "cart")
            search_tasks = self._safe_get_task_data(tasks_data[2], "search")
            repeat_tasks = self._safe_get_task_data(tasks_data[3], "repeat")

        except Exception as e:
            logger.error(f"Error gathering task data for branch {branch_code}: {e}")
            purchase_tasks = {"data": [], "total": 0}
            cart_tasks = {"data": [], "total": 0}
            search_tasks = {"data": [], "total": 0}
            repeat_tasks = {"data": [], "total": 0}

        # Create report data structure
        report_data = {
            "location": location_info,
            "report_date": report_date,
            "generated_at": datetime.now(),
            "summary": {
                "total_purchases": purchase_tasks.get("total", 0),
                "total_cart_abandonment": cart_tasks.get("total", 0),
                "total_search_issues": search_tasks.get("total", 0),
                "total_repeat_visits": repeat_tasks.get("total", 0),
                "total_revenue": self._calculate_total_revenue(
                    purchase_tasks.get("data", [])
                ),
            },
            "tasks": {
                "purchases": purchase_tasks.get("data", []),
                "cart_abandonment": cart_tasks.get("data", []),
                "search_analysis": search_tasks.get("data", []),
                "repeat_visits": repeat_tasks.get("data", []),
            },
        }

        # Generate HTML using template
        html_content = self.template_service.render_branch_report(report_data)

        logger.info(
            f"Generated {len(html_content)} character report for branch {branch_code}"
        )

        return html_content

    async def _get_location_info(
        self, tenant_id: str, branch_code: str
    ) -> dict[str, Any] | None:
        """
        Retrieve location/warehouse information for a branch code.

        Fetches location details from the database and transforms them into
        the format expected by the report template.

        Args:
            tenant_id: Tenant ID for database routing.
            branch_code: Branch/warehouse code to look up.

        Returns:
            dict[str, Any] | None: Location information dictionary containing:
                - locationId: Warehouse code
                - locationName: Warehouse name
                - city: City name
                - state: State/province code
            Returns None if location is not found.

        Note:
            - Uses tenant-specific database connection
            - Transforms database schema to template format
            - Returns None on errors for graceful handling
        """
        try:
            location = await self.repo.get_location_by_code(tenant_id, branch_code)
            if location:
                # Transform to match expected format
                return {
                    "locationId": location.get("warehouse_code", branch_code),
                    "locationName": location.get("warehouse_name", branch_code),
                    "city": location.get("city", ""),
                    "state": location.get("state", ""),
                }
            return None
        except Exception as e:
            logger.error(f"Error fetching location info for {branch_code}: {e}")
            return None

    async def _get_purchase_tasks_async(
        self, tenant_id: str, branch_code: str, date_str: str
    ) -> dict[str, Any]:
        """
        Fetch purchase analysis tasks for a branch and date range.

        Retrieves purchase events with customer information, order values,
        and product details for follow-up actions.

        Args:
            tenant_id: Tenant ID for database routing.
            branch_code: Branch code to filter purchases.
            date_str: Date string in YYYY-MM-DD format.

        Returns:
            dict[str, Any]: Paginated results containing purchase task data
                          and total count.
        """
        return await self.tasks_repo.get_purchase_tasks(
            tenant_id, 1, 500, None, branch_code, date_str, date_str
        )

    async def _get_cart_abandonment_tasks_async(
        self, tenant_id: str, branch_code: str, date_str: str
    ) -> dict[str, Any]:
        """
        Fetch cart abandonment analysis tasks for a branch and date range.

        Retrieves abandoned cart events with customer information and cart
        values for recovery campaigns.

        Args:
            tenant_id: Tenant ID for database routing.
            branch_code: Branch code to filter cart abandonments.
            date_str: Date string in YYYY-MM-DD format.

        Returns:
            dict[str, Any]: Paginated results containing cart abandonment data
                          and total count.
        """
        return await self.tasks_repo.get_cart_abandonment_tasks(
            tenant_id, 1, 500, None, branch_code, date_str, date_str
        )

    async def _get_search_analysis_tasks_async(
        self, tenant_id: str, branch_code: str, date_str: str
    ) -> dict[str, Any]:
        """
        Fetch search analysis tasks for a branch and date range.

        Retrieves search queries with no results, including search terms,
        session information, and customer details for search optimization.

        Args:
            tenant_id: Tenant ID for database routing.
            branch_code: Branch code to filter search events.
            date_str: Date string in YYYY-MM-DD format.

        Returns:
            dict[str, Any]: Paginated results containing search analysis data
                          and total count.
        """
        return await self.tasks_repo.get_search_analysis_tasks(
            tenant_id, 1, 500, None, branch_code, date_str, date_str, False
        )

    async def _get_repeat_visit_tasks_async(
        self, tenant_id: str, branch_code: str, date_str: str
    ) -> dict[str, Any]:
        """
        Fetch repeat visit analysis tasks for a branch and date range.

        Retrieves high-engagement visitor sessions with page view counts
        and product interaction details for follow-up opportunities.

        Args:
            tenant_id: Tenant ID for database routing.
            branch_code: Branch code to filter repeat visits.
            date_str: Date string in YYYY-MM-DD format.

        Returns:
            dict[str, Any]: Paginated results containing repeat visit data
                          and total count.
        """
        return await self.tasks_repo.get_repeat_visit_tasks(
            tenant_id, 1, 500, None, branch_code, date_str, date_str
        )

    def _safe_get_task_data(self, task_result: Any, task_type: str) -> dict[str, Any]:
        """
        Safely extract task data from async results with comprehensive error handling.

        This helper method handles various failure scenarios gracefully:
        - Exception results from asyncio.gather
        - None or invalid data types
        - Missing or malformed data structures

        Args:
            task_result: Result from async task execution (may be Exception, None, or dict).
            task_type: Type identifier for logging purposes (e.g., "purchase", "cart").

        Returns:
            dict[str, Any]: Standardized task data dictionary with:
                - data: List of task records (empty list on errors)
                - total: Total count of tasks (0 on errors)

        Note:
            - Logs errors but doesn't raise exceptions
            - Ensures consistent return format for template rendering
            - Handles edge cases like None data or non-list data arrays
        """
        try:
            if isinstance(task_result, Exception):
                logger.error(f"Error in {task_type} task: {task_result}")
                return {"data": [], "total": 0}

            if task_result is None:
                logger.warning(f"No data returned for {task_type} task")
                return {"data": [], "total": 0}

            if not isinstance(task_result, dict):
                logger.warning(
                    f"Unexpected data format for {task_type} task: {type(task_result)}"
                )
                return {"data": [], "total": 0}

            # Ensure data is a list
            data = task_result.get("data", [])
            if data is None:
                data = []
            elif not isinstance(data, list):
                logger.warning(f"Task data is not a list for {task_type}: {type(data)}")
                data = []

            total = task_result.get("total", len(data))
            if not isinstance(total, (int, float)):
                total = len(data)

            return {"data": data, "total": int(total)}

        except Exception as e:
            logger.error(f"Error processing {task_type} task data: {e}")
            return {"data": [], "total": 0}

    def _calculate_total_revenue(self, purchase_data: list[dict[str, Any]]) -> float:
        """
        Calculate total revenue from purchase task data.

        Sums order values from purchase records, handling various data formats
        including numeric values and formatted currency strings.

        Args:
            purchase_data: List of purchase task dictionaries, each containing
                          an "order_value" field.

        Returns:
            float: Total revenue amount. Returns 0.0 if no data or all values invalid.

        Note:
            - Handles both numeric and string currency values
            - Strips currency symbols ($) and commas from strings
            - Skips invalid values gracefully
            - Returns 0.0 for empty or invalid input
        """
        total = 0.0
        if not purchase_data:
            return total

        for purchase in purchase_data:
            try:
                revenue = purchase.get("order_value", 0)
                if isinstance(revenue, (int, float)):
                    total += revenue
                elif isinstance(revenue, str):
                    # Remove currency symbols and convert
                    clean_revenue = revenue.replace("$", "").replace(",", "").strip()
                    if clean_revenue:
                        total += float(clean_revenue)
            except (ValueError, TypeError):
                continue
        return total
