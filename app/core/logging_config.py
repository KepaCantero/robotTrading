"""
Logging Configuration Module

Configures logging to ensure all warnings and errors are written to files.
This prevents loss of important diagnostic information.
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional


def setup_file_logging(
    log_dir: str = "logs",
    root_level: int = logging.INFO,
    file_level: int = logging.WARNING,
    console_level: Optional[int] = logging.INFO,
) -> None:
    """
    Configure logging to write all warnings and errors to files.
    
    Args:
        log_dir: Directory for log files
        root_level: Level for root logger
        file_level: Minimum level to write to file (default: WARNING)
        console_level: Minimum level for console (None = disable console)
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Create separate log files for different levels
    warning_log = log_path / "warnings.log"
    error_log = log_path / "errors.log"
    all_log = log_path / "all.log"
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(root_level)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Handler for ALL logs (INFO and above)
    all_handler = RotatingFileHandler(
        all_log,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
        encoding='utf-8'
    )
    all_handler.setLevel(logging.INFO)
    all_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    all_handler.setFormatter(all_formatter)
    root_logger.addHandler(all_handler)
    
    # Handler for WARNINGS and above
    warning_handler = RotatingFileHandler(
        warning_log,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
        encoding='utf-8'
    )
    warning_handler.setLevel(logging.WARNING)
    warning_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    warning_handler.setFormatter(warning_formatter)
    root_logger.addHandler(warning_handler)
    
    # Handler for ERRORS and CRITICAL only
    error_handler = RotatingFileHandler(
        error_log,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=20,  # Keep more error logs
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(pathname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    error_handler.setFormatter(error_formatter)
    root_logger.addHandler(error_handler)
    
    # Console handler (optional, for development)
    if console_level is not None:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(console_level)
        console_formatter = logging.Formatter(
            '%(levelname)s - %(name)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    # Log that logging is configured
    root_logger.info(f"Logging configured: warnings->{warning_log}, errors->{error_log}, all->{all_log}")


def setup_module_loggers() -> None:
    """
    Configure specific loggers for important modules.
    Ensures warnings/errors from these modules are always captured.
    """
    log_path = Path("logs")
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Modules that should always log to files
    important_modules = [
        "app.strategies",
        "app.backtesting",
        "app.services",
        "app.api",
        "app.core",
    ]
    
    for module_name in important_modules:
        logger = logging.getLogger(module_name)
        
        # Create module-specific error log
        module_log_file = log_path / f"{module_name.replace('.', '_')}_errors.log"
        handler = RotatingFileHandler(
            module_log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding='utf-8'
        )
        handler.setLevel(logging.WARNING)  # WARNING and above
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.WARNING)  # Only warnings and above for these


# Initialize logging on import
# This ensures logging is configured as soon as this module is imported
import os
env = os.getenv("ENVIRONMENT", "development")

# In production, disable console logging to avoid clutter
console_level = None if env == "production" else logging.INFO

setup_file_logging(
    log_dir="logs",
    root_level=logging.INFO,
    file_level=logging.WARNING,
    console_level=console_level,
)

# Setup module-specific loggers
setup_module_loggers()

