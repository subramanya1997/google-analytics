"""
Authentication Service - Core Business Logic

This module implements the core authentication and tenant management business logic
for the authentication service. It handles OAuth 2.0 flows, tenant configuration
validation, and database provisioning.

The service follows a layered architecture:
    - API Layer: FastAPI endpoints (services.auth_service.api.v1.endpoints)
    - Service Layer: This module (business logic)
    - Database Layer: Common database utilities (common.database)

Key Responsibilities:
    1. OAuth 2.0 Authorization Code Exchange
       - Exchange authorization code for access token
       - Retrieve tenant configurations from external IdP
       - Validate and store tenant configurations

    2. Configuration Validation
       - PostgreSQL: Required, validated synchronously (blocks login if invalid)
       - BigQuery: Optional, validated asynchronously
       - SFTP: Optional, validated asynchronously
       - SMTP: Optional, validated asynchronously

    3. Tenant Management
       - Automatic database provisioning for new tenants
       - Configuration updates for existing tenants
       - Tenant configuration persistence

    4. Token Management
       - Token validation against external IdP
       - User information retrieval from tokens
       - Token invalidation (logout)

Architecture Patterns:
    - Stateless: No session storage, all tokens validated against IdP
    - Multi-tenant: Each tenant has isolated database
    - Graceful Degradation: Optional services don't block authentication
    - Async-first: All I/O operations are asynchronous

Example:
    ```python
    service = AuthenticationService()
    
    # Authenticate user
    result = await service.authenticate_with_code("oauth_code")
    if result["success"]:
        access_token = result["access_token"]
        tenant_id = result["tenant_id"]
    
    # Validate token
    validation = await service.validate_token(access_token)
    if validation["valid"]:
        user_info = {
            "tenant_id": validation["tenant_id"],
            "username": validation["username"]
        }
    ```

See Also:
    - services.auth_service.api.v1.endpoints.auth: API endpoints using this service
    - common.database: Database utilities for tenant management
    - common.config: Configuration management
"""

import asyncio
import json
from typing import Any

import httpx
from loguru import logger
from sqlalchemy import create_engine, text

from common.config import get_settings
from common.database import get_async_db_session, provision_tenant_database


class AuthenticationService:
    """
    Core authentication service for OAuth 2.0 flows and tenant management.

    This service handles the complete authentication lifecycle:
    - OAuth authorization code exchange
    - Tenant configuration retrieval and validation
    - Database provisioning for new tenants
    - Token validation and user information retrieval
    - Session termination (logout)

    The service is stateless and validates all tokens against an external
    Identity Provider. It manages tenant-specific configurations including
    PostgreSQL, BigQuery, SFTP, and SMTP settings.

    Attributes:
        settings: Service configuration settings loaded from environment
            variables. Includes BASE_URL for external IdP, service name,
            version, and other runtime configuration.

    Example:
        ```python
        # Initialize service
        auth_service = AuthenticationService()
        
        # Authenticate user with OAuth code
        result = await auth_service.authenticate_with_code("code_123")
        
        # Validate access token
        validation = await auth_service.validate_token("token_xyz")
        
        # Get login URL
        login_url = auth_service.get_login_url()
        
        # Logout user
        logout_result = await auth_service.logout_with_token("token_xyz")
        ```

    Note:
        - All methods are async to support non-blocking I/O
        - PostgreSQL validation is required and blocks authentication
        - Optional service validations are logged but don't block login
        - New tenants automatically get provisioned databases
    """

    def __init__(self) -> None:
        """
        Initialize the authentication service.

        Loads service-specific configuration settings from environment variables
        using the common configuration system. The settings include:
        - BASE_URL: External Identity Provider base URL
        - SERVICE_NAME: Service identifier ("auth-service")
        - SERVICE_VERSION: Service version string
        - Other service-specific configuration

        Raises:
            ConfigurationError: If required configuration is missing or invalid.
                This typically indicates environment variables are not set correctly.
        """
        self.settings = get_settings("auth-service")

    async def authenticate_with_code(self, code: str) -> dict[str, Any]:
        """
        Authenticate user with OAuth authorization code and validate tenant configurations.

        This method implements the OAuth 2.0 authorization code exchange flow:
        1. Exchange authorization code for access token via external IdP
        2. Retrieve tenant application settings and configurations
        3. Parse and extract PostgreSQL, BigQuery, SFTP, and SMTP configurations
        4. Validate PostgreSQL configuration (required, synchronous)
        5. Log warnings for missing optional configurations
        6. Provision tenant database if new tenant
        7. Store/update tenant configurations in database
        8. Return authentication result with access token

        The method performs synchronous validation for PostgreSQL (required) but
        handles optional service configurations gracefully without blocking authentication.

        Args:
            code (str): OAuth 2.0 authorization code received from IdP redirect.
                This is a temporary, single-use code typically 20-200 characters.
                Must be valid and not expired.

        Returns:
            dict[str, Any]: Authentication result dictionary with keys:
                - success (bool): Whether authentication succeeded
                - message (str): Human-readable status message
                - tenant_id (str | None): Tenant UUID if successful
                - first_name (str | None): User's first name
                - username (str | None): User's email/username
                - business_name (str | None): Tenant's business name
                - access_token (str | None): OAuth access token (if successful)
                - missing_configs (list[str] | None): Missing required configs
                - invalid_configs (list[str] | None): Invalid configs

        Raises:
            httpx.RequestError: If HTTP request to external IdP fails (network error,
                timeout, connection refused). Caught and returned as error response.
            json.JSONDecodeError: If response from IdP is not valid JSON. Caught and
                logged, returns error response.
            Exception: Any unexpected error during authentication. Caught and logged,
                returns generic error response.

        Example:
            ```python
            service = AuthenticationService()
            result = await service.authenticate_with_code("4/0AeanS0b...")
            
            if result["success"]:
                print(f"Authenticated tenant: {result['tenant_id']}")
                print(f"Access token: {result['access_token']}")
            else:
                print(f"Authentication failed: {result['message']}")
                if result.get("missing_configs"):
                    print(f"Missing: {result['missing_configs']}")
            ```

        Note:
            - PostgreSQL configuration is REQUIRED - authentication fails if missing/invalid
            - BigQuery, SFTP, SMTP are OPTIONAL - warnings logged but don't block login
            - New tenants automatically get provisioned databases
            - Existing tenant configurations are always updated with latest values
            - All HTTP requests have 30-second timeout
            - Configuration parsing handles JSON strings and nested structures
        """
        try:
            # Step 1: Get app property using the code
            base_url = self.settings.BASE_URL
            full_url = f"{base_url}/manage/auth/getappproperity"

            logger.info("Starting authentication process")

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
                logger.info("Fetching tenant configurations")

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
                        "bigquery_config": bigquery_config,
                        "sftp_config": sftp_config,
                        "email_config": email_config,
                    }

                    logger.info(
                        f"Configurations found - BigQuery: {'Yes' if bigquery_config else 'No'}, SFTP: {'Yes' if sftp_config else 'No'}, SMTP: {'Yes' if email_config else 'No'}"
                    )

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse settingsValues JSON: {e}")
                    formatted_settings = {
                        "bigquery_config": {},
                        "sftp_config": {},
                        "email_config": {},
                    }

                # Step 3: Validate configurations
                logger.info("Starting configuration validation")
                validation_result = await self._validate_configurations_async(
                    formatted_settings
                )

                if validation_result["valid"]:
                    logger.info("All configurations validated successfully")
                else:
                    logger.error("Configuration validation failed")

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
                bigquery_config = formatted_settings.get("bigquery_config", {})
                sftp_config = formatted_settings.get("sftp_config", {})
                email_config = formatted_settings.get("email_config", {})

                if not await self._upsert_tenant_configurations(
                    account_id,
                    bigquery_config,
                    sftp_config,
                    email_config,
                    username,
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
                "message": f"Authentication service unavailable: {e!s}",
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

    async def _validate_configurations_async(
        self, settings_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Validate tenant configurations - all configurations are optional.

        This method validates tenant configurations retrieved from the external IdP.
        All configurations (BigQuery, SFTP, SMTP) are optional and warnings are logged
        if any are missing.

        Validation Rules:
            - BigQuery: OPTIONAL - Logged as warning if missing
            - SFTP: OPTIONAL - Logged as warning if missing
            - SMTP: OPTIONAL - Logged as warning if missing

        Args:
            settings_data (dict[str, Any]): Configuration data from IdP API with keys:
                - bigquery_config (dict): BigQuery configuration (optional)
                - sftp_config (dict): SFTP configuration (optional)
                - email_config (dict): SMTP configuration (optional)

        Returns:
            dict[str, Any]: Validation result dictionary with keys:
                - valid (bool): Always True (no required configurations)
                - missing_configs (list[str]): Always empty list
                - invalid_configs (list[str]): Always empty list

        Example:
            ```python
            settings = {
                "bigquery_config": {},  # Optional
                "sftp_config": {},  # Optional
                "email_config": {}  # Optional
            }
            
            result = await service._validate_configurations_async(settings)
            # Returns: {"valid": True, "missing_configs": [], "invalid_configs": []}
            ```

        Note:
            - Missing optional configs are logged as warnings, not errors
            - Authentication proceeds regardless of configuration availability
        """
        bigquery_config = settings_data.get("bigquery_config", {})
        sftp_config = settings_data.get("sftp_config", {})
        email_config = settings_data.get("email_config", {})

        # All configs are OPTIONAL - just log warnings if missing
        if not bigquery_config:
            logger.warning(
                "Optional BigQuery configuration is missing - data ingestion from BigQuery will not be available"
            )

        if not sftp_config:
            logger.warning(
                "Optional SFTP configuration is missing - SFTP file operations will not be available"
            )

        if not email_config:
            logger.warning(
                "Optional Email/SMTP configuration is missing - email sending will not be available"
            )

        logger.info(
            "Configuration validation successful (optional configs logged)"
        )
        return {
            "valid": True,
            "missing_configs": [],
            "invalid_configs": [],
        }

    async def _upsert_tenant_configurations(
        self,
        tenant_id: str,
        bigquery_config: dict[str, Any],
        sftp_config: dict[str, Any],
        email_config: dict[str, Any],
        username: str,
    ) -> bool:
        """
        Create or update tenant configurations in the database.

        This method handles both new tenant provisioning and existing tenant
        configuration updates. For new tenants, it provisions a complete database
        with all required tables and functions before storing configurations.

        Configuration Update Strategy:
            - New tenants: Creates tenant database, then inserts configuration
            - Existing tenants: Always updates with latest values from IdP
            - All configurations are stored as JSON strings in the database
            - Configurations are encrypted at rest by the database layer

        Database Provisioning:
            For new tenants, this method calls provision_tenant_database() which:
            1. Creates a new PostgreSQL database for the tenant
            2. Creates all required tables (users, events, tenant_config, etc.)
            3. Creates all database functions (get_chart_data, etc.)
            4. Sets up proper permissions and indexes

        Args:
            tenant_id (str): Unique tenant identifier (UUID format). Used as:
                - Database name for tenant isolation
                - Primary key in tenant_config table
            bigquery_config (dict[str, Any]): BigQuery configuration dictionary.
                Extracted fields: project_id, dataset_id, service_account.
                Stored in separate columns: bigquery_project_id, bigquery_dataset_id,
                bigquery_credentials (JSON string).
            sftp_config (dict[str, Any]): SFTP configuration dictionary.
                Stored as JSON string in tenant_config.sftp_config column.
            email_config (dict[str, Any]): SMTP/Email configuration dictionary.
                Stored as JSON string in tenant_config.email_config column.
            username (str): User's email/username for tenant identification.
                Stored in tenant_config.name column.

        Returns:
            bool: True if tenant configuration was successfully created/updated,
                False if provisioning failed or database operation failed.

        Raises:
            Exception: Any exception during database operations is caught, logged,
                and returns False. Common exceptions:
                - sqlalchemy.exc.OperationalError: Database connection failed
                - sqlalchemy.exc.IntegrityError: Constraint violation
                - json.JSONEncodeError: Configuration serialization failed

        Example:
            ```python
            result = await service._upsert_tenant_configurations(
                tenant_id="550e8400-e29b-41d4-a716-446655440000",
                bigquery_config={"project_id": "my-project", "dataset_id": "analytics"},
                sftp_config={"host": "sftp.example.com", "port": 22, ...},
                email_config={"server": "smtp.example.com", "port": 587, ...},
                username="john@company.com"
            )
            
            if result:
                print("Tenant configuration stored successfully")
            ```

        Note:
            - Always updates existing tenant configurations (never skips updates)
            - New tenants get automatic database provisioning
            - All configurations stored as JSON strings for flexibility
            - BigQuery credentials stored separately for easier access
            - Sets is_active=True and updates timestamps (created_at, updated_at)
            - Uses tenant-specific database session for proper isolation
        """
        try:
            # First, check if this is a new tenant by checking if their database exists
            from common.database import tenant_database_exists

            is_new_tenant = not tenant_database_exists(tenant_id)

            if is_new_tenant:
                # Provision the tenant database (creates DB and all tables/functions)
                logger.info(
                    f"Provisioning new tenant database for tenant {tenant_id}..."
                )
                provisioned = await provision_tenant_database(tenant_id)

                if not provisioned:
                    logger.error(f"Failed to provision database for tenant {tenant_id}")
                    return False

                logger.info(
                    f"Successfully provisioned tenant database for tenant {tenant_id}"
                )

            # Use tenant-specific database session for inserting/updating tenant config
            async with get_async_db_session(
                "auth-service", tenant_id=tenant_id
            ) as session:
                # Prepare configuration data
                config_data = {
                    "tenant_id": tenant_id,
                    "name": username,
                    "bigquery_project_id": bigquery_config.get("project_id"),
                    "bigquery_dataset_id": bigquery_config.get("dataset_id"),
                    "bigquery_credentials": json.dumps(
                        bigquery_config.get("service_account", {})
                    ),
                    "sftp_config": json.dumps(sftp_config),
                    "email_config": json.dumps(email_config),
                }

                if is_new_tenant:
                    # Create new tenant config record in their own database
                    await session.execute(
                        text(
                            """
                            INSERT INTO tenant_config (
                                id, name,
                                bigquery_project_id, bigquery_dataset_id, bigquery_credentials,
                                sftp_config, email_config,
                                is_active, created_at, updated_at
                            ) VALUES (
                                :tenant_id, :name,
                                :bigquery_project_id, :bigquery_dataset_id, :bigquery_credentials,
                                :sftp_config, :email_config,
                                true, NOW(), NOW()
                            )
                        """
                        ),
                        config_data,
                    )
                    logger.info(f"Created new tenant config: {username} ({tenant_id})")
                else:
                    # Always update existing tenant config with latest configurations from authentication API
                    await session.execute(
                        text(
                            """
                            UPDATE tenant_config SET
                                name = :name,
                                bigquery_project_id = :bigquery_project_id,
                                bigquery_dataset_id = :bigquery_dataset_id,
                                bigquery_credentials = :bigquery_credentials,
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

    async def logout_with_token(self, access_token: str) -> dict[str, Any]:
        """
        Logout user by invalidating the access token with external Identity Provider.

        This method calls the external IdP's logout endpoint to invalidate the
        access token. It implements graceful error handling to allow frontend
        cleanup even if external logout fails (e.g., token already invalid, endpoint
        not found).

        Error Handling Strategy:
            - 200 OK: Logout successful
            - 404 Not Found: Endpoint not available (returns error but allows local cleanup)
            - 401 Unauthorized: Token already invalid (returns error but allows local cleanup)
            - Other errors: Returns error message
            - Network errors: Returns service unavailable message

        Args:
            access_token (str): OAuth access token (Bearer token) to invalidate.
                This token will be sent to the external IdP for revocation.
                Format: "Bearer token_string" or just "token_string"

        Returns:
            dict[str, Any]: Logout result dictionary with keys:
                - success (bool): Whether logout operation completed successfully
                - message (str): Human-readable status message

        Raises:
            httpx.RequestError: If HTTP request fails (network error, timeout).
                Caught and returned as error response with success=False.
            Exception: Any unexpected error during logout. Caught and logged,
                returns generic error response.

        Example:
            ```python
            result = await service.logout_with_token("bearer_token_here")
            
            if result["success"]:
                print("Logout successful")
            else:
                print(f"Logout failed: {result['message']}")
                # Frontend should still proceed with local cleanup
            ```

        Note:
            - Uses 30-second timeout for HTTP requests
            - Returns success=False for 404/401 but frontend should still cleanup
            - Only raises exception for service unavailability (503)
            - Logs all errors for debugging purposes
        """
        try:
            base_url = self.settings.BASE_URL
            logout_url = f"{base_url}/manage/auth/logout"

            logger.info("Starting logout process")

            async with httpx.AsyncClient(timeout=30.0) as client:
                logout_response = await client.get(
                    logout_url,
                    headers={"Authorization": f"Bearer {access_token}"},
                )

                if logout_response.status_code != 200:
                    logger.error(
                        f"Logout failed with status {logout_response.status_code}"
                    )

                    if logout_response.status_code == 404:
                        return {
                            "success": False,
                            "message": "Logout endpoint not found - the external service may not support logout",
                        }
                    if logout_response.status_code == 401:
                        return {
                            "success": False,
                            "message": "Invalid token - logout failed due to authentication error",
                        }
                    return {
                        "success": False,
                        "message": f"Logout failed with status {logout_response.status_code}",
                    }

                logger.info("Logout successful")
                return {
                    "success": True,
                    "message": "Logout successful",
                }

        except httpx.RequestError as e:
            logger.error(f"HTTP request failed during logout: {e}")
            logger.error(f"Base URL being used: {self.settings.BASE_URL}")
            return {
                "success": False,
                "message": f"Logout service unavailable: {e!s}",
            }
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return {
                "success": False,
                "message": "Internal server error during logout",
            }

    def get_login_url(self) -> str:
        """
        Get the OAuth login URL for redirecting users to the Identity Provider.

        This method constructs the complete login URL by combining the BASE_URL
        from service settings with the admin login path. The URL is used by the
        frontend to redirect users to the external IdP's authentication page.

        The constructed URL follows the pattern: "{BASE_URL}/admin/"

        Returns:
            str: Complete OAuth login URL where users should be redirected.
                Example: "https://idp.example.com/admin/"

        Example:
            ```python
            login_url = service.get_login_url()
            # Returns: "https://idp.example.com/admin/"
            
            # Frontend redirects user
            window.location.href = login_url
            ```

        Note:
            - URL is constructed from BASE_URL environment variable
            - Path "/admin/" is hardcoded based on IdP API structure
            - This is a synchronous method (no I/O required)
            - Users will be redirected back to frontend with authorization code
        """
        base_url = self.settings.BASE_URL
        # Based on the URL you provided, the admin login should be at /admin/
        return f"{base_url}/admin/"


    async def validate_token(self, access_token: str) -> dict[str, Any]:
        """
        Validate an access token and return associated user and tenant information.

        This method validates an OAuth access token by calling the external IdP's
        authentication endpoint. If the token is valid, it extracts and returns
        user information including tenant ID, username, and business name.

        The validation is performed synchronously against the external IdP to
        ensure token authenticity. This method is used by other services (analytics,
        data) to verify tokens before processing requests.

        Args:
            access_token (str): OAuth access token (Bearer token) to validate.
                This token is sent to the external IdP for validation.
                Format: "Bearer token_string" or just "token_string"

        Returns:
            dict[str, Any]: Validation result dictionary with keys:
                - valid (bool): Whether the token is valid and not expired
                - message (str): Human-readable validation status message
                - tenant_id (str | None): Tenant UUID if token is valid
                - first_name (str | None): User's first name if token is valid
                - username (str | None): User's email/username if token is valid
                - business_name (str | None): Tenant's business name if token is valid

        Raises:
            httpx.RequestError: If HTTP request fails (network error, timeout).
                Caught and returned as error response with valid=False.
            json.JSONDecodeError: If response is not valid JSON. Caught and logged,
                returns valid=True with unavailable user data.
            Exception: Any unexpected error during validation. Caught and logged,
                returns generic error response.

        Example:
            ```python
            # In another service
            validation = await service.validate_token("bearer_token_here")
            
            if validation["valid"]:
                tenant_id = validation["tenant_id"]
                username = validation["username"]
                # Process request with tenant context
            else:
                # Return 401 Unauthorized to client
                raise HTTPException(401, validation["message"])
            ```

        Note:
            - Uses getappproperity endpoint for validation (known working endpoint)
            - Returns valid=False (not exception) for invalid tokens
            - Handles 401 (invalid/expired) and 404 (endpoint not found) gracefully
            - User data parsing errors don't invalidate token (returns valid=True)
            - Uses 30-second timeout for HTTP requests
            - All errors are logged for debugging purposes
        """
        try:
            base_url = self.settings.BASE_URL
            # Try to validate token by calling the getappproperity endpoint with the token
            # This is a known working endpoint that requires authentication
            validate_url = f"{base_url}/manage/auth/getappproperity"

            logger.info("Validating access token")

            async with httpx.AsyncClient(timeout=30.0) as client:
                validate_response = await client.get(
                    validate_url,
                    headers={"Authorization": f"Bearer {access_token}"},
                )

                if validate_response.status_code != 200:
                    logger.error(
                        f"Token validation failed with status {validate_response.status_code}"
                    )

                    if validate_response.status_code == 401:
                        return {
                            "valid": False,
                            "message": "Token is invalid or expired",
                            "tenant_id": None,
                            "first_name": None,
                            "username": None,
                            "business_name": None,
                        }
                    if validate_response.status_code == 404:
                        return {
                            "valid": False,
                            "message": "Token validation endpoint not available",
                            "tenant_id": None,
                            "first_name": None,
                            "username": None,
                            "business_name": None,
                        }
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
                    logger.error(
                        f"Failed to parse user data from token validation: {e}"
                    )
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
                "message": f"Token validation service unavailable: {e!s}",
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
