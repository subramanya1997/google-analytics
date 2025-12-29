"""
SFTP client for Azure Functions.

This is an adapted version of the original SFTP client that uses
synchronous methods suitable for Azure Functions activity execution.
"""

import builtins
import contextlib
from pathlib import Path
import tempfile
from typing import Any

from loguru import logger
import pandas as pd
import paramiko


class SFTPClient:
    """
    SFTP client with proper session management for serverless environments.

    This client provides methods to download Excel files from SFTP servers,
    specifically designed for Azure Functions' stateless execution model.
    Connections are created fresh for each operation and properly closed,
    ensuring no connection leaks in serverless environments.

    The client handles user and location data downloads, parsing Excel files
    and returning pandas DataFrames ready for database insertion.

    Attributes:
        config: Complete SFTP configuration dictionary.
        host: SFTP server hostname.
        port: SFTP server port (default: 22).
        username: SFTP authentication username.
        password: SFTP authentication password.
        remote_path: Base path on SFTP server for file operations.
        user_file: Filename for user data Excel file (default: "UserReport.xlsx").
        locations_file: Filename for locations data Excel file (default: "Locations_List.xlsx").

    Example:
        >>> config = {
        ...     "host": "sftp.example.com",
        ...     "username": "user",
        ...     "password": "pass",
        ...     "remote_path": "/data"
        ... }
        >>> client = SFTPClient(config)
        >>> users_df = client._get_users_data_sync()
    """

    def __init__(self, sftp_config: dict[str, Any]) -> None:
        """
        Initialize SFTP client with connection configuration.

        Extracts connection parameters from configuration dictionary and
        validates that required fields are present. Warns if configuration
        is incomplete but allows initialization for graceful error handling.

        Args:
            sftp_config: Dictionary containing:
                - host: SFTP server hostname (required)
                - port: SFTP server port (optional, default: 22)
                - username: Authentication username (required)
                - password: Authentication password (required)
                - remote_path: Base directory path on server (optional)
                - user_file: User data filename (optional, default: "UserReport.xlsx")
                - locations_file: Locations data filename (optional, default: "Locations_List.xlsx")

        Note:
            - Warns if required fields are missing but doesn't raise exceptions
            - Allows partial configuration for testing scenarios
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
        Create a fresh SSH and SFTP connection to the configured server.

        Establishes a new SSH connection using paramiko, then opens an SFTP
        session. Connection parameters include timeouts and security settings
        appropriate for serverless environments.

        Returns:
            tuple[paramiko.SSHClient, paramiko.SFTPClient]: Tuple containing:
                - SSH client instance (for connection management)
                - SFTP client instance (for file operations)

        Raises:
            Exception: If connection fails due to network, authentication, or timeout errors.

        Note:
            - Uses AutoAddPolicy for host key acceptance (suitable for known servers)
            - Sets multiple timeouts (30 seconds) for reliability
            - Disables agent and key lookups for explicit credential use
            - Connection must be closed by caller using returned SSH client
        """
        try:
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

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

            logger.info(f"Connecting to SFTP: {self.host}")
            ssh_client.connect(**connect_params)

            sftp_client = ssh_client.open_sftp()

            logger.info("SFTP connection established successfully")
            return ssh_client, sftp_client

        except Exception as e:
            logger.error(f"Failed to create SFTP connection: {e}")
            raise

    def _build_remote_path(self, filename: str | None = None) -> str:
        """
        Build full remote file path from base path and optional filename.

        Combines the configured remote_path with an optional filename,
        handling empty paths and path separators correctly.

        Args:
            filename: Optional filename to append to base path.

        Returns:
            str: Full remote path string (e.g., "/data/UserReport.xlsx" or ".").

        Note:
            - Returns "." if no path or filename specified
            - Uses forward slashes for path separation
        """
        path_parts = []

        if self.remote_path:
            path_parts.append(self.remote_path)
        if filename:
            path_parts.append(filename)

        return "/".join(path_parts) if path_parts else "."

    def _download_file_sync(self, remote_filename: str) -> str:
        """
        Download a file from SFTP server to local temporary file.

        Creates a fresh SFTP connection, downloads the specified file to a
        temporary location, validates the download, and returns the path.
        The temporary file must be cleaned up by the caller.

        Args:
            remote_filename: Name of the file to download from SFTP server.

        Returns:
            str: Path to the downloaded temporary file.

        Raises:
            Exception: If download fails, file is empty, or connection errors occur.

        Note:
            - Creates temporary file with .xlsx suffix
            - Validates file exists and is not empty after download
            - Connection is properly closed even on errors
            - Temporary file cleanup is caller's responsibility
            - File size is logged for monitoring

        Example:
            >>> temp_path = client._download_file_sync("UserReport.xlsx")
            >>> # Use temp_path...
            >>> Path(temp_path).unlink()  # Cleanup
        """
        ssh_client = None
        sftp_client = None
        temp_path = None

        try:
            ssh_client, sftp_client = self._create_connection()

            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
            temp_path = temp_file.name
            temp_file.close()

            remote_path = self._build_remote_path(remote_filename)

            logger.info(f"Downloading {remote_path} to {temp_path}")

            sftp_client.get(remote_path, temp_path)

            temp_path_obj = Path(temp_path)
            if not temp_path_obj.exists() or temp_path_obj.stat().st_size == 0:
                msg = "Downloaded file is empty or doesn't exist"
                raise Exception(msg)

            logger.info(
                f"Successfully downloaded {remote_filename} ({temp_path_obj.stat().st_size} bytes)"
            )
            return temp_path

        except Exception as e:
            logger.error(f"Error downloading file {remote_filename}: {e}")
            if temp_path and Path(temp_path).exists():
                with contextlib.suppress(builtins.BaseException):
                    Path(temp_path).unlink()
            raise

        finally:
            if sftp_client:
                with contextlib.suppress(builtins.BaseException):
                    sftp_client.close()
            if ssh_client:
                with contextlib.suppress(builtins.BaseException):
                    ssh_client.close()

    def _get_users_data_sync(self) -> pd.DataFrame:
        """
        Download and parse user data Excel file from SFTP server.

        Downloads the user Excel file, attempts multiple parsing strategies
        for format compatibility, normalizes column names to match database
        schema, and returns a cleaned pandas DataFrame ready for database insertion.

        Returns:
            pd.DataFrame: Processed user data with columns matching database schema.
                        Columns include user_id, user_name, email, phone, address,
                        warehouse_code, etc.

        Raises:
            ValueError: If file cannot be read or parsed, or if no valid data found.

        Note:
            - Tries multiple parsing strategies for Excel format compatibility:
              1. Sheet named "User Report" with skiprows=1
              2. First sheet with skiprows=1
              3. First sheet without skiprows
            - Normalizes column names from various source formats
            - Combines FIRST_NAME, MIDDLE_NAME, LAST_NAME into user_name
            - Converts data types (strings, datetimes) appropriately
            - Filters out records without user_id
            - Handles NaN values by converting to None
            - Temporary file is automatically cleaned up

        Example:
            >>> df = client._get_users_data_sync()
            >>> df.columns.tolist()
            ['user_id', 'user_name', 'email', 'warehouse_code', ...]
        """
        temp_path = None

        try:
            temp_path = self._download_file_sync(self.user_file)

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
                msg = "Could not read user data from Excel file"
                raise ValueError(msg)

            # Process data
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
                "USER_ID": "user_id",
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
                "EMAIL": "email",
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

            # Convert ID and code fields to strings
            string_fields = [
                "user_id",
                "user_erp_id",
                "warehouse_code",
                "cimm_buying_company_id",
                "buying_company_erp_id",
                "zip",
                "office_phone",
                "cell_phone",
                "fax",
            ]

            for field in string_fields:
                if field in df.columns:
                    df[field] = df[field].astype(str)
                    df.loc[df[field] == "nan", field] = None

            # Convert datetime fields
            datetime_fields = ["registered_date", "last_login_date"]
            for field in datetime_fields:
                if field in df.columns:
                    df[field] = pd.to_datetime(df[field], errors="coerce")
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
            if temp_path and Path(temp_path).exists():
                with contextlib.suppress(builtins.BaseException):
                    Path(temp_path).unlink()

    def _get_locations_data_sync(self) -> pd.DataFrame:
        """
        Download and parse locations data Excel file from SFTP server.

        Downloads the locations Excel file, attempts multiple parsing strategies
        for format compatibility, normalizes column names to match database
        schema, and returns a cleaned pandas DataFrame ready for database insertion.

        Returns:
            pd.DataFrame: Processed location data with columns matching database schema.
                        Columns include warehouse_id, warehouse_code, warehouse_name,
                        city, state, country, address1, address2, zip.

        Raises:
            ValueError: If file cannot be read or parsed, or if no valid data found.

        Note:
            - Tries multiple parsing strategies:
              1. Sheet named "Locations"
              2. First sheet directly
            - Normalizes column names from various source formats
            - Converts warehouse_id and codes to strings
            - Filters out records without warehouse_id
            - Handles NaN values by converting to None
            - Temporary file is automatically cleaned up

        Example:
            >>> df = client._get_locations_data_sync()
            >>> df.columns.tolist()
            ['warehouse_id', 'warehouse_code', 'warehouse_name', 'city', ...]
        """
        temp_path = None

        try:
            temp_path = self._download_file_sync(self.locations_file)

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
                msg = "Could not read locations data from Excel file"
                raise ValueError(msg)

            # Rename columns to match database schema
            rename_map = {
                "WAREHOUSE_ID": "warehouse_id",
                "WAREHOUSE_CODE": "warehouse_code",
                "WAREHOUSE_NAME": "warehouse_name",
                "LOCATION_NAME": "warehouse_name",
                "CITY": "city",
                "STATE": "state",
                "PROVINCE": "state",
                "COUNTRY": "country",
                "ADDRESS1": "address1",
                "ADDRESS": "address1",
                "ADDRESS2": "address2",
                "ZIP_CODE": "zip",
                "POSTAL_CODE": "zip",
                "ZIP": "zip",
            }

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

            # Convert ID and code fields to strings
            string_fields = ["warehouse_id", "warehouse_code", "zip"]

            for field in string_fields:
                if field in df.columns:
                    df[field] = df[field].astype(str)
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
            if temp_path and Path(temp_path).exists():
                with contextlib.suppress(builtins.BaseException):
                    Path(temp_path).unlink()

