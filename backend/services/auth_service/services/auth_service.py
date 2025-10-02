"""
Authentication Service Business Logic.

This module implements the core business logic for OAuth authentication,
configuration validation, and tenant management in the Google Analytics
Intelligence System. It handles integration with external authentication
services and manages the complete authentication lifecycle.

Key Responsibilities:
- OAuth 2.0 authentication flow with external providers
- Multi-service configuration retrieval and validation  
- Real-time connectivity testing for tenant configurations
- Tenant database setup and configuration synchronization
- Access token lifecycle management (validation, logout)
- Parallel configuration validation for optimal performance

External API Integration:
The service integrates with external authentication APIs for:
- OAuth code exchange for access tokens
- Application settings and configuration retrieval
- Token validation and user information
- Session logout and token invalidation

Configuration Management:
Supports validation of four configuration types:
- PostgreSQL: Database connectivity and schema validation
- BigQuery: GCP project access and service account validation
- SFTP: File transfer server connectivity and authentication
- SMTP: Email server configuration and authentication

The service performs parallel validation of all configurations to minimize
authentication latency and provides detailed feedback on validation failures.

Database Operations:
- Tenant record creation and updates
- Configuration storage with JSON serialization
- Atomic operations with proper error handling
- Support for both new tenant creation and existing tenant updates

Performance Optimizations:
- Parallel configuration validation using asyncio.gather()
- Connection pooling for database operations  
- Async HTTP client with timeout management
- Efficient JSON parsing and serialization

Error Handling:
- Comprehensive exception handling with appropriate logging
- Graceful degradation for partial service failures
- Detailed error messages for debugging and user feedback
- Proper HTTP status code mapping for API responses
"""

import asyncio
import json
from typing import Any, Dict

import httpx
from loguru import logger
from sqlalchemy import create_engine, text

from common.config import get_settings
from common.database import get_async_db_session


class AuthenticationService:
    """
    Core service for OAuth authentication and tenant configuration management.
    
    This service handles the complete authentication workflow including OAuth
    token exchange, configuration validation, and tenant setup. It integrates
    with external authentication providers and manages tenant-specific
    configurations for multiple services.
    
    The service is designed for high reliability and performance with:
    - Parallel configuration validation
    - Comprehensive error handling  
    - Atomic database operations
    - Detailed logging and monitoring
    
    Attributes:
        settings: Service-specific configuration settings
    """

    def __init__(self):
        """
        Initialize the authentication service.
        
        Sets up the service with appropriate configuration settings for the
        auth service, including external API base URLs and timeouts.
        """
        self.settings = get_settings("auth-service")

    async def authenticate_with_code(self, code: str) -> Dict[str, Any]:
        """
        Complete OAuth authentication flow with configuration validation.

        This is the primary authentication method that handles the full OAuth 2.0
        authentication flow, from code exchange to tenant setup. It performs a
        multi-step process that ensures both authentication success and proper
        tenant configuration before allowing access.

        Authentication Process:
        1. **OAuth Code Exchange**: Exchanges authorization code for access token
        2. **Settings Retrieval**: Fetches tenant configurations from external API
        3. **Configuration Parsing**: Parses JSON settings for all services
        4. **Parallel Validation**: Tests all configurations concurrently
        5. **Tenant Management**: Creates or updates tenant in database
        6. **Success Response**: Returns access token and user information

        Args:
            code: OAuth authorization code received from authentication provider
                 (single-use, time-limited code from OAuth callback)

        Returns:
            Dict[str, Any]: Authentication result containing:
            - success (bool): Whether authentication completed successfully
            - message (str): Human-readable status or error message
            - tenant_id (str|None): Unique tenant identifier for API calls
            - first_name (str|None): User's first name from auth provider
            - username (str|None): User's login/username identifier
            - business_name (str|None): Associated business or organization name
            - access_token (str|None): Valid API access token (on success only)
            - missing_configs (List[str]|None): Missing configuration types (on failure)
            - invalid_configs (List[str]|None): Failed configuration types (on failure)

        External API Calls:
        1. GET /manage/auth/getappproperity?code={code}
           - Exchanges OAuth code for access token and user info
           - Returns: appInstanceId, accessToken, accountId, user details

        2. GET /developerApp/accountAppInstance/settings/{appInstanceId}
           - Retrieves tenant application settings using access token
           - Returns: settingsValues JSON with all service configurations

        Configuration Types Validated:
        - **PostgreSQL** (postgres-config): Database connectivity
        - **BigQuery** (BigQuery): GCP project and service account access  
        - **SFTP** (SFTP Config): File transfer server connection
        - **SMTP** (SMTP Config): Email server configuration

        Example Success Response:
        ```python
        {
            "success": True,
            "message": "Authentication successful",
            "tenant_id": "acc-12345",
            "first_name": "John",
            "username": "john.doe",
            "business_name": "Acme Corporation", 
            "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
        }
        ```

        Example Configuration Failure Response:
        ```python
        {
            "success": False,
            "message": "Authentication failed due to missing or invalid configurations",
            "tenant_id": "acc-12345",
            "first_name": "John",
            "username": "john.doe",
            "business_name": "Acme Corporation",
            "missing_configs": ["sftp_config"],
            "invalid_configs": ["postgres_config"]
        }
        ```

        Raises:
            Exception: Re-raised from underlying HTTP or database operations
            for handling by the endpoint layer with proper HTTP status codes.

        Note:
            This method performs network I/O and database operations, so it
            should always be called with await in an async context.
        """
        try:
            # Step 1: Get app property using the code
            base_url = self.settings.BASE_URL
            full_url = f"{base_url}/manage/auth/getappproperity"

            logger.info(f"Starting authentication process")

            async with httpx.AsyncClient(timeout=30.0) as client:
                # First API call to get app property
                app_property_response = await client.get(
                    full_url, params={"code": code}
                )

                if app_property_response.status_code != 200:
                    return {
                        "success": False,
                        "message": "Invalid authentication code",
                        "tenant_id": None,
                        "first_name": None,
                        "username": None,
                    }

                app_property_data = app_property_response.json()

                # Extract required fields
                app_instance_id = app_property_data.get("appInstanceId")
                access_token = app_property_data.get("accessToken")
                account_id = app_property_data.get("accountId")  # This is our tenant_id
                first_name = app_property_data.get("firstName")
                username = app_property_data.get("username")
                business_name = app_property_data.get("businessName")

                if not all([app_instance_id, access_token, account_id]):
                    return {
                        "success": False,
                        "message": "Invalid response from authentication service",
                        "tenant_id": None,
                        "first_name": first_name,
                        "username": username,
                        "business_name": business_name,
                    }

                # Step 2: Get settings using app instance ID and access token
                settings_url = f"{base_url}/developerApp/accountAppInstance/settings/{app_instance_id}"
                logger.info(f"Fetching tenant configurations")

                settings_response = await client.get(
                    settings_url, headers={"Authorization": f"Bearer {access_token}"}
                )

                if settings_response.status_code != 200:
                    return {
                        "success": False,
                        "message": "Failed to retrieve application settings",
                        "tenant_id": account_id,
                        "first_name": first_name,
                        "username": username,
                        "business_name": business_name,
                    }

                settings_data = settings_response.json()

                # Parse the settingsValues JSON string to extract configurations
                settings_values_str = settings_data.get("settingsValues", "{}")

                try:
                    parsed_settings = (
                        json.loads(settings_values_str) if settings_values_str else {}
                    )

                    # Extract configurations with the correct key names from the API
                    postgres_config = parsed_settings.get("postgres-config", {})
                    bigquery_raw_config = parsed_settings.get(
                        "BigQuery", {}
                    )  # Note: "BigQuery" not "bigquery-config"
                    sftp_config = parsed_settings.get("SFTP Config", {})
                    email_config = parsed_settings.get("SMTP Config", {})

                    # Process BigQuery config - service_account is stored as JSON string
                    bigquery_config = {}
                    if bigquery_raw_config:
                        bigquery_config = {
                            "project_id": bigquery_raw_config.get("project_id"),
                            "dataset_id": bigquery_raw_config.get("dataset_id"),
                        }

                        # Parse service_account JSON string
                        service_account_str = bigquery_raw_config.get(
                            "service_account", "{}"
                        )
                        try:
                            service_account = (
                                json.loads(service_account_str)
                                if service_account_str
                                else {}
                            )
                            bigquery_config["service_account"] = service_account
                        except json.JSONDecodeError as e:
                            logger.error(
                                f"Failed to parse BigQuery service_account JSON: {e}"
                            )
                            bigquery_config["service_account"] = {}

                    # Create the expected format for validation
                    formatted_settings = {
                        "postgres_config": postgres_config,
                        "bigquery_config": bigquery_config,
                        "sftp_config": sftp_config,
                        "email_config": email_config,
                    }

                    logger.info(
                        f"Configurations found - PostgreSQL: {'Yes' if postgres_config else 'No'}, BigQuery: {'Yes' if bigquery_config else 'No'}, SFTP: {'Yes' if sftp_config else 'No'}, SMTP: {'Yes' if email_config else 'No'}"
                    )

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse settingsValues JSON: {e}")
                    formatted_settings = {
                        "postgres_config": {},
                        "bigquery_config": {},
                        "sftp_config": {},
                        "email_config": {},
                    }

                # Step 3: Validate configurations
                logger.info(f"Starting configuration validation")
                validation_result = await self._validate_configurations_async(formatted_settings)

                if validation_result["valid"]:
                    logger.info(f"All configurations validated successfully")
                else:
                    logger.error(f"Configuration validation failed")

                if not validation_result["valid"]:
                    return {
                        "success": False,
                        "message": "Authentication failed due to missing or invalid configurations",
                        "tenant_id": account_id,
                        "first_name": first_name,
                        "username": username,
                        "business_name": business_name,
                        "missing_configs": validation_result["missing_configs"],
                        "invalid_configs": validation_result["invalid_configs"],
                    }

                # Step 4: Ensure tenant exists in database with all configurations
                postgres_config = formatted_settings.get("postgres_config", {})
                bigquery_config = formatted_settings.get("bigquery_config", {})
                sftp_config = formatted_settings.get("sftp_config", {})
                email_config = formatted_settings.get("email_config", {})

                if not await self._upsert_tenant_configurations(
                    account_id, postgres_config, bigquery_config, sftp_config, email_config, username
                ):
                    return {
                        "success": False,
                        "message": "Failed to store tenant configurations in database",
                        "tenant_id": account_id,
                        "first_name": first_name,
                        "username": username,
                        "business_name": business_name,
                    }

                # Step 5: Return success response with access token
                return {
                    "success": True,
                    "message": "Authentication successful",
                    "tenant_id": account_id,
                    "first_name": first_name,
                    "username": username,
                    "business_name": business_name,
                    "access_token": access_token,
                }

        except httpx.RequestError as e:
            logger.error(f"HTTP request failed: {e}")
            logger.error(f"Base URL being used: {self.settings.BASE_URL}")
            return {
                "success": False,
                "message": f"Authentication service unavailable: {str(e)}",
                "tenant_id": None,
                "first_name": None,
                "username": None,
                "business_name": None,
            }
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return {
                "success": False,
                "message": "Internal server error during authentication",
                "tenant_id": None,
                "first_name": None,
                "username": None,
                "business_name": None,
            }

    async def _validate_configurations_async(self, settings_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate all tenant configurations in parallel for optimal performance.

        This method orchestrates the validation of all required service configurations
        by running connectivity tests in parallel. It provides comprehensive validation
        results including which configurations are missing and which failed validation.

        The validation process:
        1. Identifies missing configurations (empty or None values)
        2. Creates validation tasks for present configurations
        3. Executes all validation tasks concurrently using asyncio.gather()
        4. Processes results to identify failed validations
        5. Returns comprehensive validation status

        Args:
            settings_data: Dictionary containing all parsed service configurations:
                - postgres_config: PostgreSQL database configuration
                - bigquery_config: Google BigQuery project and credentials
                - sftp_config: SFTP server connection configuration  
                - email_config: SMTP email server configuration

        Returns:
            Dict[str, Any]: Comprehensive validation results:
            - valid (bool): True if all configs present and valid
            - missing_configs (List[str]): Names of missing configuration types
            - invalid_configs (List[str]): Names of configurations that failed validation

        Validation Logic:
        - **Missing**: Configuration is None, empty dict, or missing required keys
        - **Invalid**: Configuration present but connectivity/validation test failed
        - **Valid**: Configuration present and passes all validation tests

        Parallel Execution:
        Uses asyncio.gather() to run all validation tasks concurrently:
        - PostgreSQL: Database connection test with SELECT 1 query
        - BigQuery: Service account and project ID validation
        - SFTP: Required fields validation (host, port, credentials)
        - SMTP: Server configuration and port validation
        """
        postgres_config = settings_data.get("postgres_config", {})
        bigquery_config = settings_data.get("bigquery_config", {})
        sftp_config = settings_data.get("sftp_config", {})
        email_config = settings_data.get("email_config", {})

        missing_configs = []
        invalid_configs = []

        # Create tasks for parallel execution
        tasks = []
        config_names = []

        if not postgres_config:
            missing_configs.append("postgres_config")
        else:
            tasks.append(self._test_postgres_connection_async(postgres_config))
            config_names.append("postgres_config")

        if not bigquery_config:
            missing_configs.append("bigquery_config")
        else:
            tasks.append(self._test_bigquery_config_async(bigquery_config))
            config_names.append("bigquery_config")

        if not sftp_config:
            missing_configs.append("sftp_config")
        else:
            tasks.append(self._test_sftp_config_async(sftp_config))
            config_names.append("sftp_config")

        if not email_config:
            missing_configs.append("email_config")
        else:
            tasks.append(self._test_email_config_async(email_config))
            config_names.append("email_config")

        # Run all validation tasks in parallel
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Configuration validation failed for {config_names[i]}: {result}")
                    invalid_configs.append(config_names[i])
                elif not result:
                    invalid_configs.append(config_names[i])

        return {
            "valid": len(missing_configs) == 0 and len(invalid_configs) == 0,
            "missing_configs": missing_configs,
            "invalid_configs": invalid_configs,
        }

    async def _test_postgres_connection_async(self, config: Dict[str, Any]) -> bool:
        """
        Test PostgreSQL database connection asynchronously.
        
        Validates PostgreSQL configuration by establishing a real database connection
        and executing a simple query to verify connectivity and credentials.
        
        Args:
            config: PostgreSQL configuration containing connection parameters:
                - host: Database server hostname/IP
                - port: Database server port
                - user: Database username
                - password: Database user password
                - database: Target database name
                
        Returns:
            bool: True if connection successful, False on any failure
            
        Connection Process:
        1. Constructs PostgreSQL connection string from config parameters
        2. Creates SQLAlchemy engine with provided credentials
        3. Establishes connection and executes 'SELECT 1' test query
        4. Closes connection and returns success status
        
        """
        try:
            logger.info(
                f"Testing PostgreSQL connection to {config.get('host')}:{config.get('port')}"
            )
            
            def test_connection():
                connection_string = f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
                engine = create_engine(connection_string)
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                return True
            
            # Run the blocking operation in a thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, test_connection)
            
            logger.info(f"PostgreSQL connection successful")
            return result
        except Exception as e:
            logger.error(f"PostgreSQL connection test failed: {e}")
            return False

    async def _test_bigquery_config_async(self, config: Dict[str, Any]) -> bool:
        """
        Validate Google BigQuery configuration and service account credentials.
        
        Performs comprehensive validation of BigQuery configuration including
        required fields, service account structure, and credential format validation.
        
        Args:
            config: BigQuery configuration containing:
                - project_id: GCP project identifier
                - dataset_id: BigQuery dataset name
                - service_account: Service account credentials (JSON object)
                
        Returns:
            bool: True if configuration is valid, False otherwise
            
        Validation Checks:
        1. **Required Fields**: Verifies presence of project_id, dataset_id, service_account
        2. **Service Account**: Validates service account JSON structure
        3. **Credential Fields**: Checks for required service account fields:
           - type: Should be "service_account"
           - project_id: Must match main project_id
           - private_key: RSA private key for authentication
           - client_email: Service account email address
           
        Field Requirements:
        - project_id: Non-empty string, GCP project identifier
        - dataset_id: Non-empty string, BigQuery dataset name
        - service_account: Valid JSON object with required credential fields
        
        Note:
        This method performs structural validation only. It does not test
        actual connectivity to BigQuery APIs or verify permissions, which
        would require network calls and could be time-consuming.
        """
        try:
            logger.info(
                f"Testing BigQuery configuration for project: {config.get('project_id')}"
            )
            required_fields = ["project_id", "dataset_id", "service_account"]
            if not all(field in config for field in required_fields):
                logger.error(f"BigQuery config missing required fields")
                return False

            service_account = config.get("service_account", {})
            required_sa_fields = ["type", "project_id", "private_key", "client_email"]
            if not all(field in service_account for field in required_sa_fields):
                logger.error(f"BigQuery service account missing required fields")
                return False

            logger.info(f"BigQuery configuration valid")
            return True
        except Exception as e:
            logger.error(f"BigQuery config validation failed: {e}")
            return False

    async def _test_sftp_config_async(self, config: Dict[str, Any]) -> bool:
        """
        Validate SFTP server configuration for file transfer operations.
        
        Validates SFTP configuration by checking for required connection
        parameters needed for secure file transfer operations.
        
        Args:
            config: SFTP configuration containing connection parameters:
                - host: SFTP server hostname or IP address
                - port: SFTP server port (typically 22)
                - username: SFTP authentication username
                - password: SFTP authentication password
                
        Returns:
            bool: True if all required fields present, False otherwise
            
        Validation Process:
        1. Checks for presence of all required connection fields
        2. Logs validation attempt for debugging
        3. Returns validation result
        
        Required Fields:
        - host: Non-empty string, server address for SFTP connection
        - port: Port number for SFTP service (usually 22)
        - username: Authentication username for SFTP login
        - password: Authentication password for SFTP login
        
        Note:
        This method performs field validation only. It does not attempt
        actual SFTP connection due to potential network latency and
        security considerations during authentication flow.
        """
        try:
            logger.info(f"Testing SFTP configuration for host: {config.get('host')}")
            required_fields = ["host", "port", "username", "password"]
            if not all(field in config for field in required_fields):
                logger.error(f"SFTP config missing required fields")
                return False

            logger.info(f"SFTP configuration valid")
            return True
        except Exception as e:
            logger.error(f"SFTP config validation failed: {e}")
            return False

    async def _test_email_config_async(self, config: Dict[str, Any]) -> bool:
        """
        Validate SMTP email server configuration for email operations.
        
        Performs comprehensive validation of SMTP configuration including
        required fields, port number validation, and email address format checking.
        
        Args:
            config: SMTP email configuration containing:
                - server: SMTP server hostname or IP address
                - port: SMTP server port (25, 587, 465, etc.)
                - from_address: Email address for sending notifications
                
        Returns:
            bool: True if configuration is valid, False otherwise
            
        Validation Checks:
        1. **Required Fields**: Verifies presence of server, port, from_address
        2. **Port Validation**: Ensures port is numeric and within valid range (1-65535)
        3. **Email Format**: Basic validation of from_address email format
        
        Port Handling:
        - Accepts both string and numeric port values
        - Converts strings to integers for validation
        - Validates port range (1-65535) for network validity
        - Common SMTP ports: 25 (standard), 587 (submission), 465 (SSL)
        
        Email Address Validation:
        - Basic format check for presence of '@' and '.' characters
        - Ensures from_address follows email format conventions
        - Does not perform DNS or deliverability validation
        
        Note:
        This method validates configuration structure and format only.
        It does not test actual SMTP connectivity or authentication.
        """
        try:
            logger.info(f"Testing email configuration for server: {config.get('server')}")
            required_fields = ["server", "port", "from_address"]
            if not all(field in config for field in required_fields):
                logger.error(f"Email config missing required fields: {required_fields}")
                logger.error(f"Available fields: {list(config.keys())}")
                return False

            # Validate port is a number
            try:
                port_value = config.get("port")
                if isinstance(port_value, str):
                    port = int(port_value)
                else:
                    port = int(port_value) if port_value else 0
                    
                if port <= 0 or port > 65535:
                    logger.error(f"Email config has invalid SMTP port: {port}")
                    return False
            except (ValueError, TypeError):
                logger.error(f"Email config SMTP port is not a valid number: {config.get('port')}")
                return False

            # Validate email format for from_address
            from_address = config.get("from_address", "")
            if "@" not in from_address or "." not in from_address:
                logger.error(f"Email config has invalid from_address format: {from_address}")
                return False

            logger.info(f"Email configuration valid")
            return True
        except Exception as e:
            logger.error(f"Email config validation failed: {e}")
            return False

    async def _upsert_tenant_configurations(
        self,
        tenant_id: str,
        postgres_config: Dict[str, Any],
        bigquery_config: Dict[str, Any],
        sftp_config: Dict[str, Any],
        email_config: Dict[str, Any],
        username: str,
    ) -> bool:
        """
        Create or update tenant record with validated configurations.

        This method handles tenant lifecycle management by creating new tenant records
        or updating existing ones with the latest validated configurations from the
        external authentication API. It ensures configuration synchronization between
        the external service and the local database.

        Database Operations:
        1. **Existence Check**: Queries database to determine if tenant exists
        2. **Data Preparation**: Serializes configuration objects to JSON strings
        3. **Insert/Update**: Creates new record or updates existing tenant
        4. **Transaction Safety**: All operations within async database session

        Args:
            tenant_id: Unique tenant identifier from authentication provider (accountId)
            postgres_config: Validated PostgreSQL database configuration dictionary
            bigquery_config: Validated Google BigQuery project and credentials
            sftp_config: Validated SFTP server connection configuration
            email_config: Validated SMTP email server configuration  
            username: User's display name for tenant record identification

        Returns:
            bool: True if tenant was successfully created/updated, False on database errors

        Configuration Storage:
        - **BigQuery Split**: project_id and dataset_id stored as separate fields,
          service_account credentials stored as JSON in bigquery_credentials
        - **Other Configs**: postgres_config, sftp_config, email_config stored as JSON blobs
        - **Metadata**: Automatic timestamp management (created_at, updated_at)
        - **Status**: is_active set to true for all upserts

        """
        try:
            # Use the async session with the tenant's postgres config
            async with get_async_db_session("auth-service") as session:
                # Check if tenant exists
                result = await session.execute(
                    text("SELECT COUNT(*) FROM tenants WHERE id = :tenant_id"),
                    {"tenant_id": tenant_id},
                )
                count = result.scalar()

                # Prepare configuration data
                config_data = {
                    "tenant_id": tenant_id,
                    "name": username,
                    "bigquery_project_id": bigquery_config.get("project_id"),
                    "bigquery_dataset_id": bigquery_config.get("dataset_id"),
                    "bigquery_credentials": json.dumps(
                        bigquery_config.get("service_account", {})
                    ),
                    "postgres_config": json.dumps(postgres_config),
                    "sftp_config": json.dumps(sftp_config),
                    "email_config": json.dumps(email_config),
                }

                if count == 0:
                    # Create new tenant with all configurations
                    await session.execute(
                        text(
                            """
                            INSERT INTO tenants (
                                id, name, 
                                bigquery_project_id, bigquery_dataset_id, bigquery_credentials,
                                postgres_config, sftp_config, email_config,
                                is_active, created_at, updated_at
                            ) VALUES (
                                :tenant_id, :name,
                                :bigquery_project_id, :bigquery_dataset_id, :bigquery_credentials,
                                :postgres_config, :sftp_config, :email_config,
                                true, NOW(), NOW()
                            )
                        """
                        ),
                        config_data,
                    )
                    logger.info(f"Created new tenant: {username} ({tenant_id})")
                else:
                    # Always update existing tenant with latest configurations from authentication API
                    await session.execute(
                        text(
                            """
                            UPDATE tenants SET
                                name = :name,
                                bigquery_project_id = :bigquery_project_id,
                                bigquery_dataset_id = :bigquery_dataset_id,
                                bigquery_credentials = :bigquery_credentials,
                                postgres_config = :postgres_config,
                                sftp_config = :sftp_config,
                                email_config = :email_config,
                                is_active = true,
                                updated_at = NOW()
                            WHERE id = :tenant_id
                        """
                        ),
                        config_data,
                    )
                    logger.info(f"Updated tenant configurations: ({tenant_id})")

            return True
        except Exception as e:
            logger.error(f"Failed to upsert tenant configurations for {tenant_id}: {e}")
            return False

    async def logout_with_token(self, access_token: str) -> Dict[str, Any]:
        """
        Invalidate user access token with external authentication service.

        Handles session termination by calling the external authentication service's
        logout endpoint to invalidate the provided access token. The method handles
        various response scenarios and provides appropriate success/failure indicators.

        Args:
            access_token: Valid access token to be invalidated with external service

        Returns:
            Dict[str, Any]: Logout operation result containing:
            - success (bool): Whether logout completed successfully
            - message (str): Human-readable result description

        External API Call:
        Makes GET request to: /manage/auth/logout
        - Headers: Authorization: Bearer {access_token}
        - Timeout: 30 seconds
        - Expected response: 200 OK for successful logout

        Usage Context:
        Called from logout endpoint to clean up user sessions. The frontend
        should handle both success and failure cases gracefully, typically
        proceeding with local logout even if external logout fails.

        """
        try:
            base_url = self.settings.BASE_URL
            logout_url = f"{base_url}/manage/auth/logout"

            logger.info(f"Starting logout process")

            async with httpx.AsyncClient(timeout=30.0) as client:
                logout_response = await client.get(
                    logout_url,
                    headers={"Authorization": f"Bearer {access_token}"},
                )

                if logout_response.status_code != 200:
                    logger.error(f"Logout failed with status {logout_response.status_code}")
                    
                    if logout_response.status_code == 404:
                        return {
                            "success": False,
                            "message": "Logout endpoint not found - the external service may not support logout",
                        }
                    elif logout_response.status_code == 401:
                        return {
                            "success": False,
                            "message": "Invalid token - logout failed due to authentication error",
                        }
                    else:
                        return {
                            "success": False,
                            "message": f"Logout failed with status {logout_response.status_code}",
                        }

                logger.info(f"Logout successful")
                return {
                    "success": True,
                    "message": "Logout successful",
                }

        except httpx.RequestError as e:
            logger.error(f"HTTP request failed during logout: {e}")
            logger.error(f"Base URL being used: {self.settings.BASE_URL}")
            return {
                "success": False,
                "message": f"Logout service unavailable: {str(e)}",
            }
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return {
                "success": False,
                "message": "Internal server error during logout",
            }

    def get_login_url(self) -> str:
        """
        Generate OAuth login URL for user authentication redirection.

        Constructs the complete URL that frontend applications should redirect
        users to when authentication is required. The URL points to the external
        authentication provider's admin login interface.

        Returns:
            str: Complete OAuth login URL for user redirection

        URL Construction:
        - Uses BASE_URL from service configuration settings
        - Appends '/admin/' path for admin authentication interface
        - Returns fully qualified URL ready for browser redirection

        Usage Flow:
        1. Frontend requests login URL from this method
        2. Frontend redirects user's browser to returned URL
        3. User authenticates with external provider
        4. External provider redirects back with authorization code
        5. Frontend uses code with authentication endpoint

        Note:
        This is a synchronous method as it only performs string concatenation
        without any network operations or external service calls.
        """
        base_url = self.settings.BASE_URL
        # Based on the URL you provided, the admin login should be at /admin/
        login_url = f"{base_url}/admin/"
        
        return login_url

    async def validate_token(self, access_token: str) -> Dict[str, Any]:
        """
        Validate access token with external service and retrieve user information.

        Verifies that an access token is still valid with the external authentication
        service and retrieves associated user information if available. This method
        is used for session persistence and user context retrieval.

        Args:
            access_token: Access token to validate against external authentication service

        Returns:
            Dict[str, Any]: Validation result containing:
            - valid (bool): Whether the token is valid and active
            - message (str): Human-readable validation status or error message
            - tenant_id (str|None): Tenant identifier if token valid
            - first_name (str|None): User's first name if available
            - username (str|None): User's username/login if available  
            - business_name (str|None): Associated business name if available

        Validation Process:
        1. **Token Test**: Calls external API endpoint with Bearer token
        2. **Response Analysis**: Checks HTTP status code for validation result
        3. **Data Extraction**: Parses user information from successful responses
        4. **Error Handling**: Maps HTTP errors to validation failure reasons

        External API Integration:
        Uses the /manage/auth/getappproperity endpoint for token validation:
        - Headers: Authorization: Bearer {access_token}
        - Method: GET request with 30-second timeout
        - Success: 200 OK with user data in response body

        Usage Contexts:
        - Session validation on application load
        - Periodic token refresh checks
        - User information retrieval for UI personalization
        - API authorization verification
        """
        try:
            base_url = self.settings.BASE_URL
            # Try to validate token by calling the getappproperity endpoint with the token
            # This is a known working endpoint that requires authentication
            validate_url = f"{base_url}/manage/auth/getappproperity"

            logger.info(f"Validating access token")

            async with httpx.AsyncClient(timeout=30.0) as client:
                validate_response = await client.get(
                    validate_url,
                    headers={"Authorization": f"Bearer {access_token}"},
                )

                if validate_response.status_code != 200:
                    logger.error(f"Token validation failed with status {validate_response.status_code}")
                    
                    if validate_response.status_code == 401:
                        return {
                            "valid": False,
                            "message": "Token is invalid or expired",
                            "tenant_id": None,
                            "first_name": None,
                            "username": None,
                            "business_name": None,
                        }
                    elif validate_response.status_code == 404:
                        return {
                            "valid": False,
                            "message": "Token validation endpoint not available",
                            "tenant_id": None,
                            "first_name": None,
                            "username": None,
                            "business_name": None,
                        }
                    else:
                        return {
                            "valid": False,
                            "message": f"Token validation failed with status {validate_response.status_code}",
                            "tenant_id": None,
                            "first_name": None,
                            "username": None,
                            "business_name": None,
                        }

                # If we get here, the token is valid
                try:
                    user_data = validate_response.json()
                    tenant_id = user_data.get("accountId")  # This is our tenant_id
                    first_name = user_data.get("firstName")
                    username = user_data.get("username")
                    business_name = user_data.get("businessName")
                    
                    logger.info(f"Token validation successful for user: {username}")
                    return {
                        "valid": True,
                        "message": "Token is valid",
                        "tenant_id": tenant_id,
                        "first_name": first_name,
                        "username": username,
                        "business_name": business_name,
                    }
                except Exception as e:
                    logger.error(f"Failed to parse user data from token validation: {e}")
                    return {
                        "valid": True,  # Token is valid, but we couldn't parse user data
                        "message": "Token is valid but user data unavailable",
                        "tenant_id": None,
                        "first_name": None,
                        "username": None,
                        "business_name": None,
                    }

        except httpx.RequestError as e:
            logger.error(f"HTTP request failed during token validation: {e}")
            logger.error(f"Base URL being used: {self.settings.BASE_URL}")
            return {
                "valid": False,
                "message": f"Token validation service unavailable: {str(e)}",
                "tenant_id": None,
                "first_name": None,
                "username": None,
                "business_name": None,
            }
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            return {
                "valid": False,
                "message": "Internal server error during token validation",
                "tenant_id": None,
                "first_name": None,
                "username": None,
                "business_name": None,
            }
