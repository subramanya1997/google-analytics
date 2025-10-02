"""
Common logging configuration for all backend services.

This module provides centralized logging setup for all services in the Google Analytics
Intelligence System. It configures structured, service-specific logging with both
console and file outputs using the loguru library.

Key Features:
- Service-specific log files with automatic rotation
- Colored console output for development
- Separate error log files for critical issues
- Configurable log levels via settings
- Automatic log directory creation
- Log compression and retention policies

Log Output Locations:
- Console: Colored structured logs for development
- Service logs: logs/{service-name}.log (all levels)
- Error logs: logs/{service-name}-error.log (ERROR and above)

Log Rotation:
- Service logs: 50MB rotation, 7 days retention
- Error logs: 10MB rotation, 30 days retention
- Compressed archives for rotated logs

Log Format:
    Console: Colored timestamps, levels, and messages with file/function context
    Files: Structured format with timestamp, level, location, and message
"""
import sys
from pathlib import Path
from loguru import logger
from common.config import get_settings


def setup_logging(service_name: str = None) -> None:
    """
    Configure logging for a service with console and file outputs.
    
    Sets up loguru logging with service-specific configuration including:
    - Colored console output for development
    - Service-specific log files with rotation
    - Error-only log files for critical issues
    - Configurable log levels from settings
    - Automatic log directory management
    
    Args:
        service_name: Name of the service for log file naming and identification.
                     If None, uses generic "app" naming.
                     
    Side Effects:
        - Removes existing loguru handlers
        - Creates logs/ directory if it doesn't exist
        - Configures console and file logging handlers
        - Sets up log rotation and retention policies
        
    Log Files Created:
        - logs/{service_name}.log: All log levels with 50MB rotation, 7 days retention
        - logs/{service_name}-error.log: ERROR+ only with 10MB rotation, 30 days retention
        - logs/app.log and logs/error.log: Used when service_name is None
        
    Example:
        ```python
        # Setup for specific service
        setup_logging("analytics-service")
        # Creates: logs/analytics-service.log, logs/analytics-service-error.log
        
        # Generic setup
        setup_logging()
        # Creates: logs/app.log, logs/error.log
        ```
        
    Note:
        Should be called early in application startup, typically in the main
        application factory or entry point.
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
