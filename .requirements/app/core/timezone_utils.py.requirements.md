# timezone_utils.py

## Purpose
Timezone-aware datetime utilities ensuring consistent UTC handling across multi-market trading system (US/EU/forex/crypto/asia).

---

## Type Definitions / Data Classes

⚠️ **CRITICAL:** This file uses standard types only (no Pydantic models or dataclasses).

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

---

## Function Signatures (Contracts)

### `utc_now() -> datetime`
**Pre:** None
**Post:** Returns datetime with UTC timezone set (tzinfo is not None)
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

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

### `is_market_open(market: str, dt: Optional[datetime] = None) -> bool`
**Pre:** market is valid market identifier
**Post:** Returns True if market is open (crypto/forex always True, stocks simplified for Phase 0.3)
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

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

---

## Acceptance Criteria
- [ ] utc_now() ALWAYS returns timezone-aware datetime (never naive)
- [ ] to_utc() converts naive datetime to UTC with warning logged
- [ ] to_utc() converts aware datetime to UTC
- [ ] validate_timezone_aware() raises ValueError for naive datetime
- [ ] ensure_timezone_aware() returns aware datetime (converts if needed)
- [ ] is_market_open() returns True for crypto/forex (24/7 markets)
- [ ] is_market_open() returns True for stocks (Phase 0.3 simplified)
- [ ] parse_iso_datetime() handles "Z" suffix for UTC
- [ ] format_utc() includes timezone in formatted string
- [ ] to_market_time() defaults to UTC for unknown markets
- [ ] get_db_timestamp_default() returns callable for SQLAlchemy defaults
- [ ] to_local_timezone() uses system timezone if local_tz not provided

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules organized by priority)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| TYP-001 | BASE_RULES.md | 100% type coverage | ✅ OK |
| TYP-003 | BASE_RULES.md | No Any without justification | ✅ OK |
| LOG-003 | BASE_RULES.md | Appropriate log levels | ✅ OK |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ⚠️ N/A - No exceptions raised |
| CC-001 | BASE_RULES.md | Descriptive names | ✅ OK |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - ValueError for naive datetime |

### Timezone-Specific Rules

| Rule | Requirement | Current Status |
|------|-------------|----------------|
| TZ-001 | NEVER use datetime.utcnow() (returns naive) | ✅ OK - utc_now() provided |
| TZ-002 | All stored timestamps must be timezone-aware | ✅ OK - to_utc() ensures awareness |
| TZ-003 | Market hours must use exchange timezone | ❌ GAP - All UTC in Phase 0.3 |
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
- **tests/core/test_timezone_utils.py:**
  - Test utc_now() returns timezone-aware datetime
  - Test to_utc() with naive datetime adds UTC timezone and logs warning
  - Test to_utc() with aware datetime converts to UTC
  - Test validate_timezone_aware() with aware datetime passes
  - Test validate_timezone_aware() with naive datetime raises ValueError
  - Test ensure_timezone_aware() with aware datetime returns unchanged
  - Test ensure_timezone_aware() with naive datetime converts and logs warning
  - Test to_market_time() for all 5 markets (us, eu, forex, crypto, asia)
  - Test to_market_time() with unknown market defaults to UTC
  - Test is_market_open() returns True for crypto (24/7)
  - Test is_market_open() returns True for forex (24/7)
  - Test is_market_open() returns True for stocks (Phase 0.3)
  - Test format_utc() includes "UTC" in output
  - Test format_market_time() includes market timezone in output
  - Test parse_iso_datetime() handles "Z" suffix
  - Test parse_iso_datetime() handles +00:00 suffix
  - Test parse_iso_datetime() raises ValueError for invalid format
  - Test get_db_timestamp_default() returns callable that produces aware datetime
  - Test get_db_timestamp_onupdate() returns callable
  - Test to_local_timezone() converts to system local timezone
  - Edge case: datetime with microseconds preserved
  - Edge case: Far future dates (year 2100+)
  - Edge case: Historical dates (pre-1970)

---

## Notes
- **Phase 0.3 Limitation:** All markets use UTC. Phase 3 will implement proper exchange timezones (US/Eastern, Europe/Madrid, Asia/Tokyo).
- **Naive Datetime Warning:** Converting naive datetime assumes UTC. This is a common source of bugs. Monitor warnings in production logs.
- **tzlocal Dependency:** to_local_timezone() requires tzlocal package. Add to requirements.txt if display functions are used.
- **Market Hours:** is_market_open() is simplified for Phase 0.3. Returns True for all stock markets. Will implement proper hours in Phase 3.
- **Database Integration:** get_db_timestamp_default() is designed for SQLAlchemy Column(default=...) usage.
