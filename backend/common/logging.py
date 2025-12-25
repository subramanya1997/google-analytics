"""
Common logging configuration for all backend services.

This module provides centralized logging configuration using loguru, ensuring
consistent logging behavior across all microservices. It configures both console
and file-based logging with appropriate formatting, rotation, and retention policies.

Features:
    - Console logging with colorized output for development
    - File-based logging with automatic rotation and compression
    - Service-specific log files for better organization
    - Configurable log levels via environment variables
    - Structured logging with timestamps, levels, and source location

Log Files:
    - {service_name}.log: All logs at configured level (default: INFO)
    - {service_name}-error.log: Only ERROR level logs

Log Rotation:
    - Error logs: Rotate at 10 MB, retain 30 days, compress with zip
    - General logs: Rotate at 50 MB, retain 7 days, compress with zip

Example:
    ```python
    from common.logging import setup_logging
    
    # Setup logging for a service
    setup_logging("analytics-service")
    
    # Now use logger throughout the application
    from loguru import logger
    logger.info("Service started successfully")
    logger.error("An error occurred", exc_info=True)
    ```
"""

from pathlib import Path
import sys

from loguru import logger

from common.config import get_settings


def setup_logging(service_name: str | None = None) -> None:
    """
    Configure logging for the application using loguru.

    This function sets up comprehensive logging configuration including:
    - Console output with colorized formatting
    - Service-specific log files with rotation and compression
    - Error-specific log files for easier debugging
    - Configurable log levels from environment settings

    Args:
        service_name: Optional name of the service (e.g., "analytics-service",
            "data-ingestion-service", "auth-service"). If provided, log files
            will be named accordingly. If None, generic names are used.

    Side Effects:
        - Removes default loguru handlers
        - Adds new console and file handlers
        - Creates 'logs' directory if it doesn't exist
        - Configures log rotation and retention policies

    Configuration:
        Log level is determined by the LOG_LEVEL setting from service configuration:
        - DEBUG: Detailed diagnostic information
        - INFO: General informational messages (default)
        - WARNING: Warning messages
        - ERROR: Error messages
        - CRITICAL: Critical errors

    Example:
        ```python
        # In service main.py
        from common.logging import setup_logging
        
        setup_logging("analytics-service")
        
        from loguru import logger
        logger.info("Analytics service initialized")
        ```

    Note:
        - This function should be called early in the application startup process
        - The 'logs' directory is created relative to the current working directory
        - Log files use UTC timestamps
        - Console output is colorized for better readability in terminals
    """

    settings = get_settings(service_name)

    # Remove default handler
    logger.remove()

    # Add console handler with custom format
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>",
        level=settings.LOG_LEVEL,
        colorize=True,
    )

    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Determine service-specific log file names
    if service_name:
        service_log_file = f"logs/{service_name}.log"
        service_error_file = f"logs/{service_name}-error.log"
    else:
        service_log_file = "logs/app.log"
        service_error_file = "logs/error.log"

    # Add file handler for errors (service-specific)
    logger.add(
        service_error_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level="ERROR",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
    )

    # Add file handler for all logs (service-specific)
    logger.add(
        service_log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        level=settings.LOG_LEVEL,
        rotation="50 MB",
        retention="7 days",
        compression="zip",
    )
