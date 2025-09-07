#!/usr/bin/env python3
"""
Export SQLite database to various formats
"""

import sqlite3
import csv
import json
import os
from datetime import datetime
import argparse

def export_to_csv(db_path, output_dir='exports/csv'):
    """Export all tables to CSV files"""
    os.makedirs(output_dir, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    for table in tables:
        table_name = table[0]
        print(f"Exporting {table_name} to CSV...")
        
        # Get all data from table
        cursor.execute(f"SELECT * FROM {table_name}")
        data = cursor.fetchall()
        
        # Get column names
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Write to CSV
        csv_file = os.path.join(output_dir, f"{table_name}.csv")
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(data)
        
        print(f"  ✓ Exported {len(data)} rows to {csv_file}")
    
    conn.close()

def export_to_json(db_path, output_dir='exports/json'):
    """Export all tables to JSON files"""
    os.makedirs(output_dir, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # This enables column access by name
    cursor = conn.cursor()
    
    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    for table in tables:
        table_name = table[0]
        print(f"Exporting {table_name} to JSON...")
        
        # Get all data from table
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        
        # Convert to list of dicts
        data = [dict(row) for row in rows]
        
        # Write to JSON
        json_file = os.path.join(output_dir, f"{table_name}.json")
        with open(json_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"  ✓ Exported {len(data)} rows to {json_file}")
    
    conn.close()

def export_sql_dump(db_path, output_file='exports/impax_dump.sql'):
    """Export database as SQL dump"""
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    
    with open(output_file, 'w') as f:
        # Write header
        f.write(f"-- SQLite dump generated on {datetime.now()}\n")
        f.write("-- To restore: sqlite3 new_database.db < impax_dump.sql\n\n")
        
        # Dump the database
        for line in conn.iterdump():
            f.write(f"{line}\n")
    
    print(f"✓ SQL dump exported to {output_file}")
    conn.close()

def create_backup(db_path, backup_dir='backups'):
    """Create a timestamped backup of the database"""
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(backup_dir, f"impax_backup_{timestamp}.db")
    
    # Copy the database file
    import shutil
    shutil.copy2(db_path, backup_file)
    
    print(f"✓ Database backed up to {backup_file}")
    return backup_file

def get_database_info(db_path):
    """Get information about the database"""
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"\nDatabase: {db_path}")
    print(f"File size: {os.path.getsize(db_path) / 1024 / 1024:.2f} MB")
    print("\nTables:")
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"  - {table_name}: {count:,} rows")
    
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export SQLite database to various formats.")
    parser.add_argument("--db-path", required=True, help="Path to the SQLite database file.")
    parser.add_argument("--format", choices=['csv', 'json', 'sql', 'backup', 'all'], default='all', help="Export format. Defaults to 'all'.")
    
    args = parser.parse_args()
    
    # Show database info
    get_database_info(args.db_path)
    
    print("\nStarting export...")
    
    if args.format == 'csv' or args.format == 'all':
        export_to_csv(args.db_path)
    
    if args.format == 'json' or args.format == 'all':
        export_to_json(args.db_path)
    
    if args.format == 'sql' or args.format == 'all':
        export_sql_dump(args.db_path)
    
    if args.format == 'backup' or args.format == 'all':
        create_backup(args.db_path)
    
    print("\n✓ Export complete!") 