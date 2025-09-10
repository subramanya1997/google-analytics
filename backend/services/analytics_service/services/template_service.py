"""
Template service for rendering HTML reports using Jinja2
"""

import json
from datetime import datetime
from typing import Any, Dict, List
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from loguru import logger


class TemplateService:
    """Service for rendering HTML templates."""

    def __init__(self):
        """Initialize template service with Jinja2 environment."""
        # Get templates directory relative to this file
        templates_dir = Path(__file__).parent.parent / "templates"
        
        # Create templates directory if it doesn't exist
        templates_dir.mkdir(exist_ok=True)
        
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=True
        )
        
        # Add custom filters
        self.env.filters['currency'] = self._currency_filter
        self.env.filters['date_format'] = self._date_format_filter
        self.env.filters['json_parse'] = self._json_parse_filter

    def render_branch_report(self, report_data: Dict[str, Any]) -> str:
        """
        Render branch report HTML template.
        
        Args:
            report_data: Report data containing location, tasks, etc.
            
        Returns:
            Rendered HTML content
        """
        try:
            template = self.env.get_template('branch_report.html')
            html_content = template.render(**report_data)
            return html_content
            
        except Exception as e:
            logger.error(f"Error rendering branch report template: {e}")
            # Return fallback HTML
            return self._render_fallback_branch_report(report_data)

    def render_combined_report(self, combined_data: Dict[str, Any]) -> str:
        """
        Render combined report HTML template.
        
        Args:
            combined_data: Combined report data with multiple branches
            
        Returns:
            Rendered HTML content
        """
        try:
            template = self.env.get_template('combined_report.html')
            html_content = template.render(**combined_data)
            return html_content
            
        except Exception as e:
            logger.error(f"Error rendering combined report template: {e}")
            # Return fallback HTML
            return self._render_fallback_combined_report(combined_data)

    def _currency_filter(self, value: Any) -> str:
        """Format value as currency."""
        try:
            if isinstance(value, str):
                # Already formatted
                if value.startswith('$'):
                    return value
                # Convert string to float
                clean_value = value.replace('$', '').replace(',', '').strip()
                value = float(clean_value) if clean_value else 0.0
            elif not isinstance(value, (int, float)):
                value = 0.0
            
            return f"${value:,.2f}"
        except:
            return str(value)

    def _date_format_filter(self, value: Any, format: str = '%Y-%m-%d') -> str:
        """Format date value."""
        try:
            if isinstance(value, datetime):
                return value.strftime(format)
            elif isinstance(value, str):
                # Try to parse string date
                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                return dt.strftime(format)
            else:
                return str(value)
        except:
            return str(value)

    def _json_parse_filter(self, value: str) -> List[Dict[str, Any]]:
        """Parse JSON string to Python object."""
        try:
            if isinstance(value, str):
                return json.loads(value)
            return value
        except:
            return []

    def _render_fallback_branch_report(self, report_data: Dict[str, Any]) -> str:
        """Render fallback HTML when template fails."""
        location = report_data.get("location", {})
        location_name = location.get("locationName", "Unknown Branch")
        city = location.get("city", "")
        state = location.get("state", "")
        
        location_display = f"{location_name}"
        if city or state:
            location_display += f" - {city}, {state}"
        
        report_date = report_data.get("report_date", datetime.now().date())
        summary = report_data.get("summary", {})
        
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
                <div class="value">{summary.get('total_purchases', 0)}</div>
            </div>
            <div class="metric">
                <h3>Total Revenue</h3>
                <div class="value">${summary.get('total_revenue', 0):,.2f}</div>
            </div>
            <div class="metric">
                <h3>Cart Abandonment</h3>
                <div class="value">{summary.get('total_cart_abandonment', 0)}</div>
            </div>
            <div class="metric">
                <h3>Search Issues</h3>
                <div class="value">{summary.get('total_search_issues', 0)}</div>
            </div>
        </div>
        
        <div class="tasks-section">
            <h2>Sales Tasks Summary</h2>
            <div class="task-list">
                <p><strong>Purchase Follow-ups:</strong> {summary.get('total_purchases', 0)} customers need follow-up contact</p>
                <p><strong>Cart Recovery:</strong> {summary.get('total_cart_abandonment', 0)} abandoned carts to recover</p>
                <p><strong>Search Analysis:</strong> {summary.get('total_search_issues', 0)} search terms need attention</p>
                <p><strong>Repeat Visitors:</strong> {summary.get('total_repeat_visits', 0)} high-engagement visitors to contact</p>
            </div>
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

    def _render_fallback_combined_report(self, combined_data: Dict[str, Any]) -> str:
        """Render fallback HTML for combined report when template fails."""
        report_date = combined_data.get("report_date", datetime.now().date())
        branches = combined_data.get("branches", [])
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Combined Sales Report - {report_date}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f8f9fa; }}
        .container {{ max-width: 900px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; border-bottom: 2px solid #dee2e6; padding-bottom: 20px; margin-bottom: 30px; }}
        .branch-report {{ margin-bottom: 40px; padding: 20px; border: 1px solid #dee2e6; border-radius: 8px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Combined Branch Sales Report</h1>
            <p>Report Date: {report_date}</p>
            <p>Total Branches: {len(branches)}</p>
        </div>
        
        {"".join(f'<div class="branch-report">{branch["html"]}</div>' for branch in branches)}
        
        <div style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; color: #666;">
            <p>Combined report generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
"""
        return html
