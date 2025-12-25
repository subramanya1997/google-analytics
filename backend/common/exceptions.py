"""
Standardized error handling for API responses.
Ensures SOC2 compliance by not exposing internal server details.
"""
from typing import Optional
from fastapi import HTTPException, status
from loguru import logger


class APIError(Exception):
    """Base exception for API errors with user-friendly messages."""
    
    def __init__(self, message: str, status_code: int = 500, internal_error: Optional[Exception] = None):
        self.message = message
        self.status_code = status_code
        self.internal_error = internal_error
        super().__init__(self.message)


def create_api_error(
    operation: str,
    status_code: int = 500,
    internal_error: Optional[Exception] = None,
    user_message: Optional[str] = None
) -> HTTPException:
    """
    Create a standardized API error response.
    
    Args:
        operation: Description of the operation that failed (for logging)
        status_code: HTTP status code (default: 500)
        internal_error: The actual exception (logged but not exposed)
        user_message: Optional user-friendly message (default: generic API error)
    
    Returns:
        HTTPException with safe error message
    """
    # Log the full error internally for debugging
    if internal_error:
        logger.error(f"API error in {operation}: {internal_error}", exc_info=True)
    
    # Determine user-facing message
    if user_message:
        message = user_message
    elif status_code == 400:
        message = "Invalid request. Please check your input and try again."
    elif status_code == 401:
        message = "Authentication failed. Please check your credentials."
    elif status_code == 403:
        message = "Access denied. You don't have permission to perform this action."
    elif status_code == 404:
        message = "Resource not found."
    elif status_code == 422:
        message = "Validation error. Please check your request parameters."
    elif status_code == 429:
        message = "Rate limit exceeded. Please try again later."
    elif status_code == 503:
        message = "Service temporarily unavailable. Please try again later."
    else:
        message = "An error occurred while processing your request. Please try again later."
    
    return HTTPException(status_code=status_code, detail=message)


def handle_database_error(operation: str, error: Exception) -> HTTPException:
    """Handle database-related errors with generic messages."""
    logger.error(f"Database error in {operation}: {error}", exc_info=True)
    return create_api_error(
        operation=operation,
        status_code=500,
        internal_error=error,
        user_message="Failed to retrieve data. Please try again later."
    )


def handle_external_service_error(operation: str, service_name: str, error: Exception) -> HTTPException:
    """Handle external service errors (BigQuery, SFTP, etc.) with generic messages."""
    logger.error(f"External service error in {operation} ({service_name}): {error}", exc_info=True)
    return create_api_error(
        operation=operation,
        status_code=503,
        internal_error=error,
        user_message=f"Unable to connect to {service_name}. Please try again later."
    )


def handle_validation_error(operation: str, error: Exception) -> HTTPException:
    """Handle validation errors."""
    logger.warning(f"Validation error in {operation}: {error}")
    return create_api_error(
        operation=operation,
        status_code=422,
        internal_error=error,
        user_message="Invalid request parameters. Please check your input."
    )
