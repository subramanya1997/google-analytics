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
    """
    
    # Task Type: Purchases
    if data['purchases']['total'] > 0:
        html += '<h3 class="table-title">Purchase Follow-up Tasks</h3>'
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
            task_id = f"purchase_{trans_id}"

            html += f"""
            <div class="card mb-3">
              <div class="card-header expandable-row" onclick="toggleDetails('{task_id}')">
                <span id="icon-{task_id}" class="expand-icon">▶</span> {customer} - {company} - ${revenue:.2f} - ID: {trans_id}
              </div>
              <div id="{task_id}" class="card-body expanded-content">
                <p><strong>Contact:</strong> {email or 'N/A'} | {phone or 'N/A'}</p>
                <div class="table-responsive">
                  <table class="table table-bordered table-sm">
                    <thead class="table-light">
                      <tr>
                        <th>Product</th>
                        <th>Brand</th>
                        <th>Category</th>
                        <th>Qty</th>
                        <th>Price</th>
                        <th>Total</th>
                      </tr>
                    </thead>
                    <tbody>
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
                        <td class="text-center">{quantity}</td>
                        <td class="text-end">${price:.2f}</td>
                        <td class="text-end">${quantity * price:.2f}</td>
                      </tr>
                    """
            
            html += """
                    </tbody>
                  </table>
                </div>
                <div class="row g-3 mt-3">
                  <div class="col-md-6">
                    <div class="form-check">
                      <input class="form-check-input" type="checkbox" id="taskCompletedCheckbox-{task_id}" {'checked' if completed else ''}>
                      <label class="form-check-label" for="taskCompletedCheckbox-{task_id}">Task Completed</label>
                    </div>
                  </div>
                  <div class="col-md-6">
                    <label for="followUpDate-{task_id}" class="form-label">Next Follow-up Date</label>
                    <input type="date" class="form-control" id="followUpDate-{task_id}">
                  </div>
                </div>
                <div class="mt-3">
                  <label for="notes-{task_id}" class="form-label">Notes</label>
                  <textarea id="notes-{task_id}" class="form-control" rows="3">{notes or ''}</textarea>
                  <button class="btn btn-primary mt-2" onclick="alert('Notes would be saved in the dashboard for task {trans_id}');">Save Notes</button>
                </div>
              </div>
            </div>
            """
    
    # Task Type: Cart Abandonment
    if data['cart_abandonment']['total'] > 0:
        html += '<h3 class="table-title">Cart Abandonment Recovery</h3>'
        for idx, sample in enumerate(data['cart_abandonment']['samples']):
            customer = sample[1] or 'Unknown'
            email = sample[2] or ''
            company = sample[3] or '-'
            phone = sample[4] or sample[5] or ''
            cart_value = float(sample[7]) if sample[7] else 0
            session_id = sample[0]
            completed = sample[10]
            notes = sample[11]
            all_items_json = sample[9] or ''
            task_id = f"cart_{session_id}"

            html += f"""
            <div class="card mb-3">
                <div class="card-header expandable-row" onclick="toggleDetails('{task_id}')">
                    <span id="icon-{task_id}" class="expand-icon">▶</span> {customer} - {company} - ${cart_value:.2f} - Session: {session_id[:8]}...
                </div>
                <div id="{task_id}" class="card-body expanded-content">
                    <p><strong>Contact:</strong> {email or 'N/A'} | {phone or 'N/A'}</p>
                    <div class="table-responsive">
                        <table class="table table-bordered table-sm">
                            <thead class="table-light">
                                <tr>
                                    <th>Product</th>
                                    <th>Brand</th>
                                    <th>Category</th>
                                    <th>Qty</th>
                                    <th>Price</th>
                                    <th>Total</th>
                                </tr>
                            </thead>
                            <tbody>
            """

            cart_items = []
            if all_items_json:
                json_parts = all_items_json.split('||SEPARATOR||')
                for json_part in json_parts:
                    if json_part and json_part != 'null':
                        items = parse_items_json(json_part)
                        cart_items.extend(items)
            
            unique_items = {}
            for item in cart_items:
                item_id = item.get('item_id', '')
                if item_id:
                    unique_items[item_id] = item
            
            for item in unique_items.values():
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
                        <td class="text-center">{quantity}</td>
                        <td class="text-end">${price:.2f}</td>
                        <td class="text-end">${quantity * price:.2f}</td>
                      </tr>
                """
            
            html += f"""
                            </tbody>
                        </table>
                    </div>
                    <div class="row g-3 mt-3">
                        <div class="col-md-6">
                            <div class="form-check">
                                <input class="form-check-input" type="checkbox" id="taskCompletedCheckbox-{task_id}" {'checked' if completed else ''}>
                                <label class="form-check-label" for="taskCompletedCheckbox-{task_id}">Task Completed</label>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <label for="followUpDate-{task_id}" class="form-label">Next Follow-up Date</label>
                            <input type="date" class="form-control" id="followUpDate-{task_id}">
                        </div>
                    </div>
                    <div class="mt-3">
                        <label for="notes-{task_id}" class="form-label">Notes</label>
                        <textarea id="notes-{task_id}" class="form-control" rows="3">{notes or ''}</textarea>
                        <button class="btn btn-primary mt-2" onclick="alert('Notes would be saved in the dashboard for session {session_id}');">Save Notes</button>
                    </div>
                </div>
            </div>
            """

    html += "</div>" # End location-section
    return html

def generate_branch_wise_report(conn: sqlite3.Connection) -> str:
    """Generate HTML email report organized by branch/location"""
    
    locations = get_all_locations(conn)
    report_date = datetime.now().strftime("%B %d, %Y")
    
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Task Report</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body {{
      font-family: Arial, sans-serif;
      background-color: #f8f9fa;
      padding: 20px;
    }}
    .expandable-row {{
      cursor: pointer;
    }}
    .expanded-content {{
      display: none;
    }}
    .expand-icon {{
      font-family: monospace;
      margin-right: 8px;
    }}
    .product-details {{
      margin-left: 1rem;
      color: #444;
    }}
    .location-header {{
        font-size: 20px;
        margin-top: 40px;
        margin-bottom: 20px;
        background-color: #e9ecef;
        padding: 10px;
        border-left: 4px solid #0d6efd;
    }}
    h3.table-title {{
        font-size: 18px;
        margin-top: 30px;
        margin-bottom: 15px;
        color: #0d6efd;
        border-bottom: 2px solid #0d6efd;
        padding-bottom: 5px;
    }}
  </style>
  <script>
    function toggleDetails(id) {{
      const content = document.getElementById(id);
      const icon = document.getElementById('icon-' + id);
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
        <div class="row mb-4">
            <div class="col">
                <h1 class="border-bottom pb-2">Branch-wise Sales Task Report</h1>
                <p class="text-muted">Report Date: {report_date}</p>
            </div>
        </div>
    """
    
    # Overall summary and other logic remains the same...
    overall_stats = {
        'total_purchases': 0,
        'total_revenue': 0,
        'total_carts': 0,
        'total_cart_value': 0,
        'total_searches': 0,
        'total_repeat_visits': 0
    }
    
    location_sections = ""
    for location in locations:
        location_data = {
            'purchases': fetch_purchase_tasks_by_location(conn, location['warehouse_code']),
            'cart_abandonment': fetch_cart_abandonment_tasks_by_location(conn, location['warehouse_code']),
            'search_no_results': fetch_search_no_results_tasks_by_location(conn, location['warehouse_code']),
            'repeat_visits': fetch_repeat_visits_tasks_by_location(conn, location['warehouse_code'])
        }
        
        overall_stats['total_purchases'] += location_data['purchases']['total']
        overall_stats['total_revenue'] += location_data['purchases']['total_revenue']
        overall_stats['total_carts'] += location_data['cart_abandonment']['total']
        overall_stats['total_cart_value'] += location_data['cart_abandonment']['total_value']
        overall_stats['total_searches'] += location_data['search_no_results']['total_searches']
        overall_stats['total_repeat_visits'] += location_data['repeat_visits']['total']
        
        location_sections += generate_location_section(location, location_data)

    overall_summary_html = f"""
    <div class="card mb-4">
        <div class="card-header">Overall Summary - All Branches</div>
        <div class="card-body">
            <table class="table">
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Total</th>
                        <th>Value</th>
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

    html += overall_summary_html + location_sections

    html += """
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
    
    conn = get_db_connection(args.db_path)
    
    try:
        html_report = generate_branch_wise_report(conn)
        
        report_dir = "branch_reports"
        os.makedirs(report_dir, exist_ok=True)
        report_filename = os.path.join(report_dir, f"D_All_report_{datetime.now().strftime('%Y%m%d')}.html")
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(html_report)
        print(f"Consolidated report generated: {report_filename}")
        
        locations = get_all_locations(conn)
        for location in locations:
            location_data = {
                'purchases': fetch_purchase_tasks_by_location(conn, location['warehouse_code']),
                'cart_abandonment': fetch_cart_abandonment_tasks_by_location(conn, location['warehouse_code']),
                'search_no_results': fetch_search_no_results_tasks_by_location(conn, location['warehouse_code']),
                'repeat_visits': fetch_repeat_visits_tasks_by_location(conn, location['warehouse_code'])
            }
            
            if (location_data['purchases']['total'] == 0 and 
                location_data['cart_abandonment']['total'] == 0 and 
                location_data['search_no_results']['total_searches'] == 0 and 
                location_data['repeat_visits']['total'] == 0):
                continue
            
            location_name = f"{location['warehouse_name']} - {location['city']} ({location['warehouse_code']})"
            report_date = datetime.now().strftime("%B %d, %Y")

            individual_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Task Report - {location['warehouse_code']}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body {{
      font-family: Arial, sans-serif;
      background-color: #f8f9fa;
      padding: 20px;
    }}
    .expandable-row {{
      cursor: pointer;
    }}
    .expanded-content {{
      display: none;
    }}
    .expand-icon {{
      font-family: monospace;
      margin-right: 8px;
    }}
    .product-details {{
      margin-left: 1rem;
      color: #444;
    }}
    h3.table-title {{
        font-size: 18px;
        margin-top: 30px;
        margin-bottom: 15px;
        color: #0d6efd;
        border-bottom: 2px solid #0d6efd;
        padding-bottom: 5px;
    }}
  </style>
  <script>
    function toggleDetails(id) {{
      const content = document.getElementById(id);
      const icon = document.getElementById('icon-' + id);
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
        <div class="row mb-4">
            <div class="col">
                <h1 class="border-bottom pb-2">{location_name}</h1>
                <p class="text-muted">Report Date: {report_date}</p>
            </div>
        </div>
        {generate_location_section(location, location_data)}
    </div>
</body>
</html>
            """
            
            individual_filename = os.path.join(report_dir, f"{location['warehouse_code']}_report_{datetime.now().strftime('%Y%m%d')}.html")
            with open(individual_filename, 'w', encoding='utf-8') as f:
                f.write(individual_html)
            print(f"Generated report for {location['warehouse_code']}: {individual_filename}")
            
    finally:
        conn.close()

if __name__ == "__main__":
    main() 