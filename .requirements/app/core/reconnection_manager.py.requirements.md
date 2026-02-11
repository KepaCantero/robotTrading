# reconnection_manager.py Requirements

**File Path:** `app/core/reconnection_manager.py`  
**Last Updated:** 2025-02-06  
**Audit Status:** PASSED
**Audit Timestamp:** 2026-02-06T19:41:12.286014

## Purpose

Robust, lock-free, thread-safe reconnection manager for automatic connection recovery with exponential backoff, circuit breaker pattern, and comprehensive state tracking.

## Type Definitions

### Classes
```python
class ConnectionState:
    """Thread-safe connection state tracking without locks."""
    def __init__(self, name: str)
    def record_success(self) -> None
    def record_failure(self) -> None
    def get_state(self) -> Dict[str, Any]

class ReconnectionConfig:
    """Reconnection policy configuration."""
    def __init__(
        self,
        max_attempts: int = 5,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_multiplier: float = 2.0,
        circuit_breaker_threshold: int = 3,
        circuit_breaker_timeout: float = 60.0,
        success_threshold: int = 2,
    )

class ReconnectionManager:
    """Manage reconnection logic with exponential backoff and circuit breaker."""
    def __init__(self, name: str, config: Optional[ReconnectionConfig] = None)
```

## Function Signatures

### ReconnectionManager
```python
def should_reconnect(self) -> bool:
    """Check if should attempt reconnection."""
    
def record_attempt(self, success: bool) -> None:
    """Record connection attempt result."""
    
def record_success(self) -> None:
    """Record successful connection."""
    
def record_failure(self) -> None:
    """Record failed connection."""
    
def reset(self) -> None:
    """Reset to initial state."""
    
def get_state(self) -> Dict[str, Any]:
    """Get current state."""
    
def get_next_delay(self) -> float:
    """Calculate delay before next attempt."""
    
def is_circuit_open(self) -> bool:
    """Check if circuit breaker is open."""
    
def update_config(self, **kwargs) -> None:
    """Update configuration parameters."""
    
def calculate_backoff(self, attempt: int) -> float:
    """Calculate exponential backoff delay."""
```

### Decorators
```python
def with_reconnect_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 10.0,
    backoff_multiplier: float = 2.0,
):
    """Decorator for automatic retry with reconnection."""
    
def with_connection_check(
    connection_manager: ReconnectionManager,
    reconnect_func: Optional[Callable] = None,
):
    """Decorator that checks connection before execution."""
```

### Context Manager
```python
@contextmanager
def managed_connection(
    manager: ReconnectionManager,
    connect_func: Callable[[], bool],
    reconnect_func: Optional[Callable[[], bool]] = None,
):
    """Context manager for managed connection lifecycle."""
```

## Acceptance Criteria

### AC-RECON-001: Exponential Backoff
```bash
# Test: Backoff increases exponentially
python -c "
from app.core.reconnection_manager import ReconnectionManager
mgr = ReconnectionManager('test')
assert mgr.get_next_delay() == 1.0  # Initial
mgr.record_failure()
assert mgr.get_next_delay() == 2.0  # 2x
mgr.record_failure()
assert mgr.get_next_delay() == 4.0  # 4x
"
```

### AC-RECON-002: Circuit Breaker Activation
```bash
# Test: Circuit breaker opens after threshold
python -c "
from app.core.reconnection_manager import ReconnectionManager
config = ReconnectionConfig(circuit_breaker_threshold=3)
mgr = ReconnectionManager('test', config)
for _ in range(3):
    mgr.record_failure()
assert mgr.is_circuit_open() == True
assert mgr.should_reconnect() == False
"
```

### AC-RECON-003: Circuit Breaker Recovery
```bash
# Test: Circuit breaker closes after success threshold
python -c "
from app.core.reconnection_manager import ReconnectionManager
config = ReconnectionConfig(
    circuit_breaker_threshold=2,
    success_threshold=2,
    circuit_breaker_timeout=1.0,
)
mgr = ReconnectionManager('test', config)
# Open circuit
mgr.record_failure()
mgr.record_failure()
assert mgr.is_circuit_open() == True
# Simulate timeout and recovery
import time
time.sleep(1.1)
mgr.record_success()
mgr.record_success()
assert mgr.is_circuit_open() == False
"
```

### AC-RECON-004: Thread-Safe State Access
```bash
# Test: Concurrent state access doesn't corrupt
python -c "
from app.core.reconnection_manager import ReconnectionManager
import threading
mgr = ReconnectionManager('test')
results = []
def access_state():
    for _ in range(100):
        state = mgr.get_state()
        results.append(state.get('attempts', 0))
threads = [threading.Thread(target=access_state) for _ in range(10)]
for t in threads:
    t.start()
for t in threads:
    t.join()
assert len(results) == 1000
"
```

## Critical Rules

### Rule RECON-001: No Locks Required
**Priority:** P0  
**Description:** `ConnectionState` uses atomic operations (counters, timestamps) and is lock-free. No need for threading locks.

### Rule RECON-002: Idempotent Operations
**Priority:** P0  
**Description:** All methods should be idempotent where possible. Calling `record_success()` multiple times should have same effect as calling once.

### Rule RECON-003: Config Validation
**Priority:** P0  
**Description:** All configuration values must be validated:
- `max_attempts > 0`
- `initial_delay > 0`
- `max_delay >= initial_delay`
- `backoff_multiplier > 1.0`
- `circuit_breaker_threshold > 0`
- `success_threshold > 0`

### Rule RECON-004: State Immutability
**Priority:** P1  
**Description:** `get_state()` returns a new dictionary each time to prevent external modification.

### Rule RECON-005: Backoff Cap
**Priority:** P1  
**Description:** Exponential backoff must be capped at `max_delay` to prevent unbounded delays.

## Dependencies

### Internal Dependencies
```python
from app.core.logging_config import get_logger
```

### External Dependencies
```python
import time
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, Optional
```

## Required Tests

### Unit Tests (app/tests/core/test_reconnection_manager.py)
```python
def test_connection_state_initialization():
    """Test ConnectionState initialization."""
    
def test_connection_state_record_success():
    """Test recording successful connection."""
    
def test_connection_state_record_failure():
    """Test recording failed connection."""
    
def test_connection_state_get_state():
    """Test getting state snapshot."""
    
def test_reconnection_config_defaults():
    """Test default configuration values."""
    
def test_reconnection_config_validation():
    """Test configuration validation."""
    
def test_reconnection_manager_initialization():
    """Test ReconnectionManager initialization."""
    
def test_should_reconnect_initially_true():
    """Test should reconnect initially true."""
    
def test_should_reconnect_after_max_attempts():
    """Test should reconnect false after max attempts."""
    
def test_should_reconnect_when_circuit_open():
    """Test should reconnect false when circuit open."""
    
def test_record_success_resets_attempts():
    """Test success resets attempt counter."""
    
def test_record_failure_increments_attempts():
    """Test failure increments attempt counter."""
    
def test_record_success_closes_circuit():
    """Test success closes circuit breaker."""
    
def test_record_failure_opens_circuit():
    """Test failures open circuit breaker."""
    
def test_reset_clears_state():
    """Test reset clears all state."""
    
def test_get_state_returns_snapshot():
    """Test get_state returns immutable snapshot."""
    
def test_get_next_delay_calculates_backoff():
    """Test next delay calculation with backoff."""
    
def test_get_next_delay_capped_at_max():
    """Test next delay capped at max_delay."""
    
def test_is_circuit_open():
    """Test circuit breaker state."""
    
def test_update_config():
    """Test configuration update."""
    
def test_calculate_backoff():
    """Test exponential backoff calculation."""
```

### Decorator Tests
```python
def test_with_reconnect_retry_success():
    """Test retry decorator on success."""
    
def test_with_reconnect_retry_failure():
    """Test retry decorator on failure."""
    
def test_with_reconnect_retry_max_attempts():
    """Test retry decorator max attempts."""
    
def test_with_connection_check():
    """Test connection check decorator."""
```

### Integration Tests
```python
def test_concurrent_state_access():
    """Test thread-safe concurrent access."""
    
def test_full_reconnection_workflow():
    """Test complete reconnection workflow."""
    
def test_circuit_breaker_recovery():
    """Test circuit breaker recovery."""
```

## File-Specific Rules

### Rule RECON-FS-001: UTC Timestamps
**Priority:** P1  
**Description:** All timestamps must use UTC timezone (from `timezone.utc`). No naive datetime objects.

### Rule RECON-FS-002: Deque for History
**Priority:** P2  
**Description:** Use `collections.deque` with `maxlen` for connection history to automatically limit size.

### Rule RECON-FS-003: Warning Logging
**Priority:** P2  
**Description:** Log warnings when circuit breaker state changes, successes after failures, and approaching max attempts.

## Usage Examples

### Basic Usage
```python
from app.core.reconnection_manager import ReconnectionManager

manager = ReconnectionManager("database")

while manager.should_reconnect():
    try:
        # Attempt connection
        if connect():
            manager.record_success()
            break
        else:
            manager.record_failure()
    except Exception as e:
        manager.record_failure()
    
    # Wait before next attempt
    delay = manager.get_next_delay()
    time.sleep(delay)
```

### Using Decorator
```python
from app.core.reconnection_manager import with_reconnect_retry

@with_reconnect_retry(max_attempts=3, initial_delay=1.0)
def fetch_data():
    # May fail due to connection issues
    return database.query("SELECT * FROM data")
```

## References

- **BASE_RULES.md:** See ../../BASE_RULES.md for universal rules
  - LOG-001: Structured logging
  - LOG-002: Correlation ID
  - TYP-001: Type hints
- **Related Files:**
  - `app/core/timezone_utils.py` - UTC timestamp utilities
  - `app/core/logging_config.py` - Logging utilities

## Changelog

### 2025-02-06
- Initial requirements documentation created
- Documented lock-free thread-safe design
- Documented exponential backoff and circuit breaker
- Audit Status: NEEDS_AUDIT
