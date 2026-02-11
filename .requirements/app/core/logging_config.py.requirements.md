# logging_config.py Requirements

**File Path:** `app/core/logging_config.py`  
**Last Updated:** 2025-02-06  
**Audit Status:** PASSED
**Audit Timestamp:** 2026-02-06T19:41:12.289899

## Purpose

Centralized logging configuration with file rotation, correlation ID tracking, sensitive data filtering, JSON format support, and timing information.

## Type Definitions

### Classes
```python
class SensitiveDataFilter(logging.Filter):
    """Filter to redact sensitive data from log messages."""
    REDACTED: str = "***REDACTED***"

class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

class TimedFormatter(logging.Formatter):
    """Enhanced text formatter with timing information."""
```

## Function Signatures

### Core Functions
```python
def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    
def get_correlation_id() -> str:
    """Get or generate correlation ID for current context."""
    
def set_correlation_id(cid: str) -> None:
    """Set correlation ID for current context."""
```

### Setup Functions
```python
def setup_file_logging(
    log_dir: str = "logs",
    root_level: int = logging.INFO,
    file_level: int = logging.WARNING,
    console_level: Optional[int] = logging.INFO,
    use_json: bool = False,
) -> None:
    """Configure logging to write all warnings and errors to files."""
    
def setup_module_loggers(use_json: bool = False) -> None:
    """Configure specific loggers for important modules."""
```

## Acceptance Criteria

### AC-LOG-001: JSON Structured Logging
```bash
# Test: JSON format produces valid JSON
python -c "
import logging
import json
from app.core.logging_config import setup_file_logging, get_logger
setup_file_logging(use_json=True)
logger = get_logger('test')
# Check that JSON formatter is used
import io
import sys
handler = logging.StreamHandler(io.StringIO())
handler.setFormatter(JSONFormatter())
logging.getLogger('test').addHandler(handler)
logger.info('test message')
# Verify JSON output
"
```

### AC-LOG-002: Correlation ID Tracking
```bash
# Test: Correlation ID is consistent across logs
python -c "
from app.core.logging_config import get_correlation_id, set_correlation_id
set_correlation_id('test-123')
assert get_correlation_id() == 'test-123'
assert get_correlation_id() == 'test-123'  # Consistent
"
```

### AC-LOG-003: Sensitive Data Redaction
```bash
# Test: Sensitive data is redacted from logs
python -c "
from app.core.logging_config import SensitiveDataFilter
import logging
f = SensitiveDataFilter()
record = logging.LogRecord(
    'test', logging.INFO, 'test.py', 1,
    'password=secret123', (), None
)
f.filter(record)
assert '***REDACTED***' in record.msg
assert 'secret123' not in record.msg
"
```

### AC-LOG-004: Timing Information
```bash
# Test: Timing information included in logs
python -c "
from app.core.logging_config import TimedFormatter
import logging
formatter = TimedFormatter()
record = logging.LogRecord(
    'test', logging.INFO, 'test.py', 1,
    'test message', (), None
)
formatted = formatter.format(record)
assert 'elapsed_ms' in formatted or 'delta_ms' in formatted
"
```

## Critical Rules

### Rule LOG-001: Structured Logging
**Priority:** P1  
**Description:** Support JSON format for structured logging when `LOG_JSON=true` or `use_json=True`.

### Rule LOG-002: Correlation ID
**Priority:** P0  
**Description:** All log entries must include correlation ID for request tracing across async operations.

### Rule LOG-003: File Rotation
**Priority:** P0  
**Description:** Use `RotatingFileHandler` with 10MB max size and appropriate backup count.

### Rule LOG-004: Error Logging
**Priority:** P0  
**Description:** All errors and warnings MUST be written to log files, not just console.

### Rule LOG-005: Sensitive Data Sanitization
**Priority:** P0  
**Description:** Sensitive data (passwords, tokens, API keys) must be redacted from all logs.

### Rule LOG-006: Timing Information
**Priority:** P2  
**Description:** Include timing information (elapsed_ms, delta_ms) in log messages for performance analysis.

## Dependencies

### Internal Dependencies
None (pure logging module)

### External Dependencies
```python
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
```

## Required Tests

### Unit Tests (app/tests/core/test_logging_config.py)
```python
def test_get_logger():
    """Test getting logger instance."""
    
def test_get_correlation_id():
    """Test correlation ID generation."""
    
def test_set_correlation_id():
    """Test setting correlation ID."""
    
def test_correlation_id_consistency():
    """Test correlation ID is consistent within context."""
    
def test_sensitive_data_filter_password():
    """Test password redaction."""
    
def test_sensitive_data_filter_token():
    """Test token redaction."""
    
def test_sensitive_data_filter_api_key():
    """Test API key redaction."""
    
def test_sensitive_data_filter_dict():
    """Test redaction in dictionary values."""
    
def test_sensitive_data_filter_record_dict():
    """Test redaction in LogRecord.__dict__."""
    
def test_json_formatter():
    """Test JSON formatter produces valid JSON."""
    
def test_json_formatter_includes_correlation_id():
    """Test JSON formatter includes correlation ID."""
    
def test_json_formatter_includes_timing():
    """Test JSON formatter includes timing_ms."""
    
def test_timed_formatter():
    """Test timed formatter includes timing info."""
    
def test_timed_formatter_includes_correlation_id():
    """Test timed formatter includes correlation ID."""
    
def test_setup_file_logging():
    """Test file logging setup."""
    
def test_setup_file_logging_json():
    """Test file logging with JSON format."""
    
def test_setup_file_logging_no_console():
    """Test file logging without console output."""
    
def test_setup_module_loggers():
    """Test module logger setup."""
    
def test_warnings_filtering():
    """Test warnings are filtered appropriately."""
```

## File-Specific Rules

### Rule LOG-FS-001: Init on Import
**Priority:** P2  
**Description:** Logging is configured automatically on module import. No manual setup required.

### Rule LOG-FS-002: Environment-Based Config
**Priority:** P0  
**Description:** Console logging disabled in production, JSON logging controlled by `LOG_JSON` env var.

### Rule LOG-FS-003: Duplicate Handler Prevention
**Priority:** P1  
**Description:** Clear existing handlers before adding new ones to prevent duplicate logging.

### Rule LOG-FS-004: Sensitive Patterns
**Priority:** P0  
**Description:** Comprehensive regex patterns for detecting sensitive data in log messages.

## Sensitive Data Patterns

### Patterns Detected
```python
_SENSITIVE_PATTERNS = {
    "password": re.compile(r"password['\"]?\s*[:=]\s*['\"]?[\w\-]+", re.IGNORECASE),
    "token": re.compile(r"token['\"]?\s*[:=]\s*['\"]?[\w\-\.]+", re.IGNORECASE),
    "api_key": re.compile(r"api[_-]?key['\"]?\s*[:=]\s*['\"]?[\w\-]+", re.IGNORECASE),
    "api_secret": re.compile(r"api[_-]?secret['\"]?\s*[:=]\s*['\"]?[\w\-]+", re.IGNORECASE),
    "secret": re.compile(r"secret['\"]?\s*[:=]\s*['\"]?[\w\-]+", re.IGNORECASE),
    "authorization": re.compile(r"authorization['\"]?\s*[:=]\s*['\"]?[Bb]earer\s+[\w\-\.]+", re.IGNORECASE),
    "bearer": re.compile(r"[Bb]earer\s+[\w\-\.]+", re.IGNORECASE),
    "credit_card": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "ssn": re.compile(r"\b\d{3}[-.]?\d{2}[-.]?\d{4}\b"),
}
```

### Fields Redacted
```python
_SENSITIVE_FIELDS = frozenset({
    "password", "passwd", "pwd",
    "token", "access_token", "refresh_token", "auth_token",
    "api_key", "apikey", "api-key", "api.key",
    "api_secret", "apisecret", "api-secret",
    "secret", "secret_key", "secretkey",
    "authorization", "auth_header",
    "bearer",
    "credit_card", "creditcard", "cc_number",
    "ssn", "social_security",
    "private_key", "privatekey",
})
```

## References

- **BASE_RULES.md:** See ../../BASE_RULES.md for universal rules
  - LOG-001: Structured logging
  - LOG-002: Correlation ID
  - LOG-004: Error logging
  - LOG-005: Sensitive data sanitization
  - SEC-005: Audit logging
- **Related Files:**
  - `app/core/audit.py` - Audit logging module

## Changelog

### 2025-02-06
- Initial requirements documentation created
- Documented sensitive data filtering
- Documented correlation ID tracking
- Documented JSON structured logging
- Audit Status: NEEDS_AUDIT
