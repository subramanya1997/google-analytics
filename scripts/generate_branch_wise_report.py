#!/usr/bin/env python3
"""
Generate branch-wise email reports for sales teams with task summaries
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import os
import argparse

def get_db_connection(db_path: str):
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

def fetch_purchase_tasks_by_location(conn: sqlite3.Connection, location_id: str) -> Dict[str, Any]:
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
    """
    
    result = conn.execute(query, (location_id,)).fetchone()
    
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
    ORDER BY p.ecommerce_purchase_revenue DESC
    """
    
    samples = conn.execute(sample_query, (location_id,)).fetchall()
    
    return {
        'total': result[0] or 0,
        'unique_customers': result[1] or 0,
        'total_revenue': result[2] or 0,
        'avg_order_value': result[3] or 0,
        'samples': samples
    }

def fetch_cart_abandonment_tasks_by_location(conn: sqlite3.Connection, location_id: str) -> Dict[str, Any]:
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
        GROUP BY ac.param_ga_session_id, ac.user_prop_webuserid
    )
    SELECT 
        COUNT(*) as total_tasks,
        COUNT(DISTINCT user_prop_webuserid) as unique_customers,
        SUM(cart_value) as total_abandoned_value,
        AVG(cart_value) as avg_cart_value
    FROM abandoned_carts
    """
    
    result = conn.execute(query, (location_id,)).fetchone()
    
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
    GROUP BY ac.param_ga_session_id, ac.user_prop_webuserid, u.name, u.email, u.customer_name, u.office_phone, u.cell_phone, tt.completed, tt.notes, ac.device_web_info_hostname
    ORDER BY cart_value DESC
    LIMIT 10
    """
    
    samples = conn.execute(sample_query, (location_id,)).fetchall()
    
    return {
        'total': result[0] or 0,
        'unique_customers': result[1] or 0,
        'total_value': result[2] or 0,
        'avg_value': result[3] or 0,
        'samples': samples
    }

def fetch_search_no_results_tasks_by_location(conn: sqlite3.Connection, location_id: str) -> Dict[str, Any]:
    """Fetch search with no results tasks for a specific location"""
    query = """
    SELECT 
        COUNT(DISTINCT param_no_search_results_term) as unique_terms,
        COUNT(*) as total_searches,
        COUNT(DISTINCT param_ga_session_id) as affected_sessions
    FROM no_search_results
    WHERE param_no_search_results_term IS NOT NULL
    AND user_prop_default_branch_id = ?
    """
    
    result = conn.execute(query, (location_id,)).fetchone()
    
    # Get top failed search terms
    sample_query = """
    SELECT 
        nsr.param_no_search_results_term as search_term,
        COUNT(*) as search_count,
        COUNT(DISTINCT nsr.param_ga_session_id) as unique_sessions,
        tt.completed,
        tt.notes
    FROM no_search_results nsr
    LEFT JOIN task_tracking tt ON tt.task_id = ('SEARCH_' || nsr.param_no_search_results_term) AND tt.task_type = 'search'
    WHERE nsr.param_no_search_results_term IS NOT NULL
    AND nsr.user_prop_default_branch_id = ?
    GROUP BY nsr.param_no_search_results_term, tt.completed, tt.notes
    ORDER BY search_count DESC
    LIMIT 10
    """
    
    samples = conn.execute(sample_query, (location_id,)).fetchall()
    
    return {
        'unique_terms': result[0] or 0,
        'total_searches': result[1] or 0,
        'affected_sessions': result[2] or 0,
        'samples': samples
    }

def fetch_repeat_visits_tasks_by_location(conn: sqlite3.Connection, location_id: str) -> Dict[str, Any]:
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
        GROUP BY pv.param_ga_session_id
        HAVING pages_viewed >= 3
    )
    SELECT 
        COUNT(*) as total_sessions,
        AVG(pages_viewed) as avg_pages_viewed
    FROM repeat_visitors
    """
    
    result = conn.execute(query, (location_id,)).fetchone()
    
    # Get sample repeat visitors
    sample_query = """
    SELECT 
        pv.param_ga_session_id,
        u.name as customer_name,
        u.email,
        u.customer_name as company,
        COUNT(DISTINCT pv.param_page_location) as pages_viewed,
        MAX(pv.event_timestamp) as last_visit,
        GROUP_CONCAT(DISTINCT pv.param_page_title) as pages_visited,
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
    GROUP BY pv.param_ga_session_id, u.user_id, tt.completed, tt.notes
    HAVING pages_viewed >= 3
    ORDER BY pages_viewed DESC
    LIMIT 10
    """
    
    samples = conn.execute(sample_query, (location_id,)).fetchall()
    
    return {
        'total': result[0] or 0,
        'avg_pages': result[1] or 0,
        'samples': samples
    }

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
        <div class="location-section">
            <h2 class="location-header">{location_name} ({location_code})</h2>
            
            <!-- Location Summary -->
            <h3 class="table-title">Location Overview</h3>
            <table class="summary-table">
                <tr>
                    <th>Metric</th>
                    <th>Value</th>
                    <th>Details</th>
                </tr>
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
            </table>
    """
    
    # Add purchase details if any
    if data['purchases']['total'] > 0:
        html += f"""
            <div class="task-section">
                <h3 class="table-title">Purchase Follow-up Tasks</h3>
                <table class="task-table">
                    <tr>
                        <th style="width: 20px;"></th>
                        <th>Customer</th>
                        <th>Company</th>
                        <th>Order Value</th>
                        <th>Transaction ID</th>
                        <th>Status</th>
                    </tr>
        """
        
        for idx, sample in enumerate(data['purchases']['samples']):
            customer = sample[4] or 'Unknown'
            company = sample[6] or '-'
            revenue = float(sample[1]) if sample[1] else 0
            trans_id = sample[0] or '-'
            email = sample[5] or ''
            phone = sample[7] or sample[8] or ''
            items_json = sample[3]
            completed = sample[13]
            notes = sample[14]
            hostname = sample[15] or 'example.com'  # Default hostname
            task_id = f"purchase_{trans_id}"
            
            status_class = "status-complete" if completed else "status-pending"
            status_text = "Complete" if completed else "Pending"
            
            html += f"""
                    <tr class="expandable-row" onclick="toggleDetails('purchase-{location_code}-{idx}')">
                        <td><span id="icon-purchase-{location_code}-{idx}" class="expand-icon">▶</span></td>
                        <td>{customer}</td>
                        <td>{company}</td>
                        <td>${revenue:.2f}</td>
                        <td>{trans_id}</td>
                        <td><button class="status-btn {status_class}" onclick="event.stopPropagation(); alert('Status update would be handled by dashboard');">{status_text}</button></td>
                    </tr>
                    <tr>
                        <td colspan="6" style="padding: 0;">
                            <div id="purchase-{location_code}-{idx}" class="expanded-content">
                                <strong>Contact:</strong> {email or 'N/A'} | {phone or 'N/A'}<br>
                                <strong>Products:</strong><br>
                                <table class="product-table" style="margin: 10px 0;">
                                    <tr>
                                        <th>Product</th>
                                        <th>Brand</th>
                                        <th>Category</th>
                                        <th>Qty</th>
                                        <th>Price</th>
                                        <th>Total</th>
                                    </tr>
            """
            
            items = parse_items_json(items_json)
            if items:
                for item in items:
                    item_name = item.get('item_name', 'Unknown Product')
                    quantity = int(item.get('quantity', 1))
                    price = float(item.get('price', 0))
                    item_id = item.get('item_id', '')
                    item_brand = item.get('item_brand', '-')
                    item_category = item.get('item_category', '-')
                    
                    html += f"""
                                    <tr>
                                        <td>{item_name}<br><small>SKU: {item_id}</small></td>
                                        <td>{item_brand}</td>
                                        <td>{item_category}</td>
                                        <td style="text-align: center;">{quantity}</td>
                                        <td style="text-align: right;">${price:.2f}</td>
                                        <td style="text-align: right;">${quantity * price:.2f}</td>
                                    </tr>
                    """
            
            html += f"""
                                </table>
                                <br><strong>Task Status:</strong><br>
                                <div class="product-details">
                                    <strong>Completed:</strong> {'Yes' if completed else 'No'}
                                </div>
                                <div class="notes-section">
                                    <strong>Notes:</strong>
                                    <textarea id="notes-{task_id}">{notes or ''}</textarea>
                                    <button class="notes-btn" onclick="event.stopPropagation(); alert('Notes would be saved in the dashboard for task {task_id}');">Save Notes</button>
                                </div>
                            </div>
                        </td>
                    </tr>
            """
        
        html += """
                </table>
            </div>
        """
    
    # Add cart abandonment details if any
    if data['cart_abandonment']['total'] > 0:
        html += f"""
            <div class="task-section">
                <h3 class="table-title">Cart Abandonment Recovery Tasks</h3>
                <table class="task-table">
                    <tr>
                        <th style="width: 20px;"></th>
                        <th>Customer</th>
                        <th>Company</th>
                        <th>Cart Value</th>
                        <th>Items</th>
                        <th>Status</th>
                    </tr>
        """
        
        for idx, sample in enumerate(data['cart_abandonment']['samples']):
            customer = sample[1] or 'Unknown'
            email = sample[2] or ''
            company = sample[3] or '-'
            office_phone = sample[4] or ''
            cell_phone = sample[5] or ''
            items_count = sample[6] or 0
            cart_value = float(sample[7]) if sample[7] else 0
            all_items_json = sample[9] or ''
            completed = sample[10]
            notes = sample[11]
            hostname = sample[12] or 'example.com'
            session_id = sample[0]
            task_id = f"cart_{session_id}"
            
            phone = office_phone or cell_phone or ''
            
            status_class = "status-complete" if completed else "status-pending"
            status_text = "Complete" if completed else "Pending"

            html += f"""
                    <tr class="expandable-row" onclick="toggleDetails('cart-{location_code}-{idx}')">
                        <td><span id="icon-cart-{location_code}-{idx}" class="expand-icon">▶</span></td>
                        <td>{customer}</td>
                        <td>{company}</td>
                        <td>${cart_value:.2f}</td>
                        <td>{items_count}</td>
                        <td><button class="status-btn {status_class}" onclick="event.stopPropagation(); alert('Status update would be handled by dashboard');">{status_text}</button></td>
                    </tr>
                    <tr>
                        <td colspan="6" style="padding: 0;">
                            <div id="cart-{location_code}-{idx}" class="expanded-content">
                                <strong>Contact:</strong> {email or 'N/A'} | {phone or 'N/A'}<br>
                                <strong>Products in Cart:</strong><br>
                                <table class="product-table" style="margin: 10px 0;">
                                    <tr>
                                        <th>Product</th>
                                        <th>Brand</th>
                                        <th>Category</th>
                                        <th>Qty</th>
                                        <th>Price</th>
                                        <th>Total</th>
                                    </tr>
            """
            
            # Parse all items JSON
            cart_items = []
            if all_items_json:
                json_parts = all_items_json.split('||SEPARATOR||')
                for json_part in json_parts:
                    if json_part and json_part != 'null':
                        items = parse_items_json(json_part)
                        cart_items.extend(items)
            
            # Remove duplicates based on item_id
            unique_items = {}
            for item in cart_items:
                item_id = item.get('item_id', '')
                if item_id:
                    if item_id in unique_items:
                        # Add quantities if duplicate
                        unique_items[item_id]['quantity'] = str(int(unique_items[item_id]['quantity']) + int(item.get('quantity', 1)))
                    else:
                        unique_items[item_id] = item
            
            # Display items in table
            for item in unique_items.values():
                item_name = item.get('item_name', 'Unknown Product')
                item_id = item.get('item_id', '')
                item_brand = item.get('item_brand', '-')
                item_category = item.get('item_category', '-')
                quantity = int(item.get('quantity', 1))
                price = float(item.get('price', 0))
                
                html += f"""
                                    <tr>
                                        <td>{item_name}<br><small>SKU: {item_id}</small></td>
                                        <td>{item_brand}</td>
                                        <td>{item_category}</td>
                                        <td style="text-align: center;">{quantity}</td>
                                        <td style="text-align: right;">${price:.2f}</td>
                                        <td style="text-align: right;">${quantity * price:.2f}</td>
                                    </tr>
                """
            
            html += f"""
                                </table>
                                <br><strong>Task Status:</strong><br>
                                <div class="product-details">
                                    <strong>Completed:</strong> {'Yes' if completed else 'No'}
                                </div>
                                <div class="notes-section">
                                    <strong>Notes:</strong>
                                    <textarea id="notes-{task_id}">{notes or ''}</textarea>
                                    <button class="notes-btn" onclick="event.stopPropagation(); alert('Notes would be saved in the dashboard for task {task_id}');">Save Notes</button>
                                </div>
                            </div>
                        </td>
                    </tr>
            """
        
        html += """
                </table>
            </div>
        """
    
    # Add failed searches if any
    if data['search_no_results']['total_searches'] > 0:
        html += f"""
            <div class="task-section">
                <h3 class="table-title">Failed Search Recovery Tasks</h3>
                <table class="task-table">
                    <tr>
                        <th style="width: 20px;"></th>
                        <th>Search Term</th>
                        <th>Count</th>
                        <th>Sessions</th>
                        <th>Status</th>
                    </tr>
        """
        
        for idx, sample in enumerate(data['search_no_results']['samples'][:5]):
            term = sample[0] or '-'
            count = sample[1] or 0
            sessions = sample[2] or 0
            completed = sample[3]
            notes = sample[4]
            # Sanitize term for use in HTML id
            safe_term = "".join(c if c.isalnum() else '_' for c in term)
            task_id = f"search_{location_code}_{safe_term}"
            
            status_class = "status-complete" if completed else "status-pending"
            status_text = "Complete" if completed else "Pending"
            
            html += f"""
                    <tr class="expandable-row" onclick="toggleDetails('search-{location_code}-{idx}')">
                        <td><span id="icon-search-{location_code}-{idx}" class="expand-icon">▶</span></td>
                        <td>{term}</td>
                        <td>{count}</td>
                        <td>{sessions}</td>
                        <td><button class="status-btn {status_class}" onclick="event.stopPropagation(); alert('Status update would be handled by dashboard');">{status_text}</button></td>
                    </tr>
                    <tr>
                        <td colspan="5" style="padding: 0;">
                            <div id="search-{location_code}-{idx}" class="expanded-content">
                                <div class="notes-section">
                                    <strong>Notes:</strong>
                                    <textarea id="notes-{task_id}">{notes or ''}</textarea>
                                    <button class="notes-btn" onclick="event.stopPropagation(); alert('Notes would be saved in the dashboard for task {task_id}');">Save Notes</button>
                                </div>
                            </div>
                        </td>
                    </tr>
            """
        
        html += """
                </table>
            </div>
        """

    # Add repeat visits if any
    if data['repeat_visits']['total'] > 0:
        html += f"""
            <div class="task-section">
                <h3 class="table-title">Repeat Visit Conversion Tasks</h3>
                <table class="task-table">
                    <tr>
                        <th style="width: 20px;"></th>
                        <th>Customer</th>
                        <th>Company</th>
                        <th>Pages Viewed</th>
                        <th>Last Visit</th>
                        <th>Status</th>
                    </tr>
        """
        
        for idx, sample in enumerate(data['repeat_visits']['samples']):
            customer = sample[1] or 'Unknown'
            company = sample[3] or '-'
            pages_viewed = sample[4] or 0
            last_visit_raw = sample[5]
            last_visit = datetime.fromtimestamp(int(last_visit_raw) / 1000000).strftime('%Y-%m-%d') if last_visit_raw else 'N/A'
            email = sample[2] or ''
            pages_visited = sample[6] or ''
            completed = sample[7]
            notes = sample[8]
            session_id = sample[0]
            user_id = customer  # This is simplified, in real case you'd get the actual user_id
            task_id = f"REPEAT_{session_id}_{user_id}"
            
            status_class = "status-complete" if completed else "status-pending"
            status_text = "Complete" if completed else "Pending"

            html += f"""
                    <tr class="expandable-row" onclick="toggleDetails('visit-{location_code}-{idx}')">
                        <td><span id="icon-visit-{location_code}-{idx}" class="expand-icon">▶</span></td>
                        <td>{customer}</td>
                        <td>{company}</td>
                        <td>{pages_viewed}</td>
                        <td>{last_visit}</td>
                        <td><button class="status-btn {status_class}" onclick="event.stopPropagation(); alert('Status update would be handled by dashboard');">{status_text}</button></td>
                    </tr>
                    <tr>
                        <td colspan="6" style="padding: 0;">
                            <div id="visit-{location_code}-{idx}" class="expanded-content">
                                <strong>Contact:</strong> {email or 'N/A'}<br>
                                <strong>Pages Visited:</strong><br>
                                <div class="product-details">{pages_visited or 'N/A'}</div>
                                <br><strong>Task Status:</strong><br>
                                <div class="product-details">
                                    <strong>Completed:</strong> {'Yes' if completed else 'No'}
                                </div>
                                <div class="notes-section">
                                    <strong>Notes:</strong>
                                    <textarea id="notes-{task_id}">{notes or ''}</textarea>
                                    <button class="notes-btn" onclick="event.stopPropagation(); alert('Notes would be saved in the dashboard for task {task_id}');">Save Notes</button>
                                </div>
                            </div>
                        </td>
                    </tr>
            """
        
        html += """
                </table>
            </div>
        """
    
    html += """
        </div>
    """
    
    return html

def generate_branch_wise_report(conn: sqlite3.Connection) -> str:
    """Generate HTML email report organized by branch/location"""
    
    # Get all locations
    locations = get_all_locations(conn)
    
    # Format date
    report_date = datetime.now().strftime("%B %d, %Y")
    
    # Start HTML
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: Arial, sans-serif;
            color: #000;
            background-color: #fff;
            margin: 0;
            padding: 20px;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        .main-header {{
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            border-bottom: 3px solid #000;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        
        .main-header h1 {{
            font-size: 28px;
            margin: 0;
            border-bottom: none;
            padding-bottom: 0;
        }}

        .report-date {{
            font-size: 16px;
            color: #555;
        }}
        
        h1 {{
            font-size: 28px;
            margin-bottom: 10px;
            border-bottom: 3px solid #000;
            padding-bottom: 10px;
        }}
        
        h2.location-header {{
            font-size: 20px;
            margin-top: 40px;
            margin-bottom: 20px;
            background-color: #f0f0f0;
            padding: 10px;
            border-left: 4px solid #333;
        }}
        
        h3 {{
            font-size: 16px;
            margin-top: 20px;
            margin-bottom: 10px;
        }}
        
        h3.table-title {{
            font-size: 18px;
            margin-top: 30px;
            margin-bottom: 15px;
            color: #2c5aa0;
            border-bottom: 2px solid #2c5aa0;
            padding-bottom: 5px;
        }}
        
        .summary-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 30px;
            background-color: #f9f9f9;
        }}
        
        .summary-table th,
        .summary-table td {{
            border: 1px solid #ddd;
            padding: 10px;
            text-align: left;
        }}
        
        .summary-table th {{
            background-color: #e0e0e0;
            font-weight: bold;
        }}
        
        .task-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }}
        
        .task-table th,
        .task-table td {{
            border: 1px solid #ccc;
            padding: 8px;
            text-align: left;
        }}
        
        .task-table th {{
            background-color: #f0f0f0;
            font-weight: bold;
        }}
        
        .location-section {{
            margin-bottom: 50px;
            border: 1px solid #ddd;
            padding: 20px;
            page-break-inside: avoid;
        }}
        
        .task-section {{
            margin-top: 20px;
        }}
        
        .task-suggestion {{
            background-color: #f0f8ff;
            border: 1px solid #b0d4e3;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 5px;
        }}
        
        .task-suggestion ul {{
            margin: 10px 0 0 20px;
            padding: 0;
        }}
        
        .task-suggestion li {{
            margin-bottom: 5px;
        }}
        
        .expandable-row {{
            cursor: pointer;
            background-color: #fafafa;
        }}
        
        .expandable-row:hover {{
            background-color: #f0f0f0;
        }}
        
        .expanded-content {{
            display: none;
            background-color: #f9f9f9;
            border: 1px solid #e0e0e0;
            padding: 10px;
            margin-top: 5px;
            font-size: 0.9em;
        }}
        
        .expand-icon {{
            font-family: monospace;
            margin-right: 8px;
        }}
        
        .product-details {{
            margin-left: 20px;
            font-size: 0.9em;
            color: #444;
        }}
        .product-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
            background-color: #fff;
            border: 1px solid #ddd;
        }}
        .product-table th,
        .product-table td {{
            border: 1px solid #e0e0e0;
            padding: 6px 10px;
            text-align: left;
            font-size: 0.9em;
        }}
        .product-table th {{
            background-color: #f5f5f5;
            font-weight: bold;
            color: #333;
        }}
        .product-table td {{
            background-color: #fff;
        }}
        .product-table tr:nth-child(even) td {{
            background-color: #fafafa;
        }}
        .product-table a {{
            color: #2c5aa0;
            text-decoration: none;
        }}
        .product-table a:hover {{
            text-decoration: underline;
        }}
        .product-table small {{
            color: #666;
            font-size: 0.85em;
        }}
        
        .notes-section {{
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px dashed #ccc;
        }}

        .notes-section textarea {{
            width: 95%;
            min-height: 60px;
            padding: 5px;
            border: 1px solid #ccc;
            border-radius: 4px;
            margin-top: 5px;
        }}

        .notes-btn {{
            padding: 5px 15px;
            border: 1px solid #2c5aa0;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            font-weight: bold;
            background-color: #2c5aa0;
            color: #fff;
            margin-top: 5px;
        }}

        .notes-btn:hover {{
            opacity: 0.9;
        }}
        
        .status-btn {{
            padding: 4px 12px;
            border: 1px solid #ccc;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            font-weight: bold;
        }}
        
        .status-pending {{
            background-color: #fff3cd;
            color: #856404;
        }}
        
        .status-complete {{
            background-color: #d4edda;
            color: #155724;
        }}
        
        .footer {{
            margin-top: 50px;
            padding-top: 20px;
            border-top: 2px solid #000;
            font-size: 12px;
            color: #666;
        }}
        
        .overall-summary {{
            background-color: #e8f4f8;
            padding: 20px;
            margin-bottom: 30px;
            border: 1px solid #b0d4e3;
        }}
        
        .metric {{
            font-size: 24px;
            font-weight: bold;
            color: #2c5aa0;
        }}
        
        @media print {{
            .expandable-row {{
                cursor: default;
            }}
            .location-section {{
                page-break-inside: avoid;
            }}
            .status-btn {{
                pointer-events: none;
            }}
        }}

        .product-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
            background-color: #fff;
            border: 1px solid #ddd;
        }}
        
        .product-table th,
        .product-table td {{
            border: 1px solid #e0e0e0;
            padding: 6px 10px;
            text-align: left;
            font-size: 0.9em;
        }}
        
        .product-table th {{
            background-color: #f5f5f5;
            font-weight: bold;
            color: #333;
        }}
        
        .product-table td {{
            background-color: #fff;
        }}
        
        .product-table tr:nth-child(even) td {{
            background-color: #fafafa;
        }}
        
        .product-table small {{
            color: #666;
            font-size: 0.85em;
        }}
    </style>
    <script>
        function toggleDetails(id) {{
            var content = document.getElementById(id);
            var icon = document.getElementById('icon-' + id);
            if (content.style.display === 'block') {{
                content.style.display = 'none';
                icon.innerHTML = '▶';
            }} else {{
                content.style.display = 'block';
                icon.innerHTML = '▼';
            }}
        }}
    </script>
</head>
<body>
    <div class="container">
        <div class="main-header">
            <h1>Branch-wise Sales Task Report</h1>
            <span class="report-date">{report_date}</span>
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
    for location in locations:
        # Fetch data for this location
        location_data = {
            'purchases': fetch_purchase_tasks_by_location(conn, location['warehouse_code']),
            'cart_abandonment': fetch_cart_abandonment_tasks_by_location(conn, location['warehouse_code']),
            'search_no_results': fetch_search_no_results_tasks_by_location(conn, location['warehouse_code']),
            'repeat_visits': fetch_repeat_visits_tasks_by_location(conn, location['warehouse_code'])
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
            html += section
    
    # Add overall summary at the beginning (we'll insert it)
    overall_summary = f"""
        <div class="overall-summary">
            <h2>Overall Summary - All Branches</h2>
            <table class="summary-table">
                <tr>
                    <th>Metric</th>
                    <th>Total</th>
                    <th>Value</th>
                </tr>
                <tr>
                    <td>Total Purchases</td>
                    <td class="metric">{overall_stats['total_purchases']}</td>
                    <td>${overall_stats['total_revenue']:.2f}</td>
                </tr>
                <tr>
                    <td>Total Cart Abandonments</td>
                    <td class="metric">{overall_stats['total_carts']}</td>
                    <td>${overall_stats['total_cart_value']:.2f}</td>
                </tr>
                <tr>
                    <td>Total Failed Searches</td>
                    <td class="metric">{overall_stats['total_searches']}</td>
                    <td>-</td>
                </tr>
                <tr>
                    <td>Total Repeat Visits (No Purchase)</td>
                    <td class="metric">{overall_stats['total_repeat_visits']}</td>
                    <td>-</td>
                </tr>
            </table>
        </div>
    """
    
    # Insert overall summary after the h1
    insert_pos = html.find('</h1>') + 5
    html = html[:insert_pos] + overall_summary + html[insert_pos:]
    
    # Add footer
    html += f"""
        <div class="footer">
            <p><strong>Report Generated:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <p>This is an automated branch-wise report from the Impax Sales Intelligence System.</p>
            <p><em>Click on rows with ▶ to expand and see detailed information.</em></p>
            <p><strong>Note:</strong> Status and notes functionality are for demonstration. Actual updates should be done through the dashboard.</p>
        </div>
    </div>
</body>
</html>
    """
    
    return html

def main():
    """Main function to generate the branch-wise email report"""
    parser = argparse.ArgumentParser(description="Generate branch-wise email reports.")
    parser.add_argument("--db-path", default="db/branch_wise_location.db", help="Path to the SQLite database.")
    args = parser.parse_args()
    
    # Connect to database
    conn = get_db_connection(args.db_path)
    
    try:
        # Generate HTML report
        html_report = generate_branch_wise_report(conn)
        
        # Save to file
        report_dir = "branch_reports"
        os.makedirs(report_dir, exist_ok=True)
        report_filename = os.path.join(report_dir, f"D_All_report_{datetime.now().strftime('%Y%m%d')}.html")

        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(html_report)
        
        print(f"Branch-wise report generated: {report_filename}")
        
        # Also generate individual reports for each location
        locations = get_all_locations(conn)
        
        for location in locations:
            location_data = {
                'purchases': fetch_purchase_tasks_by_location(conn, location['warehouse_code']),
                'cart_abandonment': fetch_cart_abandonment_tasks_by_location(conn, location['warehouse_code']),
                'search_no_results': fetch_search_no_results_tasks_by_location(conn, location['warehouse_code']),
                'repeat_visits': fetch_repeat_visits_tasks_by_location(conn, location['warehouse_code'])
            }
            
            # Skip if no data
            if (location_data['purchases']['total'] == 0 and 
                location_data['cart_abandonment']['total'] == 0 and 
                location_data['search_no_results']['total_searches'] == 0 and 
                location_data['repeat_visits']['total'] == 0):
                continue
            
            # Generate individual report
            individual_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: Arial, sans-serif;
            color: #000;
            background-color: #fff;
            margin: 0;
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
        }}
        .main-header {{
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            border-bottom: 2px solid #000;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .main-header h1 {{
            font-size: 24px;
            margin: 0;
            border-bottom: none;
            padding-bottom: 0;
        }}
        .report-date {{
            font-size: 14px;
            color: #555;
        }}
        h1 {{
            font-size: 24px;
            margin-bottom: 10px;
            border-bottom: 2px solid #000;
            padding-bottom: 10px;
        }}
        .summary-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 30px;
        }}
        .summary-table th,
        .summary-table td {{
            border: 1px solid #ddd;
            padding: 10px;
            text-align: left;
        }}
        .summary-table th {{
            background-color: #e0e0e0;
        }}
        .task-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
        }}
        .task-table th,
        .task-table td {{
            border: 1px solid #ccc;
            padding: 8px;
            text-align: left;
        }}
        .task-table th {{
            background-color: #f0f0f0;
        }}
        .expandable-row {{
            cursor: pointer;
            background-color: #fafafa;
        }}
        .expandable-row:hover {{
            background-color: #f0f0f0;
        }}
        .expanded-content {{
            display: none;
            background-color: #f9f9f9;
            border: 1px solid #e0e0e0;
            padding: 10px;
            margin-top: 5px;
        }}
        .expand-icon {{
            font-family: monospace;
            margin-right: 8px;
        }}
        .product-details {{
            margin-left: 20px;
            font-size: 0.9em;
            color: #444;
        }}
        .notes-section {{
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px dashed #ccc;
        }}
        .notes-section textarea {{
            width: 95%;
            min-height: 60px;
            padding: 5px;
            border: 1px solid #ccc;
            border-radius: 4px;
            margin-top: 5px;
        }}
        .notes-btn {{
            padding: 5px 15px;
            border: 1px solid #2c5aa0;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            font-weight: bold;
            background-color: #2c5aa0;
            color: #fff;
            margin-top: 5px;
        }}
        .notes-btn:hover {{
            opacity: 0.9;
        }}
        .status-btn {{
            padding: 4px 12px;
            border: 1px solid #ccc;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
            font-weight: bold;
        }}
        .status-pending {{
            background-color: #fff3cd;
            color: #856404;
        }}
        .status-complete {{
            background-color: #d4edda;
            color: #155724;
        }}
    </style>
    <script>
        function toggleDetails(id) {{
            var content = document.getElementById(id);
            var icon = document.getElementById('icon-' + id);
            if (content.style.display === 'block') {{
                content.style.display = 'none';
                icon.innerHTML = '▶';
            }} else {{
                content.style.display = 'block';
                icon.innerHTML = '▼';
            }}
        }}
    </script>
</head>
<body>
    <div class="container">
        <div class="main-header">
            <h1>{location['warehouse_name']} - {location['city']} ({location['warehouse_code']})</h1>
            <span class="report-date">{datetime.now().strftime("%B %d, %Y")}</span>
        </div>
        {generate_location_section(location, location_data)}
    </div>
</body>
</html>
            """
            
            # Save individual report
            individual_filename = os.path.join(report_dir, f"{location['warehouse_code']}_report_{datetime.now().strftime('%Y%m%d')}.html")

            with open(individual_filename, 'w', encoding='utf-8') as f:
                f.write(individual_html)
            
            print(f"Generated report for {location['warehouse_code']}: {individual_filename}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main() 