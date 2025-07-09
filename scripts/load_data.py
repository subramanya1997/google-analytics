#!/usr/bin/env python3
"""
Enhanced SQLite loader that captures ALL fields from GA4 JSON/JSONL, including nested structures
"""

import os
import json
import re
import sqlite3
import logging
from typing import Dict, Set, List, Any
import pandas as pd
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def read_records(file_path: str):
    """Generator to yield records from either a .json or .jsonl file."""
    if file_path.endswith('.jsonl'):
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue
    elif file_path.endswith('.json'):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                for line in f:
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue
            except json.JSONDecodeError:
                pass # Silently ignore malformed JSON files

def sanitize_column(name: str) -> str:
    """Sanitize arbitrary GA4 param key into a SQLite-compatible column identifier."""
    # Replace invalid chars with underscore
    name = re.sub(r"[^0-9a-zA-Z_]+", "_", name)
    # Ensure column does not start with digit
    if re.match(r"^[0-9]", name):
        name = f"_{name}"
    return name.lower()

def safe_str(value: Any) -> str:
    """Safely convert any value to string"""
    if value is None:
        return None
    elif isinstance(value, (dict, list)):
        return json.dumps(value)
    else:
        return str(value)

def flatten_dict(d: Dict, parent_key: str = '', sep: str = '_') -> Dict[str, Any]:
    """Flatten nested dictionary into single-level dict with concatenated keys"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            # For lists, we'll store as JSON string
            items.append((new_key, json.dumps(v)))
        else:
            # Convert all values to strings to avoid type issues
            items.append((new_key, safe_str(v)))
    return dict(items)

def extract_all_fields(record: Dict) -> Dict[str, Any]:
    """Extract all fields from a GA4 record, including nested structures"""
    
    # Start with basic fields
    extracted = {
        'event_date': record.get('event_date'),
        'event_timestamp': record.get('event_timestamp'),
        'event_name': record.get('event_name'),
        'event_value_in_usd': record.get('event_value_in_usd'),
        'event_bundle_sequence_id': record.get('event_bundle_sequence_id'),
        'user_pseudo_id': record.get('user_pseudo_id'),
        'user_first_touch_timestamp': record.get('user_first_touch_timestamp'),
        'stream_id': record.get('stream_id'),
        'platform': record.get('platform'),
        'batch_event_index': record.get('batch_event_index'),
        'batch_ordering_id': record.get('batch_ordering_id'),
        'batch_page_id': record.get('batch_page_id'),
        'is_active_user': record.get('is_active_user'),
    }
    
    # Extract event parameters
    for param in record.get('event_params', []):
        key = param.get('key')
        if key:
            # Extract value based on type
            value_dict = param.get('value', {})
            value = None
            for value_type in ['string_value', 'int_value', 'double_value', 'float_value', 'bool_value']:
                if value_type in value_dict:
                    value = value_dict[value_type]
                    break
            extracted[f'param_{sanitize_column(key)}'] = value
    
    # Extract user properties
    for prop in record.get('user_properties', []):
        key = prop.get('key')
        if key:
            value_dict = prop.get('value', {})
            value = None
            for value_type in ['string_value', 'int_value', 'double_value', 'float_value', 'bool_value']:
                if value_type in value_dict:
                    value = value_dict[value_type]
                    break
            extracted[f'user_prop_{sanitize_column(key)}'] = value
    
    # Extract device information
    device = record.get('device', {})
    if device:
        device_flat = flatten_dict(device, 'device')
        extracted.update(device_flat)
    
    # Extract geo information
    geo = record.get('geo', {})
    if geo:
        geo_flat = flatten_dict(geo, 'geo')
        extracted.update(geo_flat)
    
    # Extract traffic source information
    traffic_source = record.get('traffic_source', {})
    if traffic_source:
        traffic_flat = flatten_dict(traffic_source, 'traffic')
        extracted.update(traffic_flat)
    
    # Extract collected traffic source
    collected_traffic = record.get('collected_traffic_source', {})
    if collected_traffic:
        collected_flat = flatten_dict(collected_traffic, 'collected_traffic')
        extracted.update(collected_flat)
    
    # Extract session traffic source
    session_traffic = record.get('session_traffic_source_last_click', {})
    if session_traffic:
        session_flat = flatten_dict(session_traffic, 'session_traffic')
        extracted.update(session_flat)
    
    # Extract user LTV
    user_ltv = record.get('user_ltv', {})
    if user_ltv:
        ltv_flat = flatten_dict(user_ltv, 'user_ltv')
        extracted.update(ltv_flat)
    
    # Extract privacy info
    privacy = record.get('privacy_info', {})
    if privacy:
        privacy_flat = flatten_dict(privacy, 'privacy')
        extracted.update(privacy_flat)
    
    # Extract ecommerce data
    ecommerce = record.get('ecommerce', {})
    if ecommerce:
        ecommerce_flat = flatten_dict(ecommerce, 'ecommerce')
        extracted.update(ecommerce_flat)
    
    # Extract items (store as JSON for now)
    items = record.get('items', [])
    if items:
        extracted['items_json'] = json.dumps(items)
        # Also extract first item details for easier querying
        if len(items) > 0:
            first_item = items[0]
            for k, v in first_item.items():
                # Convert to string to avoid type issues
                extracted[f'first_item_{sanitize_column(k)}'] = safe_str(v)
    
    # Convert all values to strings to ensure SQLite compatibility
    for key, value in extracted.items():
        extracted[key] = safe_str(value)
    
    return extracted

def discover_enhanced_schema(file_path: str, max_lines: int = 10000) -> Dict[str, Set[str]]:
    """Discover all fields including nested structures from a JSON or JSONL file."""
    schema: Dict[str, Set[str]] = {}
    
    for idx, record in enumerate(read_records(file_path)):
        if idx >= max_lines:
            break
        try:
            event_name = record.get("event_name")
            if not event_name:
                continue
                
            # Extract all fields
            fields = extract_all_fields(record)
            
            # Sanitize column names
            sanitized_fields = {sanitize_column(k) for k in fields.keys()}
            
            schema.setdefault(event_name, set()).update(sanitized_fields)
        except Exception: # Broad exception to avoid crashing on one bad record
            continue
    
    return schema

def create_enhanced_tables(conn: sqlite3.Connection, schema: Dict[str, Set[str]]):
    """Create tables with all discovered fields"""
    cur = conn.cursor()
    
    for event_name, columns in schema.items():
        table_name = sanitize_column(event_name)
        
        # Check if table exists
        cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}';")
        table_exists = cur.fetchone() is not None
        
        if table_exists:
            # Get existing columns
            cur.execute(f"PRAGMA table_info({table_name})")
            existing_columns = {row[1] for row in cur.fetchall() if row[1] != 'id'}
            
            # Add any new columns that don't exist
            new_columns = columns - existing_columns
            if new_columns:
                logger.info(f"Adding {len(new_columns)} new columns to table {table_name}")
                for col in new_columns:
                    try:
                        cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {col} TEXT;")
                    except sqlite3.OperationalError as e:
                        logger.warning(f"Could not add column {col} to {table_name}: {e}")
        else:
            # Create new table
            cols_sql = [f"{col} TEXT" for col in sorted(columns)]
            cur.execute(
                f"CREATE TABLE {table_name} (id INTEGER PRIMARY KEY AUTOINCREMENT, {', '.join(cols_sql)});"
            )
            logger.info(f"Created new table {table_name} with {len(columns)} columns")
    
    conn.commit()

def ingest_enhanced_events(conn: sqlite3.Connection, file_path: str, schema: Dict[str, Set[str]], batch: int = 1000):
    """Ingest events with all fields from a JSON or JSONL file."""
    cur = conn.cursor()
    
    # Track skipped event types
    skipped_events = set()
    
    buffer_by_table: Dict[str, List[List]] = {}
    
    for record_num, record in enumerate(read_records(file_path)):
        if record_num % 1000 == 0:
            print(f"  Processing record {record_num:,}...")
            
        try:
            event_name = record.get("event_name")
            if not event_name:
                continue
            
            # Skip events not in schema
            if event_name not in schema:
                if event_name not in skipped_events:
                    print(f"  Warning: Skipping event type '{event_name}' not found in schema. Consider increasing --sample-lines")
                    skipped_events.add(event_name)
                continue
                
            table = sanitize_column(event_name)
            allowed_cols = schema[event_name]
            
            # Extract all fields
            extracted = extract_all_fields(record)
            
            # Sanitize keys and filter to allowed columns
            row = {}
            for k, v in extracted.items():
                sanitized_key = sanitize_column(k)
                if sanitized_key in allowed_cols:
                    row[sanitized_key] = v
            
            # Ensure all columns present in correct order
            columns_order = sorted(allowed_cols)
            values = [row.get(col) for col in columns_order]
            
            buffer_by_table.setdefault(table, []).append(values)
            
            # Flush if batch reached
            if len(buffer_by_table.get(table, [])) >= batch:
                placeholders = ",".join(["?"] * len(columns_order))
                cur.executemany(
                    f"INSERT INTO {table} ({', '.join(columns_order)}) VALUES ({placeholders});",
                    buffer_by_table[table],
                )
                buffer_by_table[table].clear()
        except Exception: # Broad exception to handle any bad records
            continue
    
    # Flush remaining
    for table, rows in buffer_by_table.items():
        if not rows:
            continue
        # Get columns for this table
        event_name_original = [k for k in schema.keys() if sanitize_column(k) == table][0]
        allowed_cols = schema[event_name_original]
        columns_order = sorted(allowed_cols)
        placeholders = ",".join(["?"] * len(columns_order))
        cur.executemany(
            f"INSERT INTO {table} ({', '.join(columns_order)}) VALUES ({placeholders});",
            rows,
        )
    
    # Print summary of skipped events if any
    if skipped_events:
        print(f"\n  Skipped {len(skipped_events)} event types not in schema: {', '.join(sorted(skipped_events))}")
    
    conn.commit()

def create_task_tracking_table(conn: sqlite3.Connection):
    """Create table for tracking task completion status and notes"""
    cur = conn.cursor()
    
    # Create task_tracking table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS task_tracking (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id TEXT NOT NULL,
        task_type TEXT NOT NULL,
        completed BOOLEAN DEFAULT 0,
        notes TEXT,
        completed_at TEXT,
        completed_by TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(task_id, task_type)
    );
    """)
    
    # Create indexes for efficient querying
    cur.execute("CREATE INDEX IF NOT EXISTS idx_task_tracking_task_id ON task_tracking(task_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_task_tracking_task_type ON task_tracking(task_type);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_task_tracking_completed ON task_tracking(completed);")
    
    conn.commit()
    print("  Created task_tracking table for completion status and notes")

def create_useful_indexes(conn: sqlite3.Connection):
    """Create indexes on commonly queried fields"""
    cur = conn.cursor()
    
    # Get all tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    tables = [row[0] for row in cur.fetchall()]
    
    for table in tables:
        # Skip the task_tracking table as it has its own indexes
        if table == 'task_tracking':
            continue
            
        # Check which columns exist in this table
        cur.execute(f"PRAGMA table_info({table})")
        columns = {row[1] for row in cur.fetchall()}
        
        # Create indexes on common fields if they exist
        index_fields = [
            'event_timestamp',
            'user_pseudo_id',
            'param_ga_session_id',
            'event_date',
            'param_page_location',
            'param_transaction_id',
            'user_prop_default_branch_id'
        ]
        
        for field in index_fields:
            if field in columns:
                index_name = f"idx_{table}_{field}"
                try:
                    cur.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON {table}({field});")
                except sqlite3.OperationalError:
                    pass  # Index might already exist
    
    conn.commit()

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced GA4 JSONL loader with all fields")
    parser.add_argument("--data-dir", required=True, help="Path to directory containing JSONL and Excel files")
    parser.add_argument("--ga-file-pattern", default="*.json*", help="Glob pattern for GA4 JSON/JSONL files")
    parser.add_argument("--excel-file", required=True, help="Excel file name inside data dir for users")
    parser.add_argument("--locations-file", required=True, help="Excel file name inside data dir for locations")
    parser.add_argument("--out", default="db/branch_wise_location.db", help="Output SQLite DB path")
    parser.add_argument("--sample-lines", type=int, default=50000, help="Lines to sample for schema discovery")
    
    args = parser.parse_args()
    
    data_dir = args.data_dir
    out_db = args.out
    
    # Create output directory if it doesn't exist
    out_dir = os.path.dirname(out_db)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    
    print(f"Creating enhanced database: {out_db}")
    conn = sqlite3.connect(out_db)
    
    # Process Users Excel first
    excel_path = os.path.join(data_dir, args.excel_file)
    print(f"Loading users from {excel_path}...")
    df = pd.read_excel(excel_path)
    if isinstance(df, dict):
        df = next(iter(df.values()))
    df.columns = [sanitize_column(c) for c in df.columns]
    df.to_sql("users", conn, if_exists="append", index=False)
    
    # Process Locations Excel
    locations_path = os.path.join(data_dir, args.locations_file)
    print(f"Loading locations from {locations_path}...")
    locations_df = pd.read_excel(locations_path)
    if isinstance(locations_df, dict):
        locations_df = next(iter(locations_df.values()))
    locations_df.columns = [sanitize_column(c) for c in locations_df.columns]
    locations_df.to_sql("locations", conn, if_exists="append", index=False)
    print(f"  Loaded {len(locations_df)} locations")
    
    # Discover enhanced schema
    import glob
    ga4_file_paths = glob.glob(os.path.join(data_dir, args.ga_file_pattern))
    
    if not ga4_file_paths:
        print(f"Warning: No files found for pattern '{args.ga_file_pattern}' in '{data_dir}'")
    
    combined_schema: Dict[str, Set[str]] = {}
    for path in ga4_file_paths:
        print(f"Discovering enhanced schema in {path}...")
        schema = discover_enhanced_schema(path, max_lines=args.sample_lines)
        # Merge schemas
        for evt, keys in schema.items():
            combined_schema.setdefault(evt, set()).update(keys)
    
    print(f"\nDiscovered {len(combined_schema)} event types")
    for event, fields in combined_schema.items():
        print(f"  {event}: {len(fields)} fields")
    
    print("\nCreating enhanced tables...")
    create_enhanced_tables(conn, combined_schema)
    
    # Create task tracking table
    print("\nCreating task tracking table...")
    create_task_tracking_table(conn)
    
    for path in ga4_file_paths:
        print(f"\nIngesting all fields from {path}...")
        ingest_enhanced_events(conn, path, combined_schema)
    
    print("\nCreating indexes...")
    create_useful_indexes(conn)
    
    # Print summary
    cur = conn.cursor()
    print("\n" + "="*60)
    print("ENHANCED DATABASE SUMMARY")
    print("="*60)
    
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;")
    tables = cur.fetchall()
    
    total_rows = 0
    for table in tables:
        table_name = table[0]
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cur.fetchone()[0]
        total_rows += count
        
        # Get column count
        cur.execute(f"PRAGMA table_info({table_name})")
        col_count = len(cur.fetchall())
        
        # Special handling for users, locations, and task_tracking tables to show more info
        if table_name == 'users':
            print(f"{table_name}: {count:,} rows, {col_count} columns (user data)")
        elif table_name == 'locations':
            print(f"{table_name}: {count:,} rows, {col_count} columns (location/warehouse data)")
        elif table_name == 'task_tracking':
            print(f"{table_name}: {count:,} rows, {col_count} columns (task completion tracking)")
        else:
            print(f"{table_name}: {count:,} rows, {col_count} columns")
    
    print(f"\nTotal rows: {total_rows:,}")
    
    # Show a note about default_branch_id
    print("\nNote: default_branch_id is captured as 'user_prop_default_branch_id' in event tables")
    
    conn.close()
    print(f"\nEnhanced database written to: {out_db}")

if __name__ == "__main__":
    main() 