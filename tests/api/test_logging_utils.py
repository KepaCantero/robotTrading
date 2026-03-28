"""
Tests for API logging utilities with correlation ID support.

Tests the logging_utils module which provides structured logging with correlation IDs.
"""

from unittest.mock import Mock, patch

import pytest

from app.presentation.api.logging_utils import (
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

    @patch("app.presentation.api.logging_utils.logger")
    def test_log_with_context_info_level(self, mock_logger):
        """Test logging with context at info level."""
        # Create mock request
        request = Mock()
        request.state.correlation_id = "test-correlation-456"

        # Log with context
        log_with_context(
            request,
            "Test info message",
            level="info",
            extra_key="extra_value",
            user_id="user123",
        )

        # Verify logger.info was called
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "Test info message"
        assert "correlation_id" in call_args[1]["extra"]
        assert call_args[1]["extra"]["correlation_id"] == "test-correlation-456"
        assert call_args[1]["extra"]["extra_key"] == "extra_value"
        assert call_args[1]["extra"]["user_id"] == "user123"

    @patch("app.presentation.api.logging_utils.logger")
    def test_log_with_context_warning_level(self, mock_logger):
        """Test logging with context at warning level."""
        # Create mock request
        request = Mock()
        request.state.correlation_id = "test-correlation-789"

        # Log with context
        log_with_context(
            request,
            "Test warning message",
            level="warning",
            warning_type="test_warning",
        )

        # Verify logger.warning was called
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert call_args[0][0] == "Test warning message"
        assert call_args[1]["extra"]["correlation_id"] == "test-correlation-789"
        assert call_args[1]["extra"]["warning_type"] == "test_warning"

    @patch("app.presentation.api.logging_utils.logger")
    def test_log_with_context_error_level(self, mock_logger):
        """Test logging with context at error level."""
        # Create mock request
        request = Mock()
        request.state.correlation_id = "test-correlation-error"

        # Log with context
        log_with_context(
            request,
            "Test error message",
            level="error",
            error_code="TEST_ERROR",
        )

        # Verify logger.error was called
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert call_args[0][0] == "Test error message"
        assert call_args[1]["extra"]["correlation_id"] == "test-correlation-error"
        assert call_args[1]["extra"]["error_code"] == "TEST_ERROR"

    @patch("app.presentation.api.logging_utils.logger")
    def test_log_info_convenience_function(self, mock_logger):
        """Test the log_info convenience function."""
        request = Mock()
        request.state.correlation_id = "test-correlation-info"

        log_info(
            request,
            "Info log test",
            endpoint="/test/endpoint",
            method="GET",
        )

        # Verify
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "Info log test"
        assert call_args[1]["extra"]["endpoint"] == "/test/endpoint"
        assert call_args[1]["extra"]["method"] == "GET"

    @patch("app.presentation.api.logging_utils.logger")
    def test_log_warning_convenience_function(self, mock_logger):
        """Test the log_warning convenience function."""
        request = Mock()
        request.state.correlation_id = "test-correlation-warn"

        log_warning(
            request,
            "Warning log test",
            warning_code="WARN_001",
        )

        # Verify
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert call_args[0][0] == "Warning log test"
        assert call_args[1]["extra"]["warning_code"] == "WARN_001"

    @patch("app.presentation.api.logging_utils.logger")
    def test_log_error_convenience_function_without_exception(self, mock_logger):
        """Test the log_error convenience function without exception."""
        request = Mock()
        request.state.correlation_id = "test-correlation-err"

        log_error(
            request,
            "Error log test",
            error_code="ERR_001",
        )

        # Verify
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert call_args[0][0] == "Error log test"
        assert call_args[1]["extra"]["error_code"] == "ERR_001"

    @patch("app.presentation.api.logging_utils.logger")
    def test_log_error_convenience_function_with_exception(self, mock_logger):
        """Test the log_error convenience function with exception."""
        request = Mock()
        request.state.correlation_id = "test-correlation-exception"

        exception = ValueError("Test exception message")

        log_error(
            request,
            "Exception occurred",
            exception=exception,
            context_key="context_value",
        )

        # Verify
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert call_args[0][0] == "Exception occurred"
        assert call_args[1]["extra"]["error_type"] == "ValueError"
        assert call_args[1]["extra"]["error_message"] == "Test exception message"
        assert call_args[1]["extra"]["context_key"] == "context_value"

    @patch("app.presentation.api.logging_utils.logger")
    def test_log_debug_convenience_function(self, mock_logger):
        """Test the log_debug convenience function."""
        request = Mock()
        request.state.correlation_id = "test-correlation-debug"

        log_debug(
            request,
            "Debug log test",
            debug_var="debug_value",
        )

        # Verify
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        assert call_args[0][0] == "Debug log test"
        assert call_args[1]["extra"]["debug_var"] == "debug_value"

    def test_log_with_context_invalid_level_does_not_crash(self):
        """Test that invalid log level doesn't crash the application."""
        request = Mock()
        request.state.correlation_id = "test-correlation-invalid"

        # This should not crash - invalid level should default to logger.info
        log_with_context(
            request,
            "Invalid level test",
            level="nonexistent_level",
        )

        # If we get here without exception, the test passes
        # The actual behavior is that getattr(logger, level, logger.info)
        # will return logger.info when the level doesn't exist

    @patch("app.presentation.api.logging_utils.logger")
    def test_multiple_logs_with_different_correlation_ids(self, mock_logger):
        """Test multiple logs with different correlation IDs."""
        request1 = Mock()
        request1.state.correlation_id = "correlation-1"

        request2 = Mock()
        request2.state.correlation_id = "correlation-2"

        log_info(request1, "Request 1 message")
        log_info(request2, "Request 2 message")

        # Verify both logs exist
        assert mock_logger.info.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
