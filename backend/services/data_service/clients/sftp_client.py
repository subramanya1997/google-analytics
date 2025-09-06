import asyncio
import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional
import paramiko
import tempfile
import os
from loguru import logger


class SFTPClient:
    """SFTP client for retrieving user and location data."""
    
    def __init__(self, sftp_config: Dict[str, Any]):
        """
        Initialize SFTP client with configuration.
        
        Args:
            sftp_config: Dictionary containing SFTP connection details:
                - host: SFTP server hostname
                - port: SFTP server port (default 22)
                - username: SFTP username
                - password: SFTP password
                - remote_path: Remote directory path (e.g., "hercules")
                - data_dir: Data subdirectory (e.g., "data")
                - user_file: User file name (e.g., "UserReport.xlsx")
                - locations_file: Locations file name (e.g., "Locations_List1750281613134.xlsx")
        """
        self.config = sftp_config
        self.host = sftp_config.get('host')
        self.port = sftp_config.get('port', 22)
        self.username = sftp_config.get('username')
        self.password = sftp_config.get('password')
        self.remote_path = sftp_config.get('remote_path', '')
        self.data_dir = sftp_config.get('data_dir', 'data')
        self.user_file = sftp_config.get('user_file', 'UserReport.xlsx')
        self.locations_file = sftp_config.get('locations_file', 'Locations_List.xlsx')
        
        self.client = None
        self.sftp = None
        
        if not all([self.host, self.username, self.password]):
            logger.warning("SFTP configuration incomplete, SFTP operations will be disabled")
    
    async def connect(self) -> None:
        """Establish SFTP connection."""
        if not all([self.host, self.username, self.password]):
            raise ValueError("SFTP configuration incomplete")
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._connect_sync)
            logger.info(f"Connected to SFTP server {self.host}")
        except Exception as e:
            logger.error(f"Failed to connect to SFTP server {self.host}: {e}")
            raise
    
    def _connect_sync(self) -> None:
        """Synchronous SFTP connection."""
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        self.client.connect(
            hostname=self.host,
            port=self.port,
            username=self.username,
            password=self.password
        )
        
        self.sftp = self.client.open_sftp()
    
    async def disconnect(self) -> None:
        """Close SFTP connection."""
        if self.sftp:
            self.sftp.close()
        if self.client:
            self.client.close()
        logger.info("Disconnected from SFTP server")
    
    async def list_files(self, pattern: str = "*.xlsx") -> list:
        """
        List files matching pattern in remote directory.
        
        Args:
            pattern: File pattern to match
            
        Returns:
            List of matching filenames
        """
        if not self.sftp:
            await self.connect()
        
        try:
            loop = asyncio.get_event_loop()
            files = await loop.run_in_executor(
                None,
                self._list_files_sync,
                pattern
            )
            return files
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            raise
    
    def _list_files_sync(self, pattern: str) -> list:
        """Synchronous file listing."""
        import fnmatch
        
        # Build full remote directory path
        full_remote_path = self._build_remote_path()
        
        files = self.sftp.listdir(full_remote_path)
        matching_files = [f for f in files if fnmatch.fnmatch(f, pattern)]
        return sorted(matching_files, reverse=True)  # Most recent first
    
    def _build_remote_path(self, filename: str = None) -> str:
        """Build full remote path."""
        path_parts = []
        
        if self.remote_path:
            path_parts.append(self.remote_path)
        if self.data_dir:
            path_parts.append(self.data_dir)
        if filename:
            path_parts.append(filename)
        
        return '/'.join(path_parts) if path_parts else '.'
    
    async def download_file(self, remote_filename: str) -> str:
        """
        Download file from SFTP server to temporary location.
        
        Args:
            remote_filename: Name of file to download (can be full path or just filename)
            
        Returns:
            Path to downloaded temporary file
        """
        if not self.sftp:
            await self.connect()
        
        try:
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
            temp_path = temp_file.name
            temp_file.close()
            
            # Build full remote path if just filename provided
            if '/' not in remote_filename:
                remote_path = self._build_remote_path(remote_filename)
            else:
                remote_path = remote_filename
            
            # Download file
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self.sftp.get,
                remote_path,
                temp_path
            )
            
            logger.info(f"Downloaded {remote_path} to {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"Error downloading file {remote_filename}: {e}")
            # Clean up temp file if it was created
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.unlink(temp_path)
            raise
    
    async def get_latest_users_data(self) -> pd.DataFrame:
        """
        Get the latest users data from SFTP using configured file name.
        
        Returns:
            DataFrame containing users data
        """
        try:
            # Download the specific user file
            temp_path = await self.download_file(self.user_file)
            
            try:
                # Read Excel file - try different sheet names and skip rows
                df = None
                try:
                    # Try with 'User Report' sheet and skip first row
                    df = pd.read_excel(temp_path, sheet_name='User Report', skiprows=1)
                except:
                    try:
                        # Try first sheet with skip rows
                        df = pd.read_excel(temp_path, skiprows=1)
                    except:
                        # Try without skip rows
                        df = pd.read_excel(temp_path)
                
                if df is None or df.empty:
                    raise ValueError("Could not read user data from Excel file")
                
                # Process data similar to original load_data.py
                if 'FIRST_NAME' in df.columns:
                    df['user_name'] = df[['FIRST_NAME', 'MIDDLE_NAME', 'LAST_NAME']].fillna('').agg(' '.join, axis=1).str.strip()
                
                # Rename columns to match database schema
                rename_map = {
                    'CIMM_USER_ID': 'user_id',
                    'USER_ID': 'user_id',  # Alternative name
                    'USER_ERP_ID': 'user_erp_id',
                    'FIRST_NAME': 'first_name',
                    'MIDDLE_NAME': 'middle_name',
                    'LAST_NAME': 'last_name',
                    'JOB_TITLE': 'job_title',
                    'ROLE_NAME': 'role_name',
                    'BUYING_COMPANY_NAME': 'buying_company_name',
                    'BUYING_COMPANY_ERP_ID': 'buying_company_erp_id',
                    'CIMM_BUYING_COMPANY_ID': 'cimm_buying_company_id',
                    'EMAIL_ADDRESS': 'email',
                    'EMAIL': 'email',  # Alternative name
                    'PHONE_NUMBER': 'office_phone',
                    'OFFICE_PHONE': 'office_phone',
                    'CELL_PHONE': 'cell_phone',
                    'MOBILE_PHONE': 'cell_phone',
                    'FAX': 'fax',
                    'ADDRESS1': 'address1',
                    'ADDRESS2': 'address2',
                    'ADDRESS3': 'address3',
                    'CITY': 'city',
                    'STATE': 'state',
                    'COUNTRY': 'country',
                    'ZIP': 'zip',
                    'POSTAL_CODE': 'zip',
                    'DEFAULT_BRANCH_ID': 'warehouse_code',
                    'WAREHOUSE_CODE': 'warehouse_code',
                    'REGISTERED_DATE': 'registered_date',
                    'LAST_LOGIN_DATE': 'last_login_date',
                    'SITE_NAME': 'site_name'
                }
                
                # Apply only the rename mappings that match existing columns
                rename_dict = {}
                for old_col, new_col in rename_map.items():
                    if old_col in df.columns:
                        rename_dict[old_col] = new_col
                
                df = df.rename(columns=rename_dict)
                
                # Keep all columns that match the database schema
                # These are the actual columns from the Users model
                db_columns = ['user_id', 'user_name', 'first_name', 'middle_name', 'last_name',
                             'job_title', 'user_erp_id', 'fax', 'address1', 'address2', 'address3',
                             'city', 'state', 'country', 'office_phone', 'cell_phone', 'email',
                             'registered_date', 'zip', 'warehouse_code', 'last_login_date',
                             'cimm_buying_company_id', 'buying_company_name', 'buying_company_erp_id',
                             'role_name', 'site_name']
                
                existing_columns = [col for col in db_columns if col in df.columns]
                df = df[existing_columns]
                
                # Ensure user_id is present and convert to string (it's String(100) in DB)
                if 'user_id' not in df.columns:
                    raise ValueError("user_id column not found in user data")
                
                # Convert user_id to string and clean it
                df['user_id'] = df['user_id'].astype(str)
                df = df.dropna(subset=['user_id'])
                df = df[df['user_id'].str.strip() != '']
                df = df[df['user_id'] != 'nan']  # Remove 'nan' strings from conversion
                
                logger.info(f"Processed {len(df)} users from {self.user_file}")
                return df
                
            finally:
                # Clean up temporary file
                os.unlink(temp_path)
                
        except Exception as e:
            logger.error(f"Error getting users data from {self.user_file}: {e}")
            raise
    
    async def get_latest_locations_data(self) -> pd.DataFrame:
        """
        Get the latest locations data from SFTP using configured file name.
        
        Returns:
            DataFrame containing locations data
        """
        try:
            # Download the specific locations file
            temp_path = await self.download_file(self.locations_file)
            
            try:
                # Read Excel file
                df = pd.read_excel(temp_path)
                
                # Handle case where Excel returns a dict of DataFrames
                if isinstance(df, dict):
                    df = next(iter(df.values()))
                
                if df is None or df.empty:
                    raise ValueError("Could not read locations data from Excel file")
                
                # Rename columns to match database schema - try different possible column names
                rename_map = {
                    'warehouse_code': 'warehouse_id',
                    'warehouse_name': 'warehouse_name',
                    'location_code': 'warehouse_id',
                    'location_name': 'warehouse_name',
                    'branch_code': 'warehouse_id',
                    'branch_name': 'warehouse_name',
                    'city': 'city',
                    'state': 'state',
                    'country': 'country'
                }
                
                # Apply renames only for columns that exist
                existing_renames = {k: v for k, v in rename_map.items() if k in df.columns}
                df = df.rename(columns=existing_renames)
                
                # Select only required columns that exist
                required_columns = ['warehouse_id', 'warehouse_name', 'city', 'state', 'country']
                existing_columns = [col for col in required_columns if col in df.columns]
                df = df[existing_columns]
                
                # Ensure warehouse_id is present
                if 'warehouse_id' not in df.columns:
                    raise ValueError("warehouse_id column not found in locations data")
                
                # Convert warehouse_id to string and remove null values
                df['warehouse_id'] = df['warehouse_id'].astype(str)
                df = df.dropna(subset=['warehouse_id'])
                df = df[df['warehouse_id'].str.strip() != '']
                
                logger.info(f"Processed {len(df)} locations from {self.locations_file}")
                return df
                
            finally:
                # Clean up temporary file
                os.unlink(temp_path)
                
        except Exception as e:
            logger.error(f"Error getting locations data from {self.locations_file}: {e}")
            raise
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        asyncio.create_task(self.disconnect())
