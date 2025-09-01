"""
Common logging configuration for all backend services.
"""
import sys
from pathlib import Path
from loguru import logger
from common.config import get_settings


def setup_logging(service_name: str = None) -> None:
    """Configure logging for the application."""
    
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
