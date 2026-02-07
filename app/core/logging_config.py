import logging
import os
import re
import sys
import time
import uuid
import warnings
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional, Pattern

"""
Logging Configuration Module

Thresholds logging to ensure all warnings and errors are written to files.
This prevents loss of important diagnostic information.

LOG-001: Structured logging with JSON format support
LOG-002: Correlation ID tracking for request tracing
LOG-005: Sensitive data sanitization in logs
LOG-006: Timing information for operations
"""


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    This is a convenience wrapper around logging.getLogger that ensures
    consistent logger creation across the application.

    Args:
        name: The name for the logger (typically __name__ of the calling module)

    Returns:
        A logger instance with the specified name
    """
    return logging.getLogger(name)


# LOG-002: Context variable for correlation ID tracking
_correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> str:
    """
    Get or generate correlation ID for the current request/context.

    LOG-002: Provides correlation ID for request tracing across async operations.

    Returns:
        Correlation ID string
    """
    cid = _correlation_id.get()
    if cid is None:
        cid = str(uuid.uuid4())[:8]  # Short UUID for readability
        _correlation_id.set(cid)
    return cid


def set_correlation_id(cid: str) -> None:
    """
    Set correlation ID for the current request/context.

    Args:
        cid: Correlation ID to set
    """
    _correlation_id.set(cid)


# LOG-005: Patterns for detecting sensitive data in logs
_SENSITIVE_PATTERNS: Dict[str, Pattern[str]] = {
    "password": re.compile(r"password['\"]?\s*[:=]\s*['\"]?[\w\-]+", re.IGNORECASE),
    "token": re.compile(r"token['\"]?\s*[:=]\s*['\"]?[\w\-\.]+", re.IGNORECASE),
    "api_key": re.compile(r"api[_-]?key['\"]?\s*[:=]\s*['\"]?[\w\-]+", re.IGNORECASE),
    "api_secret": re.compile(r"api[_-]?secret['\"]?\s*[:=]\s*['\"]?[\w\-]+", re.IGNORECASE),
    "secret": re.compile(r"secret['\"]?\s*[:=]\s*['\"]?[\w\-]+", re.IGNORECASE),
    "authorization": re.compile(
        r"authorization['\"]?\s*[:=]\s*['\"]?[Bb]earer\s+[\w\-\.]+", re.IGNORECASE
    ),
    "bearer": re.compile(r"[Bb]earer\s+[\w\-\.]+", re.IGNORECASE),
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "ssn": re.compile(r"\b\d{3}[-.]?\d{2}[-.]?\d{4}\b"),
}

# Sensitive field names to redact in structured logging
_SENSITIVE_FIELDS: frozenset[str] = frozenset(
    {
        "password",
        "passwd",
        "pwd",
        "token",
        "access_token",
        "refresh_token",
        "auth_token",
        "api_key",
        "apikey",
        "api-key",
        "api.key",
        "api_secret",
        "apisecret",
        "api-secret",
        "secret",
        "secret_key",
        "secretkey",
        "authorization",
        "auth_header",
        "bearer",
        "credit_card",
        "creditcard",
        "cc_number",
        "ssn",
        "social_security",
        "private_key",
        "privatekey",
    }
)


class SensitiveDataFilter(logging.Filter):
    """
    Filter to redact sensitive data from log messages.

    LOG-005: Prevents sensitive data (passwords, tokens, API keys) from being logged.

    This filter:
    1. Redacts common sensitive field values in structured logs
    2. Uses regex patterns to detect potential sensitive data patterns
    3. Applies to all log handlers to ensure comprehensive coverage

    Example:
        >>> filter = SensitiveDataFilter()
        >>> logger.addFilter(filter)
        >>> logger.info("User logged in with password=secret123")
        # Logs: "User logged in with password=***REDACTED***"
    """

    #: Redaction placeholder used to replace sensitive values
    REDACTED: str = "***REDACTED***"

    def __init__(self) -> None:
        """Initialize the sensitive data filter."""
        super().__init__()
        self._patterns = _SENSITIVE_PATTERNS
        self._sensitive_fields = _SENSITIVE_FIELDS

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter and redact sensitive data from the log record.

        Args:
            record: The log record to filter

        Returns:
            True (always allows the record through, just modifies it)
        """
        # Redact sensitive data from the message
        record.msg = self._redact_message(str(record.msg))

        # Redact sensitive data from the formatted message if already set
        if hasattr(record, "getMessage"):
            try:
                original_message = record.getMessage()
                if original_message != str(record.msg):
                    # If the formatted message differs, update it
                    record.args = ()  # Clear args to prevent double formatting
            except Exception:
                pass

        # Redact sensitive data from extra fields (kwargs passed to log call)
        if hasattr(record, "extra_fields"):
            record.extra_fields = self._redact_dict(record.extra_fields)

        # For JSON formatters, also sanitize the record's __dict__
        self._sanitize_record_dict(record)

        return True

    def _redact_message(self, message: str) -> str:
        """
        Redact sensitive patterns from a message string.

        Args:
            message: The message to sanitize

        Returns:
            The sanitized message with sensitive data redacted
        """
        redacted = message

        # Apply all regex patterns
        for pattern_name, pattern in self._patterns.items():
            redacted = pattern.sub(f"{pattern_name.upper()}={self.REDACTED}", redacted)

        return redacted

    def _redact_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Redact sensitive values from a dictionary.

        Args:
            data: Dictionary to sanitize

        Returns:
            Dictionary with sensitive values redacted
        """
        if not isinstance(data, dict):
            return data

        redacted = {}
        for key, value in data.items():
            key_lower = key.lower().replace("-", "_").replace(".", "")

            # Check if this is a sensitive field
            if any(
                sensitive in key_lower
                for sensitive in [
                    "password",
                    "passwd",
                    "pwd",
                    "token",
                    "access_token",
                    "refresh_token",
                    "api_key",
                    "apikey",
                    "api_key",
                    "api_secret",
                    "apisecret",
                    "secret",
                    "secret_key",
                    "authorization",
                    "bearer",
                    "credit_card",
                    "cc_number",
                    "ssn",
                    "social_security",
                    "private_key",
                ]
            ):
                redacted[key] = self.REDACTED
            elif isinstance(value, dict):
                redacted[key] = self._redact_dict(value)
            elif isinstance(value, (list, tuple)):
                # Handle sequences
                redacted[key] = type(value)(
                    self._redact_dict(item) if isinstance(item, dict) else item for item in value
                )
            else:
                # For string values, also apply pattern redaction
                if isinstance(value, str):
                    redacted[key] = self._redact_message(value)
                else:
                    redacted[key] = value

        return redacted

    def _sanitize_record_dict(self, record: logging.LogRecord) -> None:
        """
        Sanitize the record's __dict__ to remove sensitive data.

        This handles extra parameters passed to log calls like:
            logger.info("Message", password="secret123")

        Args:
            record: The log record to sanitize
        """
        for key in list(record.__dict__.keys()):
            if key.startswith("_") or key in {
                "name",
                "msg",
                "args",
                "asctime",
                "created",
                "filename",
                "funcName",
                "levelname",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
                "asctime",
                "correlation_id",
                "elapsed_ms",
                "delta_ms",
            }:
                continue

            value = record.__dict__[key]
            key_lower = key.lower().replace("-", "_").replace(".", "")

            # Check if this is a sensitive field
            if any(
                sensitive in key_lower
                for sensitive in [
                    "password",
                    "passwd",
                    "pwd",
                    "token",
                    "access_token",
                    "refresh_token",
                    "api_key",
                    "apikey",
                    "api_secret",
                    "apisecret",
                    "secret",
                    "secret_key",
                    "authorization",
                    "bearer",
                    "credit_card",
                    "cc_number",
                    "ssn",
                    "social_security",
                    "private_key",
                ]
            ):
                record.__dict__[key] = self.REDACTED
            elif isinstance(value, str):
                record.__dict__[key] = self._redact_message(value)
            elif isinstance(value, dict):
                record.__dict__[key] = self._redact_dict(value)


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    LOG-001: Outputs logs in JSON format for better parsing and analysis.
    LOG-002: Includes correlation_id field
    LOG-006: Includes timing_ms field for operation timing
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._start_time: float = time.time()

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        import json

        # Calculate timing since formatter initialization
        timing_ms = (time.time() - self._start_time) * 1000

        # Create structured log data
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            # LOG-002: Include correlation ID
            "correlation_id": get_correlation_id(),
            # LOG-006: Include timing information
            "timing_ms": round(timing_ms, 2),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add pathname for error logs
        if record.levelno >= logging.ERROR:
            log_data["pathname"] = record.pathname

        # Add process and thread info for debugging
        log_data["process_id"] = record.process
        log_data["thread_id"] = record.thread

        return json.dumps(log_data, default=str)


class TimedFormatter(logging.Formatter):
    """
    Enhanced text formatter with timing information.

    LOG-006: Adds timing information to log messages.
    """

    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None) -> None:
        super().__init__(fmt, datefmt)
        self._start_time: float = time.time()
        self._last_time: float = self._start_time

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with timing information.

        Args:
            record: Log record to format

        Returns:
            Formatted log string with timing info
        """
        # Calculate timing
        current_time = time.time()
        elapsed_total = (current_time - self._start_time) * 1000
        elapsed_since_last = (current_time - self._last_time) * 1000
        self._last_time = current_time

        # Add timing to record
        record.elapsed_ms = round(elapsed_total, 2)
        record.delta_ms = round(elapsed_since_last, 2)
        # LOG-002: Add correlation ID
        record.correlation_id = get_correlation_id()

        return super().format(record)


# Configure Python warnings to reduce noise
# Suppress known warnings that are expected and handled gracefully
warnings.filterwarnings(
    "ignore", category=UserWarning, module="pydantic._internal._model_construction"
)
warnings.filterwarnings("ignore", message=".*validate_percentage.*overrides.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pandas")
warnings.filterwarnings("ignore", category=FutureWarning, module="pandas")
# Only show warnings once per unique message
warnings.simplefilter("once", UserWarning)


def setup_file_logging(
    log_dir: str = "logs",
    root_level: int = logging.INFO,
    file_level: int = logging.WARNING,
    console_level: Optional[int] = logging.INFO,
    use_json: bool = False,
) -> None:
    """
    Configure logging to write all warnings and errors to files.

    Args:
        log_dir: Directory for log files
        root_level: Level for root logger
        file_level: Minimum level to write to file (default: WARNING)
        console_level: Minimum level for console (None = disable console)
        use_json: If True, use JSON format for structured logging (LOG-001)
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

    # LOG-005: Create sensitive data filter for all handlers
    sensitive_filter = SensitiveDataFilter()

    # Determine formatter based on use_json flag
    # LOG-001: Support JSON structured logging
    if use_json:
        all_formatter = JSONFormatter()
        warning_formatter = JSONFormatter()
        error_formatter = JSONFormatter()
        console_formatter = logging.Formatter('%(levelname)s - %(name)s - %(message)s')
    else:
        # LOG-006: Use TimedFormatter for timing information
        all_formatter = TimedFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(correlation_id)s - '
            '[%(elapsed_ms).2fms / %(delta_ms).2fms] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
        )
        warning_formatter = TimedFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(correlation_id)s - '
            '[%(elapsed_ms).2fms] - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
        )
        error_formatter = TimedFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(correlation_id)s - '
            '[%(elapsed_ms).2fms] - %(funcName)s:%(lineno)d - %(pathname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
        )
        console_formatter = logging.Formatter(
            '%(levelname)s - %(name)s - %(correlation_id)s - %(message)s'
        )

    # Handler for ALL logs (INFO and above)
    all_handler = RotatingFileHandler(
        all_log, maxBytes=10 * 1024 * 1024, backupCount=10, encoding='utf-8'  # 10MB
    )
    all_handler.setLevel(logging.INFO)
    all_handler.setFormatter(all_formatter)
    all_handler.addFilter(sensitive_filter)  # LOG-005: Add sensitive data filter
    root_logger.addHandler(all_handler)

    # Handler for WARNINGS and above
    warning_handler = RotatingFileHandler(
        warning_log, maxBytes=10 * 1024 * 1024, backupCount=10, encoding='utf-8'  # 10MB
    )
    warning_handler.setLevel(logging.WARNING)
    warning_handler.setFormatter(warning_formatter)
    warning_handler.addFilter(sensitive_filter)  # LOG-005: Add sensitive data filter
    root_logger.addHandler(warning_handler)

    # Handler for ERRORS and CRITICAL only
    error_handler = RotatingFileHandler(
        error_log,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=20,  # Keep more error logs
        encoding='utf-8',
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(error_formatter)
    error_handler.addFilter(sensitive_filter)  # LOG-005: Add sensitive data filter
    root_logger.addHandler(error_handler)

    # Console handler (optional, for development)
    if console_level is not None:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(console_level)
        console_handler.setFormatter(console_formatter)
        console_handler.addFilter(sensitive_filter)  # LOG-005: Add sensitive data filter
        root_logger.addHandler(console_handler)

    # Log that logging is configured
    root_logger.info(
        f"Logging configured: warnings->{warning_log}, errors->{error_log}, all->{all_log}",
        extra={"correlation_id": get_correlation_id()},
    )


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

    # LOG-005: Create sensitive data filter for module handlers
    sensitive_filter = SensitiveDataFilter()

    for module_name in important_modules:
        logger = logging.getLogger(module_name)

        # Create module-specific error log
        module_log_file = log_path / f"{module_name.replace('.', '_')}_errors.log"
        handler = RotatingFileHandler(
            module_log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding='utf-8'
        )
        handler.setLevel(logging.WARNING)  # WARNING and above
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
        )
        handler.setFormatter(formatter)
        handler.addFilter(sensitive_filter)  # LOG-005: Add sensitive data filter
        logger.addHandler(handler)
        logger.setLevel(logging.WARNING)  # Only warnings and above for these


def setup_module_loggers(use_json: bool = False) -> None:
    """
    Configure specific loggers for important modules.
    Ensures warnings/errors from these modules are always captured.

    Args:
        use_json: If True, use JSON format for structured logging (LOG-001)
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

    # Choose formatter based on use_json flag
    if use_json:
        formatter = JSONFormatter()
    else:
        # LOG-006: Use TimedFormatter with timing info
        formatter = TimedFormatter(
            '%(asctime)s - %(levelname)s - %(correlation_id)s - '
            '[%(elapsed_ms).2fms] - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
        )

    # LOG-005: Create sensitive data filter for module handlers
    sensitive_filter = SensitiveDataFilter()

    for module_name in important_modules:
        logger = logging.getLogger(module_name)

        # Create module-specific error log
        module_log_file = log_path / f"{module_name.replace('.', '_')}_errors.log"
        handler = RotatingFileHandler(
            module_log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding='utf-8'
        )
        handler.setLevel(logging.WARNING)  # WARNING and above
        handler.setFormatter(formatter)
        handler.addFilter(sensitive_filter)  # LOG-005: Add sensitive data filter
        logger.addHandler(handler)
        logger.setLevel(logging.WARNING)  # Only warnings and above for these


# Initialize logging on import
# This ensures logging is configured as soon as this module is imported

env = os.getenv("ENVIRONMENT", "development")

# LOG-001: Check if JSON logging is enabled via environment variable
use_json_logging = os.getenv("LOG_JSON", "false").lower() == "true"

# In production, disable console logging to avoid clutter
console_level = None if env == "production" else logging.INFO

setup_file_logging(
    log_dir="logs",
    root_level=logging.INFO,
    file_level=logging.WARNING,
    console_level=console_level,
    use_json=use_json_logging,
)

# Setup module-specific loggers
setup_module_loggers(use_json=use_json_logging)
