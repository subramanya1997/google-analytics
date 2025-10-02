"""
Report Generation Service for Branch Analytics.

This module provides HTML report generation functionality for branch-specific
analytics data, including purchase analysis, cart abandonment, search behavior,
and repeat visitor tracking.

Integrates with database client for data retrieval and template service for
HTML rendering, supporting parallel data gathering for optimal performance.
"""

import asyncio
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from loguru import logger

from services.analytics_service.database.postgres_client import AnalyticsPostgresClient
from services.analytics_service.services.template_service import TemplateService


class ReportService:
    """HTML report generation service for branch analytics.
    
    Generates comprehensive branch reports by aggregating analytics data from
    multiple sources including purchases, cart abandonment, search analysis,
    and repeat visitor tracking. Utilizes parallel data gathering and template
    rendering for efficient report generation.
    """

    def __init__(self, db_client: AnalyticsPostgresClient):
        """Initialize report service with database client dependency.
        
        Args:
            db_client: Analytics PostgreSQL client for data operations
        """
        self.db_client = db_client
        self.template_service = TemplateService()

    async def generate_branch_report(
        self, 
        tenant_id: str, 
        branch_code: str, 
        report_date: date
    ) -> str:
        """
        Generate comprehensive HTML report for a specific branch.
        
        Orchestrates data collection from multiple analytics sources including purchases,
        cart abandonment, search analysis, and repeat visitors. Uses parallel data
        gathering for optimal performance and comprehensive error handling.
        
        Args:
            tenant_id (str): Unique identifier for the tenant
            branch_code (str): Branch/location identifier for report generation
            report_date (date): Specific date for report data collection
            
        Returns:
            str: Complete HTML report content ready for email delivery
            
        Raises:
            Exception: Location information not found or template rendering failures
        """
        logger.info(f"Generating report for branch {branch_code} on {report_date}")
        
        # Convert date to string format
        date_str = report_date.strftime('%Y-%m-%d')
        
        # Get branch/location information
        location_info = await self._get_location_info(tenant_id, branch_code)
        
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


    async def _get_location_info(self, tenant_id: str, branch_code: str) -> Optional[Dict[str, Any]]:
        """Get location metadata information for a specific branch.
        
        Retrieves location details including name, city, and state information
        for report header and identification purposes.
        
        Args:
            tenant_id (str): Unique identifier for the tenant
            branch_code (str): Branch/location identifier
            
        Returns:
            Optional[Dict[str, Any]]: Location information containing:
                - locationId (str): Branch identifier
                - locationName (str): Human-readable location name
                - city (Optional[str]): Location city
                - state (Optional[str]): Location state
                Returns None if branch not found
                
        """
        try:
            locations = await self.db_client.get_locations(tenant_id)
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
        """Get purchase tasks asynchronously.
        
        Retrieves purchase analytics tasks with pagination and filtering capabilities.
        
        Args:
            tenant_id (str): Unique identifier for the tenant
            branch_code (str): Branch identifier
            date_str (str): Date in YYYY-MM-DD format
        """
        return await self.db_client.get_purchase_tasks(
            tenant_id, 1, 50, None, branch_code, date_str, date_str
        )

    async def _get_cart_abandonment_tasks_async(
        self, tenant_id: str, branch_code: str, date_str: str
    ) -> Dict[str, Any]:
        """
        Retrieves cart abandonment analytics tasks with pagination and filtering capabilities.
        
        Args:
            tenant_id (str): Unique identifier for the tenant
            branch_code (str): Branch identifier
            date_str (str): Date in YYYY-MM-DD format
        """
        return await self.db_client.get_cart_abandonment_tasks(
            tenant_id, 1, 50, None, branch_code, date_str, date_str
        )

    async def _get_search_analysis_tasks_async(
        self, tenant_id: str, branch_code: str, date_str: str
    ) -> Dict[str, Any]:
        """
        Retrieves search analytics tasks with pagination and filtering capabilities.
        
        Args:
            tenant_id (str): Unique identifier for the tenant
            branch_code (str): Branch identifier
            date_str (str): Date in YYYY-MM-DD format
        """
        return await self.db_client.get_search_analysis_tasks(
            tenant_id, 1, 50, None, branch_code, date_str, date_str, False
        )

    async def _get_repeat_visit_tasks_async(
        self, tenant_id: str, branch_code: str, date_str: str
    ) -> Dict[str, Any]:
        """
        Retrieves repeat visit analytics tasks with pagination and filtering capabilities.
        
        Args:
            tenant_id (str): Unique identifier for the tenant
            branch_code (str): Branch identifier
            date_str (str): Date in YYYY-MM-DD format
        """
        return await self.db_client.get_repeat_visit_tasks(
            tenant_id, 1, 50, None, branch_code, date_str, date_str
        )

    def _safe_get_task_data(self, task_result: Any, task_type: str) -> Dict[str, Any]:
        """
        Processes task results to ensure data integrity and proper handling of
        various data types and structures.
        
        Args:
            task_result (Any): Task result data
            task_type (str): Type of task (purchase, cart, search, repeat)
        """
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
        """Calculate total revenue from purchase task data with robust parsing.
        
        Processes purchase records to compute total revenue with support for
        various currency formats and data types, including string-based values
        with currency symbols.
        
        Args:
            purchase_data (List[Dict[str, Any]]): List of purchase records containing
                order_value fields in various formats (int, float, string)
                
        Returns:
            float: Total revenue amount as decimal value
            
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
