#!/usr/bin/env python3
"""
Test SFTP connection and show directory structure
"""

import json
import paramiko
from datetime import datetime

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
            
            # List contents
            items = sftp.listdir_attr('.')
            print(f"\nContents of {config['remote_path']}:")
            
            if not items:
                print("  (empty directory)")
            else:
                jsonl_count = 0
                for item in items:
                    if item.st_mode & 0o40000:  # Directory
                        print(f"  [DIR]  {item.filename}")
                    else:
                        size_mb = item.st_size / (1024 * 1024)
                        print(f"  [FILE] {item.filename} ({size_mb:.2f} MB)")
                        if item.filename.endswith('.jsonl'):
                            jsonl_count += 1
                
                print(f"\nFound {jsonl_count} .jsonl files")
                
        except FileNotFoundError:
            print(f"✗ Remote path '{config['remote_path']}' not found")
            print("\nAvailable directories in root:")
            for item in sftp.listdir_attr('.'):
                if item.st_mode & 0o40000:
                    print(f"  - {item.filename}")
        
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