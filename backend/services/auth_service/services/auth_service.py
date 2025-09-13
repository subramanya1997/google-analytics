"""
Authentication service business logic.
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

                if not all([app_instance_id, access_token, account_id]):
                    return {
                        "success": False,
                        "message": "Invalid response from authentication service",
                        "tenant_id": None,
                        "first_name": first_name,
                        "username": username,
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
                    }

                # Step 5: Return success response with access token
                return {
                    "success": True,
                    "message": "Authentication successful",
                    "tenant_id": account_id,
                    "first_name": first_name,
                    "username": username,
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
            }
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return {
                "success": False,
                "message": "Internal server error during authentication",
                "tenant_id": None,
                "first_name": None,
                "username": None,
            }

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
                        }
                    elif validate_response.status_code == 404:
                        return {
                            "valid": False,
                            "message": "Token validation endpoint not available",
                            "tenant_id": None,
                            "first_name": None,
                            "username": None,
                        }
                    else:
                        return {
                            "valid": False,
                            "message": f"Token validation failed with status {validate_response.status_code}",
                            "tenant_id": None,
                            "first_name": None,
                            "username": None,
                        }

                # If we get here, the token is valid
                try:
                    user_data = validate_response.json()
                    tenant_id = user_data.get("accountId")  # This is our tenant_id
                    first_name = user_data.get("firstName")
                    username = user_data.get("username")
                    
                    logger.info(f"Token validation successful for user: {username}")
                    return {
                        "valid": True,
                        "message": "Token is valid",
                        "tenant_id": tenant_id,
                        "first_name": first_name,
                        "username": username,
                    }
                except Exception as e:
                    logger.error(f"Failed to parse user data from token validation: {e}")
                    return {
                        "valid": True,  # Token is valid, but we couldn't parse user data
                        "message": "Token is valid but user data unavailable",
                        "tenant_id": None,
                        "first_name": None,
                        "username": None,
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
            }
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            return {
                "valid": False,
                "message": "Internal server error during token validation",
                "tenant_id": None,
                "first_name": None,
                "username": None,
            }
