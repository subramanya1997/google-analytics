#!/usr/bin/env python3
"""
Test SFTP connection and show directory structure
"""

import json
import paramiko
from datetime import datetime

def list_directory_recursive(sftp, path=".", level=0, max_level=2):
    """Recursively list directory contents"""
    indent = "  " * level
    try:
        items = sftp.listdir_attr(path)
        for item in items:
            item_path = f"{path}/{item.filename}" if path != "." else item.filename
            
            if item.st_mode & 0o40000:  # Directory
                print(f"{indent}[DIR]  {item.filename}/")
                if level < max_level:
                    list_directory_recursive(sftp, item_path, level + 1, max_level)
            else:
                size_mb = item.st_size / (1024 * 1024)
                print(f"{indent}[FILE] {item.filename} ({size_mb:.2f} MB)")
    except Exception as e:
        print(f"{indent}Error reading {path}: {e}")

def search_for_files(sftp, extensions=['.xlsx', '.jsonl'], search_path=".", max_depth=3):
    """Search for specific file extensions"""
    found_files = {ext: [] for ext in extensions}
    
    def search_recursive(path, current_depth=0):
        if current_depth > max_depth:
            return
            
        try:
            items = sftp.listdir_attr(path)
            for item in items:
                item_path = f"{path}/{item.filename}" if path != "." else item.filename
                
                if item.st_mode & 0o40000:  # Directory
                    search_recursive(item_path, current_depth + 1)
                else:
                    for ext in extensions:
                        if item.filename.lower().endswith(ext.lower()):
                            size_mb = item.st_size / (1024 * 1024)
                            found_files[ext].append({
                                'name': item.filename,
                                'path': item_path,
                                'size_mb': size_mb
                            })
        except Exception as e:
            print(f"Error searching {path}: {e}")
    
    search_recursive(search_path)
    return found_files

def test_sftp_connection(config_file='configs/sftp_config.json'):
    # Load configuration
    with open(config_file, 'r') as f:
        config = json.load(f)
    
    print(f"Testing SFTP Connection - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print(f"Host: {config['host']}")
    print(f"Username: {config['username']}")
    print(f"Remote Path: {config['remote_path']}")
    print("=" * 60)
    
    try:
        # Connect
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        print("\nConnecting...")
        ssh.connect(
            hostname=config['host'],
            port=config.get('port', 22),
            username=config['username'],
            password=config['password'],
            look_for_keys=False,
            allow_agent=False
        )
        
        sftp = ssh.open_sftp()
        print("✓ Connected successfully!")
        
        # Test remote path
        print(f"\nChecking remote path: {config['remote_path']}")
        try:
            sftp.chdir(config['remote_path'])
            print(f"✓ Remote path exists")
            
            # First, do a simple listing
            print(f"\nDirect contents of {config['remote_path']}:")
            items = sftp.listdir_attr('.')
            
            if not items:
                print("  (empty directory)")
            else:
                for item in items:
                    if item.st_mode & 0o40000:  # Directory
                        print(f"  [DIR]  {item.filename}/")
                    else:
                        size_mb = item.st_size / (1024 * 1024)
                        print(f"  [FILE] {item.filename} ({size_mb:.2f} MB)")
            
            # Now do a recursive search for specific files
            print(f"\n" + "="*60)
            print("SEARCHING FOR SPECIFIC FILES (.xlsx, .jsonl)")
            print("="*60)
            
            found_files = search_for_files(sftp, ['.xlsx', '.jsonl', '.json'])
            
            for ext, files in found_files.items():
                if files:
                    print(f"\n{ext.upper()} FILES FOUND ({len(files)}):")
                    for file_info in files:
                        print(f"  ✓ {file_info['name']} ({file_info['size_mb']:.2f} MB)")
                        print(f"    Path: {file_info['path']}")
                else:
                    print(f"\n{ext.upper()} FILES: None found")
            
            # Check specifically for the expected files from config
            expected_files = [config.get('user_file'), config.get('locations_file')]
            print(f"\n" + "="*60)
            print("CHECKING FOR EXPECTED CONFIG FILES")
            print("="*60)
            
            for expected_file in expected_files:
                if expected_file:
                    print(f"\nLooking for: {expected_file}")
                    found = False
                    for ext, files in found_files.items():
                        for file_info in files:
                            if file_info['name'] == expected_file:
                                print(f"  ✓ FOUND: {file_info['path']} ({file_info['size_mb']:.2f} MB)")
                                found = True
                                break
                    if not found:
                        print(f"  ✗ NOT FOUND: {expected_file}")
            
            # Show recursive directory structure (limited depth)
            print(f"\n" + "="*60)
            print("RECURSIVE DIRECTORY STRUCTURE")
            print("="*60)
            list_directory_recursive(sftp, ".", 0, 2)
            
        except FileNotFoundError:
            print(f"✗ Remote path '{config['remote_path']}' not found")
            print("\nAvailable directories in root:")
            for item in sftp.listdir_attr('.'):
                if item.st_mode & 0o40000:
                    print(f"  - {item.filename}")
        
        # Also check root directory for xlsx files
        print(f"\n" + "="*60)
        print("CHECKING ROOT DIRECTORY FOR XLSX FILES")
        print("="*60)
        
        try:
            sftp.chdir('/')
            print("Checking root directory (/)...")
            root_found_files = search_for_files(sftp, ['.xlsx'], ".", 2)
            
            if root_found_files['.xlsx']:
                print(f"XLSX FILES FOUND IN ROOT ({len(root_found_files['.xlsx'])}):")
                for file_info in root_found_files['.xlsx']:
                    print(f"  ✓ {file_info['name']} ({file_info['size_mb']:.2f} MB)")
                    print(f"    Path: {file_info['path']}")
            else:
                print("No .xlsx files found in root directory")
                
            # List root directories
            print("\nRoot directory structure:")
            list_directory_recursive(sftp, ".", 0, 1)
            
        except Exception as e:
            print(f"Could not access root directory: {e}")
            
        # Check if files exist in current local data directory
        print(f"\n" + "="*60)
        print("CHECKING LOCAL DATA DIRECTORY")
        print("="*60)
        
        import os
        data_dir = config.get('data_dir', 'data')
        if os.path.exists(data_dir):
            print(f"Local data directory '{data_dir}' exists:")
            for root, dirs, files in os.walk(data_dir):
                for file in files:
                    if file.endswith('.xlsx'):
                        file_path = os.path.join(root, file)
                        file_size = os.path.getsize(file_path) / (1024 * 1024)
                        print(f"  ✓ {file} ({file_size:.2f} MB)")
                        print(f"    Path: {file_path}")
        else:
            print(f"Local data directory '{data_dir}' does not exist")
        
        # Show current working directory
        print(f"\nCurrent directory: {sftp.getcwd()}")
        
        sftp.close()
        ssh.close()
        print("\n✓ Connection test completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Connection failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    import sys
    config_file = sys.argv[1] if len(sys.argv) > 1 else 'configs/sftp_config.json'
    test_sftp_connection(config_file) 