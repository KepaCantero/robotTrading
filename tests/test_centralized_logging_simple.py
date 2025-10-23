"""
Simplified Tests for Centralized Logging System
TASK-3: Configuración de logging centralizado
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.services.centralized_logging import (
    CentralizedLogger,
    LogLevel,
    LogService,
    LogEntry,
    centralized_logger,
    log_performance,
    log_async_performance,
    log_trading_signal,
    log_trade_execution,
    log_portfolio_update,
    log_market_data
)


class TestLogEntry:
    """Tests for LogEntry class."""

    def test_log_entry_creation(self):
        """Test log entry creation."""
        log_entry = LogEntry(
            timestamp="2023-01-01T00:00:00Z",
            level="INFO",
            service="trading",
            message="Test message",
            environment="test",
            metadata={"test": "data"}
        )
        
        assert log_entry.timestamp == "2023-01-01T00:00:00Z"
        assert log_entry.level == "INFO"
        assert log_entry.service == "trading"
        assert log_entry.message == "Test message"
        assert log_entry.environment == "test"
        assert log_entry.metadata == {"test": "data"}

    def test_log_entry_to_dict(self):
        """Test log entry to dictionary conversion."""
        log_entry = LogEntry(
            timestamp="2023-01-01T00:00:00Z",
            level="INFO",
            service="trading",
            message="Test message",
            environment="test",
            metadata={"test": "data"}
        )
        
        log_dict = log_entry.to_dict()
        
        assert log_dict["timestamp"] == "2023-01-01T00:00:00Z"
        assert log_dict["level"] == "INFO"
        assert log_dict["service"] == "trading"
        assert log_dict["message"] == "Test message"
        assert log_dict["environment"] == "test"
        assert log_dict["metadata"] == {"test": "data"}


class TestCentralizedLogger:
    """Tests for CentralizedLogger class."""

    @pytest.fixture
    def mock_logger(self):
        """Create mock logger instance."""
        with patch('app.services.centralized_logging.Path') as mock_path:
            mock_path.return_value.mkdir = MagicMock()
            with patch('app.services.centralized_logging.get_config') as mock_config:
                mock_config.return_value = MagicMock()
                with patch.dict('os.environ', {'ENVIRONMENT': 'test', 'APP_VERSION': '1.0.0'}):
                    with patch('app.services.centralized_logging.logging.getLogger') as mock_get_logger:
                        mock_logger_instance = MagicMock()
                        mock_get_logger.return_value = mock_logger_instance
                        
                        logger = CentralizedLogger()
                        logger.loggers = {service.value: mock_logger_instance for service in LogService}
                        return logger

    def test_logger_initialization(self, mock_logger):
        """Test logger initialization."""
        assert mock_logger.environment == "test"
        assert mock_logger.app_version == "1.0.0"
        assert len(mock_logger.loggers) == len(LogService)

    def test_create_log_entry(self, mock_logger):
        """Test log entry creation."""
        log_entry = mock_logger._create_log_entry(
            LogLevel.INFO,
            LogService.TRADING,
            "Test message",
            {"test": "data"}
        )
        
        assert log_entry.level == "INFO"
        assert log_entry.service == "trading"
        assert log_entry.message == "Test message"
        assert log_entry.environment == "test"
        assert log_entry.application == "algotrading"
        assert log_entry.version == "1.0.0"
        assert log_entry.metadata == {"test": "data"}

    def test_log_info(self, mock_logger):
        """Test info logging."""
        mock_logger.info(LogService.TRADING, "Test info message", {"test": "data"})
        
        # Check that logger was called
        mock_logger.loggers["trading"].info.assert_called_once()

    def test_log_error(self, mock_logger):
        """Test error logging."""
        mock_logger.error(LogService.TRADING, "Test error message", {"test": "data"}, "Error details")
        
        # Check that logger was called
        mock_logger.loggers["trading"].error.assert_called_once()

    def test_log_performance(self, mock_logger):
        """Test performance logging."""
        mock_logger.log_performance(LogService.TRADING, "test_operation", 150.5, {"test": "data"})
        
        # Check that logger was called
        mock_logger.loggers["trading"].info.assert_called_once()

    def test_log_trading_signal(self, mock_logger):
        """Test trading signal logging."""
        signal_data = {
            "symbol": "AAPL",
            "signal_type": "BUY",
            "confidence": 85.0,
            "price": 150.0
        }
        
        mock_logger.log_trading_signal(signal_data, {"test": "metadata"})
        
        # Check that logger was called
        mock_logger.loggers["trading"].info.assert_called_once()

    def test_log_trade_execution(self, mock_logger):
        """Test trade execution logging."""
        trade_data = {
            "symbol": "AAPL",
            "side": "BUY",
            "quantity": 100,
            "price": 150.0
        }
        
        mock_logger.log_trade_execution(trade_data, {"test": "metadata"})
        
        # Check that logger was called
        mock_logger.loggers["trading"].info.assert_called_once()

    def test_log_portfolio_update(self, mock_logger):
        """Test portfolio update logging."""
        portfolio_data = {
            "total_value": 10000.0,
            "cash": 5000.0,
            "positions": 2
        }
        
        mock_logger.log_portfolio_update(portfolio_data, {"test": "metadata"})
        
        # Check that logger was called
        mock_logger.loggers["portfolio"].info.assert_called_once()

    def test_log_market_data(self, mock_logger):
        """Test market data logging."""
        market_data = {
            "symbol": "AAPL",
            "price": 150.0,
            "volume": 1000000,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        mock_logger.log_market_data(market_data, {"test": "metadata"})
        
        # Check that logger was called
        mock_logger.loggers["market_data"].info.assert_called_once()


class TestLoggingDecorators:
    """Tests for logging decorators."""

    def test_log_performance_decorator(self):
        """Test performance logging decorator."""
        @log_performance(LogService.TRADING, "test_operation")
        def test_function():
            return "test_result"
        
        result = test_function()
        assert result == "test_result"

    @pytest.mark.asyncio
    async def test_log_async_performance_decorator(self):
        """Test async performance logging decorator."""
        @log_async_performance(LogService.TRADING, "test_async_operation")
        async def test_async_function():
            return "test_async_result"
        
        result = await test_async_function()
        assert result == "test_async_result"


class TestConvenienceFunctions:
    """Tests for convenience logging functions."""

    def test_log_trading_signal_function(self):
        """Test trading signal logging function."""
        signal_data = {
            "symbol": "AAPL",
            "signal_type": "BUY",
            "confidence": 85.0
        }
        
        # This should not raise an exception
        log_trading_signal(signal_data, {"test": "metadata"})

    def test_log_trade_execution_function(self):
        """Test trade execution logging function."""
        trade_data = {
            "symbol": "AAPL",
            "side": "BUY",
            "quantity": 100
        }
        
        # This should not raise an exception
        log_trade_execution(trade_data, {"test": "metadata"})

    def test_log_portfolio_update_function(self):
        """Test portfolio update logging function."""
        portfolio_data = {
            "total_value": 10000.0,
            "cash": 5000.0
        }
        
        # This should not raise an exception
        log_portfolio_update(portfolio_data, {"test": "metadata"})

    def test_log_market_data_function(self):
        """Test market data logging function."""
        market_data = {
            "symbol": "AAPL",
            "price": 150.0,
            "volume": 1000000
        }
        
        # This should not raise an exception
        log_market_data(market_data, {"test": "metadata"})


class TestLogServiceEnum:
    """Tests for LogService enum."""

    def test_log_service_values(self):
        """Test LogService enum values."""
        assert LogService.FASTAPI.value == "fastapi"
        assert LogService.TRADING.value == "trading"
        assert LogService.MARKET_DATA.value == "market_data"
        assert LogService.PORTFOLIO.value == "portfolio"
        assert LogService.ERROR_HANDLER.value == "error_handler"
        assert LogService.PERFORMANCE_MONITOR.value == "performance_monitor"


class TestLogLevelEnum:
    """Tests for LogLevel enum."""

    def test_log_level_values(self):
        """Test LogLevel enum values."""
        assert LogLevel.DEBUG.value == "DEBUG"
        assert LogLevel.INFO.value == "INFO"
        assert LogLevel.WARNING.value == "WARNING"
        assert LogLevel.ERROR.value == "ERROR"
        assert LogLevel.CRITICAL.value == "CRITICAL"
