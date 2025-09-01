# Authentication Service

Authentication and authorization service for the Google Analytics Intelligence System.

## Overview

This service handles user authentication through external authentication providers and validates system configurations before allowing access to the system.

## Features

- **Code-based Authentication**: Validates authentication codes with external services
- **Configuration Validation**: Ensures all required configurations (PostgreSQL, BigQuery, SFTP) are available and valid
- **Tenant Management**: Automatically creates and manages tenant records in the database
- **Comprehensive Error Handling**: Provides detailed error messages for missing or invalid configurations

## API Endpoints

### POST /api/v1/auth/authenticate

Authenticates a user with an authentication code.

**Request:**
```json
{
  "code": "authentication_code_here"
}
```

**Response (Success):**
```json
{
  "success": true,
  "message": "Authentication successful",
  "tenant_id": "e0f01854-6c2e-4b76-bf7b-67f3c28dbdac",
  "first_name": "Subramanya",
  "username": "subramanyanagabhushan@gmail.com"
}
```

**Response (Configuration Issues):**
```json
{
  "success": false,
  "message": "Authentication failed due to missing or invalid configurations",
  "tenant_id": "e0f01854-6c2e-4b76-bf7b-67f3c28dbdac",
  "first_name": "Subramanya",
  "username": "subramanyanagabhushan@gmail.com",
  "missing_configs": ["postgres_config"],
  "invalid_configs": ["bigquery_config"]
}
```

## Authentication Flow

1. **Code Validation**: Validates the provided code with the external authentication service
2. **Token Retrieval**: Uses the validated code to obtain access tokens and app instance information
3. **Settings Retrieval**: Fetches application settings using the app instance ID and access token
4. **Configuration Validation**: Validates all required configurations:
   - PostgreSQL: Tests database connection
   - BigQuery: Validates service account credentials and required fields
   - SFTP: Validates connection parameters
5. **Tenant Management**: Ensures the tenant exists in the database
6. **Response**: Returns authentication result with tenant ID for frontend use

## Configuration

The service uses the common configuration system. Set the `BASE_URL` environment variable or update the settings to point to your authentication service endpoint.

## Dependencies

- FastAPI for the web framework
- httpx for HTTP client functionality
- SQLAlchemy for database operations
- Common utilities from the shared common package

## Running the Service

The service is automatically included when running `python run_all_services.py` from the backend root directory.

Individual service startup:
```bash
poetry run uvicorn services.auth_service.app.main:app --host 0.0.0.0 --port 8003 --reload
```
