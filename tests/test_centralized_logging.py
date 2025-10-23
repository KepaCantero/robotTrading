"""
Tests for Centralized Logging System
TASK-3: Configuración de logging centralizado
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
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


class TestCentralizedLogger:
    """Tests for CentralizedLogger class."""

    @pytest.fixture
    def temp_log_dir(self):
        """Create temporary log directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def logger(self, temp_log_dir):
        """Create logger instance with temporary directory."""
        with patch('app.services.centralized_logging.Path') as mock_path:
            mock_path.return_value = temp_log_dir
            with patch('app.services.centralized_logging.get_config') as mock_config:
                mock_config.return_value = MagicMock()
                with patch.dict('os.environ', {'ENVIRONMENT': 'test', 'APP_VERSION': '1.0.0'}):
                    logger = CentralizedLogger()
                    logger.log_dir = temp_log_dir
                    return logger

    def test_logger_initialization(self, logger, temp_log_dir):
        """Test logger initialization."""
        assert logger.environment == "test"
        assert logger.app_version == "1.0.0"
        assert logger.log_dir == temp_log_dir
        assert len(logger.loggers) == len(LogService)

    def test_create_log_entry(self, logger):
        """Test log entry creation."""
        log_entry = logger._create_log_entry(
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

    def test_log_info(self, logger):
        """Test info logging."""
        logger.info(LogService.TRADING, "Test info message", {"test": "data"})
        
        # Check that log file was created
        log_file = logger.log_dir / "trading" / "trading.log"
        assert log_file.exists()
        
        # Check log content
        with open(log_file, 'r') as f:
            log_content = f.read()
            assert "Test info message" in log_content
            assert "INFO" in log_content

    def test_log_error(self, logger):
        """Test error logging."""
        logger.error(LogService.TRADING, "Test error message", {"test": "data"}, "Error details")
        
        # Check that log file was created
        log_file = logger.log_dir / "trading" / "trading.log"
        assert log_file.exists()
        
        # Check log content
        with open(log_file, 'r') as f:
            log_content = f.read()
            assert "Test error message" in log_content
            assert "ERROR" in log_content

    def test_log_performance(self, logger):
        """Test performance logging."""
        logger.log_performance(LogService.TRADING, "test_operation", 150.5, {"test": "data"})
        
        # Check that log file was created
        log_file = logger.log_dir / "trading" / "trading.log"
        assert log_file.exists()
        
        # Check log content
        with open(log_file, 'r') as f:
            log_content = f.read()
            assert "test_operation" in log_content
            assert "150.5" in log_content
            assert "Performance" in log_content

    def test_performance_timer_context_manager(self, logger):
        """Test performance timer context manager."""
        with logger.performance_timer(LogService.TRADING, "test_operation", {"test": "data"}):
            pass
        
        # Check that log file was created
        log_file = logger.log_dir / "trading" / "trading.log"
        assert log_file.exists()
        
        # Check log content
        with open(log_file, 'r') as f:
            log_content = f.read()
            assert "test_operation" in log_content
            assert "Performance" in log_content

    def test_log_trading_signal(self, logger):
        """Test trading signal logging."""
        signal_data = {
            "symbol": "AAPL",
            "signal_type": "BUY",
            "confidence": 85.0,
            "price": 150.0
        }
        
        logger.log_trading_signal(signal_data, {"test": "metadata"})
        
        # Check that log file was created
        log_file = logger.log_dir / "trading" / "trading.log"
        assert log_file.exists()
        
        # Check log content
        with open(log_file, 'r') as f:
            log_content = f.read()
            assert "AAPL" in log_content
            assert "Signal generated" in log_content

    def test_log_trade_execution(self, logger):
        """Test trade execution logging."""
        trade_data = {
            "symbol": "AAPL",
            "side": "BUY",
            "quantity": 100,
            "price": 150.0
        }
        
        logger.log_trade_execution(trade_data, {"test": "metadata"})
        
        # Check that log file was created
        log_file = logger.log_dir / "trading" / "trading.log"
        assert log_file.exists()
        
        # Check log content
        with open(log_file, 'r') as f:
            log_content = f.read()
            assert "AAPL" in log_content
            assert "Trade executed" in log_content

    def test_log_portfolio_update(self, logger):
        """Test portfolio update logging."""
        portfolio_data = {
            "total_value": 10000.0,
            "cash": 5000.0,
            "positions": 2
        }
        
        logger.log_portfolio_update(portfolio_data, {"test": "metadata"})
        
        # Check that log file was created
        log_file = logger.log_dir / "portfolio" / "portfolio.log"
        assert log_file.exists()
        
        # Check log content
        with open(log_file, 'r') as f:
            log_content = f.read()
            assert "10000.0" in log_content
            assert "Portfolio updated" in log_content

    def test_log_market_data(self, logger):
        """Test market data logging."""
        market_data = {
            "symbol": "AAPL",
            "price": 150.0,
            "volume": 1000000,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.log_market_data(market_data, {"test": "metadata"})
        
        # Check that log file was created
        log_file = logger.log_dir / "market_data" / "market_data.log"
        assert log_file.exists()
        
        # Check log content
        with open(log_file, 'r') as f:
            log_content = f.read()
            assert "AAPL" in log_content
            assert "Market data processed" in log_content


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


class TestCentralizedLoggerIntegration:
    """Integration tests for centralized logger."""

    def test_multiple_services_logging(self):
        """Test logging to multiple services."""
        with patch('app.services.centralized_logging.Path') as mock_path:
            temp_dir = Path(tempfile.mkdtemp())
            mock_path.return_value = temp_dir
            
            with patch('app.services.centralized_logging.get_config') as mock_config:
                mock_config.return_value = MagicMock()
                with patch.dict('os.environ', {'ENVIRONMENT': 'test', 'APP_VERSION': '1.0.0'}):
                    logger = CentralizedLogger()
                    
                    # Log to different services
                    logger.info(LogService.TRADING, "Trading message")
                    logger.info(LogService.PORTFOLIO, "Portfolio message")
                    logger.info(LogService.MARKET_DATA, "Market data message")
                    
                    # Check that all log files were created
                    assert (temp_dir / "trading" / "trading.log").exists()
                    assert (temp_dir / "portfolio" / "portfolio.log").exists()
                    assert (temp_dir / "market_data" / "market_data.log").exists()
                    
                    # Cleanup
                    shutil.rmtree(temp_dir)

    def test_log_rotation_simulation(self):
        """Test log rotation simulation."""
        with patch('app.services.centralized_logging.Path') as mock_path:
            temp_dir = Path(tempfile.mkdtemp())
            mock_path.return_value = temp_dir
            
            with patch('app.services.centralized_logging.get_config') as mock_config:
                mock_config.return_value = MagicMock()
                with patch.dict('os.environ', {'ENVIRONMENT': 'test', 'APP_VERSION': '1.0.0'}):
                    logger = CentralizedLogger()
                    
                    # Generate multiple log entries
                    for i in range(10):
                        logger.info(LogService.TRADING, f"Message {i}")
                    
                    # Check that log file contains all messages
                    log_file = temp_dir / "trading" / "trading.log"
                    assert log_file.exists()
                    
                    with open(log_file, 'r') as f:
                        log_content = f.read()
                        for i in range(10):
                            assert f"Message {i}" in log_content
                    
                    # Cleanup
                    shutil.rmtree(temp_dir)
