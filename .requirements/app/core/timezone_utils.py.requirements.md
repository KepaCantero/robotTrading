# timezone_utils.py

## Purpose
Timezone-aware datetime utilities ensuring consistent UTC handling across multi-market trading system (US/EU/forex/crypto/asia).

---

## Type Definitions / Data Classes

⚠️ **CRITICAL:** If this file uses Pydantic models or dataclasses, document the COMPLETE schema here.

### Market Timezone Configuration
```python
MARKET_TIMEZONES: Dict[str, timezone] = {
    "us": timezone.utc,      # Phase 0.3: UTC placeholder, Phase 3: US/Eastern
    "eu": timezone.utc,      # Phase 0.3: UTC placeholder, Phase 3: Europe/Madrid
    "forex": timezone.utc,
    "crypto": timezone.utc,
    "asia": timezone.utc,    # Phase 0.3: UTC placeholder, Phase 3: Asia/Tokyo
}
```

**Validation Rules:**
- All datetime objects must have tzinfo set (timezone-aware)
- Naive datetime input triggers warning but is converted to UTC
- Market identifiers are case-insensitive
- Market hours simplified in Phase 0.3 (proper implementation in Phase 3)

---

## Function Signatures (Contracts)

### `utc_now() -> datetime`
**Pre:** None
**Post:** Returns datetime with UTC timezone set (tzinfo is not None)
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (pure function)

### `to_utc(dt: datetime) -> datetime`
**Pre:** dt is valid datetime (naive or aware)
**Post:** Returns datetime with UTC timezone, logs warning if input was naive
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Logs warning for naive datetime input

### `to_market_time(dt: datetime, market: str) -> datetime`
**Pre:** dt is valid datetime, market is valid key in MARKET_TIMEZONES
**Post:** Returns datetime converted to market timezone
**Raises:** ❌ No (defaults to UTC for unknown market)
**Retry:** ❌ No
**Side Effects:** None

### `format_utc(dt: datetime, fmt: str = "%Y-%m-%d %H:%M:%S %Z") -> str`
**Pre:** dt is valid datetime
**Post:** Returns formatted string with timezone info
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

### `format_market_time(dt: datetime, market: str, fmt: str = "%Y-%m-%d %H:%M:%S %Z") -> str`
**Pre:** dt is valid datetime, market is valid identifier
**Post:** Returns formatted string in market timezone
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

### `is_market_open(market: str, dt: Optional[datetime] = None) -> bool`
**Pre:** market is valid market identifier
**Post:** Returns True if market is open (crypto/forex always True, stocks simplified for Phase 0.3)
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

**Phase 0.3 Behavior:**
- crypto/forex: Always True (24/7 markets)
- us/eu/asia: Always True (simplified, proper implementation in Phase 3)

### `get_market_open_close_time(market: str, dt: Optional[datetime] = None) -> tuple[datetime, datetime]`
**Pre:** market is valid identifier, dt is reference date
**Post:** Returns (open_time, close_time) in UTC
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

**Phase 0.3 Behavior:** Returns placeholder times, proper implementation in Phase 3

### `validate_timezone_aware(dt: datetime, param_name: str = "datetime") -> None`
**Pre:** dt is valid datetime
**Post:** Raises ValueError if dt is naive
**Raises:** ValueError if dt.tzinfo is None
**Retry:** ❌ No
**Side Effects:** None

### `ensure_timezone_aware(dt: datetime, param_name: str = "datetime") -> datetime`
**Pre:** dt is valid datetime
**Post:** Returns timezone-aware datetime, logs warning if conversion needed
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Logs warning for naive datetime

### `parse_iso_datetime(iso_string: str) -> datetime`
**Pre:** iso_string is valid ISO 8601 format
**Post:** Returns timezone-aware datetime in UTC
**Raises:** ValueError if string cannot be parsed
**Retry:** ❌ No
**Side Effects:** None

### `get_db_timestamp_default() -> Callable[[], datetime]`
**Pre:** None
**Post:** Returns callable that produces timezone-aware UTC datetime
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (for SQLAlchemy Column default)

### `get_db_timestamp_onupdate() -> Callable[[], datetime]`
**Pre:** None
**Post:** Returns callable that produces timezone-aware UTC datetime
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None (for SQLAlchemy Column onupdate)

### `to_local_timezone(dt: datetime, local_tz: Optional[timezone] = None) -> datetime`
**Pre:** dt is valid datetime
**Post:** Returns datetime converted to local timezone
**Raises:** ❌ No (falls back to system timezone)
**Retry:** ❌ No
**Side Effects:** May import tzlocal if not provided

### `format_for_display(dt: datetime, local_tz: Optional[timezone] = None) -> str`
**Pre:** dt is valid datetime
**Post:** Returns formatted string in local timezone
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] **AC-TZ-001**: utc_now() ALWAYS returns timezone-aware datetime (never naive)
- [ ] **AC-TZ-002**: to_utc() converts naive datetime to UTC with warning logged
- [ ] **AC-TZ-003**: to_utc() converts aware datetime to UTC
- [ ] **AC-TZ-004**: validate_timezone_aware() raises ValueError for naive datetime
- [ ] **AC-TZ-005**: ensure_timezone_aware() returns aware datetime (converts if needed)
- [ ] **AC-TZ-006**: is_market_open() returns True for crypto/forex (24/7 markets)
- [ ] **AC-TZ-007**: is_market_open() returns True for stocks (Phase 0.3 simplified)
- [ ] **AC-TZ-008**: parse_iso_datetime() handles "Z" suffix for UTC
- [ ] **AC-TZ-009**: format_utc() includes timezone in formatted string
- [ ] **AC-TZ-010**: to_market_time() defaults to UTC for unknown markets
- [ ] **AC-TZ-011**: get_db_timestamp_default() returns callable for SQLAlchemy defaults
- [ ] **AC-TZ-012**: to_local_timezone() uses system timezone if local_tz not provided
- [ ] **AC-TZ-013**: All functions have type hints (TYP-001)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96 rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES | 100% type coverage | ✅ OK - All functions have type hints |
| TYP-002 | BASE_RULES | Modern syntax (tuple[T, T]) | ✅ OK - Uses tuple[datetime, datetime] |
| TYP-003 | BASE_RULES | No Any without justification | ✅ OK - Specific types used |
| LOG-003 | BASE_RULES | Appropriate log levels | ✅ OK - debug/info/warning used |
| CC-001 | BASE_RULES | Descriptive names | ✅ OK - Clear function names |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK - ValueError for naive datetime |
| FMT-007 | BASE_RULES | No mutable defaults | ✅ OK - No mutable defaults |

### Timezone-Specific Rules

| Rule | Requirement | Current Status |
|------|-------------|----------------|
| TZ-001 | NEVER use datetime.utcnow() (returns naive) | ✅ OK - utc_now() provided |
| TZ-002 | All stored timestamps must be timezone-aware | ✅ OK - to_utc() ensures awareness |
| TZ-003 | Market hours must use exchange timezone | ⚠️ ACCEPTED - Known Phase 0.3 limitation, to be fixed in Phase 3 |
| TZ-004 | Naive datetime input must log warning | ✅ OK - to_utc() and ensure_timezone_aware() |
| TZ-005 | Database timestamps use UTC | ✅ OK - get_db_timestamp_default() provided |
| TZ-006 | ISO parsing handles Z suffix | ✅ OK - parse_iso_datetime() |
| TZ-007 | Display functions convert to local timezone | ✅ OK - to_local_timezone() |

---

## Dependencies
- **External:** None (standard library only)
- **Internal:** None (pure utility module)
- **Standard Library:** `datetime`, `datetime.timezone`, `logging`, `typing`
- **Optional External:** `tzlocal` (for to_local_timezone, may fail if not installed)

---

## Required Tests
- **test_timezone_utils.py:**
  - Success: utc_now() returns timezone-aware datetime
  - Success: to_utc() with naive datetime adds UTC timezone and logs warning
  - Success: to_utc() with aware datetime converts to UTC
  - Success: validate_timezone_aware() with aware datetime passes
  - Success: validate_timezone_aware() with naive datetime raises ValueError
  - Success: ensure_timezone_aware() with aware datetime returns unchanged
  - Success: ensure_timezone_aware() with naive datetime converts and logs warning
  - Success: to_market_time() for all 5 markets (us, eu, forex, crypto, asia)
  - Success: to_market_time() with unknown market defaults to UTC
  - Success: is_market_open() returns True for crypto (24/7)
  - Success: is_market_open() returns True for forex (24/7)
  - Success: is_market_open() returns True for stocks (Phase 0.3)
  - Success: format_utc() includes "UTC" in output
  - Success: format_market_time() includes market timezone in output
  - Success: parse_iso_datetime() handles "Z" suffix
  - Success: parse_iso_datetime() handles +00:00 suffix
  - Error: parse_iso_datetime() raises ValueError for invalid format
  - Success: get_db_timestamp_default() returns callable that produces aware datetime
  - Success: get_db_timestamp_onupdate() returns callable
  - Success: to_local_timezone() converts to system local timezone
  - Edge: datetime with microseconds preserved
  - Edge: Far future dates (year 2100+)
  - Edge: Historical dates (pre-1970)
  - Edge: Daylight saving time transitions handled
  - Type: All functions have return type hints

---

## Notes
- **Phase 0.3 Limitation:** All markets use UTC. Phase 3 will implement proper exchange timezones (US/Eastern, Europe/Madrid, Asia/Tokyo).
- **Naive Datetime Warning:** Converting naive datetime assumes UTC. This is a common source of bugs. Monitor warnings in production logs.
- **tzlocal Dependency:** to_local_timezone() requires tzlocal package. Add to requirements.txt if display functions are used.
- **Market Hours:** is_market_open() is simplified for Phase 0.3. Returns True for all stock markets. Will implement proper hours in Phase 3.
- **Database Integration:** get_db_timestamp_default() is designed for SQLAlchemy Column(default=...) usage.
