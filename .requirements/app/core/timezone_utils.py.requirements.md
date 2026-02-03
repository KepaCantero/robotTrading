# timezone_utils.py Requirements

**File Path:** `app/core/timezone_utils.py`  
**Last Updated:** 2025-02-06  
**Audit Status:** NEEDS_AUDIT

## Purpose

Timezone utilities for multi-market trading system. Ensures consistent timezone handling across stocks (US/EU), forex (24/7), and crypto (24/7) markets with UTC-first approach.

## Type Definitions

### Type Aliases
```python
# All datetime operations use timezone-aware datetime
from datetime import datetime
from typing import Optional
```

### Constants
```python
MARKET_TIMEZONES: Dict[str, timezone] = {
    "us": timezone.utc,
    "eu": timezone.utc,
    "forex": timezone.utc,
    "crypto": timezone.utc,
    "asia": timezone.utc,
}
```

## Function Signatures

### Core Functions
```python
def utc_now() -> datetime:
    """Get current UTC time with timezone info."""
    
def to_utc(dt: datetime) -> datetime:
    """Convert datetime to UTC (handles naive with warning)."""
    
def to_market_time(dt: datetime, market: str) -> datetime:
    """Convert datetime to market-specific timezone."""
    
def format_utc(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S %Z") -> str:
    """Format datetime as UTC string."""
    
def format_market_time(dt: datetime, market: str, fmt: str = "%Y-%m-%d %H:%M:%S %Z") -> str:
    """Format datetime in market-specific timezone."""
    
def get_market_timezone(market: str) -> timezone:
    """Get timezone for a specific market."""
    
def is_market_open(market: str, dt: Optional[datetime] = None) -> bool:
    """Check if market is open at given time."""
    
def get_market_open_close_time(market: str, dt: Optional[datetime] = None) -> tuple[datetime, datetime]:
    """Get market open and close times for a given date."""
    
def validate_timezone_aware(dt: datetime, param_name: str = "datetime") -> None:
    """Validate that a datetime is timezone-aware."""
    
def ensure_timezone_aware(dt: datetime, param_name: str = "datetime") -> datetime:
    """Ensure datetime is timezone-aware, converting if necessary."""
    
def parse_iso_datetime(iso_string: str) -> datetime:
    """Parse ISO 8601 datetime string to timezone-aware datetime."""
```

### Database Compatibility
```python
def get_db_timestamp_default() -> Callable[[], datetime]:
    """Get default timestamp for database columns."""
    
def get_db_timestamp_onupdate() -> Callable[[], datetime]:
    """Get onupdate timestamp for database columns."""
```

### Display Utilities
```python
def to_local_timezone(dt: datetime, local_tz: Optional[timezone] = None) -> datetime:
    """Convert datetime to local timezone for display."""
    
def format_for_display(dt: datetime, local_tz: Optional[timezone] = None) -> str:
    """Format datetime for user display in local timezone."""
```

## Acceptance Criteria

### AC-TZ-001: All Functions Return Timezone-Aware Datetime
```bash
# Test: All datetime returns have tzinfo
python -c "
from app.core.timezone_utils import *
assert utc_now().tzinfo is not None
assert to_utc(datetime.now()).tzinfo is not None
assert to_market_time(utc_now(), 'us').tzinfo is not None
"
```

### AC-TZ-002: Naive Datetime Conversion Warning
```bash
# Test: Converting naive datetime logs warning
python -c "
import logging
from app.core.timezone_utils import to_utc
logging.basicConfig(level=logging.WARNING)
to_utc(datetime(2024, 1, 1))  # Should log warning
" | grep -q "Converting naive datetime"
```

### AC-TZ-003: Market Open Check
```bash
# Test: Crypto/forex always return True
python -c "
from app.core.timezone_utils import is_market_open
assert is_market_open('crypto') == True
assert is_market_open('forex') == True
"
```

### AC-TZ-004: ISO Parsing Validation
```bash
# Test: ISO parsing fails on invalid input
python -c "
import pytest
from app.core.timezone_utils import parse_iso_datetime
with pytest.raises(ValueError):
    parse_iso_datetime('invalid')
"
```

## Critical Rules

### Rule TZ-001: Always Use Timezone-Aware Datetime
**Priority:** P0  
**Description:** All datetime operations must use timezone-aware datetime objects. Never use `datetime.utcnow()` or naive datetime.  
**Enforcement:** Use `utc_now()` instead of `datetime.utcnow()`.

### Rule TZ-002: UTC as Internal Representation
**Priority:** P0  
**Description:** Store and process all times internally in UTC. Convert to market timezone only for display/logic.

### Rule TZ-003: Validate External Datetime Inputs
**Priority:** P1  
**Description:** All datetime parameters from external sources must be validated for timezone awareness.

### Rule TZ-004: Thread-Safe Market Timezone Access
**Priority:** P2  
**Description:** `MARKET_TIMEZONES` dict is read-only, safe for concurrent access.

## Dependencies

### Internal Dependencies
None (pure utility module)

### External Dependencies
```python
from datetime import datetime, timezone
from typing import Optional
import logging
```

### Optional Dependencies
```python
import tzlocal  # For to_local_timezone()
```

## Required Tests

### Unit Tests (app/tests/core/test_timezone_utils.py)
```python
def test_utc_now_returns_timezone_aware():
    """Test utc_now returns aware datetime."""
    
def test_to_utc_converts_naive_with_warning():
    """Test to_utc converts naive datetime with warning."""
    
def test_to_utc_preserves_aware_datetime():
    """Test to_utc doesn't modify aware datetime."""
    
def test_to_market_time_valid_markets():
    """Test to_market_time for all valid markets."""
    
def test_to_market_time_invalid_market_defaults_to_utc():
    """Test invalid market defaults to UTC."""
    
def test_is_market_open_crypto_forex_always_true():
    """Test crypto/forex always open."""
    
def test_is_market_open_stocks_placeholder():
    """Test stock market open check (placeholder in Phase 0.3)."""
    
def test_get_market_open_close_time_returns_tuple():
    """Test open/close time returns proper tuple."""
    
def test_validate_timezone_aware_rejects_naive():
    """Test validation rejects naive datetime."""
    
def test_validate_timezone_aware_accepts_aware():
    """Test validation accepts aware datetime."""
    
def test_ensure_timezone_aware_converts_naive():
    """Test ensure converts naive datetime."""
    
def test_parse_iso_datetime_valid_format():
    """Test ISO parsing with valid format."""
    
def test_parse_iso_datetime_invalid_format_raises():
    """Test ISO parsing raises on invalid format."""
    
def test_format_utc_includes_timezone():
    """Test formatted string includes timezone."""
    
def test_format_market_time_includes_timezone():
    """Test market format includes timezone."""
```

### Integration Tests
```python
def test_database_timestamp_defaults():
    """Test DB timestamp defaults work with SQLAlchemy."""
    
def test_local_timezone_conversion():
    """Test local timezone conversion for display."""
```

## File-Specific Rules

### Rule TZ-FS-001: No Pytz Usage
**Priority:** P1  
**Description:** Use standard library `timezone.utc` instead of `pytz` for simplicity in Phase 0.3. Phase 3 will add proper exchange timezones.

### Rule TZ-FS-002: Market Open Placeholder
**Priority:** P2  
**Description:** Current `is_market_open()` returns True for all markets. Proper implementation scheduled for Phase 3.

### Rule TZ-FS-003: Import Safety
**Priority:** P1  
**Description:** `tzlocal` import is inside `to_local_timezone()` to make it optional.

## References

- **BASE_RULES.md:** See ../../BASE_RULES.md for universal rules (TYP-001, LOG-004, ASYNC-001)
- **Related Files:**
  - `app/core/audit.py` - Uses `utc_now()` for audit timestamps
  - `app/core/reconnection_manager.py` - Uses timezone-aware datetimes
  - Database models - Use `get_db_timestamp_default()` for column defaults

## Migration Notes

### Phase 0.3 → Phase 3 Migration
When implementing proper exchange timezones:
1. Replace `timezone.utc` with actual timezones in `MARKET_TIMEZONES`
2. Implement proper `is_market_open()` logic
3. Implement proper `get_market_open_close_time()` logic
4. Add exchange holiday calendar support

## Changelog

### 2025-02-06
- Initial requirements documentation created
- Audit Status: NEEDS_AUDIT
