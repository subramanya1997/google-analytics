#!/usr/bin/env python3
"""
SFTP sync script to fetch .json/.jsonl files and run data loading with cleanup
"""

import os
import sys
import json
import shutil
import paramiko
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple
import subprocess
import glob
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SFTPDataSyncer:
    def __init__(self, host: str, username: str, password: Optional[str] = None,
                 key_path: Optional[str] = None, port: int = 22):
        """Initialize SFTP connection parameters"""
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.key_path = key_path
        self.sftp = None
        self.ssh = None
    
    def connect(self) -> bool:
        """Establish SFTP connection"""
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            connect_params = {
                "hostname": self.host,
                "port": self.port,
                "username": self.username,
                "look_for_keys": False,
                "allow_agent": False,
                "timeout": 30
            }
            
            # Connect with password or key
            if self.key_path:
                logger.info(f"Connecting to {self.host}:{self.port} with SSH key")
                private_key = paramiko.RSAKey.from_private_key_file(self.key_path)
                connect_params["pkey"] = private_key
            else:
                logger.info(f"Connecting to {self.host}:{self.port} with password")
                connect_params["password"] = self.password
            
            self.ssh.connect(**connect_params)
            
            # Set keepalive and socket timeout to prevent hangs
            transport = self.ssh.get_transport()
            if transport and transport.is_active():
                transport.sock.settimeout(60)
                transport.set_keepalive(30)
            
            self.sftp = self.ssh.open_sftp()
            logger.info("SFTP connection established successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to SFTP server: {e}")
            return False
    
    def disconnect(self):
        """Close SFTP connection"""
        if self.sftp:
            self.sftp.close()
        if self.ssh:
            self.ssh.close()
        logger.info("SFTP connection closed")
    
    def list_json_files(self, remote_path: str = '.') -> List[str]:
        """List all .json and .jsonl files in remote directory"""
        try:
            files = []
            for file_attr in self.sftp.listdir_attr(remote_path):
                if file_attr.filename.endswith('.jsonl') or file_attr.filename.endswith('.json'):
                    files.append(file_attr.filename)
            logger.info(f"Found {len(files)} .json/.jsonl files on remote server")
            return files
        except Exception as e:
            logger.error(f"Failed to list remote files: {e}")
            return []
    
    def download_file(self, remote_file: str, local_file: str, remote_path: str = '.') -> bool:
        """Download a single file from SFTP server with automatic reconnection and resume support"""
        max_retries = 5
        retry_count = 0
        chunk_size = 32768
        
        while retry_count < max_retries:
            try:
                # Check if connection is still alive
                try:
                    self.sftp.getcwd()
                except:
                    logger.info("Connection lost, attempting to reconnect...")
                    self.disconnect()
                    if not self.connect():
                        logger.error("Failed to reconnect to SFTP server")
                        return False
                
                remote_full_path = f"{remote_path}/{remote_file}" if remote_path != '.' else remote_file
                logger.info(f"Downloading {remote_full_path} to {local_file}")
                
                # Get remote file size
                remote_stat = self.sftp.stat(remote_full_path)
                remote_size = remote_stat.st_size
                
                # Get current local size for resume
                local_size = 0
                if os.path.exists(local_file):
                    local_size = os.path.getsize(local_file)
                    if local_size == remote_size:
                        logger.info(f"File already completely downloaded: {remote_file} ({remote_size:,} bytes)")
                        return True
                    elif local_size > remote_size:
                        logger.warning(f"Local file larger than remote, restarting download: {local_file}")
                        os.remove(local_file)
                        local_size = 0
                
                # Open local file in append mode if resuming
                with open(local_file, 'ab' if local_size > 0 else 'wb') as local_f:
                    if local_size > 0:
                        logger.info(f"Resuming download from byte {local_size:,}")
                    
                    with self.sftp.open(remote_full_path, 'rb') as remote_f:
                        if local_size > 0:
                            remote_f.seek(local_size)
                        
                        with tqdm(
                            total=remote_size,
                            initial=local_size,
                            unit='B',
                            unit_scale=True,
                            desc=remote_file,
                            miniters=1,
                            ncols=80
                        ) as pbar:
                            while True:
                                data = remote_f.read(chunk_size)
                                if not data:
                                    break
                                local_f.write(data)
                                pbar.update(len(data))
                
                # Verify file size
                final_local_size = os.path.getsize(local_file)
                if final_local_size == remote_size:
                    logger.info(f"Successfully downloaded {remote_file} ({remote_size:,} bytes)")
                    return True
                else:
                    logger.error(f"File size mismatch for {remote_file}: local {final_local_size:,} vs remote {remote_size:,}")
                    # Don't delete partial file, allow future resume
                    return False
                    
            except Exception as e:
                retry_count += 1
                logger.error(f"Failed to download {remote_file} (attempt {retry_count}/{max_retries}): {e}")
                if retry_count < max_retries:
                    import time
                    time.sleep(5)
                    logger.info("Reconnecting for retry...")
                    self.disconnect()
                    if not self.connect():
                        logger.error("Failed to reconnect to SFTP server")
                        return False
                    
        return False


def get_date_suffix(use_yesterday: bool = False) -> str:
    """Get date suffix for files (YYYYMMDD format)"""
    if use_yesterday:
        date = datetime.now() - timedelta(days=1)
    else:
        date = datetime.now()
    return date.strftime("%Y%m%d")


def clean_data_folder(data_dir: str, keep_patterns: List[str] = None) -> None:
    """Clean data folder, keeping only specified patterns"""
    if keep_patterns is None:
        keep_patterns = ["*.xlsx"]  # Keep Excel files by default
    
    logger.info(f"Cleaning data folder: {data_dir}")
    
    # Get all files in data directory
    all_files = []
    for file in os.listdir(data_dir):
        file_path = os.path.join(data_dir, file)
        if os.path.isfile(file_path):
            all_files.append(file_path)
    
    # Determine which files to keep
    files_to_keep = set()
    for pattern in keep_patterns:
        for file in glob.glob(os.path.join(data_dir, pattern)):
            files_to_keep.add(file)
    
    # Remove files not in keep list
    removed_count = 0
    for file_path in all_files:
        if file_path not in files_to_keep:
            try:
                os.remove(file_path)
                logger.info(f"Removed: {os.path.basename(file_path)}")
                removed_count += 1
            except Exception as e:
                logger.error(f"Failed to remove {file_path}: {e}")
    
    logger.info(f"Cleaned up {removed_count} files from data folder")


def clean_database(db_path: str, backup: bool = True) -> None:
    """Clean/remove existing database with optional backup"""
    if os.path.exists(db_path):
        if backup:
            backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            try:
                shutil.copy2(db_path, backup_path)
                logger.info(f"Created database backup: {backup_path}")
            except Exception as e:
                logger.error(f"Failed to backup database: {e}")
        
        try:
            os.remove(db_path)
            logger.info(f"Removed existing database: {db_path}")
        except Exception as e:
            logger.error(f"Failed to remove database: {e}")


def run_load_data(data_dir: str, user_file: str, locations_file: str, db_path: str) -> bool:
    """Run the load_data.py script"""
    script_path = os.path.join("scripts", "load_data.py")
    
    cmd = [
        sys.executable,
        script_path,
        "--data-dir", data_dir,
        "--excel-file", user_file,
        "--locations-file", locations_file,
        "--out", db_path,
        "--ga-file-pattern", "*.json*"  # Ensure we process both .json and .jsonl files
    ]
    
    logger.info(f"Running load_data.py with command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Data loading completed successfully")
            if result.stdout:
                logger.info(f"Output:\n{result.stdout}")
            return True
        else:
            logger.error(f"Data loading failed with code {result.returncode}")
            if result.stderr:
                logger.error(f"Error output:\n{result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to run load_data.py: {e}")
        return False


def run_generate_reports(db_path: str) -> bool:
    """Run the branch-wise report generation script"""
    script_path = os.path.join("scripts", "generate_branch_wise_report.py")
    
    cmd = [
        sys.executable,
        script_path,
        "--db-path", db_path
    ]
    
    logger.info("Generating branch-wise reports...")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Report generation completed successfully")
            if result.stdout:
                logger.info(f"Output:\n{result.stdout}")
            return True
        else:
            logger.error(f"Report generation failed with code {result.returncode}")
            if result.stderr:
                logger.error(f"Error output:\n{result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to run report generation: {e}")
        return False


def run_send_emails(smtp_config: str = None, branch_mapping: str = None) -> bool:
    """Send branch reports via email"""
    script_path = os.path.join("scripts", "send_branch_reports.py")
    
    cmd = [sys.executable, script_path]
    
    if smtp_config:
        cmd.extend(["--smtp-config", smtp_config])
    if branch_mapping:
        cmd.extend(["--branch-mapping", branch_mapping])
    
    logger.info("Sending branch reports via email...")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("Email sending completed successfully")
            if result.stdout:
                logger.info(f"Output:\n{result.stdout}")
            return True
        else:
            logger.error(f"Email sending failed with code {result.returncode}")
            if result.stderr:
                logger.error(f"Error output:\n{result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to send emails: {e}")
        return False


def load_config(config_file: str) -> dict:
    """Load configuration from JSON file"""
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load config file: {e}")
        return {}


def main():
    parser = argparse.ArgumentParser(description="SFTP sync and data loading script")
    
    # SFTP connection parameters
    parser.add_argument("--host", help="SFTP server hostname")
    parser.add_argument("--port", type=int, default=22, help="SFTP server port")
    parser.add_argument("--username", help="SFTP username")
    parser.add_argument("--password", help="SFTP password (use --key-path for key auth)")
    parser.add_argument("--key-path", help="Path to SSH private key")
    parser.add_argument("--remote-path", default=".", help="Remote directory path")
    
    # Data management parameters
    parser.add_argument("--data-dir", default="data", help="Local data directory")
    parser.add_argument("--use-yesterday", action="store_true", help="Use yesterday's date for file suffix")
    parser.add_argument("--no-date-suffix", action="store_true", help="Don't add date suffix to downloaded files")
    
    # Database parameters
    parser.add_argument("--user-file", default="USER_LIST_FOR_AI1749843290493.xlsx", help="User Excel file name")
    parser.add_argument("--locations-file", default="Locations_List1750281613134.xlsx", help="Locations Excel file name")
    parser.add_argument("--db-path", default="db/branch_wise_location.db", help="Database output path")
    parser.add_argument("--no-db-backup", action="store_true", help="Don't backup database before cleaning")
    parser.add_argument("--no-clean-db", action="store_true", help="Don't clean/remove existing database (append mode)")
    
    # Configuration file - default to configs/sftp_config.json
    parser.add_argument("--config", default="configs/sftp_config.json", help="JSON configuration file (overrides command line args)")
    
    # Control flags
    parser.add_argument("--download-only", action="store_true", help="Only download files, don't run load_data")
    parser.add_argument("--load-only", action="store_true", help="Only run load_data, don't download")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without doing it")
    
    # Report generation and email
    parser.add_argument("--generate-reports", action="store_true", help="Generate branch-wise reports after loading")
    parser.add_argument("--send-emails", action="store_true", help="Send reports via email after generation")
    parser.add_argument("--smtp-config", default="configs/smtp_config.json", help="SMTP configuration file")
    parser.add_argument("--branch-mapping", default="configs/branch_email_mapping.json", help="Branch email mapping file")
    
    args = parser.parse_args()
    
    # Load config file - use default if it exists
    config = {}
    if args.config and os.path.exists(args.config):
        config = load_config(args.config)
        logger.info(f"Loaded configuration from: {args.config}")
        
        # Get the defaults for comparison
        defaults = vars(parser.parse_args([]))
        
        # Override args with config values (only if arg wasn't explicitly provided)
        for key, value in config.items():
            # Map config keys to argument attribute names (hyphens become underscores)
            arg_attr = key.replace('-', '_')
            
            # Special handling for boolean flags
            if arg_attr in ['use_yesterday', 'no_date_suffix', 'no_db_backup', 'no_clean_db', 'generate_reports', 'send_emails']:
                if value and not getattr(args, arg_attr, False):
                    setattr(args, arg_attr, value)
            # For other values, only override if not explicitly set (matches default)
            elif hasattr(args, arg_attr) and getattr(args, arg_attr) == defaults.get(arg_attr):
                setattr(args, arg_attr, value)
    elif args.config:
        logger.warning(f"Configuration file not found: {args.config}")
    
    # Log key configuration values
    logger.info("Configuration summary:")
    logger.info(f"  SFTP Host: {args.host}")
    logger.info(f"  Remote Path: {args.remote_path}")
    logger.info(f"  Data Directory: {args.data_dir}")
    logger.info(f"  Database Path: {args.db_path}")
    logger.info(f"  Generate Reports: {args.generate_reports}")
    logger.info(f"  Send Emails: {args.send_emails}")
    
    # Validate required parameters
    if not args.load_only:
        if not args.host or not args.username:
            logger.error("SFTP host and username are required (unless using --load-only)")
            return 1
        
        if not args.password and not args.key_path:
            logger.error("Either password or key-path is required for SFTP authentication")
            return 1
    
    # Create data directory if it doesn't exist
    os.makedirs(args.data_dir, exist_ok=True)
    
    # Step 1: Download files from SFTP
    downloaded_files = []
    successful_remote = []
    
    if not args.load_only:
        syncer = SFTPDataSyncer(
            host=args.host,
            username=args.username,
            password=args.password,
            key_path=args.key_path,
            port=args.port
        )
        
        if not syncer.connect():
            return 1
        
        try:
            # List remote files
            remote_files = syncer.list_json_files(args.remote_path)
            logger.info(f"Files to download: {', '.join(remote_files)}")
            
            if not remote_files:
                logger.warning("No .json/.jsonl files found on remote server")
            else:
                # Clean data folder before downloading
                if not args.dry_run:
                    clean_data_folder(args.data_dir, keep_patterns=["*.xlsx"])
                else:
                    logger.info("[DRY RUN] Would clean data folder")
                
                # Download each file
                date_suffix = get_date_suffix(args.use_yesterday) if not args.no_date_suffix else ""
                
                for remote_file in remote_files:
                    # Determine local filename
                    if date_suffix:
                        # Handle both .json and .jsonl extensions
                        if remote_file.endswith('.jsonl'):
                            base_name = remote_file.replace('.jsonl', '')
                            local_file = f"{base_name}_{date_suffix}.jsonl"
                        else:  # .json
                            base_name = remote_file.replace('.json', '')
                            local_file = f"{base_name}_{date_suffix}.json"
                    else:
                        local_file = remote_file
                    
                    local_path = os.path.join(args.data_dir, local_file)
                    
                    if args.dry_run:
                        logger.info(f"[DRY RUN] Would download {remote_file} to {local_path}")
                        downloaded_files.append(local_path)
                        successful_remote.append(remote_file)
                    else:
                        if syncer.download_file(remote_file, local_path, args.remote_path):
                            downloaded_files.append(local_path)
                            successful_remote.append(remote_file)
                        else:
                            logger.error(f"Failed to download {remote_file}")
            
            logger.info(f"Successfully downloaded {len(downloaded_files)} out of {len(remote_files)} files")
            if len(downloaded_files) < len(remote_files):
                failed_files = set(remote_files) - set(successful_remote)
                logger.warning(f"Failed to download the following files: {', '.join(failed_files)}")
        
        finally:
            syncer.disconnect()
    
    # Step 2: Run load_data.py
    if not args.download_only:
        # Check if we have .json or .jsonl files to process
        json_files = glob.glob(os.path.join(args.data_dir, "*.json"))
        jsonl_files = glob.glob(os.path.join(args.data_dir, "*.jsonl"))
        all_json_files = json_files + jsonl_files
        
        if not all_json_files:
            logger.error("No .json/.jsonl files found in data directory")
            return 1
        
        logger.info(f"Found {len(all_json_files)} .json/.jsonl files to process ({len(json_files)} .json, {len(jsonl_files)} .jsonl)")
        
        # Clean database
        if not args.dry_run:
            if not args.no_clean_db:
                clean_database(args.db_path, backup=not args.no_db_backup)
            else:
                logger.info(f"Skipping database cleanup - appending to existing database: {args.db_path}")
        else:
            if not args.no_clean_db:
                logger.info(f"[DRY RUN] Would clean database: {args.db_path}")
            else:
                logger.info(f"[DRY RUN] Would NOT clean database: {args.db_path} (append mode)")
        
        # Run load_data
        if not args.dry_run:
            success = run_load_data(
                data_dir=args.data_dir,
                user_file=args.user_file,
                locations_file=args.locations_file,
                db_path=args.db_path
            )
            
            if not success:
                logger.error("Data loading failed")
                return 1
                
            # Generate reports if requested
            if args.generate_reports:
                logger.info("Generating branch-wise reports...")
                if not run_generate_reports(args.db_path):
                    logger.error("Report generation failed")
                    return 1
                
                # Send emails if requested
                if args.send_emails:
                    logger.info("Sending reports via email...")
                    if not run_send_emails(args.smtp_config, args.branch_mapping):
                        logger.error("Email sending failed")
                        # Don't fail the entire process if email fails
                        logger.warning("Continuing despite email sending failure")
        else:
            logger.info("[DRY RUN] Would run load_data.py")
            if args.generate_reports:
                logger.info("[DRY RUN] Would generate branch-wise reports")
                if args.send_emails:
                    logger.info("[DRY RUN] Would send reports via email")
    
    logger.info("Process completed successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main()) 