"""
Authentication service business logic.
"""

import json
from typing import Any, Dict

import httpx
from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from common.config import get_settings
from common.database import get_engine


class AuthenticationService:
    """Service for handling authentication and configuration validation."""

    def __init__(self):
        """Initialize the authentication service."""
        self.engine = get_engine("auth-service")
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

            logger.info(f"🔐 Starting authentication process")

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
                logger.info(f"📋 Fetching tenant configurations")

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
                    }

                    logger.info(
                        f"📊 Configurations found - PostgreSQL: {'✅' if postgres_config else '❌'}, BigQuery: {'✅' if bigquery_config else '❌'}, SFTP: {'✅' if sftp_config else '❌'}"
                    )

                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse settingsValues JSON: {e}")
                    formatted_settings = {
                        "postgres_config": {},
                        "bigquery_config": {},
                        "sftp_config": {},
                    }

                # Step 3: Validate configurations
                logger.info(f"🔧 Starting configuration validation")
                validation_result = self._validate_configurations(formatted_settings)

                if validation_result["valid"]:
                    logger.info(f"🎉 All configurations validated successfully")
                else:
                    logger.error(f"❌ Configuration validation failed")

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

                if not self._upsert_tenant_configurations(
                    account_id, postgres_config, bigquery_config, sftp_config, username
                ):
                    return {
                        "success": False,
                        "message": "Failed to store tenant configurations in database",
                        "tenant_id": account_id,
                        "first_name": first_name,
                        "username": username,
                    }

                # Step 5: Return success response
                return {
                    "success": True,
                    "message": "Authentication successful",
                    "tenant_id": account_id,
                    "first_name": first_name,
                    "username": username,
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

    def _validate_configurations(self, settings_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate all required configurations.

        Args:
            settings_data: Settings data from the API

        Returns:
            Dict containing validation results
        """
        postgres_config = settings_data.get("postgres_config", {})
        bigquery_config = settings_data.get("bigquery_config", {})
        sftp_config = settings_data.get("sftp_config", {})

        missing_configs = []
        invalid_configs = []

        # Check if configs exist and are valid
        if not postgres_config:
            missing_configs.append("postgres_config")
        elif not self._test_postgres_connection(postgres_config):
            invalid_configs.append("postgres_config")

        if not bigquery_config:
            missing_configs.append("bigquery_config")
        elif not self._test_bigquery_config(bigquery_config):
            invalid_configs.append("bigquery_config")

        if not sftp_config:
            missing_configs.append("sftp_config")
        elif not self._test_sftp_config(sftp_config):
            invalid_configs.append("sftp_config")

        return {
            "valid": len(missing_configs) == 0 and len(invalid_configs) == 0,
            "missing_configs": missing_configs,
            "invalid_configs": invalid_configs,
        }

    def _test_postgres_connection(self, config: Dict[str, Any]) -> bool:
        """Test PostgreSQL connection."""
        try:
            logger.info(
                f"🔍 Testing PostgreSQL connection to {config.get('host')}:{config.get('port')}"
            )
            connection_string = f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
            engine = create_engine(connection_string)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info(f"✅ PostgreSQL connection successful")
            return True
        except Exception as e:
            logger.error(f"❌ PostgreSQL connection test failed: {e}")
            return False

    def _test_bigquery_config(self, config: Dict[str, Any]) -> bool:
        """Test BigQuery configuration."""
        try:
            logger.info(
                f"🔍 Testing BigQuery configuration for project: {config.get('project_id')}"
            )
            required_fields = ["project_id", "dataset_id", "service_account"]
            if not all(field in config for field in required_fields):
                logger.error(f"❌ BigQuery config missing required fields")
                return False

            service_account = config.get("service_account", {})
            required_sa_fields = ["type", "project_id", "private_key", "client_email"]
            if not all(field in service_account for field in required_sa_fields):
                logger.error(f"❌ BigQuery service account missing required fields")
                return False

            logger.info(f"✅ BigQuery configuration valid")
            return True
        except Exception as e:
            logger.error(f"❌ BigQuery config validation failed: {e}")
            return False

    def _test_sftp_config(self, config: Dict[str, Any]) -> bool:
        """Test SFTP configuration."""
        try:
            logger.info(f"🔍 Testing SFTP configuration for host: {config.get('host')}")
            required_fields = ["host", "port", "username", "password"]
            if not all(field in config for field in required_fields):
                logger.error(f"❌ SFTP config missing required fields")
                return False

            logger.info(f"✅ SFTP configuration valid")
            return True
        except Exception as e:
            logger.error(f"❌ SFTP config validation failed: {e}")
            return False

    def _upsert_tenant_configurations(
        self,
        tenant_id: str,
        postgres_config: Dict[str, Any],
        bigquery_config: Dict[str, Any],
        sftp_config: Dict[str, Any],
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

        Returns:
            True if successful, False otherwise
        """
        try:
            connection_string = f"postgresql://{postgres_config['user']}:{postgres_config['password']}@{postgres_config['host']}:{postgres_config['port']}/{postgres_config['database']}"
            engine = create_engine(connection_string)

            with Session(engine) as session:
                # Check if tenant exists
                result = session.execute(
                    text("SELECT COUNT(*) FROM tenants WHERE id = :tenant_id"),
                    {"tenant_id": tenant_id},
                ).scalar()

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
                }

                if result == 0:
                    # Create new tenant with all configurations
                    session.execute(
                        text(
                            """
                            INSERT INTO tenants (
                                id, name, 
                                bigquery_project_id, bigquery_dataset_id, bigquery_credentials,
                                postgres_config, sftp_config,
                                is_active, created_at, updated_at
                            ) VALUES (
                                :tenant_id, :name,
                                :bigquery_project_id, :bigquery_dataset_id, :bigquery_credentials,
                                :postgres_config, :sftp_config,
                                true, NOW(), NOW()
                            )
                        """
                        ),
                        config_data,
                    )
                    session.commit()
                    logger.info(f"✅ Created new tenant: {username} ({tenant_id})")
                else:
                    # Always update existing tenant with latest configurations from authentication API
                    session.execute(
                        text(
                            """
                            UPDATE tenants SET
                                name = :name,
                                bigquery_project_id = :bigquery_project_id,
                                bigquery_dataset_id = :bigquery_dataset_id,
                                bigquery_credentials = :bigquery_credentials,
                                postgres_config = :postgres_config,
                                sftp_config = :sftp_config,
                                is_active = true,
                                updated_at = NOW()
                            WHERE id = :tenant_id
                        """
                        ),
                        config_data,
                    )
                    session.commit()
                    logger.info(f"🔄 Updated tenant configurations: ({tenant_id})")

            return True
        except Exception as e:
            logger.error(f"Failed to upsert tenant configurations for {tenant_id}: {e}")
            return False
