"""
Template service for rendering HTML reports using Jinja2.

Adapted for Azure Functions from the analytics_service.
"""

from datetime import datetime
import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
from loguru import logger


class TemplateService:
    """
    Service for rendering HTML email templates using Jinja2.

    This service provides template rendering capabilities for branch analytics
    reports. It uses Jinja2 for template processing with custom filters for
    currency formatting, date formatting, and JSON parsing.

    Templates are loaded from the templates directory and rendered with
    analytics data to produce complete HTML emails ready for SMTP delivery.

    Attributes:
        env: Jinja2 Environment instance configured with template loader and filters.

    Example:
        >>> service = TemplateService()
        >>> html = service.render_branch_report(report_data)
    """

    def __init__(self) -> None:
        """
        Initialize template service with Jinja2 environment.

        Sets up the Jinja2 environment with:
        - FileSystemLoader for template loading
        - Auto-escaping enabled for security
        - Custom filters for currency, dates, and JSON

        Note:
            Templates directory is located at: services/templates/
            Directory is created if it doesn't exist.
        """
        # Get templates directory relative to this file
        # In Azure Functions: services/template_service.py -> templates/
        templates_dir = Path(__file__).parent.parent / "templates"

        # Create templates directory if it doesn't exist
        templates_dir.mkdir(exist_ok=True)

        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)), autoescape=True
        )

        # Add custom filters
        self.env.filters["currency"] = self._currency_filter
        self.env.filters["date_format"] = self._date_format_filter
        self.env.filters["json_parse"] = self._json_parse_filter

    def render_branch_report(self, report_data: dict[str, Any]) -> str:
        """
        Render branch analytics report HTML template with data.

        This method transforms analytics data into a complete HTML email report
        by rendering the Jinja2 template with formatted data including:
        - Location information
        - Purchase summaries and samples
        - Cart abandonment metrics
        - Search analysis results
        - Repeat visit patterns
        - Revenue calculations

        Args:
            report_data: Dictionary containing:
                - location: Branch location information
                - report_date: Date object for the report
                - summary: Summary statistics dictionary
                - tasks: Dictionary of task data by type

        Returns:
            str: Complete HTML content ready for email delivery.

        Raises:
            Exception: If template rendering fails, returns fallback HTML instead.

        Note:
            - Uses branch_report.html template
            - Transforms data to match template expectations
            - Includes fallback HTML generation on template errors
            - Custom filters handle currency and date formatting
            - Calculates derived metrics (unique customers, averages, etc.)

        Example:
            >>> report_data = {
            ...     "location": {"locationId": "BR001", ...},
            ...     "report_date": date(2024, 1, 14),
            ...     "summary": {"total_purchases": 50, ...},
            ...     "tasks": {"purchases": [...], ...}
            ... }
            >>> html = service.render_branch_report(report_data)
        """
        try:
            template = self.env.get_template("branch_report.html")

            # Transform data to match template expectations
            location = report_data.get("location", {})
            tasks = report_data.get("tasks", {})
            summary = report_data.get("summary", {})

            # Prepare template data
            template_data = {
                "location": {
                    "warehouse_code": location.get("locationId", ""),
                    "warehouse_name": location.get("locationName", "Unknown"),
                    "city": location.get("city", ""),
                    "state": location.get("state", ""),
                },
                "report_date": report_data.get("report_date"),
                "datetime": datetime,  # Pass datetime module for template use
                "data": {
                    "purchases": {
                        "total": summary.get("total_purchases", 0),
                        "total_revenue": summary.get("total_revenue", 0),
                        "unique_customers": len(
                            {
                                p.get("user_id", "")
                                for p in tasks.get("purchases", [])
                                if p.get("user_id")
                            }
                        ),
                        "avg_order_value": summary.get("total_revenue", 0)
                        / max(summary.get("total_purchases", 1), 1),
                        "samples": self._transform_purchase_samples(
                            tasks.get("purchases", [])
                        ),
                    },
                    "cart_abandonment": {
                        "total": summary.get("total_cart_abandonment", 0),
                        "unique_customers": len(
                            {
                                c.get("user_id", "")
                                for c in tasks.get("cart_abandonment", [])
                                if c.get("user_id")
                            }
                        ),
                        "total_value": sum(
                            float(c.get("total_value", 0))
                            for c in tasks.get("cart_abandonment", [])
                        ),
                        "avg_value": sum(
                            float(c.get("total_value", 0))
                            for c in tasks.get("cart_abandonment", [])
                        )
                        / max(summary.get("total_cart_abandonment", 1), 1),
                        "samples": self._transform_cart_samples(
                            tasks.get("cart_abandonment", [])
                        ),
                    },
                    "search_no_results": {
                        "unique_terms": summary.get("total_search_issues", 0),
                        "total_searches": sum(
                            s.get("search_count", 0)
                            for s in tasks.get("search_analysis", [])
                        ),
                        "affected_sessions": len(
                            {
                                s.get("session_id", "")
                                for s in tasks.get("search_analysis", [])
                                if s.get("session_id")
                            }
                        ),
                        "unique_users": len(
                            {
                                s.get("user_id", "")
                                for s in tasks.get("search_analysis", [])
                                if s.get("user_id")
                            }
                        ),
                        "samples": self._transform_search_samples(
                            tasks.get("search_analysis", [])
                        ),
                    },
                    "repeat_visits": {
                        "total": summary.get("total_repeat_visits", 0),
                        "avg_pages": sum(
                            r.get("page_views_count", 0)
                            for r in tasks.get("repeat_visits", [])
                        )
                        / max(summary.get("total_repeat_visits", 1), 1),
                        "samples": self._transform_repeat_samples(
                            tasks.get("repeat_visits", [])
                        ),
                    },
                },
            }

            return template.render(**template_data)

        except Exception as e:
            logger.error(f"Error rendering branch report template: {e}")
            # Return fallback HTML
            return self._render_fallback_branch_report(report_data)

    def _currency_filter(self, value: Any) -> str:
        """
        Jinja2 filter to format numeric values as US currency.

        Converts various input types (int, float, string) to formatted
        currency string with dollar sign and comma separators.

        Args:
            value: Numeric value or string to format. Can be int, float, or string.

        Returns:
            str: Formatted currency string (e.g., "$1,234.56").
                Returns original value as string if conversion fails.

        Note:
            - Handles already-formatted strings (returns as-is)
            - Strips existing currency symbols before formatting
            - Defaults to "$0.00" for invalid inputs
        """
        try:
            if isinstance(value, str):
                # Already formatted
                if value.startswith("$"):
                    return value
                # Convert string to float
                clean_value = value.replace("$", "").replace(",", "").strip()
                value = float(clean_value) if clean_value else 0.0
            elif not isinstance(value, (int, float)):
                value = 0.0

            return f"${value:,.2f}"
        except:
            return str(value)

    def _date_format_filter(self, value: Any, format: str = "%Y-%m-%d") -> str:
        """
        Jinja2 filter to format date/datetime values as strings.

        Converts datetime objects or ISO date strings to formatted date strings
        using the specified format pattern.

        Args:
            value: Date value to format. Can be datetime object or ISO string.
            format: strftime format pattern (default: "%Y-%m-%d").

        Returns:
            str: Formatted date string. Returns original value as string if conversion fails.

        Note:
            - Handles datetime objects directly
            - Parses ISO format strings (handles 'Z' timezone indicator)
            - Returns original value as string on parse errors
        """
        try:
            if isinstance(value, datetime):
                return value.strftime(format)
            if isinstance(value, str):
                # Try to parse string date
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return dt.strftime(format)
            return str(value)
        except:
            return str(value)

    def _json_parse_filter(self, value: str) -> list[dict[str, Any]]:
        """
        Jinja2 filter to parse JSON strings to Python objects.

        Converts JSON-encoded strings (typically from database JSONB columns)
        back to Python lists/dictionaries for template rendering.

        Args:
            value: JSON string to parse.

        Returns:
            list[dict[str, Any]]: Parsed JSON data as Python list.
                                Returns empty list if parsing fails.

        Note:
            - Used for parsing product lists and other JSON data
            - Returns empty list on parse errors for graceful handling
        """
        try:
            if isinstance(value, str):
                return json.loads(value)
            return value
        except:
            return []

    def _render_fallback_branch_report(self, report_data: dict[str, Any]) -> str:
        """
        Generate fallback HTML report when template rendering fails.

        Creates a simplified HTML report with basic styling when the main
        template cannot be rendered. This ensures email delivery always
        succeeds even if template processing fails.

        Args:
            report_data: Report data dictionary containing location and summary information.

        Returns:
            str: Complete HTML document with fallback report content.

        Note:
            - Used as error recovery mechanism
            - Includes basic styling for email client compatibility
            - Displays summary statistics even if detailed data unavailable
        """
        location = report_data.get("location", {})
        location_name = location.get("locationName", "Unknown Branch")
        city = location.get("city", "")
        state = location.get("state", "")

        location_display = f"{location_name}"
        if city or state:
            location_display += f" - {city}, {state}"

        report_date = report_data.get("report_date", datetime.now().date())
        summary = report_data.get("summary", {})

        return f"""
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
        .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }}
        .metric {{ background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; }}
        .metric h3 {{ margin: 0 0 10px 0; color: #495057; font-size: 14px; }}
        .metric .value {{ font-size: 24px; font-weight: bold; color: #007bff; }}
        .tasks-section {{ margin-bottom: 30px; }}
        .tasks-section h2 {{ color: #333; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
        .task-list {{ background: #f8f9fa; padding: 15px; border-radius: 8px; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; color: #666; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{location_display}</h1>
            <p>Daily Sales Report - {report_date}</p>
        </div>

        <div class="summary">
            <div class="metric">
                <h3>Total Purchases</h3>
                <div class="value">{summary.get("total_purchases", 0)}</div>
            </div>
            <div class="metric">
                <h3>Total Revenue</h3>
                <div class="value">${summary.get("total_revenue", 0):,.2f}</div>
            </div>
            <div class="metric">
                <h3>Cart Abandonment</h3>
                <div class="value">{summary.get("total_cart_abandonment", 0)}</div>
            </div>
            <div class="metric">
                <h3>Search Issues</h3>
                <div class="value">{summary.get("total_search_issues", 0)}</div>
            </div>
        </div>

        <div class="tasks-section">
            <h2>Sales Tasks Summary</h2>
            <div class="task-list">
                <p><strong>Purchase Follow-ups:</strong> {summary.get("total_purchases", 0)} customers need follow-up contact</p>
                <p><strong>Cart Recovery:</strong> {summary.get("total_cart_abandonment", 0)} abandoned carts to recover</p>
                <p><strong>Search Analysis:</strong> {summary.get("total_search_issues", 0)} search terms need attention</p>
                <p><strong>Repeat Visitors:</strong> {summary.get("total_repeat_visits", 0)} high-engagement visitors to contact</p>
            </div>
        </div>

        <div class="footer">
            <p>Report generated at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <p>This is an automated report from the Sales Intelligence System</p>
        </div>
    </div>
</body>
</html>
"""

    def _transform_purchase_samples(
        self, purchases: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Transform purchase task data to template-expected format.

        Converts database purchase records into the structure expected by
        the Jinja2 template, including product list parsing and field mapping.

        Args:
            purchases: List of purchase task dictionaries from database.

        Returns:
            list[dict[str, Any]]: Transformed purchase records with template fields.

        Note:
            - Parses JSON product lists from database
            - Maps database fields to template field names
            - Handles missing fields gracefully with defaults
        """
        samples = []
        for purchase in purchases:
            sample = {
                "customer_name": purchase.get("customer_name", "Unknown"),
                "company_name": purchase.get("company", ""),
                "trans_id": purchase.get("transaction_id", ""),
                "revenue": float(purchase.get("order_value", 0)),
                "email": purchase.get("email", ""),
                "phone": purchase.get("phone") or purchase.get("office_phone", ""),
                "products": [],
            }

            # Parse products - already in JSON format from database
            products = purchase.get("products", [])
            if isinstance(products, str):
                try:
                    products = json.loads(products)
                except:
                    products = []

            if isinstance(products, list):
                for item in products:
                    sample["products"].append(
                        {
                            "quantity": int(item.get("quantity", 1)),
                            "item_name": item.get("item_name", "Unknown"),
                            "item_id": item.get("item_id", ""),
                        }
                    )

            samples.append(sample)

        return samples

    def _transform_cart_samples(
        self, carts: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Transform cart abandonment data to template-expected format.

        Converts database cart abandonment records into the structure expected
        by the Jinja2 template, including product list parsing.

        Args:
            carts: List of cart abandonment task dictionaries from database.

        Returns:
            list[dict[str, Any]]: Transformed cart records with template fields.

        Note:
            - Parses JSON product lists from database
            - Maps database fields to template field names
            - Handles missing fields gracefully
        """
        samples = []
        for cart in carts:
            sample = {
                "cart_id": cart.get("session_id", ""),
                "customer_name": cart.get("customer_name", "Unknown"),
                "company_name": cart.get("company", ""),
                "cart_value": float(cart.get("total_value", 0)),
                "email": cart.get("email", ""),
                "phone": cart.get("phone") or cart.get("office_phone", ""),
                "products": [],
            }

            # Parse products - already in JSON format from database
            products = cart.get("products", [])
            if isinstance(products, str):
                try:
                    products = json.loads(products)
                except:
                    products = []

            if isinstance(products, list):
                for item in products:
                    sample["products"].append(
                        {
                            "quantity": int(item.get("quantity", 1)),
                            "item_name": item.get("item_name", "Unknown"),
                            "item_id": item.get("item_id", ""),
                        }
                    )

            samples.append(sample)

        return samples

    def _transform_search_samples(
        self, searches: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Transform search analysis data to template-expected format.

        Groups search events by search term and aggregates statistics including
        total searches, unique sessions, and user details.

        Args:
            searches: List of search analysis task dictionaries from database.

        Returns:
            list[dict[str, Any]]: Transformed search records grouped by term,
                                sorted by search count (top 10).

        Note:
            - Groups multiple search events by search term
            - Calculates unique sessions and user counts
            - Returns top 10 search terms by frequency
        """
        # Group by search term
        term_groups = {}
        for search in searches:
            term = search.get("search_term", "")
            if term not in term_groups:
                term_groups[term] = {
                    "term": term,
                    "total_searches": 0,
                    "unique_sessions": set(),
                    "user_details": [],
                }

            term_groups[term]["total_searches"] += 1
            if search.get("session_id"):
                term_groups[term]["unique_sessions"].add(search["session_id"])

            if search.get("customer_name"):
                term_groups[term]["user_details"].append(
                    {
                        "name": search.get("customer_name", ""),
                        "company": search.get("company", ""),
                        "email": search.get("email", ""),
                        "phone": search.get("phone", ""),
                    }
                )

        # Convert to list format
        samples = []
        for _term, data in term_groups.items():
            samples.append(
                {
                    "term": data["term"],
                    "total_searches": data["total_searches"],
                    "unique_sessions": len(data["unique_sessions"]),
                    "user_details": data["user_details"],
                }
            )

        return sorted(samples, key=lambda x: x["total_searches"], reverse=True)[:10]

    def _transform_repeat_samples(
        self, visits: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Transform repeat visit data to template-expected format.

        Converts database repeat visit records into the structure expected by
        the Jinja2 template, including product detail parsing.

        Args:
            visits: List of repeat visit task dictionaries from database.

        Returns:
            list[dict[str, Any]]: Transformed visit records with template fields.

        Note:
            - Parses JSON product details from database
            - Transforms products to page-like structure for display
            - Limits to top 5 products per visit
        """
        samples = []
        for visit in visits:
            pages_summary = []

            # Parse product details if available
            products_details = visit.get("products_details", [])
            if products_details:
                try:
                    # Ensure it's a list (it should be from the SQL function)
                    if isinstance(products_details, str):
                        products_details = json.loads(products_details)

                    # Transform product details to page-like structure
                    for product in products_details[:5]:  # Take top 5 products
                        if product and isinstance(product, dict):
                            pages_summary.append(
                                {
                                    "count": 1,  # Products are typically viewed once per session
                                    "title": product.get("title", "Unknown Product"),
                                    "url": product.get("url", "#"),
                                    "category": product.get("category", ""),
                                    "price": product.get("price", 0),
                                }
                            )
                except:
                    pass

            sample = {
                "customer": visit.get("customer_name", "Unknown"),
                "email": visit.get("email", ""),
                "company": visit.get("company", ""),
                "pages_viewed": visit.get("page_views_count", 0),
                "pages_summary": pages_summary,
            }

            samples.append(sample)

        return samples
