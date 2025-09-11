"""
Report generation service for creating HTML branch reports
"""

import asyncio
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from loguru import logger

from services.analytics_service.database.postgres_client import AnalyticsPostgresClient
from services.analytics_service.services.template_service import TemplateService
from services.analytics_service.utils import run_sync_in_executor


class ReportService:
    """Service for generating HTML reports."""

    def __init__(self, db_client: AnalyticsPostgresClient):
        """Initialize report service."""
        self.db_client = db_client
        self.template_service = TemplateService()

    async def generate_branch_report(
        self, 
        tenant_id: str, 
        branch_code: str, 
        report_date: date
    ) -> str:
        """
        Generate HTML report for a specific branch.
        
        Args:
            tenant_id: Tenant ID
            branch_code: Branch code to generate report for
            report_date: Date to generate report for
            
        Returns:
            HTML report content
        """
        logger.info(f"Generating report for branch {branch_code} on {report_date}")
        
        # Convert date to string format
        date_str = report_date.strftime('%Y-%m-%d')
        
        # Get branch/location information
        location_info = await run_sync_in_executor(
            self._get_location_info, tenant_id, branch_code
        )
        
        if not location_info:
            raise Exception(f"Location information not found for branch {branch_code}")
        
        # Gather all task data in parallel
        try:
            tasks_data = await asyncio.gather(
                self._get_purchase_tasks_async(tenant_id, branch_code, date_str),
                self._get_cart_abandonment_tasks_async(tenant_id, branch_code, date_str),
                self._get_search_analysis_tasks_async(tenant_id, branch_code, date_str),
                self._get_repeat_visit_tasks_async(tenant_id, branch_code, date_str),
                return_exceptions=True
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
                "total_revenue": self._calculate_total_revenue(purchase_tasks.get("data", []))
            },
            "tasks": {
                "purchases": purchase_tasks.get("data", []),
                "cart_abandonment": cart_tasks.get("data", []),
                "search_analysis": search_tasks.get("data", []), 
                "repeat_visits": repeat_tasks.get("data", []),
            }
        }
        
        # Generate HTML using template
        html_content = self.template_service.render_branch_report(report_data)
        
        logger.info(f"Generated {len(html_content)} character report for branch {branch_code}")
        
        return html_content


    def _get_location_info(self, tenant_id: str, branch_code: str) -> Optional[Dict[str, Any]]:
        """Get location information for a branch."""
        try:
            locations = self.db_client.get_locations(tenant_id)
            for location in locations:
                if location.get("locationId") == branch_code:
                    return location
            return None
        except Exception as e:
            logger.error(f"Error fetching location info for {branch_code}: {e}")
            return None

    async def _get_purchase_tasks_async(
        self, tenant_id: str, branch_code: str, date_str: str
    ) -> Dict[str, Any]:
        """Get purchase tasks asynchronously."""
        return await run_sync_in_executor(
            self.db_client.get_purchase_tasks,
            tenant_id, 1, 50, None, branch_code, date_str, date_str
        )

    async def _get_cart_abandonment_tasks_async(
        self, tenant_id: str, branch_code: str, date_str: str
    ) -> Dict[str, Any]:
        """Get cart abandonment tasks asynchronously."""
        return await run_sync_in_executor(
            self.db_client.get_cart_abandonment_tasks,
            tenant_id, 1, 50, None, branch_code, date_str, date_str
        )

    async def _get_search_analysis_tasks_async(
        self, tenant_id: str, branch_code: str, date_str: str
    ) -> Dict[str, Any]:
        """Get search analysis tasks asynchronously."""
        return await run_sync_in_executor(
            self.db_client.get_search_analysis_tasks,
            tenant_id, 1, 50, None, branch_code, date_str, date_str, False
        )

    async def _get_repeat_visit_tasks_async(
        self, tenant_id: str, branch_code: str, date_str: str
    ) -> Dict[str, Any]:
        """Get repeat visit tasks asynchronously."""
        return await run_sync_in_executor(
            self.db_client.get_repeat_visit_tasks,
            tenant_id, 1, 50, None, branch_code, date_str, date_str
        )

    def _safe_get_task_data(self, task_result: Any, task_type: str) -> Dict[str, Any]:
        """Safely get task data with proper error handling."""
        try:
            if isinstance(task_result, Exception):
                logger.error(f"Error in {task_type} task: {task_result}")
                return {"data": [], "total": 0}
            
            if task_result is None:
                logger.warning(f"No data returned for {task_type} task")
                return {"data": [], "total": 0}
            
            if not isinstance(task_result, dict):
                logger.warning(f"Unexpected data format for {task_type} task: {type(task_result)}")
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

    def _calculate_total_revenue(self, purchase_data: List[Dict[str, Any]]) -> float:
        """Calculate total revenue from purchase data."""
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
