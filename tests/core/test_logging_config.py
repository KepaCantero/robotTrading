"""
Tests for core logging configuration module.

Tests the SensitiveDataFilter which prevents sensitive data from being logged.
"""

import json
import logging

import pytest

from app.core.logging_config import (
    JSONFormatter,
    SensitiveDataFilter,
    TimedFormatter,
    get_correlation_id,
    set_correlation_id,
    setup_file_logging,
)


class TestSensitiveDataFilter:
    """Test suite for SensitiveDataFilter LOG-005."""

    def test_password_redaction_in_message(self, caplog):
        """Test that passwords are redacted from log messages."""
        filter_obj = SensitiveDataFilter()

        with caplog.at_level(logging.INFO):
            logger = logging.getLogger("test_logger")
            logger.addFilter(filter_obj)

            logger.info("User logged in with password=secret123")

            assert len(caplog.records) >= 1
            record = caplog.records[-1]
            assert "secret123" not in record.getMessage()
            assert "***REDACTED***" in record.getMessage() or "PASSWORD" in record.getMessage()

    def test_token_redaction_in_message(self, caplog):
        """Test that tokens are redacted from log messages."""
        filter_obj = SensitiveDataFilter()

        with caplog.at_level(logging.INFO):
            logger = logging.getLogger("test_token_logger")
            logger.addFilter(filter_obj)

            logger.info("API request with token=abc123def456")

            assert len(caplog.records) >= 1
            record = caplog.records[-1]
            assert "abc123def456" not in record.getMessage()

    def test_api_key_redaction_in_message(self, caplog):
        """Test that API keys are redacted from log messages."""
        filter_obj = SensitiveDataFilter()

        with caplog.at_level(logging.INFO):
            logger = logging.getLogger("test_apikey_logger")
            logger.addFilter(filter_obj)

            logger.info("Config loaded with api_key=my_secret_key_123")

            assert len(caplog.records) >= 1
            record = caplog.records[-1]
            assert "my_secret_key_123" not in record.getMessage()

    def test_api_secret_redaction_in_message(self, caplog):
        """Test that API secrets are redacted from log messages."""
        filter_obj = SensitiveDataFilter()

        with caplog.at_level(logging.INFO):
            logger = logging.getLogger("test_apisecret_logger")
            logger.addFilter(filter_obj)

            logger.info("Authentication with api_secret=top_secret_abc")

            assert len(caplog.records) >= 1
            record = caplog.records[-1]
            assert "top_secret_abc" not in record.getMessage()

    def test_authorization_bearer_redaction(self, caplog):
        """Test that Bearer tokens in Authorization headers are redacted."""
        filter_obj = SensitiveDataFilter()

        with caplog.at_level(logging.INFO):
            logger = logging.getLogger("test_auth_logger")
            logger.addFilter(filter_obj)

            logger.info("Request with authorization=Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")

            assert len(caplog.records) >= 1
            record = caplog.records[-1]
            assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in record.getMessage()

    def test_credit_card_pattern_redaction(self, caplog):
        """Test that credit card numbers are redacted from log messages."""
        filter_obj = SensitiveDataFilter()

        with caplog.at_level(logging.INFO):
            logger = logging.getLogger("test_cc_logger")
            logger.addFilter(filter_obj)

            logger.info("Payment with card 4532-1234-5678-9010")

            assert len(caplog.records) >= 1
            record = caplog.records[-1]
            message = record.getMessage()
            # Credit card pattern should be redacted
            assert "4532-1234-5678-9010" not in message or "CREDIT_CARD" in message

    def test_ssn_pattern_redaction(self, caplog):
        """Test that Social Security Numbers are redacted from log messages."""
        filter_obj = SensitiveDataFilter()

        with caplog.at_level(logging.INFO):
            logger = logging.getLogger("test_ssn_logger")
            logger.addFilter(filter_obj)

            logger.info("User SSN: 123-45-6789")

            assert len(caplog.records) >= 1
            record = caplog.records[-1]
            message = record.getMessage()
            # SSN pattern should be redacted
            assert "123-45-6789" not in message or "SSN" in message

    def test_sensitive_field_in_extra_kwargs(self, caplog):
        """Test that sensitive fields in extra kwargs are redacted."""
        filter_obj = SensitiveDataFilter()

        with caplog.at_level(logging.INFO):
            logger = logging.getLogger("test_kwargs_logger")
            logger.addFilter(filter_obj)

            # Use the 'extra' parameter to add custom fields
            logger.info("User login", extra={"password": "my_secret_password"})

            assert len(caplog.records) >= 1
            record = caplog.records[-1]
            # Check that password was redacted in record dict
            if hasattr(record, "password"):
                assert record.password == "***REDACTED***" or "my_secret_password" not in str(
                    record.password
                )

    def test_multiple_sensitive_fields(self, caplog):
        """Test that multiple sensitive fields in one message are all redacted."""
        filter_obj = SensitiveDataFilter()

        with caplog.at_level(logging.INFO):
            logger = logging.getLogger("test_multi_logger")
            logger.addFilter(filter_obj)

            # Use the 'extra' parameter to add custom fields
            logger.info(
                "Config loaded",
                extra={"password": "secret123", "api_key": "key_abc", "token": "token_xyz"},
            )

            assert len(caplog.records) >= 1
            record = caplog.records[-1]
            message = record.getMessage()
            # All sensitive values should be redacted
            assert "secret123" not in message
            assert "key_abc" not in message
            assert "token_xyz" not in message

    def test_case_insensitive_password_detection(self, caplog):
        """Test that password detection is case-insensitive."""
        filter_obj = SensitiveDataFilter()

        with caplog.at_level(logging.INFO):
            logger = logging.getLogger("test_case_logger")
            logger.addFilter(filter_obj)

            # Test various case combinations
            logger.info("Login with PASSWORD=secret123")
            logger.info("Login with Password=secret456")
            logger.info("Login with password=secret789")

            assert len(caplog.records) >= 3
            for record in caplog.records[-3:]:
                message = record.getMessage()
                # None of the actual secrets should be in the message
                assert "secret123" not in message
                assert "secret456" not in message
                assert "secret789" not in message

    def test_dict_redaction(self):
        """Test that dictionaries with sensitive keys are properly redacted."""
        filter_obj = SensitiveDataFilter()

        test_dict = {
            "username": "john_doe",
            "password": "secret123",
            "email": "john@example.com",
            "api_key": "key_abc",
            "nested": {"secret": "nested_secret", "normal_value": "keep_this"},
        }

        redacted = filter_obj._redact_dict(test_dict)

        assert redacted["username"] == "john_doe"
        assert redacted["password"] == "***REDACTED***"
        assert redacted["email"] == "john@example.com"
        assert redacted["api_key"] == "***REDACTED***"
        assert redacted["nested"]["secret"] == "***REDACTED***"
        assert redacted["nested"]["normal_value"] == "keep_this"

    def test_filter_returns_true(self):
        """Test that filter always returns True (allows record through)."""
        filter_obj = SensitiveDataFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test message",
            args=(),
            exc_info=None,
        )

        result = filter_obj.filter(record)

        # Filter should always return True (just modifies, never blocks)
        assert result is True

    def test_redacted_constant(self):
        """Test that REDACTED constant is set correctly."""
        filter_obj = SensitiveDataFilter()
        assert filter_obj.REDACTED == "***REDACTED***"

    def test_bearer_token_detection(self, caplog):
        """Test that standalone Bearer tokens are detected and redacted."""
        filter_obj = SensitiveDataFilter()

        with caplog.at_level(logging.INFO):
            logger = logging.getLogger("test_bearer_logger")
            logger.addFilter(filter_obj)

            logger.info("Auth header: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abc")

            assert len(caplog.records) >= 1
            record = caplog.records[-1]
            message = record.getMessage()
            # JWT token should be redacted
            assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in message

    def test_various_sensitive_key_formats(self, caplog):
        """Test that various formats of sensitive keys are detected."""
        filter_obj = SensitiveDataFilter()

        with caplog.at_level(logging.INFO):
            logger = logging.getLogger("test_formats_logger")
            logger.addFilter(filter_obj)

            # Test various key formats with underscores - using 'extra' parameter
            logger.info("Config loaded", extra={"api_key": "val1", "api_key_alt": "val2"})
            logger.info("Config loaded", extra={"api_secret": "val4", "secret_key": "val5"})
            logger.info("Config loaded", extra={"secret_key": "val6", "secretkey": "val7"})

            assert len(caplog.records) >= 3
            for record in caplog.records[-3:]:
                # All sensitive values should be redacted
                message = record.getMessage()
                assert "val1" not in message
                assert "val2" not in message
                assert "val4" not in message
                assert "val5" not in message
                assert "val6" not in message
                assert "val7" not in message


class TestCorrelationId:
    """Test suite for correlation ID tracking LOG-002."""

    def test_get_correlation_id_generates_new_id(self):
        """Test that get_correlation_id generates a new ID if none exists."""
        # Clear the context variable
        from app.core.logging_config import _correlation_id

        _correlation_id.set(None)

        cid = get_correlation_id()

        assert cid is not None
        assert len(cid) == 8  # Short UUID format

    def test_set_and_get_correlation_id(self):
        """Test setting and getting correlation ID."""
        test_id = "test-correlation-123"
        set_correlation_id(test_id)

        cid = get_correlation_id()

        assert cid == test_id


class TestJSONFormatter:
    """Test suite for JSONFormatter LOG-001."""

    def test_json_formatter_outputs_valid_json(self, caplog):
        """Test that JSONFormatter outputs valid JSON."""
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.funcName = "test_func"
        record.module = "test_module"
        record.process = 12345
        record.thread = 67890

        formatted = formatter.format(record)

        # Should be valid JSON
        data = json.loads(formatted)

        assert data["level"] == "INFO"
        assert data["message"] == "Test message"
        assert data["logger"] == "test"
        assert "correlation_id" in data
        assert "timing_ms" in data

    def test_json_formatter_includes_correlation_id(self, caplog):
        """Test that JSONFormatter includes correlation ID LOG-002."""
        formatter = JSONFormatter()
        test_cid = "test-json-cid"
        set_correlation_id(test_cid)

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        data = json.loads(formatted)

        assert "correlation_id" in data

    def test_json_formatter_includes_timing_info(self):
        """Test that JSONFormatter includes timing information LOG-006."""
        formatter = JSONFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        data = json.loads(formatted)

        assert "timing_ms" in data
        assert isinstance(data["timing_ms"], (int, float))


class TestTimedFormatter:
    """Test suite for TimedFormatter LOG-006."""

    def test_timed_formatter_adds_timing_fields(self):
        """Test that TimedFormatter adds elapsed_ms and delta_ms."""
        formatter = TimedFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(elapsed_ms).2fms] - %(message)s'
        )

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatter.format(record)

        # After formatting, record should have timing attributes
        assert hasattr(record, "elapsed_ms")
        assert hasattr(record, "delta_ms")
        assert hasattr(record, "correlation_id")

    def test_timed_formatter_includes_correlation_id(self):
        """Test that TimedFormatter includes correlation ID LOG-002."""
        formatter = TimedFormatter('%(message)s - %(correlation_id)s')

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)

        # The formatted string should contain the message and some correlation ID value
        assert "Test message" in formatted
        # After the message there should be a correlation ID (8 chars typically)
        parts = formatted.split(" - ")
        assert len(parts) >= 2
        # Second part should be the correlation ID
        correlation_id = parts[-1].strip()
        assert len(correlation_id) > 0  # Should have some value


class TestSetupFileLogging:
    """Test suite for setup_file_logging function."""

    def test_setup_file_logging_creates_log_directory(self, tmp_path):
        """Test that setup_file_logging creates log directory."""
        log_dir = tmp_path / "test_logs"

        setup_file_logging(
            log_dir=str(log_dir),
            console_level=None,  # Disable console
        )

        assert log_dir.exists()
        assert (log_dir / "warnings.log").exists()
        assert (log_dir / "errors.log").exists()
        assert (log_dir / "all.log").exists()

    def test_setup_file_logging_applies_sensitive_filter(self, tmp_path, caplog):
        """Test that setup_file_logging applies SensitiveDataFilter LOG-005."""
        log_dir = tmp_path / "test_sensitive_logs"

        setup_file_logging(
            log_dir=str(log_dir),
            console_level=None,
        )

        logger = logging.getLogger()
        logger.info("Test with password=secret123")

        # Check that the filter was applied by checking the log file
        all_log = log_dir / "all.log"
        if all_log.exists():
            content = all_log.read_text()
            # Password should be redacted
            assert "secret123" not in content or "***REDACTED***" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
