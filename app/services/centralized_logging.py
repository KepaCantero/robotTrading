"""
Centralized Logging Service for AlgoTrading
TASK-3: Configuración de logging centralizado
"""

import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path
from enum import Enum
from dataclasses import dataclass, asdict
from contextlib import contextmanager
import asyncio
from functools import wraps

from app.core.centralized_config import get_config


class LogLevel(Enum):
    """Log levels for centralized logging."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogService(Enum):
    """Services that can generate logs."""
    FASTAPI = "fastapi"
    TRADING = "trading"
    MARKET_DATA = "market_data"
    PORTFOLIO = "portfolio"
    ERROR_HANDLER = "error_handler"
    PERFORMANCE_MONITOR = "performance_monitor"


@dataclass
class LogEntry:
    """Structured log entry."""
    timestamp: str
    level: str
    service: str
    message: str
    environment: str
    application: str = "algotrading"
    version: str = "1.0.0"
    metadata: Optional[Dict[str, Any]] = None
    duration: Optional[float] = None
    operation: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class CentralizedLogger:
    """Centralized logging service for AlgoTrading."""

    def __init__(self):
        self.config = get_config()
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.app_version = os.getenv("APP_VERSION", "1.0.0")
        self.log_dir = Path(os.getenv("LOG_DIR", "logs"))
        self._setup_log_directories()
        self._setup_loggers()

    def _setup_log_directories(self) -> None:
        """Create log directories for each service."""
        services = [service.value for service in LogService]
        for service in services:
            service_dir = self.log_dir / service
            service_dir.mkdir(parents=True, exist_ok=True)

    def _setup_loggers(self) -> None:
        """Setup loggers for each service."""
        self.loggers = {}
        
        for service in LogService:
            logger = logging.getLogger(f"algotrading.{service.value}")
            logger.setLevel(logging.DEBUG)
            
            # Create file handler
            log_file = self.log_dir / service.value / f"{service.value}.log"
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            
            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            
            logger.addHandler(file_handler)
            self.loggers[service.value] = logger

    def _create_log_entry(
        self,
        level: LogLevel,
        service: LogService,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        duration: Optional[float] = None,
        operation: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> LogEntry:
        """Create a structured log entry."""
        return LogEntry(
            timestamp=datetime.utcnow().isoformat(),
            level=level.value,
            service=service.value,
            message=message,
            environment=self.environment,
            application="algotrading",
            version=self.app_version,
            metadata=metadata,
            duration=duration,
            operation=operation,
            error_message=error_message
        )

    def log(
        self,
        level: LogLevel,
        service: LogService,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        duration: Optional[float] = None,
        operation: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Log a message with structured data."""
        log_entry = self._create_log_entry(
            level, service, message, metadata, duration, operation, error_message
        )
        
        # Log to file
        logger = self.loggers[service.value]
        log_message = json.dumps(log_entry.to_dict())
        
        if level == LogLevel.DEBUG:
            logger.debug(log_message)
        elif level == LogLevel.INFO:
            logger.info(log_message)
        elif level == LogLevel.WARNING:
            logger.warning(log_message)
        elif level == LogLevel.ERROR:
            logger.error(log_message)
        elif level == LogLevel.CRITICAL:
            logger.critical(log_message)

    def debug(
        self,
        service: LogService,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log debug message."""
        self.log(LogLevel.DEBUG, service, message, metadata)

    def info(
        self,
        service: LogService,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log info message."""
        self.log(LogLevel.INFO, service, message, metadata)

    def warning(
        self,
        service: LogService,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log warning message."""
        self.log(LogLevel.WARNING, service, message, metadata)

    def error(
        self,
        service: LogService,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Log error message."""
        self.log(LogLevel.ERROR, service, message, metadata, error_message=error_message)

    def critical(
        self,
        service: LogService,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Log critical message."""
        self.log(LogLevel.CRITICAL, service, message, metadata, error_message=error_message)

    def log_performance(
        self,
        service: LogService,
        operation: str,
        duration: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log performance metrics."""
        self.log(
            LogLevel.INFO,
            service,
            f"Performance: {operation} took {duration}ms",
            metadata=metadata,
            duration=duration,
            operation=operation
        )

    @contextmanager
    def performance_timer(
        self,
        service: LogService,
        operation: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Context manager for performance timing."""
        start_time = datetime.utcnow()
        try:
            yield
        finally:
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds() * 1000
            self.log_performance(service, operation, duration, metadata)

    def log_trading_signal(
        self,
        signal_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log trading signal generation."""
        self.info(
            LogService.TRADING,
            f"Signal generated: {signal_data.get('symbol', 'unknown')}",
            metadata={**signal_data, **(metadata or {})}
        )

    def log_trade_execution(
        self,
        trade_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log trade execution."""
        self.info(
            LogService.TRADING,
            f"Trade executed: {trade_data.get('symbol', 'unknown')}",
            metadata={**trade_data, **(metadata or {})}
        )

    def log_portfolio_update(
        self,
        portfolio_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log portfolio update."""
        self.info(
            LogService.PORTFOLIO,
            f"Portfolio updated: {portfolio_data.get('total_value', 0)}",
            metadata={**portfolio_data, **(metadata or {})}
        )

    def log_market_data(
        self,
        market_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log market data processing."""
        self.info(
            LogService.MARKET_DATA,
            f"Market data processed: {market_data.get('symbol', 'unknown')}",
            metadata={**market_data, **(metadata or {})}
        )


# Global logger instance
centralized_logger = CentralizedLogger()


def log_performance(service: LogService, operation: str):
    """Decorator for logging function performance."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with centralized_logger.performance_timer(service, operation):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def log_async_performance(service: LogService, operation: str):
    """Decorator for logging async function performance."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            with centralized_logger.performance_timer(service, operation):
                return await func(*args, **kwargs)
        return wrapper
    return decorator


# Convenience functions
def log_trading_signal(signal_data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
    """Log trading signal generation."""
    centralized_logger.log_trading_signal(signal_data, metadata)


def log_trade_execution(trade_data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
    """Log trade execution."""
    centralized_logger.log_trade_execution(trade_data, metadata)


def log_portfolio_update(portfolio_data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
    """Log portfolio update."""
    centralized_logger.log_portfolio_update(portfolio_data, metadata)


def log_market_data(market_data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
    """Log market data processing."""
    centralized_logger.log_market_data(market_data, metadata)
