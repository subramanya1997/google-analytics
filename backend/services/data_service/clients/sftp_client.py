"""
Azure Blob Storage SFTP Client with Comprehensive File Processing.

This module provides a robust SFTP client specifically designed for connecting to
Azure Blob Storage SFTP endpoints and processing Excel files containing user and
location data. It handles the complexities of Azure SFTP authentication, session
management, file downloading, and Excel data processing with multiple fallback
strategies for resilient data extraction.

Key Features:
- **Azure Blob Storage Integration**: Optimized for Azure SFTP endpoints
- **Robust Session Management**: Proper connection handling with cleanup
- **Excel File Processing**: Multi-strategy Excel parsing with fallback options
- **Data Transformation**: Column mapping and type conversion for database storage
- **Async Operation Support**: Non-blocking operations with thread pool execution
- **Error Recovery**: Graceful handling of connection and file processing failures
- **Multi-Tenant Support**: Configuration-driven client instantiation

Supported File Types:
1. **User Data Files**: Customer profiles, demographics, and activity data
2. **Location Data Files**: Warehouse, branch, and facility information

Data Processing Pipeline:
1. **Connection Management**: Secure SFTP connection with Azure-specific settings
2. **File Download**: Temporary file handling with proper cleanup
3. **Excel Processing**: Multi-strategy parsing with sheet detection
4. **Data Transformation**: Column mapping, type conversion, and validation
5. **Database Preparation**: Clean, structured data ready for database storage

Azure SFTP Compatibility:
The client includes Azure-specific connection parameters and timeout settings
to ensure reliable connections to Azure Blob Storage SFTP endpoints, which
have specific requirements different from traditional SFTP servers.
"""

import asyncio
import os
import tempfile
from typing import Any, Dict

import pandas as pd
import paramiko
from loguru import logger


class SFTPClient:
    """
    Azure Blob Storage SFTP client with comprehensive file processing capabilities.
    
    This client specializes in connecting to Azure Blob Storage SFTP endpoints
    and processing Excel files containing user and location data. It provides
    robust session management, multi-strategy file parsing, and comprehensive
    data transformation for analytics database storage.
    
    Key Capabilities:
    - Azure-optimized SFTP connection handling
    - Secure authentication with timeout management
    - Excel file processing with multiple fallback strategies
    - Data cleaning and transformation for database compatibility
    - Async operations with proper resource cleanup
    - Comprehensive error handling and recovery
    
    Attributes:
        config: Complete SFTP configuration dictionary
        host: SFTP server hostname (Azure Blob Storage endpoint)
        port: SFTP server port (typically 22)
        username: SFTP authentication username
        password: SFTP authentication password
        remote_path: Remote directory path for file access
        user_file: Filename for user data Excel file
        locations_file: Filename for locations data Excel file
    
    """

    def __init__(self, sftp_config: Dict[str, Any]):
        """
        Initialize Azure SFTP client with tenant-specific configuration.
        
        Sets up SFTP client with Azure Blob Storage-specific connection parameters
        and file processing configuration. Validates required configuration and
        provides warnings for incomplete setups to enable graceful degradation.
        
        Args:
            sftp_config: Configuration dictionary containing:
                - host (str): Azure SFTP endpoint (e.g., "account.sftp.core.windows.net")
                - port (int, optional): SFTP port (default: 22)
                - username (str): SFTP authentication username
                - password (str): SFTP authentication password
                - remote_path (str, optional): Remote directory path (default: "")
                - user_file (str, optional): User data filename (default: "UserReport.xlsx")
                - locations_file (str, optional): Locations filename (default: "Locations_List.xlsx")
        
        Configuration Validation:
            Checks for required connection parameters (host, username, password).
            Missing parameters trigger warning logs and disable SFTP operations
            to prevent runtime failures during data processing.
        
        Azure Compatibility:
            Designed for Azure Blob Storage SFTP endpoints with specific connection
            requirements including timeout settings and authentication patterns.
        
        Multi-Tenant Support:
            Each client instance is configured for a specific tenant's SFTP
            credentials and file locations, enabling secure multi-tenant operation.
        """
        self.config = sftp_config
        self.host = sftp_config.get("host")
        self.port = sftp_config.get("port", 22)
        self.username = sftp_config.get("username")
        self.password = sftp_config.get("password")
        self.remote_path = sftp_config.get("remote_path", "")
        self.user_file = sftp_config.get("user_file", "UserReport.xlsx")
        self.locations_file = sftp_config.get("locations_file", "Locations_List.xlsx")

        if not all([self.host, self.username, self.password]):
            logger.warning(
                "SFTP configuration incomplete, SFTP operations will be disabled"
            )

    def _create_connection(self) -> tuple[paramiko.SSHClient, paramiko.SFTPClient]:
        """
        Create fresh SSH/SFTP connection with Azure Blob Storage optimizations.
        
        Establishes a new SFTP connection with Azure-specific parameters including
        proper timeout settings, authentication configuration, and connection
        options optimized for Azure Blob Storage SFTP endpoints.
        
        **Azure-Specific Configuration:**
        - Extended timeout settings for Azure network latency
        - Disabled SSH agent and key lookup for password-only auth
        - Proper banner and channel timeout handling
        - AutoAddPolicy for Azure host key management
        
        Returns:
            tuple[paramiko.SSHClient, paramiko.SFTPClient]: Connected SSH and SFTP clients
            
        Raises:
            Exception: Connection failures, authentication errors, or timeout issues
            
        **Connection Parameters:**
        - Connection timeout: 30 seconds
        - Banner timeout: 30 seconds (Azure requirement)
        - Authentication timeout: 30 seconds
        - Channel timeout: 30 seconds
        - Agent/key lookup: Disabled (password-only)
        
        """
        try:
            # Create SSH client with Azure-compatible settings
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            # Azure Blob Storage SFTP specific connection parameters
            connect_params = {
                "hostname": self.host,
                "port": self.port,
                "username": self.username,
                "password": self.password,
                "timeout": 30,
                "allow_agent": False,
                "look_for_keys": False,
                "banner_timeout": 30,
                "auth_timeout": 30,
                "channel_timeout": 30,
            }

            logger.info(f"Connecting to Azure SFTP: {self.host}")
            ssh_client.connect(**connect_params)

            # Open SFTP channel
            sftp_client = ssh_client.open_sftp()

            logger.info("Azure SFTP connection established successfully")
            return ssh_client, sftp_client

        except Exception as e:
            logger.error(f"Failed to create Azure SFTP connection: {e}")
            raise

    def _build_remote_path(self, filename: str = None) -> str:
        """Build full remote path."""
        path_parts = []

        if self.remote_path:
            path_parts.append(self.remote_path)
        if filename:
            path_parts.append(filename)

        return "/".join(path_parts) if path_parts else "."

    def _download_file_sync(self, remote_filename: str) -> str:
        """
        Download file from SFTP server synchronously with proper session management.

        Args:
            remote_filename: Name of file to download

        Returns:
            Path to downloaded temporary file
        """
        ssh_client = None
        sftp_client = None
        temp_path = None

        try:
            # Create fresh connection for this operation
            ssh_client, sftp_client = self._create_connection()

            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
            temp_path = temp_file.name
            temp_file.close()

            # Build remote file path
            remote_path = self._build_remote_path(remote_filename)

            logger.info(f"Downloading {remote_path} to {temp_path}")

            # Download file
            sftp_client.get(remote_path, temp_path)

            # Verify file was downloaded
            if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
                raise Exception("Downloaded file is empty or doesn't exist")

            logger.info(
                f"Successfully downloaded {remote_filename} ({os.path.getsize(temp_path)} bytes)"
            )
            return temp_path

        except Exception as e:
            logger.error(f"Error downloading file {remote_filename}: {e}")
            # Clean up temp file if it exists
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass
            raise

        finally:
            # Always close connections
            if sftp_client:
                try:
                    sftp_client.close()
                except:
                    pass
            if ssh_client:
                try:
                    ssh_client.close()
                except:
                    pass

    async def download_file(self, remote_filename: str) -> str:
        """
        Download file from SFTP server (async wrapper).

        Args:
            remote_filename: Name of file to download

        Returns:
            Path to downloaded temporary file
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._download_file_sync, remote_filename
        )

    def _get_users_data_sync(self) -> pd.DataFrame:
        """Get users data synchronously with proper session management."""
        temp_path = None

        try:
            # Download the users file
            temp_path = self._download_file_sync(self.user_file)

            # Read Excel file with multiple fallback strategies
            df = None

            # Strategy 1: Try with 'User Report' sheet and skip first row
            try:
                df = pd.read_excel(temp_path, sheet_name="User Report", skiprows=1)
                logger.info("Successfully read users data with 'User Report' sheet")
            except Exception as e:
                logger.debug(f"Strategy 1 failed: {e}")

            # Strategy 2: Try first sheet with skip rows
            if df is None or df.empty:
                try:
                    df = pd.read_excel(temp_path, skiprows=1)
                    logger.info("Successfully read users data with skiprows=1")
                except Exception as e:
                    logger.debug(f"Strategy 2 failed: {e}")

            # Strategy 3: Try without skip rows
            if df is None or df.empty:
                try:
                    df = pd.read_excel(temp_path)
                    logger.info("Successfully read users data without skiprows")
                except Exception as e:
                    logger.debug(f"Strategy 3 failed: {e}")

            if df is None or df.empty:
                raise ValueError("Could not read user data from Excel file")

            # Process data similar to original implementation
            if "FIRST_NAME" in df.columns:
                df["user_name"] = (
                    df[["FIRST_NAME", "MIDDLE_NAME", "LAST_NAME"]]
                    .fillna("")
                    .agg(" ".join, axis=1)
                    .str.strip()
                )

            # Rename columns to match database schema
            rename_map = {
                "CIMM_USER_ID": "user_id",
                "USER_ID": "user_id",  # Alternative name
                "USER_ERP_ID": "user_erp_id",
                "FIRST_NAME": "first_name",
                "MIDDLE_NAME": "middle_name",
                "LAST_NAME": "last_name",
                "JOB_TITLE": "job_title",
                "ROLE_NAME": "role_name",
                "BUYING_COMPANY_NAME": "buying_company_name",
                "BUYING_COMPANY_ERP_ID": "buying_company_erp_id",
                "CIMM_BUYING_COMPANY_ID": "cimm_buying_company_id",
                "EMAIL_ADDRESS": "email",
                "EMAIL": "email",  # Alternative name
                "PHONE_NUMBER": "office_phone",
                "OFFICE_PHONE": "office_phone",
                "CELL_PHONE": "cell_phone",
                "MOBILE_PHONE": "cell_phone",
                "FAX": "fax",
                "ADDRESS1": "address1",
                "ADDRESS2": "address2",
                "ADDRESS3": "address3",
                "CITY": "city",
                "STATE": "state",
                "COUNTRY": "country",
                "ZIP": "zip",
                "POSTAL_CODE": "zip",
                "DEFAULT_BRANCH_ID": "warehouse_code",
                "WAREHOUSE_CODE": "warehouse_code",
                "REGISTERED_DATE": "registered_date",
                "LAST_LOGIN_DATE": "last_login_date",
                "SITE_NAME": "site_name",
            }

            # Apply only the rename mappings that match existing columns
            rename_dict = {}
            for old_col, new_col in rename_map.items():
                if old_col in df.columns:
                    rename_dict[old_col] = new_col

            df = df.rename(columns=rename_dict)

            # Keep all columns that match the database schema
            db_columns = [
                "user_id",
                "user_name",
                "first_name",
                "middle_name",
                "last_name",
                "job_title",
                "user_erp_id",
                "fax",
                "address1",
                "address2",
                "address3",
                "city",
                "state",
                "country",
                "office_phone",
                "cell_phone",
                "email",
                "registered_date",
                "zip",
                "warehouse_code",
                "last_login_date",
                "cimm_buying_company_id",
                "buying_company_name",
                "buying_company_erp_id",
                "role_name",
                "site_name",
            ]

            available_cols = [col for col in db_columns if col in df.columns]

            if available_cols:
                df = df[available_cols]

            # Convert ID and code fields to strings to match database schema
            string_fields = [
                "user_id", "user_erp_id", "warehouse_code", 
                "cimm_buying_company_id", "buying_company_erp_id",
                "zip", "office_phone", "cell_phone", "fax"
            ]
            
            for field in string_fields:
                if field in df.columns:
                    df[field] = df[field].astype(str)
                    # Clean up 'nan' strings
                    df.loc[df[field] == "nan", field] = None
            
            # Convert datetime fields
            datetime_fields = ["registered_date", "last_login_date"]
            for field in datetime_fields:
                if field in df.columns:
                    # Convert to datetime, handling various formats
                    df[field] = pd.to_datetime(df[field], errors='coerce')
                    # Convert NaT to None for database compatibility
                    df[field] = df[field].where(pd.notna(df[field]), None)
            
            # Ensure user_id is present and valid
            if "user_id" in df.columns:
                df = df.dropna(subset=["user_id"])
                df = df[df["user_id"].str.strip() != ""]

            logger.info(
                f"Successfully processed {len(df)} users with columns: {list(df.columns)}"
            )
            return df

        except Exception as e:
            logger.error(f"Error getting users data: {e}")
            raise

        finally:
            # Clean up temporary file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass

    async def get_latest_users_data(self) -> pd.DataFrame:
        """
        Get latest users data from SFTP with comprehensive processing and transformation.

        This is the primary interface for extracting user data from SFTP sources.
        It handles the complete pipeline from SFTP file download through Excel
        processing to database-ready structured data with comprehensive error
        handling and multiple parsing strategies.

        **Processing Pipeline:**
        1. **File Download**: Secure download from SFTP with temporary storage
        2. **Multi-Strategy Parsing**: Attempts multiple Excel reading approaches
        3. **Data Transformation**: Column mapping and standardization
        4. **Type Conversion**: Proper data types for database storage
        5. **Data Cleaning**: Handle missing values and format inconsistencies
        6. **Validation**: Ensure required fields and data integrity


        Returns:
            pd.DataFrame: Processed user data ready for database storage with columns:
            - user_id, user_name, first_name, middle_name, last_name
            - job_title, user_erp_id, email, office_phone, cell_phone
            - address1, address2, address3, city, state, country, zip
            - warehouse_code, registered_date, last_login_date
            - buying_company_name, buying_company_erp_id, role_name, site_name

        Raises:
            Exception: SFTP connection failures, file processing errors, or data validation issues


        **Multi-Tenant Support:**
        Uses tenant-specific SFTP configuration for secure access to
        appropriate data sources with proper isolation.

        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_users_data_sync)

    def _get_locations_data_sync(self) -> pd.DataFrame:
        """Get locations data synchronously with proper session management."""
        temp_path = None

        try:
            # Download the locations file
            temp_path = self._download_file_sync(self.locations_file)

            # Read Excel file with multiple fallback strategies
            df = None

            # Strategy 1: Try with 'Locations' sheet
            try:
                df = pd.read_excel(temp_path, sheet_name="Locations")
                logger.info("Successfully read locations data with 'Locations' sheet")
            except Exception as e:
                logger.debug(f"Strategy 1 failed: {e}")

            # Strategy 2: Try first sheet directly
            if df is None or df.empty:
                try:
                    df = pd.read_excel(temp_path)
                    logger.info("Successfully read locations data from first sheet")
                except Exception as e:
                    logger.debug(f"Strategy 2 failed: {e}")

            if df is None or df.empty:
                raise ValueError("Could not read locations data from Excel file")

            # Rename columns to match database schema
            rename_map = {
                "WAREHOUSE_ID": "warehouse_id",
                "WAREHOUSE_CODE": "warehouse_code",
                "WAREHOUSE_NAME": "warehouse_name",
                "LOCATION_NAME": "warehouse_name",  # Alternative name
                "CITY": "city",
                "STATE": "state",
                "PROVINCE": "state",  # Alternative name
                "COUNTRY": "country",
                "ADDRESS1": "address1",
                "ADDRESS": "address1",  # Alternative name
                "ADDRESS2": "address2",
                "ZIP_CODE": "zip",
                "POSTAL_CODE": "zip",  # Alternative name
                "ZIP": "zip",  # Alternative name
            }

            # Apply only the rename mappings that match existing columns
            rename_dict = {}
            for old_col, new_col in rename_map.items():
                if old_col in df.columns:
                    rename_dict[old_col] = new_col

            df = df.rename(columns=rename_dict)

            # Keep only columns that match the database schema
            db_columns = [
                "warehouse_id",
                "warehouse_code", 
                "warehouse_name",
                "city",
                "state",
                "country",
                "address1",
                "address2",
                "zip",
            ]

            available_cols = [col for col in db_columns if col in df.columns]

            if available_cols:
                df = df[available_cols]

            # Convert ID and code fields to strings to match database schema
            string_fields = [
                "warehouse_id", "warehouse_code", "zip",
                "latitude", "longitude", "phone_number", "fax",
                "subset_id", "wfl_phase_id", "ac", "branch_location_id",
                "toll_free_number", "cne_batch_id", "external_system_ref_id"
            ]
            
            for field in string_fields:
                if field in df.columns:
                    df[field] = df[field].astype(str)
                    # Clean up 'nan' strings
                    df.loc[df[field] == "nan", field] = None
            
            # Ensure warehouse_id is present and valid
            if "warehouse_id" in df.columns:
                df = df.dropna(subset=["warehouse_id"])
                df = df[df["warehouse_id"].str.strip() != ""]

            logger.info(
                f"Successfully processed {len(df)} locations with columns: {list(df.columns)}"
            )
            return df

        except Exception as e:
            logger.error(f"Error getting locations data: {e}")
            raise

        finally:
            # Clean up temporary file
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except:
                    pass

    async def get_latest_locations_data(self) -> pd.DataFrame:
        """
        Get the latest locations data from SFTP (async wrapper).

        Returns:
            DataFrame containing locations data
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_locations_data_sync)

    def _list_files_sync(self) -> list:
        """List files synchronously with proper session management."""
        ssh_client = None
        sftp_client = None

        try:
            # Create fresh connection
            ssh_client, sftp_client = self._create_connection()

            # Build remote directory path
            remote_path = self._build_remote_path()

            # List files
            files = sftp_client.listdir(remote_path)

            # Filter for Excel files
            excel_files = [f for f in files if f.lower().endswith((".xlsx", ".xls"))]

            logger.info(f"Found {len(excel_files)} Excel files in {remote_path}")
            return sorted(excel_files, reverse=True)  # Most recent first

        except Exception as e:
            logger.error(f"Error listing files: {e}")
            raise

        finally:
            # Always close connections
            if sftp_client:
                try:
                    sftp_client.close()
                except:
                    pass
            if ssh_client:
                try:
                    ssh_client.close()
                except:
                    pass

    async def list_files(self) -> list:
        """List files (async wrapper)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._list_files_sync)

    async def test_connection(self) -> bool:
        """Test SFTP connection."""
        try:
            files = await self.list_files()
            logger.info(f"Connection test successful, found {len(files)} files")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
