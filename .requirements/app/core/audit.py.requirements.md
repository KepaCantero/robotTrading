# audit.py Requirements

**File Path:** `app/core/audit.py`  
**Last Updated:** 2025-02-06  
**Audit Status:** NEEDS_AUDIT

## Purpose

Audit logging module for sensitive operations. Provides structured audit logging for trades, deployments, configuration changes, and user actions with correlation ID tracking and retention management.

## Type Definitions

### Enums
```python
class AuditAction(str, Enum):
    """Audit action types."""
    # Trading actions
    TRADE_CREATE = "trade.create"
    TRADE_EXECUTE = "trade.execute"
    TRADE_CANCEL = "trade.cancel"
    TRADE_MODIFY = "trade.modify"
    
    # Portfolio actions
    PORTFOLIO_CREATE = "portfolio.create"
    PORTFOLIO_UPDATE = "portfolio.update"
    PORTFOLIO_DELETE = "portfolio.delete"
    PORTFOLIO_READ = "portfolio.read"
    
    # Deployment actions
    STRATEGY_DEPLOY = "strategy.deploy"
    STRATEGY_VALIDATE = "strategy.validate"
    STRATEGY_STOP = "strategy.stop"
    CONFIG_CHANGE = "config.change"
    
    # Authentication actions
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    AUTH_FAILED = "auth.failed"
    
    # Data actions
    DATA_EXPORT = "data.export"
    DATA_IMPORT = "data.import"
    DATA_DELETE = "data.delete"
    
    # System actions
    SYSTEM_START = "system.start"
    SYSTEM_STOP = "system.stop"
    SYSTEM_ERROR = "system.error"
```

### Classes
```python
class AuditLogger:
    """Centralized audit logging."""
    
    def __init__(self, log_dir: str = "logs/audit"):
        """Initialize audit logger."""
```

## Function Signatures

### Core Methods
```python
def log(
    self,
    action: AuditAction,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    validate: bool = True,
) -> None:
    """Log an audit event."""
    
def log_trade(
    self,
    action: AuditAction,
    symbol: str,
    side: str,
    quantity: float,
    price: Optional[float] = None,
    trade_id: Optional[str] = None,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    portfolio_id: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    **kwargs,
) -> None:
    """Log a trading action."""
    
def log_deployment(
    self,
    action: AuditAction,
    strategy_name: str,
    decision_id: Optional[str] = None,
    status: Optional[str] = None,
    scores: Optional[Dict[str, float]] = None,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    **kwargs,
) -> None:
    """Log a deployment action."""
    
def log_portfolio(
    self,
    action: AuditAction,
    portfolio_id: Optional[str] = None,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    **kwargs,
) -> None:
    """Log a portfolio action."""
    
def from_request(
    self,
    action: AuditAction,
    request: Request,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
) -> None:
    """Log an audit event from a FastAPI request."""
```

### Management Methods
```python
def cleanup_old_logs(
    self,
    retention_days: Optional[int] = None,
) -> int:
    """Remove audit log files older than retention period."""
    
def get_log_size_info(self) -> Dict[str, Any]:
    """Get information about audit log file sizes."""
```

### Validation
```python
def _validate_string_param(
    self,
    value: Optional[str],
    param_name: str,
    allow_empty: bool = False,
) -> Optional[str]:
    """Validate a string parameter."""
    
def _validate_log_params(
    self,
    action: AuditAction,
    user_id: Optional[str],
    username: Optional[str],
    resource_type: Optional[str],
    resource_id: Optional[str],
    ip_address: Optional[str],
) -> None:
    """Validate log parameters."""
```

### Singleton Access
```python
def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance."""
```

### Context Manager
```python
@contextmanager
def audit_context(
    action: AuditAction,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    auto_log: bool = True,
):
    """Context manager for audit logging."""
```

### Convenience Functions
```python
def log_trade_execution(
    symbol: str,
    side: str,
    quantity: float,
    price: Optional[float] = None,
    trade_id: Optional[str] = None,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    portfolio_id: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None,
):
    """Log a trade execution."""
    
def log_deployment_decision(
    strategy_name: str,
    decision_id: Optional[str] = None,
    status: Optional[str] = None,
    scores: Optional[Dict[str, float]] = None,
    user_id: Optional[str] = None,
    username: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None,
):
    """Log a deployment decision."""
    
def cleanup_audit_logs(
    retention_days: Optional[int] = None,
) -> int:
    """Clean up old audit log files."""
    
def get_audit_log_info() -> Dict[str, Any]:
    """Get information about audit log file sizes."""
```

## Acceptance Criteria

### AC-AUDIT-001: All Sensitive Operations Logged
```bash
# Test: Trade execution creates audit log
python -c "
from app.core.audit import log_trade_execution
log_trade_execution('AAPL', 'BUY', 100, price=150.0)
import os
assert os.path.exists('logs/audit/audit.log')
"
```

### AC-AUDIT-002: Audit Log Format
```bash
# Test: Audit log includes required fields
python -c "
from app.core.audit import get_audit_logger, AuditAction
logger = get_audit_logger()
logger.log(AuditAction.TRADE_CREATE, user_id='test')
# Check log format
with open('logs/audit/audit.log', 'r') as f:
    log_entry = f.readlines()[-1]
    assert 'trade.create' in log_entry
    assert 'user=test' in log_entry
    assert 'correlation_id=' in log_entry
"
```

### AC-AUDIT-003: Audit Log Retention
```bash
# Test: Old logs are cleaned up
python -c "
from app.core.audit import get_audit_logger
logger = get_audit_logger()
removed = logger.cleanup_old_logs(retention_days=90)
assert isinstance(removed, int)
"
```

### AC-AUDIT-004: Context Manager Logging
```bash
# Test: Context manager logs on success and failure
python -c "
from app.core.audit import audit_context, AuditAction
with audit_context(AuditAction.TRADE_EXECUTE, user_id='test') as audit:
    audit.mark_success(details={'trade_id': '123'})
# Should log success event
"
```

## Critical Rules

### Rule AUDIT-001: All Sensitive Operations Logged
**Priority:** P0  
**Description:** All sensitive operations (trades, deployments, config changes) must be logged.

### Rule AUDIT-002: Audit Log Content
**Priority:** P0  
**Description:** Audit logs must include: user context, timestamp, action details, IP address, correlation ID.

### Rule AUDIT-003: Separate Audit Log
**Priority:** P0  
**Description:** Audit logs must be written to a separate, immutable log file (`logs/audit/audit.log`).

### Rule AUDIT-SEC-001: Sensitive Data Redaction
**Priority:** P0  
**Description:** Audit logs must not contain sensitive data (passwords, tokens). Use logging_config filter.

### Rule AUDIT-SEC-002: Immutable Logs
**Priority:** P1  
**Description:** In production, audit logs should be on append-only file system to prevent tampering.

### Rule AUDIT-SEC-003: Retention Policy
**Priority:** P0  
**Description:** Implement NFR-003 retention policy (90 days default).

## Dependencies

### Internal Dependencies
```python
from app.core.logging_config import get_logger, get_correlation_id
```

### External Dependencies
```python
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import Request
```

## Required Tests

### Unit Tests (app/tests/core/test_audit.py)
```python
def test_audit_action_enum():
    """Test AuditAction enum values."""
    
def test_audit_logger_initialization():
    """Test AuditLogger initialization."""
    
def test_log_basic():
    """Test basic logging."""
    
def test_log_with_all_parameters():
    """Test logging with all parameters."""
    
def test_log_trade():
    """Test trade logging."""
    
def test_log_deployment():
    """Test deployment logging."""
    
def test_log_portfolio():
    """Test portfolio logging."""
    
def test_from_request():
    """Test logging from FastAPI request."""
    
def test_cleanup_old_logs():
    """Test old log cleanup."""
    
def test_get_log_size_info():
    """Test getting log size info."""
    
def test_validate_string_param():
    """Test string parameter validation."""
    
def test_validate_string_param_empty():
    """Test string parameter validation with empty string."""
    
def test_validate_log_params():
    """Test log parameters validation."""
    
def test_validate_log_params_invalid_type():
    """Test validation catches invalid types."""
    
def test_get_audit_logger_singleton():
    """Test singleton pattern."""
    
def test_audit_context_success():
    """Test context manager on success."""
    
def test_audit_context_failure():
    """Test context manager on failure."""
    
def test_log_trade_execution():
    """Test trade execution logging."""
    
def test_log_deployment_decision():
    """Test deployment decision logging."""
    
def test_cleanup_audit_logs():
    """Test audit log cleanup."""
    
def test_get_audit_log_info():
    """Test getting audit log info."""
```

## File-Specific Rules

### Rule AUDIT-FS-001: Audit Log Format
**Priority:** P0  
**Description:** Use simple, parseable format: `timestamp | level | message`.

### Rule AUDIT-FS-002: Correlation ID
**Priority:** P0  
**Description:** All audit entries must include correlation ID for tracing.

### Rule AUDIT-FS-003: Double-Checked Locking
**Priority:** P1  
**Description:** Singleton must use double-checked locking pattern.

### Rule AUDIT-FS-004: Rotating File Handler
**Priority:** P0  
**Description:** Use `RotatingFileHandler` with 100MB max size and 100 backups.

## Audit Log Retention

### Retention Settings
```python
AUDIT_LOG_RETENTION_DAYS = 90  # NFR-003
AUDIT_LOG_MAX_SIZE_BYTES = 100 * 1024 * 1024  # 100MB
AUDIT_LOG_MAX_BACKUPS = 100
```

### Cleanup Schedule
```python
# Should be called periodically (e.g., daily via cron)
cleanup_audit_logs(retention_days=90)
```

## References

- **BASE_RULES.md:** See ../../BASE_RULES.md for universal rules
  - SEC-005: Audit logging
  - LOG-001: Structured logging
  - LOG-002: Correlation ID
- **Related Files:**
  - `app/core/logging_config.py` - Sensitive data filtering
  - `app/core/auth.py` - Authentication events

## Changelog

### 2025-02-06
- Initial requirements documentation created
- Documented all audit actions
- Documented retention policy (NFR-003)
- Documented correlation ID tracking
- Audit Status: NEEDS_AUDIT
