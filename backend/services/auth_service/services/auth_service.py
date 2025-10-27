"""
Authentication service business logic.
"""

import asyncio
import json
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException, status as http_status
from loguru import logger
from sqlalchemy import create_engine, text

from common.config import get_settings
from common.database import get_async_db_session


class AuthenticationService:
    """Service for handling authentication and configuration validation."""

    def __init__(self):
        """Initialize the authentication service."""
        self.settings = get_settings("auth-service")

    async def authenticate_with_code(self, code: str) -> Dict[str, Any]:
        """
        Authenticate user with code and validate configurations.

        Args:
            code: Authentication code from the client

        Returns:
            Dict containing authentication result
        """
        try:
            # Step 1: Get app property using the code
            base_url = self.settings.BASE_URL
            full_url = f"{base_url}/manage/auth/getappproperity"

            async with httpx.AsyncClient(timeout=30.0) as client:
                # First API call to get app property
                app_property_response = await client.get(
                    full_url, params={"code": code}
                )

                if app_property_response.status_code != 200:
                    raise HTTPException(
                        status_code=http_status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid authentication code"
                    )

                app_property_data = app_property_response.json()

                # Extract required fields
                app_instance_id = app_property_data.get("appInstanceId")
                access_token = app_property_data.get("accessToken")
                account_id = app_property_data.get("accountId")  # This is our tenant_id
                first_name = app_property_data.get("firstName")
                username = app_property_data.get("username")
                business_name = app_property_data.get("businessName")

                if not all([app_instance_id, access_token, account_id]):
                    raise HTTPException(
                        status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Invalid response from authentication service"
                    )

                # Step 2: Get settings using app instance ID and access token
                settings_url = f"{base_url}/developerApp/accountAppInstance/settings/{app_instance_id}"

                settings_response = await client.get(
                    settings_url, headers={"Authorization": f"Bearer {access_token}"}
                )

                if settings_response.status_code != 200:
                    raise HTTPException(
                        status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to retrieve application settings"
                    )

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

                # Step 3: Validate PostgreSQL configuration synchronously (blocking)
                postgres_config = formatted_settings.get("postgres_config", {})
                bigquery_config = formatted_settings.get("bigquery_config", {})
                sftp_config = formatted_settings.get("sftp_config", {})
                email_config = formatted_settings.get("email_config", {})
                
                if not postgres_config:
                    raise HTTPException(
                        status_code=http_status.HTTP_401_UNAUTHORIZED,
                        detail="PostgreSQL configuration is missing - authentication cannot proceed"
                    )
                
                # Test PostgreSQL connection - must succeed for authentication
                postgres_valid = await self._test_postgres_connection_async(postgres_config)
                if not postgres_valid:
                    raise HTTPException(
                        status_code=http_status.HTTP_401_UNAUTHORIZED,
                        detail="PostgreSQL connection failed - authentication cannot proceed"
                    )

                # Step 4: Store tenant configurations in database
                # Service validation happens in background
                if not await self._upsert_tenant_configurations(
                    account_id, postgres_config, bigquery_config, sftp_config, email_config, username
                ):
                    raise HTTPException(
                        status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to store tenant configurations in database"
                    )
                
                # Step 5: Validate other services in background (non-blocking)
                # This will update service status in database without blocking authentication
                asyncio.create_task(
                    self._validate_and_update_services_async(
                        account_id, bigquery_config, sftp_config, email_config
                    )
                )
                logger.info(f"Background service validation triggered for tenant {account_id}")

                logger.info(f"Access token: {access_token}")

                # Step 6: Return success response with access token
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
            raise HTTPException(
                status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Authentication service unavailable: {str(e)}"
            )
        except HTTPException:
            # Re-raise HTTPExceptions as-is
            raise
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error during authentication"
            )

    async def _validate_configurations_async(self, settings_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate all required configurations in parallel.

        Args:
            settings_data: Settings data from the API

        Returns:
            Dict containing validation results
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

    async def _validate_and_update_services_async(
        self,
        tenant_id: str,
        bigquery_config: Dict[str, Any],
        sftp_config: Dict[str, Any],
        email_config: Dict[str, Any]
    ) -> None:
        """
        Validate services in background and update their status in the database.
        
        This method validates BigQuery, SFTP, and SMTP configurations and updates
        the corresponding enabled/disabled flags in the tenants table.
        
        Args:
            tenant_id: The tenant ID
            bigquery_config: BigQuery configuration
            sftp_config: SFTP configuration
            email_config: Email/SMTP configuration
        """
        try:
            logger.info(f"Starting background service validation for tenant {tenant_id}")
            
            # Validate each service
            bigquery_enabled = False
            bigquery_error = None
            sftp_enabled = False
            sftp_error = None
            smtp_enabled = False
            smtp_error = None
            
            # Validate BigQuery
            if bigquery_config:
                bigquery_enabled = await self._test_bigquery_config_async(bigquery_config)
                if not bigquery_enabled:
                    bigquery_error = "BigQuery configuration validation failed"
            else:
                bigquery_error = "BigQuery configuration is missing"
            
            # Validate SFTP
            if sftp_config:
                sftp_enabled = await self._test_sftp_config_async(sftp_config)
                if not sftp_enabled:
                    sftp_error = "SFTP configuration validation failed"
            else:
                sftp_error = "SFTP configuration is missing"
            
            # Validate SMTP
            if email_config:
                smtp_enabled = await self._test_email_config_async(email_config)
                if not smtp_enabled:
                    smtp_error = "SMTP configuration validation failed"
            else:
                smtp_error = "SMTP configuration is missing"
            
            # Update database with validation results
            await self._update_service_status(
                tenant_id,
                bigquery_enabled, bigquery_error,
                sftp_enabled, sftp_error,
                smtp_enabled, smtp_error
            )
            
            logger.info(
                f"Service validation completed for tenant {tenant_id}: "
                f"BigQuery={bigquery_enabled}, SFTP={sftp_enabled}, SMTP={smtp_enabled}"
            )
            
        except Exception as e:
            logger.error(f"Background service validation failed for tenant {tenant_id}: {e}")

    async def _update_service_status(
        self,
        tenant_id: str,
        bigquery_enabled: bool,
        bigquery_error: Optional[str],
        sftp_enabled: bool,
        sftp_error: Optional[str],
        smtp_enabled: bool,
        smtp_error: Optional[str]
    ) -> None:
        """
        Update service status in the database.
        
        Args:
            tenant_id: The tenant ID
            bigquery_enabled: Whether BigQuery is enabled
            bigquery_error: BigQuery validation error message
            sftp_enabled: Whether SFTP is enabled
            sftp_error: SFTP validation error message
            smtp_enabled: Whether SMTP is enabled
            smtp_error: SMTP validation error message
        """
        try:
            from common.database import get_async_db_session
            
            async with get_async_db_session("auth-service") as session:
                await session.execute(
                    text("""
                        UPDATE tenants SET
                            bigquery_enabled = :bigquery_enabled,
                            bigquery_validation_error = :bigquery_error,
                            sftp_enabled = :sftp_enabled,
                            sftp_validation_error = :sftp_error,
                            smtp_enabled = :smtp_enabled,
                            smtp_validation_error = :smtp_error,
                            updated_at = NOW()
                        WHERE id = :tenant_id
                    """),
                    {
                        "tenant_id": tenant_id,
                        "bigquery_enabled": bigquery_enabled,
                        "bigquery_error": bigquery_error,
                        "sftp_enabled": sftp_enabled,
                        "sftp_error": sftp_error,
                        "smtp_enabled": smtp_enabled,
                        "smtp_error": smtp_error
                    }
                )
                
                # Commit the transaction to persist changes
                await session.commit()
                
                logger.info(f"Updated service status in database for tenant {tenant_id}")
                
        except Exception as e:
            logger.error(f"Failed to update service status for tenant {tenant_id}: {e}")

    async def revalidate_tenant_services(self, tenant_id: str) -> None:
        """
        Revalidate all services for a tenant and update their status.
        
        This method retrieves the tenant's current configurations and validates
        all services, updating their enabled/disabled status in the database.
        
        Args:
            tenant_id: The tenant ID to revalidate
        """
        try:
            logger.info(f"Revalidating services for tenant {tenant_id}")
            
            from common.database import get_async_db_session
            
            # Get current configurations from database
            async with get_async_db_session("auth-service") as session:
                result = await session.execute(
                    text("""
                        SELECT 
                            bigquery_project_id, bigquery_dataset_id, bigquery_credentials,
                            postgres_config, sftp_config, email_config
                        FROM tenants 
                        WHERE id = :tenant_id
                    """),
                    {"tenant_id": tenant_id}
                )
                row = result.fetchone()
                
                if not row:
                    logger.error(f"Tenant not found: {tenant_id}")
                    return
                
                # Parse configurations
                import json
                
                bigquery_config = {}
                if row.bigquery_project_id and row.bigquery_dataset_id:
                    bigquery_config = {
                        "project_id": row.bigquery_project_id,
                        "dataset_id": row.bigquery_dataset_id,
                        "service_account": json.loads(row.bigquery_credentials) if row.bigquery_credentials else {}
                    }
                
                postgres_config = json.loads(row.postgres_config) if row.postgres_config else {}
                sftp_config = json.loads(row.sftp_config) if row.sftp_config else {}
                email_config = json.loads(row.email_config) if row.email_config else {}
            
            # Validate and update services
            await self._validate_and_update_services_async(
                tenant_id, bigquery_config, sftp_config, email_config
            )
            
        except Exception as e:
            logger.error(f"Failed to revalidate services for tenant {tenant_id}: {e}")

    async def _test_postgres_connection_async(self, config: Dict[str, Any]) -> bool:
        """Test PostgreSQL connection asynchronously."""
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
        """Test BigQuery configuration asynchronously."""
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
        """Test SFTP configuration asynchronously."""
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
        """Test email configuration asynchronously."""
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
        Create or update tenant with the latest configurations from authentication API.

        This method always updates the tenant configurations with the latest values
        retrieved from the authentication API, ensuring that any configuration changes
        are immediately reflected in the database.

        Args:
            tenant_id: The tenant ID
            postgres_config: PostgreSQL configuration from authentication API
            bigquery_config: BigQuery configuration from authentication API
            sftp_config: SFTP configuration from authentication API
            email_config: Email/SMTP configuration from authentication API
            username: Username for tenant identification

        Returns:
            True if successful, False otherwise
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
                
                # Commit the transaction to persist changes
                await session.commit()

            return True
        except Exception as e:
            logger.error(f"Failed to upsert tenant configurations for {tenant_id}: {e}")
            return False

    async def logout_with_token(self, access_token: str) -> Dict[str, Any]:
        """
        Logout user by invalidating the access token.

        Args:
            access_token: The access token to invalidate

        Returns:
            Dict containing logout result
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
        Get the login URL for OAuth authentication.

        Returns:
            The complete login URL for the external OAuth service
        """
        base_url = self.settings.BASE_URL
        # Based on the URL you provided, the admin login should be at /admin/
        login_url = f"{base_url}/admin/"
        
        return login_url

    async def validate_token(self, access_token: str) -> Dict[str, Any]:
        """
        Validate an access token and return user information.

        Args:
            access_token: The access token to validate

        Returns:
            Dict containing validation result and user information
        """
        try:
            base_url = self.settings.BASE_URL
            # Try to validate token by calling the getappproperity endpoint with the token
            # This is a known working endpoint that requires authentication
            validate_url = f"{base_url}/manage/auth/getappproperity"

            logger.info(f"Token to validate: {access_token}")

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
