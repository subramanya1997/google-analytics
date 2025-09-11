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
                    "state": location.get("state", "")
                },
                "report_date": report_data.get("report_date"),
                "datetime": datetime,  # Pass datetime module for template use
                "data": {
                    "purchases": {
                        "total": summary.get("total_purchases", 0),
                        "total_revenue": summary.get("total_revenue", 0),
                        "unique_customers": len(set(p.get("user_id", "") for p in tasks.get("purchases", []) if p.get("user_id"))),
                        "avg_order_value": summary.get("total_revenue", 0) / max(summary.get("total_purchases", 1), 1),
                        "samples": self._transform_purchase_samples(tasks.get("purchases", []))
                    },
                    "cart_abandonment": {
                        "total": summary.get("total_cart_abandonment", 0),
                        "unique_customers": len(set(c.get("user_id", "") for c in tasks.get("cart_abandonment", []) if c.get("user_id"))),
                        "total_value": sum(float(c.get("cart_value", 0)) for c in tasks.get("cart_abandonment", [])),
                        "avg_value": sum(float(c.get("cart_value", 0)) for c in tasks.get("cart_abandonment", [])) / max(summary.get("total_cart_abandonment", 1), 1),
                        "samples": self._transform_cart_samples(tasks.get("cart_abandonment", []))
                    },
                    "search_no_results": {
                        "unique_terms": summary.get("total_search_issues", 0),
                        "total_searches": sum(s.get("search_count", 0) for s in tasks.get("search_analysis", [])),
                        "affected_sessions": len(set(s.get("session_id", "") for s in tasks.get("search_analysis", []) if s.get("session_id"))),
                        "unique_users": len(set(s.get("user_id", "") for s in tasks.get("search_analysis", []) if s.get("user_id"))),
                        "samples": self._transform_search_samples(tasks.get("search_analysis", []))
                    },
                    "repeat_visits": {
                        "total": summary.get("total_repeat_visits", 0),
                        "avg_pages": sum(r.get("pages_viewed", 0) for r in tasks.get("repeat_visits", [])) / max(summary.get("total_repeat_visits", 1), 1),
                        "samples": self._transform_repeat_samples(tasks.get("repeat_visits", []))
                    }
                }
            }
            
            html_content = template.render(**template_data)
            return html_content
            
        except Exception as e:
            logger.error(f"Error rendering branch report template: {e}")
            # Return fallback HTML
            return self._render_fallback_branch_report(report_data)


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


    def _transform_purchase_samples(self, purchases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform purchase data to match template format."""
        samples = []
        for purchase in purchases:
            sample = {
                "customer_name": purchase.get("customer_name", "Unknown"),
                "company_name": purchase.get("company", ""),  # May need to get from user data
                "trans_id": purchase.get("transaction_id", ""),
                "revenue": float(purchase.get("order_value", 0)),
                "email": purchase.get("email", ""),
                "phone": purchase.get("phone") or purchase.get("office_phone", ""),
                "products": []
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
                    sample["products"].append({
                        "quantity": int(item.get("quantity", 1)),
                        "item_name": item.get("item_name", "Unknown"),
                        "item_id": item.get("item_id", "")
                    })
            
            samples.append(sample)
        
        return samples

    def _transform_cart_samples(self, carts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform cart abandonment data to match template format."""
        samples = []
        for cart in carts:
            sample = {
                "cart_id": cart.get("session_id", ""),
                "customer_name": cart.get("customer_name", "Unknown"),
                "company_name": cart.get("company", ""),  # May need to get from user data
                "cart_value": float(cart.get("total_value", 0)),
                "email": cart.get("email", ""),
                "phone": cart.get("phone") or cart.get("office_phone", ""),
                "products": []
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
                    sample["products"].append({
                        "quantity": int(item.get("quantity", 1)),
                        "item_name": item.get("item_name", "Unknown"),
                        "item_id": item.get("item_id", "")
                    })
            
            samples.append(sample)
        
        return samples

    def _transform_search_samples(self, searches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform search data to match template format."""
        # Group by search term
        term_groups = {}
        for search in searches:
            term = search.get("search_term", "")
            if term not in term_groups:
                term_groups[term] = {
                    "term": term,
                    "total_searches": 0,
                    "unique_sessions": set(),
                    "user_details": []
                }
            
            term_groups[term]["total_searches"] += 1
            if search.get("session_id"):
                term_groups[term]["unique_sessions"].add(search["session_id"])
            
            if search.get("customer_name"):
                term_groups[term]["user_details"].append({
                    "name": search.get("customer_name", ""),
                    "company": search.get("company", ""),
                    "email": search.get("email", ""),
                    "phone": search.get("phone", "")
                })
        
        # Convert to list format
        samples = []
        for term, data in term_groups.items():
            samples.append({
                "term": data["term"],
                "total_searches": data["total_searches"],
                "unique_sessions": len(data["unique_sessions"]),
                "user_details": data["user_details"]
            })
        
        return sorted(samples, key=lambda x: x["total_searches"], reverse=True)[:10]

    def _transform_repeat_samples(self, visits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform repeat visit data to match template format."""
        samples = []
        for visit in visits:
            pages_summary = []
            
            # Parse visited pages if available
            pages_json = visit.get("pages_json", "")
            if pages_json:
                try:
                    pages = json.loads(pages_json) if isinstance(pages_json, str) else pages_json
                    # Group by URL
                    url_counts = {}
                    for page in pages:
                        url = page.get("url", "")
                        title = page.get("title", "Unknown")
                        if url not in url_counts:
                            url_counts[url] = {"count": 0, "title": title, "url": url}
                        url_counts[url]["count"] += 1
                    
                    # Sort by count and take top 5
                    pages_summary = sorted(
                        url_counts.values(), 
                        key=lambda x: x["count"], 
                        reverse=True
                    )[:5]
                except:
                    pass
            
            sample = {
                "customer": visit.get("customer_name", "Unknown"),
                "email": visit.get("email", ""),
                "company": visit.get("company", ""),
                "pages_viewed": visit.get("pages_viewed", 0),
                "pages_summary": pages_summary
            }
            
            samples.append(sample)
        
        return samples
