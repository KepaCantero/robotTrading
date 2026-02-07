"""
Tests for API logging utilities with correlation ID support.

Tests the logging_utils module which provides structured logging with correlation IDs.
"""

import logging
from unittest.mock import Mock

import pytest

from app.api.logging_utils import (
    get_correlation_id_from_request,
    log_debug,
    log_error,
    log_info,
    log_warning,
    log_with_context,
)


class TestLoggingUtils:
    """Test suite for logging utilities."""

    def test_get_correlation_id_from_request_with_correlation_id(self):
        """Test extracting correlation ID when it exists in request state."""
        # Create mock request with correlation ID
        request = Mock()
        request.state.correlation_id = "test-correlation-123"

        # Extract correlation ID
        result = get_correlation_id_from_request(request)

        # Verify
        assert result == "test-correlation-123"

    def test_get_correlation_id_from_request_without_correlation_id(self):
        """Test extracting correlation ID when it doesn't exist in request state."""
        # Create mock request without correlation_id attribute
        request = Mock(spec=["state"])

        # Delete the correlation_id attribute to simulate it not existing
        # This makes getattr return the default value
        del request.state.correlation_id

        # Extract correlation ID - should return "unknown"
        result = get_correlation_id_from_request(request)

        # Verify
        assert result == "unknown"

    def test_log_with_context_info_level(self, caplog):
        """Test logging with context at info level."""
        # Create mock request
        request = Mock()
        request.state.correlation_id = "test-correlation-456"

        # Log with context
        with caplog.at_level(logging.INFO):
            log_with_context(
                request,
                "Test info message",
                level="info",
                extra_key="extra_value",
                user_id="user123",
            )

        # Verify log entry
        assert len(caplog.records) >= 1
        # The last record should be our log
        record = caplog.records[-1]
        assert record.message == "Test info message"
        assert record.levelname == "INFO"

    def test_log_with_context_warning_level(self, caplog):
        """Test logging with context at warning level."""
        # Create mock request
        request = Mock()
        request.state.correlation_id = "test-correlation-789"

        # Log with context
        with caplog.at_level(logging.WARNING):
            log_with_context(
                request,
                "Test warning message",
                level="warning",
                warning_type="test_warning",
            )

        # Verify log entry
        assert len(caplog.records) >= 1
        record = caplog.records[-1]
        assert record.message == "Test warning message"
        assert record.levelname == "WARNING"

    def test_log_with_context_error_level(self, caplog):
        """Test logging with context at error level."""
        # Create mock request
        request = Mock()
        request.state.correlation_id = "test-correlation-error"

        # Log with context
        with caplog.at_level(logging.ERROR):
            log_with_context(
                request,
                "Test error message",
                level="error",
                error_code="TEST_ERROR",
            )

        # Verify log entry
        assert len(caplog.records) >= 1
        record = caplog.records[-1]
        assert record.message == "Test error message"
        assert record.levelname == "ERROR"

    def test_log_info_convenience_function(self, caplog):
        """Test the log_info convenience function."""
        request = Mock()
        request.state.correlation_id = "test-correlation-info"

        with caplog.at_level(logging.INFO):
            log_info(
                request,
                "Info log test",
                endpoint="/test/endpoint",
                method="GET",
            )

        # Verify
        assert len(caplog.records) >= 1
        record = caplog.records[-1]
        assert record.message == "Info log test"
        assert record.levelname == "INFO"

    def test_log_warning_convenience_function(self, caplog):
        """Test the log_warning convenience function."""
        request = Mock()
        request.state.correlation_id = "test-correlation-warn"

        with caplog.at_level(logging.WARNING):
            log_warning(
                request,
                "Warning log test",
                warning_code="WARN_001",
            )

        # Verify
        assert len(caplog.records) >= 1
        record = caplog.records[-1]
        assert record.message == "Warning log test"
        assert record.levelname == "WARNING"

    def test_log_error_convenience_function_without_exception(self, caplog):
        """Test the log_error convenience function without exception."""
        request = Mock()
        request.state.correlation_id = "test-correlation-err"

        with caplog.at_level(logging.ERROR):
            log_error(
                request,
                "Error log test",
                error_code="ERR_001",
            )

        # Verify
        assert len(caplog.records) >= 1
        record = caplog.records[-1]
        assert record.message == "Error log test"
        assert record.levelname == "ERROR"

    def test_log_error_convenience_function_with_exception(self, caplog):
        """Test the log_error convenience function with exception."""
        request = Mock()
        request.state.correlation_id = "test-correlation-exception"

        exception = ValueError("Test exception message")

        with caplog.at_level(logging.ERROR):
            log_error(
                request,
                "Exception occurred",
                exception=exception,
                context_key="context_value",
            )

        # Verify
        assert len(caplog.records) >= 1
        record = caplog.records[-1]
        assert record.message == "Exception occurred"
        assert record.levelname == "ERROR"

    def test_log_debug_convenience_function(self, caplog):
        """Test the log_debug convenience function."""
        request = Mock()
        request.state.correlation_id = "test-correlation-debug"

        with caplog.at_level(logging.DEBUG):
            log_debug(
                request,
                "Debug log test",
                debug_var="debug_value",
            )

        # Verify
        assert len(caplog.records) >= 1
        record = caplog.records[-1]
        assert record.message == "Debug log test"
        assert record.levelname == "DEBUG"

    def test_log_with_context_invalid_level_defaults_to_info(self, caplog):
        """Test that invalid log level defaults to info."""
        request = Mock()
        request.state.correlation_id = "test-correlation-invalid"

        with caplog.at_level(logging.INFO):
            log_with_context(
                request,
                "Invalid level test",
                level="invalid_level",
            )

        # Verify - should default to INFO
        assert len(caplog.records) >= 1
        record = caplog.records[-1]
        assert record.message == "Invalid level test"
        assert record.levelname == "INFO"

    def test_multiple_logs_with_different_correlation_ids(self, caplog):
        """Test multiple logs with different correlation IDs."""
        request1 = Mock()
        request1.state.correlation_id = "correlation-1"

        request2 = Mock()
        request2.state.correlation_id = "correlation-2"

        with caplog.at_level(logging.INFO):
            log_info(request1, "Request 1 message")
            log_info(request2, "Request 2 message")

        # Verify both logs exist
        assert len(caplog.records) >= 2
        messages = [r.message for r in caplog.records[-2:]]
        assert "Request 1 message" in messages
        assert "Request 2 message" in messages


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
