#!/usr/bin/env python3
"""
Generate branch-wise email reports for sales teams with task summaries
"""

import sqlite3
from urllib.parse import urlparse
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import os
from datetime import datetime
from urllib.parse import urlparse
import htmlmin
from pynliner import Pynliner

DB_PATH = 'db/branch_wise_location.db'

HEAD_CONTENT = """
<style>
    body { font-family: Arial, sans-serif; font-size: 14px; margin: 0; padding: 20px; background-color: #f8f9fa; color: #333; }
    .container { max-width: 1200px; margin: auto; background-color: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
    .header { display: flex; flex-direction: column; align-items: flex-start; border-bottom: 2px solid #dee2e6; padding-bottom: 10px; margin-bottom: 20px; }
    .header h1 { font-size: 24px; margin: 0 0 5px 0; }
    .header p { font-size: 16px; margin: 0; color: #6c757d; }
    h2 { font-size: 22px; border-bottom: 1px solid #eee; padding-bottom: 5px; margin-top: 30px; }
    h4 { font-size: 18px; margin-top: 20px; margin-bottom: 10px; }
    .table { width: 100%; border-collapse: collapse; }
    .table th, .table td { padding: 8px 12px; border: 1px solid #dee2e6; text-align: left; }
    .table th { background-color: #f2f2f2; }
    .text-center { text-align: center; }
    hr { border: 0; border-top: 1px solid #dee2e6; margin: 20px 0; }
    a { color: #007bff; text-decoration: none; }
    a:hover { text-decoration: underline; }
</style>
"""

def create_connection(db_path: str):
    """Get database connection"""
    return sqlite3.connect(db_path)

def get_all_locations(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Get all locations from the database"""
    query = """
    SELECT 
        warehouse_code,
        warehouse_name,
        city,
        state
    FROM locations
    ORDER BY warehouse_code
    """
    
    cursor = conn.execute(query)
    columns = [description[0] for description in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

def fetch_purchase_tasks_by_location(conn: sqlite3.Connection, location_id: str, start_time: int, end_time: int) -> Dict[str, Any]:
    """Fetch all purchase follow-up tasks for a specific location"""
    query = """
    SELECT 
        COUNT(DISTINCT p.param_transaction_id) as total_tasks,
        COUNT(DISTINCT p.user_prop_webuserid) as unique_customers,
        SUM(CAST(p.ecommerce_purchase_revenue AS REAL)) as total_revenue,
        AVG(CAST(p.ecommerce_purchase_revenue AS REAL)) as avg_order_value
    FROM purchase p
    WHERE p.param_transaction_id IS NOT NULL
    AND p.user_prop_default_branch_id = ?
    AND p.event_timestamp BETWEEN ? AND ?
    """
    
    result = conn.execute(query, (location_id, start_time, end_time)).fetchone()
    
    # Get all purchase details for this location
    sample_query = """
    SELECT 
        p.param_transaction_id,
        p.ecommerce_purchase_revenue,
        p.event_timestamp,
        p.items_json,
        u.name as customer_name,
        u.email,
        u.customer_name as company,
        u.office_phone,
        u.cell_phone,
        p.user_prop_default_branch_id,
        l.warehouse_name,
        l.city,
        l.state,
        tt.completed,
        tt.notes,
        p.device_web_info_hostname as hostname
    FROM purchase p
    LEFT JOIN users u ON CAST(p.user_prop_webuserid AS INTEGER) = u.user_id
    LEFT JOIN locations l ON p.user_prop_default_branch_id = l.warehouse_code
    LEFT JOIN task_tracking tt ON tt.task_id = ('purchase_' || p.param_transaction_id) AND tt.task_type = 'purchase'
    WHERE p.param_transaction_id IS NOT NULL
    AND p.user_prop_default_branch_id = ?
    AND p.event_timestamp BETWEEN ? AND ?
    ORDER BY p.ecommerce_purchase_revenue DESC
    """
    
    samples = conn.execute(sample_query, (location_id, start_time, end_time)).fetchall()
    
    return {
        'total': result[0] or 0,
        'unique_customers': result[1] or 0,
        'total_revenue': result[2] or 0,
        'avg_order_value': result[3] or 0,
        'samples': samples
    }

def fetch_cart_abandonment_tasks_by_location(conn: sqlite3.Connection, location_id: str, start_time: int, end_time: int) -> Dict[str, Any]:
    """Fetch cart abandonment tasks for a specific location"""
    query = """
    WITH abandoned_carts AS (
        SELECT DISTINCT
            ac.param_ga_session_id,
            ac.user_prop_webuserid,
            COUNT(DISTINCT ac.first_item_item_id) as items_count,
            SUM(CAST(ac.first_item_price AS REAL) * CAST(ac.first_item_quantity AS INTEGER)) as cart_value
        FROM add_to_cart ac
        WHERE ac.param_ga_session_id NOT IN (
            SELECT DISTINCT param_ga_session_id FROM purchase WHERE param_ga_session_id IS NOT NULL
        )
        AND ac.user_prop_default_branch_id = ?
        AND ac.event_timestamp BETWEEN ? AND ?
        GROUP BY ac.param_ga_session_id, ac.user_prop_webuserid
    )
    SELECT 
        COUNT(*) as total_tasks,
        COUNT(DISTINCT user_prop_webuserid) as unique_customers,
        SUM(cart_value) as total_abandoned_value,
        AVG(cart_value) as avg_cart_value
    FROM abandoned_carts
    """
    
    result = conn.execute(query, (location_id, start_time, end_time)).fetchone()
    
    # Get sample abandoned carts with more details including items_json
    sample_query = """
    SELECT 
        ac.param_ga_session_id,
        u.name as customer_name,
        u.email,
        u.customer_name as company,
        u.office_phone,
        u.cell_phone,
        COUNT(DISTINCT ac.first_item_item_id) as items_count,
        SUM(CAST(ac.first_item_price AS REAL) * CAST(ac.first_item_quantity AS INTEGER)) as cart_value,
        MAX(ac.event_timestamp) as last_activity,
        GROUP_CONCAT(ac.items_json, '||SEPARATOR||') as all_items_json,
        tt.completed,
        tt.notes,
        ac.device_web_info_hostname as hostname
    FROM add_to_cart ac
    LEFT JOIN users u ON CAST(ac.user_prop_webuserid AS INTEGER) = u.user_id
    LEFT JOIN task_tracking tt ON tt.task_id = ('cart_' || ac.param_ga_session_id) AND tt.task_type = 'cart'
    WHERE ac.param_ga_session_id NOT IN (
        SELECT DISTINCT param_ga_session_id FROM purchase WHERE param_ga_session_id IS NOT NULL
    )
    AND ac.user_prop_default_branch_id = ?
    AND ac.event_timestamp BETWEEN ? AND ?
    GROUP BY ac.param_ga_session_id, ac.user_prop_webuserid, u.name, u.email, u.customer_name, u.office_phone, u.cell_phone, tt.completed, tt.notes, ac.device_web_info_hostname
    ORDER BY cart_value DESC
    LIMIT 10
    """
    
    samples = conn.execute(sample_query, (location_id, start_time, end_time)).fetchall()
    
    return {
        'total': result[0] or 0,
        'unique_customers': result[1] or 0,
        'total_value': result[2] or 0,
        'avg_value': result[3] or 0,
        'samples': samples
    }

def fetch_search_no_results_tasks_by_location(conn: sqlite3.Connection, location_id: str, start_time: int, end_time: int) -> Dict[str, Any]:
    """Fetch search with no results tasks for a specific location"""
    query = """
    SELECT 
        COUNT(DISTINCT param_no_search_results_term) as unique_terms,
        COUNT(*) as total_searches,
        COUNT(DISTINCT param_ga_session_id) as affected_sessions,
        COUNT(DISTINCT user_prop_webuserid) as unique_users
    FROM no_search_results
    WHERE param_no_search_results_term IS NOT NULL
    AND user_prop_default_branch_id = ?
    AND event_timestamp BETWEEN ? AND ?
    """
    
    result = conn.execute(query, (location_id, start_time, end_time)).fetchone()
    
    # Get failed searches grouped by term with user details
    sample_query = """
    SELECT
        s.param_no_search_results_term,
        COUNT(s.param_no_search_results_term) as total_searches,
        COUNT(DISTINCT s.param_ga_session_id) as unique_sessions,
        '[' || GROUP_CONCAT(DISTINCT json_object('name', u.name, 'company', u.customer_name, 'email', u.email, 'phone', COALESCE(u.cell_phone, u.office_phone, ''))) || ']' as user_details_json
    FROM no_search_results s
    LEFT JOIN users u ON CAST(s.user_prop_webuserid AS INTEGER) = u.user_id
    WHERE s.user_prop_default_branch_id = ? AND s.param_no_search_results_term IS NOT NULL
    AND s.event_timestamp BETWEEN ? AND ?
    GROUP BY s.param_no_search_results_term
    ORDER BY total_searches DESC
    LIMIT 10
    """
    
    samples = conn.execute(sample_query, (location_id, start_time, end_time)).fetchall()
    
    return {
        'unique_terms': result[0] or 0,
        'total_searches': result[1] or 0,
        'affected_sessions': result[2] or 0,
        'unique_users': result[3] or 0,
        'samples': samples
    }

def fetch_repeat_visits_tasks_by_location(conn: sqlite3.Connection, location_id: str, start_time: int, end_time: int) -> Dict[str, Any]:
    """Fetch repeat visits without purchase tasks for a specific location"""
    query = """
    WITH repeat_visitors AS (
        SELECT 
            pv.param_ga_session_id,
            COUNT(DISTINCT pv.param_page_location) as pages_viewed
        FROM page_view pv
        WHERE pv.param_ga_session_id NOT IN (
            SELECT DISTINCT param_ga_session_id FROM purchase
        )
        AND pv.user_prop_default_branch_id = ?
        AND pv.event_timestamp BETWEEN ? AND ?
        GROUP BY pv.param_ga_session_id
        HAVING pages_viewed >= 3
    )
    SELECT 
        COUNT(*) as total_sessions,
        AVG(pages_viewed) as avg_pages_viewed
    FROM repeat_visitors
    """
    
    result = conn.execute(query, (location_id, start_time, end_time)).fetchone()
    
    # Get sample repeat visitors
    sample_query = """
    SELECT 
        pv.param_ga_session_id,
        u.name as customer_name,
        u.email,
        u.customer_name as company,
        COUNT(DISTINCT pv.param_page_location) as pages_viewed,
        MAX(pv.event_timestamp) as last_visit,
        '[' || GROUP_CONCAT(DISTINCT json_object('title', pv.param_page_title, 'url', pv.param_page_location)) || ']' as pages_visited_json,
        tt.completed,
        tt.notes
    FROM page_view pv
    LEFT JOIN users u ON CAST(pv.user_prop_webuserid AS INTEGER) = u.user_id
    LEFT JOIN task_tracking tt ON tt.task_id = ('REPEAT_' || pv.param_ga_session_id || '_' || CAST(u.user_id AS TEXT)) AND tt.task_type = 'visit'
    WHERE pv.param_ga_session_id NOT IN (
        SELECT DISTINCT param_ga_session_id FROM purchase
    )
    AND pv.user_prop_webuserid IS NOT NULL
    AND pv.user_prop_default_branch_id = ?
    AND pv.event_timestamp BETWEEN ? AND ?
    GROUP BY pv.param_ga_session_id, u.user_id, tt.completed, tt.notes
    HAVING pages_viewed >= 3
    ORDER BY pages_viewed DESC
    LIMIT 10
    """
    
    samples = conn.execute(sample_query, (location_id, start_time, end_time)).fetchall()
    
    return {
        'total': result[0] or 0,
        'avg_pages': result[1] or 0,
        'samples': samples
    }

def get_unique_dates(conn: sqlite3.Connection) -> List[str]:
    """Get all unique dates with events in the database"""
    query = """
    SELECT DISTINCT date(datetime(event_timestamp / 1000000, 'unixepoch')) as event_date
    FROM (
        SELECT event_timestamp FROM purchase
        UNION SELECT event_timestamp FROM add_to_cart
        UNION SELECT event_timestamp FROM no_search_results
        UNION SELECT event_timestamp FROM page_view
    ) t
    WHERE event_timestamp IS NOT NULL
    ORDER BY event_date
    """
    cursor = conn.execute(query)
    return [row[0] for row in cursor.fetchall()]

def parse_items_json(items_json: str) -> List[Dict]:
    """Parse items JSON and return list of products"""
    try:
        if items_json:
            items = json.loads(items_json)
            return items if isinstance(items, list) else []
    except:
        return []
    return []

def generate_location_section(location: Dict[str, Any], data: Dict[str, Any]) -> str:
    """Generate HTML section for a specific location"""
    
    location_name = f"{location['warehouse_name']} - {location['city']}, {location['state']}"
    location_code = location['warehouse_code']
    
    # Skip if no data for this location
    if (data['purchases']['total'] == 0 and 
        data['cart_abandonment']['total'] == 0 and 
        data['search_no_results']['total_searches'] == 0 and 
        data['repeat_visits']['total'] == 0):
        return ""
    
    html = f"""
            <!-- Location Summary Table -->
            <div>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Metric</th>
                            <th>Count</th>
                            <th>Value/Details</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Purchases</td>
                            <td>{data['purchases']['total']}</td>
                            <td>${data['purchases']['total_revenue']:.2f} total revenue</td>
                        </tr>
                        <tr>
                            <td>Cart Abandonments</td>
                            <td>{data['cart_abandonment']['total']}</td>
                            <td>${data['cart_abandonment']['total_value']:.2f} at risk</td>
                        </tr>
                        <tr>
                            <td>Failed Searches</td>
                            <td>{data['search_no_results']['unique_terms']}</td>
                            <td>{data['search_no_results']['total_searches']} total searches</td>
                        </tr>
                        <tr>
                            <td>Repeat Visits (No Purchase)</td>
                            <td>{data['repeat_visits']['total']}</td>
                            <td>{data['repeat_visits']['avg_pages']:.1f} avg pages viewed</td>
                        </tr>
                    </tbody>
                </table>
            </div>
    """
    
    # Add purchase details if any
    if data['purchases']['total'] > 0:
        html += f"""
            <h4>Purchase Follow-up Tasks</h4>
            <div>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Customer Details</th>
                            <th>Products</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for sample in data['purchases']['samples']:
            customer_name = sample[4] or 'Unknown'
            company_name = sample[6] or ''
            revenue = float(sample[1]) if sample[1] else 0
            trans_id = sample[0] or '-'
            email = sample[5] or ''
            phone = sample[7] or sample[8] or ''
            items_json = sample[3]

            customer_details_parts = [customer_name]
            if company_name:
                customer_details_parts.append(company_name)
            customer_details_parts.append(f"ID: {trans_id}")
            customer_details_parts.append(f"Total: ${revenue:.2f}")
            if email:
                customer_details_parts.append(f"Contact: <a href='mailto:{email}'>{email}</a>")
            if phone:
                customer_details_parts.append(phone)
            customer_details = "<br>".join(customer_details_parts)

            product_details = []
            if items_json:
                try:
                    items = json.loads(items_json)
                    for item in items:
                        item_name = item.get('item_name', 'N/A')
                        quantity = int(item.get('quantity', 1))
                        item_id = item.get('item_id', '')
                        if item_id != '':
                            product_details.append(f"{quantity} x {item_name} ({item_id})")
                        else:
                            product_details.append(f"{quantity} x {item_name}")
                except (json.JSONDecodeError, TypeError):
                    product_details.append("Error parsing items")
            
            products_str = "<br>".join(product_details) if product_details else "N/A"

            html += f"""
                        <tr>
                            <td>{customer_details}</td>
                            <td>{products_str}</td>
                        </tr>
            """
            
        html += """
                    </tbody>
                </table>
            </div>
        """
        
    # Add cart abandonment details if any
    if data['cart_abandonment']['total'] > 0:
        html += f"""
            <h4>Cart Abandonment Recovery Tasks</h4>
            <div>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Customer Details</th>
                            <th>Products</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for sample in data['cart_abandonment']['samples']:
            cart_id = sample[0]
            customer_name = sample[1] or 'Unknown'
            email = sample[2] or ''
            company_name = sample[3] or ''
            office_phone = sample[4] or ''
            cell_phone = sample[5] or ''
            cart_value = float(sample[7]) if sample[7] else 0
            items_json = sample[9]  # Corrected index for all_items_json
            phone = cell_phone or office_phone

            customer_details_parts = [customer_name]
            if company_name:
                customer_details_parts.append(company_name)
            customer_details_parts.append(f"Cart ID: {cart_id}")
            customer_details_parts.append(f"Cart Value: ${cart_value:.2f}")
            if email:
                customer_details_parts.append(f"Contact: <a href='mailto:{email}'>{email}</a>")
            if phone:
                customer_details_parts.append(phone)
            customer_details = "<br>".join(customer_details_parts)

            product_details = []
            if items_json:
                # Handle concatenated JSON strings from GROUP_CONCAT
                cart_items = []
                json_parts = items_json.split('||SEPARATOR||')
                for json_part in json_parts:
                    if json_part and json_part.strip() and json_part != 'null':
                        try:
                            items = json.loads(json_part)
                            if isinstance(items, list):
                                cart_items.extend(items)
                        except (json.JSONDecodeError, TypeError):
                            continue  # Ignore parts that fail to parse
                
                # Aggregate quantities for unique items
                unique_items = {}
                for item in cart_items:
                    item_key = (item.get('item_id'), item.get('item_name'))
                    if item_key in unique_items:
                        unique_items[item_key]['quantity'] = unique_items[item_key].get('quantity', 0) + int(item.get('quantity', 1))
                    else:
                        unique_items[item_key] = item.copy()
                        unique_items[item_key]['quantity'] = int(item.get('quantity', 1))

                for item in unique_items.values():
                    item_name = item.get('item_name', 'N/A')
                    quantity = item.get('quantity', 1)
                    item_id = item.get('item_id', '')
                    if item_id != '':
                        product_details.append(f"{quantity} x {item_name} ({item_id})")
                    else:
                        product_details.append(f"{quantity} x {item_name}")

            if not product_details:
                product_details.append("N/A")

            products_str = "<br>".join(product_details)

            html += f"""
                        <tr>
                            <td>{customer_details}</td>
                            <td>{products_str}</td>
                        </tr>
            """
            
        html += """
                    </tbody>
                </table>
            </div>
        """
    
    # Add failed searches if any
    if data['search_no_results']['total_searches'] > 0:
        html += f"""
            <h4>Failed Search Recovery Tasks</h4>
            <div>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Search Details</th>
                            <th>Customers</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for sample in data['search_no_results']['samples']:
            term = sample[0] or '-'
            total_searches = sample[1] or 0
            unique_sessions = sample[2] or 0
            user_details_json = sample[3] or '[]'
            
            search_details = f"<strong>Term:</strong> {term}<br><strong>Total Searches:</strong> {total_searches}<br><strong>Unique Sessions:</strong> {unique_sessions}"
            
            customers_html_parts = []
            try:
                user_details = json.loads(user_details_json)
                if not user_details or not any(user_details):
                    customers_html_parts.append("No user details available")
                else:
                    for user in user_details:
                        if not user or not user.get('name'): continue
                        user_name = user.get('name') or 'Unknown'
                        company = user.get('company') or ''
                        email = user.get('email') or ''
                        phone = user.get('phone') or ''
                        
                        customer_str_parts = [user_name]
                        if company:
                            customer_str_parts.append(company)
                        if email:
                            customer_str_parts.append(f"<a href='mailto:{email}'>{email}</a>")
                        if phone:
                            customer_str_parts.append(phone)
                        customers_html_parts.append("<br>".join(customer_str_parts))
            except json.JSONDecodeError:
                customers_html_parts.append("Error parsing user details")
                
            customers_html = "<hr style='margin: 5px 0;'>".join(customers_html_parts)
            
            html += f"""
                        <tr>
                            <td>{search_details}</td>
                            <td>{customers_html}</td>
                        </tr>
            """
            
        html += """
                    </tbody>
                </table>
            </div>
        """
    # Add repeat visits if any
    if data['repeat_visits']['total'] > 0:
        html += f"""
            <h4>Repeat Visit Conversion Tasks</h4>
            <div>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Customer Details</th>
                            <th>Visited Pages (Top 5 by Base URL)</th>
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for sample in data['repeat_visits']['samples']:
            customer = sample[1] or 'Unknown'
            email = sample[2] or ''
            company = sample[3] or '-'
            pages_viewed = sample[4] or 0
            last_visit_raw = sample[5]
            last_visit = datetime.fromtimestamp(int(last_visit_raw) / 1000000).strftime('%Y-%m-%d') if last_visit_raw else 'N/A'
            pages_visited_json = sample[6] or ''

            customer_details_parts = [customer]
            if company and company != '-':
                customer_details_parts.append(company)
            customer_details_parts.append(f"Pages Viewed: {pages_viewed}")
            if email:
                customer_details_parts.append(f"Contact: <a href='mailto:{email}'>{email}</a>")
            customer_details = "<br>".join(customer_details_parts)

            pages_summary_parts = []
            if pages_visited_json:
                try:
                    pages_data = json.loads(pages_visited_json)
                    base_url_counts = {}

                    for page in pages_data:
                        if page and page.get('title') and page.get('url'):
                            url = page['url']
                            parsed_url = urlparse(url)
                            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
                            
                            if base_url not in base_url_counts:
                                base_url_counts[base_url] = {'count': 0, 'titles': set()}
                            
                            base_url_counts[base_url]['count'] += 1
                            base_url_counts[base_url]['titles'].add(page['title'])

                    sorted_bases = sorted(base_url_counts.items(), key=lambda item: item[1]['count'], reverse=True)

                    for base_url, data in sorted_bases:
                        count = data['count']
                        title_text = ", ".join(list(data['titles'])[:2])
                        if len(data['titles']) > 2:
                            title_text += "..."
                        
                        pages_summary_parts.append(f"{count}x <a href='{base_url}' target='_blank'>{title_text}</a>")

                except (json.JSONDecodeError, TypeError):
                    pages_summary_parts.append("Could not parse visited pages data.")

            pages_summary = "<br>".join(pages_summary_parts) if pages_summary_parts else "N/A"

            html += f"""
                        <tr>
                            <td>{customer_details}</td>
                            <td>{pages_summary}</td>
                        </tr>
            """
            
        html += """
                    </tbody>
                </table>
            </div>
        """
    
    html += """
        <hr class="my-5">
    """
    
    return html

def generate_branch_wise_report(conn: sqlite3.Connection, report_date_str: str) -> str:
    """Generate HTML email report organized by branch/location"""
    
    report_date = datetime.strptime(report_date_str, '%Y-%m-%d')
    start_time = int(report_date.timestamp() * 1000000)
    end_time = int((report_date + timedelta(days=1)).timestamp() * 1000000) - 1
    
    # Get all locations
    locations = get_all_locations(conn)
    
    # Start HTML
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Branch-wise Sales Task Report - {report_date.strftime("%B %d, %Y")}</title>
    {HEAD_CONTENT}
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Branch-wise Sales Task Report</h1>
            <p>Report Date: {report_date.strftime("%B %d, %Y")}</p>
        </div>
    """
    
    # Add overall summary
    overall_stats = {
        'total_purchases': 0,
        'total_revenue': 0,
        'total_carts': 0,
        'total_cart_value': 0,
        'total_searches': 0,
        'total_repeat_visits': 0
    }
    
    # Generate sections for each location
    all_sections = []
    for location in locations:
        # Fetch data for this location
        location_data = {
            'purchases': fetch_purchase_tasks_by_location(conn, location['warehouse_code'], start_time, end_time),
            'cart_abandonment': fetch_cart_abandonment_tasks_by_location(conn, location['warehouse_code'], start_time, end_time),
            'search_no_results': fetch_search_no_results_tasks_by_location(conn, location['warehouse_code'], start_time, end_time),
            'repeat_visits': fetch_repeat_visits_tasks_by_location(conn, location['warehouse_code'], start_time, end_time)
        }
        
        # Update overall stats
        overall_stats['total_purchases'] += location_data['purchases']['total']
        overall_stats['total_revenue'] += location_data['purchases']['total_revenue']
        overall_stats['total_carts'] += location_data['cart_abandonment']['total']
        overall_stats['total_cart_value'] += location_data['cart_abandonment']['total_value']
        overall_stats['total_searches'] += location_data['search_no_results']['total_searches']
        overall_stats['total_repeat_visits'] += location_data['repeat_visits']['total']
        
        # Generate section for this location
        section = generate_location_section(location, location_data)
        if section:  # Only add if there's data
            all_sections.append(section)
    
    # Add overall summary
    html += f"""
        <div>
            <h2>Overall Summary - All Branches for {report_date.strftime("%Y-%m-%d")}</h2>
            <div>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Metric</th>
                            <th>Total Count</th>
                            <th>Total Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Total Purchases</td>
                            <td>{overall_stats['total_purchases']}</td>
                            <td>${overall_stats['total_revenue']:.2f}</td>
                        </tr>
                        <tr>
                            <td>Total Cart Abandonments</td>
                            <td>{overall_stats['total_carts']}</td>
                            <td>${overall_stats['total_cart_value']:.2f}</td>
                        </tr>
                        <tr>
                            <td>Total Failed Searches</td>
                            <td>{overall_stats['total_searches']}</td>
                            <td>-</td>
                        </tr>
                        <tr>
                            <td>Total Repeat Visits (No Purchase)</td>
                            <td>{overall_stats['total_repeat_visits']}</td>
                            <td>-</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    """
    
    # Add all location sections
    for section in all_sections:
        html += section
    
    # Add footer
    html += f"""
        <div class="mt-5 pt-3 border-top text-muted">
            <p><strong>Report Generated:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <p>This is an automated branch-wise report from the Impax Sales Intelligence System.</p>
            <p>This report covers activity on {report_date.strftime("%Y-%m-%d")}.</p>
            <p><em>Click on rows with ▶ to expand and see detailed information.</em></p>
            <p><strong>Note:</strong> Status and notes functionality are for demonstration. Actual updates should be done through the dashboard.</p>
        </div>
    </div>
</body>
</html>
    """
    
    # Inline CSS
    p = Pynliner()
    inlined_html = p.from_string(html).run()
    inlined_html = htmlmin.minify(inlined_html, remove_empty_space=True)

    return inlined_html

def main():
    """Main function to generate the branch-wise email report"""
    # Create reports directory if it doesn't exist
    if not os.path.exists('branch_reports'):
        os.makedirs('branch_reports')

    conn = create_connection(DB_PATH)
    if conn is not None:
        try:
            unique_dates = get_unique_dates(conn)
            if not unique_dates:
                print("No data dates found in database")
                return

            latest_date = max(unique_dates)
            yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

            for date_str in unique_dates:
                report_date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                report_fmt = report_date_obj.strftime('%Y%m%d')

                combined_filename = f"branch_reports/D_All_report_{report_fmt}.html"
                if os.path.exists(combined_filename):
                    print(f"Combined report already exists for {date_str}")
                    continue

                if date_str == latest_date and date_str != yesterday_str:
                    print(f"Skipping generation for latest date {date_str} as it is not yesterday")
                    continue

                # Generate combined report
                html_report = generate_branch_wise_report(conn, date_str)
                with open(combined_filename, 'w', encoding='utf-8') as f:
                    f.write(html_report)
                print(f"Generated combined report for {date_str}: {combined_filename}")

                # Generate individual reports
                locations = get_all_locations(conn)
                start_time = int(report_date_obj.timestamp() * 1000000)
                end_time = int((report_date_obj + timedelta(days=1)).timestamp() * 1000000) - 1

                for location in locations:
                    location_data = {
                        'purchases': fetch_purchase_tasks_by_location(conn, location['warehouse_code'], start_time, end_time),
                        'cart_abandonment': fetch_cart_abandonment_tasks_by_location(conn, location['warehouse_code'], start_time, end_time),
                        'search_no_results': fetch_search_no_results_tasks_by_location(conn, location['warehouse_code'], start_time, end_time),
                        'repeat_visits': fetch_repeat_visits_tasks_by_location(conn, location['warehouse_code'], start_time, end_time)
                    }

                    # Skip if no data for this location
                    if (location_data['purchases']['total'] == 0 and 
                        location_data['cart_abandonment']['total'] == 0 and 
                        location_data['search_no_results']['total_searches'] == 0 and 
                        location_data['repeat_visits']['total'] == 0):
                        continue

                    individual_filename = f"branch_reports/{location['warehouse_code']}_report_{report_fmt}.html"
                    if os.path.exists(individual_filename):
                        print(f"Individual report already exists for {location['warehouse_code']} on {date_str}")
                        continue

                    p = Pynliner()
                    individual_html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{location['warehouse_name']} Report - {report_date_obj.strftime('%B %d, %Y')}</title>
    {HEAD_CONTENT}
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{location['warehouse_name']} - {location['city']}, {location['state']}</h1>
            <p>Report for: {report_date_obj.strftime('%B %d, %Y')}</p>
        </div>
        {generate_location_section(location, location_data)}
        <div class="mt-5 pt-3 border-top text-muted">
            <p><strong>Report Generated:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <p>This report covers activity on {report_date_obj.strftime("%Y-%m-%d")}.</p>
        </div>
    </div>
</body>
</html>
                    """
                    
                    inlined_html = p.from_string(individual_html_template).run()
                    minified_html = htmlmin.minify(inlined_html, remove_empty_space=True)
                    with open(individual_filename, 'w', encoding='utf-8') as f:
                        f.write(minified_html)
                    print(f"Generated individual report for {location['warehouse_code']} on {date_str}: {individual_filename}")

        finally:
            conn.close()

if __name__ == '__main__':
    main()