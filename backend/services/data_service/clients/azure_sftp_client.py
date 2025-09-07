"""
Azure Blob Storage SFTP client with proper session management
"""

import asyncio
import os
import tempfile
from typing import Any, Dict

import pandas as pd
import paramiko
from loguru import logger


class AzureSFTPClient:
    """Azure Blob Storage SFTP client with proper session management."""

    def __init__(self, sftp_config: Dict[str, Any]):
        """
        Initialize Azure SFTP client with configuration.

        Args:
            sftp_config: Dictionary containing SFTP connection details
        """
        self.config = sftp_config
        self.host = sftp_config.get("host")
        self.port = sftp_config.get("port", 22)
        self.username = sftp_config.get("username")
        self.password = sftp_config.get("password")
        self.remote_path = sftp_config.get("remote_path", "")
        self.data_dir = sftp_config.get("data_dir", "")
        self.user_file = sftp_config.get("user_file", "UserReport.xlsx")
        self.locations_file = sftp_config.get("locations_file", "Locations_List.xlsx")

        if not all([self.host, self.username, self.password]):
            logger.warning(
                "SFTP configuration incomplete, SFTP operations will be disabled"
            )

    def _create_connection(self) -> tuple[paramiko.SSHClient, paramiko.SFTPClient]:
        """Create a fresh SSH/SFTP connection with Azure-specific settings."""
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
        if self.data_dir:
            path_parts.append(self.data_dir)
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

            # Ensure user_id is present and convert to string
            if "user_id" in df.columns:
                df["user_id"] = df["user_id"].astype(str)
                df = df.dropna(subset=["user_id"])
                df = df[df["user_id"].str.strip() != ""]
                df = df[df["user_id"] != "nan"]  # Remove 'nan' strings

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
        Get the latest users data from SFTP (async wrapper).

        Returns:
            DataFrame containing users data
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_users_data_sync)

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
