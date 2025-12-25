"""
Standardized error handling for API responses.

This module provides a comprehensive error handling system for FastAPI applications
that ensures SOC2 compliance by preventing exposure of internal server details to
clients. It provides consistent error responses, proper logging, and user-friendly
error messages.

Key Features:
    - SOC2-compliant error messages (no internal details exposed)
    - Centralized error handling with consistent response format
    - Automatic logging of errors for debugging
    - Type-safe error creation with proper HTTP status codes
    - Specialized handlers for common error scenarios

Architecture:
    The module uses a two-tier error handling approach:
    1. Internal errors are logged with full details for debugging
    2. User-facing errors contain only safe, generic messages

This ensures that sensitive information (database errors, stack traces, internal
paths) is never exposed to API clients while still providing useful feedback.

Example:
    ```python
    from common.exceptions import create_api_error, handle_database_error
    
    try:
        # Some operation
        result = db.query(...)
    except DatabaseError as e:
        raise handle_database_error("fetching user data", e)
    
    # Or create custom error
    raise create_api_error(
        operation="processing payment",
        status_code=400,
        user_message="Invalid payment method"
    )
    ```
"""

from fastapi import HTTPException
from loguru import logger

# HTTP Status Code Constants
HTTP_400_BAD_REQUEST = 400
HTTP_401_UNAUTHORIZED = 401
HTTP_403_FORBIDDEN = 403
HTTP_404_NOT_FOUND = 404
HTTP_422_UNPROCESSABLE_ENTITY = 422
HTTP_429_TOO_MANY_REQUESTS = 429
HTTP_500_INTERNAL_SERVER_ERROR = 500
HTTP_503_SERVICE_UNAVAILABLE = 503


class APIError(Exception):
    """
    Base exception class for API errors with user-friendly messages.

    This exception class is designed for use in API endpoints where you need to
    raise errors that will be converted to HTTP responses. It separates
    user-facing messages from internal error details for security compliance.

    Attributes:
        message (str): User-friendly error message that can be safely exposed to clients.
        status_code (int): HTTP status code to return (default: 500).
        internal_error (Exception | None): The original exception that caused this error,
            stored for logging purposes but not exposed to clients.

    Example:
        ```python
        from common.exceptions import APIError
        
        if not user:
            raise APIError(
                message="User not found",
                status_code=404,
                internal_error=ValueError("User ID not in database")
            )
        ```

    Note:
        - The message should never contain sensitive information
        - Internal errors are logged but not included in API responses
        - This exception should be caught by FastAPI exception handlers
    """

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        internal_error: Exception | None = None,
    ) -> None:
        """
        Initialize an APIError instance.

        Args:
            message: User-friendly error message safe to expose to API clients.
                Should not contain sensitive information, stack traces, or internal details.
            status_code: HTTP status code to return. Defaults to 500 (Internal Server Error).
                Common values: 400 (Bad Request), 401 (Unauthorized), 403 (Forbidden),
                404 (Not Found), 422 (Unprocessable Entity), 500 (Internal Server Error).
            internal_error: Optional original exception that caused this error. This is
                logged for debugging but never exposed to clients.
        """
        self.message = message
        self.status_code = status_code
        self.internal_error = internal_error
        super().__init__(self.message)


def create_api_error(
    operation: str,
    status_code: int = 500,
    internal_error: Exception | None = None,
    user_message: str | None = None,
) -> HTTPException:
    """
    Create a standardized API error response with SOC2-compliant error messages.

    This function creates a FastAPI HTTPException with a user-friendly error message
    while logging the full internal error details for debugging. It ensures that
    sensitive information is never exposed to API clients.

    Args:
        operation: Description of the operation that failed (e.g., "fetching user data",
            "processing payment", "validating input"). Used for logging context.
        status_code: HTTP status code to return. Defaults to 500 (Internal Server Error).
            Common values:
                - 400: Bad Request (invalid input)
                - 401: Unauthorized (authentication failed)
                - 403: Forbidden (insufficient permissions)
                - 404: Not Found (resource doesn't exist)
                - 422: Unprocessable Entity (validation error)
                - 429: Too Many Requests (rate limit exceeded)
                - 500: Internal Server Error (server-side error)
                - 503: Service Unavailable (external service error)
        internal_error: Optional original exception that caused this error. The full
            exception (including stack trace) is logged but not included in the response.
        user_message: Optional custom user-friendly message. If None, a generic message
            appropriate for the status code is used. The message should never contain
            sensitive information, stack traces, or internal implementation details.

    Returns:
        HTTPException configured with the appropriate status code and safe error message.
        This can be raised directly in FastAPI route handlers.

    Raises:
        HTTPException: Always raises an HTTPException (this is the intended behavior).

    Example:
        ```python
        from common.exceptions import create_api_error
        
        try:
            result = complex_operation()
        except ValueError as e:
            raise create_api_error(
                operation="processing user input",
                status_code=400,
                internal_error=e,
                user_message="Invalid input provided. Please check your data."
            )
        ```

    Note:
        - If user_message is None, a default message is generated based on status_code
        - All internal errors are logged with full exception details for debugging
        - Error messages are designed to be safe for public API exposure
    """
    # Log the full error internally for debugging
    if internal_error:
        logger.exception(f"API error in {operation}: {internal_error}")

    # Determine user-facing message
    if user_message:
        message = user_message
    elif status_code == HTTP_400_BAD_REQUEST:
        message = "Invalid request. Please check your input and try again."
    elif status_code == HTTP_401_UNAUTHORIZED:
        message = "Authentication failed. Please check your credentials."
    elif status_code == HTTP_403_FORBIDDEN:
        message = "Access denied. You don't have permission to perform this action."
    elif status_code == HTTP_404_NOT_FOUND:
        message = "Resource not found."
    elif status_code == HTTP_422_UNPROCESSABLE_ENTITY:
        message = "Validation error. Please check your request parameters."
    elif status_code == HTTP_429_TOO_MANY_REQUESTS:
        message = "Rate limit exceeded. Please try again later."
    elif status_code == HTTP_503_SERVICE_UNAVAILABLE:
        message = "Service temporarily unavailable. Please try again later."
    else:
        message = (
            "An error occurred while processing your request. Please try again later."
        )

    return HTTPException(status_code=status_code, detail=message)


def handle_database_error(operation: str, error: Exception) -> HTTPException:
    """
    Handle database-related errors with generic, safe error messages.

    This is a convenience function specifically designed for handling database
    errors (SQLAlchemy exceptions, connection errors, etc.). It automatically
    logs the full error details while returning a generic message to the client.

    Args:
        operation: Description of the database operation that failed (e.g.,
            "fetching user records", "updating tenant configuration").
        error: The database exception that occurred. Common types include:
            - sqlalchemy.exc.SQLAlchemyError
            - sqlalchemy.exc.OperationalError (connection issues)
            - sqlalchemy.exc.IntegrityError (constraint violations)
            - psycopg2 errors (PostgreSQL-specific errors)

    Returns:
        HTTPException with status code 500 and a generic error message that doesn't
        expose database structure, query details, or connection information.

    Example:
        ```python
        from common.exceptions import handle_database_error
        from sqlalchemy.exc import SQLAlchemyError
        
        try:
            user = db.query(User).filter_by(id=user_id).first()
        except SQLAlchemyError as e:
            raise handle_database_error("fetching user", e)
        ```

    Note:
        - Always returns status code 500 (Internal Server Error)
        - Full error details are logged for debugging
        - Error message is intentionally generic to prevent information leakage
    """
    logger.exception(f"Database error in {operation}: {error}")
    return create_api_error(
        operation=operation,
        status_code=500,
        internal_error=error,
        user_message="Failed to retrieve data. Please try again later.",
    )


def handle_external_service_error(
    operation: str, service_name: str, error: Exception
) -> HTTPException:
    """
    Handle errors from external services with generic, safe error messages.

    This function is designed for handling errors from external services such as
    BigQuery, SFTP servers, SMTP servers, or third-party APIs. It returns a
    503 Service Unavailable status code and logs the full error for debugging.

    Args:
        operation: Description of the operation that failed (e.g., "fetching analytics data",
            "uploading file to SFTP", "sending email notification").
        service_name: Name of the external service that failed (e.g., "BigQuery", "SFTP",
            "SMTP", "Google Analytics API"). This name is included in the user-facing
            error message.
        error: The exception that occurred when communicating with the external service.
            Common types include:
            - requests.exceptions.RequestException (HTTP errors)
            - ConnectionError (network issues)
            - TimeoutError (service timeout)
            - Service-specific exceptions

    Returns:
        HTTPException with status code 503 (Service Unavailable) and a message indicating
        that the external service is temporarily unavailable.

    Example:
        ```python
        from common.exceptions import handle_external_service_error
        import requests
        
        try:
            response = requests.get("https://api.example.com/data", timeout=30)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise handle_external_service_error(
                operation="fetching analytics data",
                service_name="BigQuery",
                error=e
            )
        ```

    Note:
        - Always returns status code 503 (Service Unavailable)
        - Service name is included in the error message for user clarity
        - Full error details are logged for debugging
        - Error message suggests retrying later, which is appropriate for transient failures
    """
    logger.exception(
        f"External service error in {operation} ({service_name}): {error}"
    )
    return create_api_error(
        operation=operation,
        status_code=503,
        internal_error=error,
        user_message=f"Unable to connect to {service_name}. Please try again later.",
    )


def handle_validation_error(operation: str, error: Exception) -> HTTPException:
    """
    Handle validation errors with appropriate error messages.

    This function is designed for handling input validation errors, typically from
    Pydantic models or custom validation logic. It returns a 422 Unprocessable Entity
    status code, which is the standard for validation errors in REST APIs.

    Args:
        operation: Description of the operation that failed validation (e.g.,
            "validating user input", "processing form data", "parsing request body").
        error: The validation exception that occurred. Common types include:
            - pydantic.ValidationError (Pydantic model validation)
            - ValueError (general value errors)
            - TypeError (type mismatches)
            - Custom validation exceptions

    Returns:
        HTTPException with status code 422 (Unprocessable Entity) and a message
        indicating that the request parameters are invalid.

    Example:
        ```python
        from common.exceptions import handle_validation_error
        from pydantic import ValidationError
        
        try:
            user_data = UserCreate(**request.json())
        except ValidationError as e:
            raise handle_validation_error("creating user", e)
        ```

    Note:
        - Returns status code 422 (Unprocessable Entity) - standard for validation errors
        - Logs at WARNING level (validation errors are expected and less severe)
        - Error message guides users to check their input
        - For Pydantic errors, consider extracting specific field errors for more
          detailed feedback (this function provides a generic message)
    """
    logger.warning(f"Validation error in {operation}: {error}")
    return create_api_error(
        operation=operation,
        status_code=422,
        internal_error=error,
        user_message="Invalid request parameters. Please check your input.",
    )
