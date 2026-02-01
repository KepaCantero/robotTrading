# rate_limit_governor.py

## Purpose
Rate limiting implementation for API calls and trading operations to prevent exceeding broker limits and system overload.

---

## Type Definitions / Data Classes

⚠️ **CRITICAL:** This file uses thread-safe rate limiting with sliding window.

### Rate Limit Configuration
```python
class RateLimit(BaseModel):
    requests_per_minute: int = Field(default=120, ge=1)
    requests_per_second: int = Field(default=2, ge=1)
    burst_size: int = Field(default=10, ge=1)
    
class RateLimitGovernor:
    _limits: Dict[str, RateLimit]         # REQUIRED - Per-endpoint limits
    _timestamps: Dict[str, Deque[float]]   # REQUIRED - Request timestamps
    _lock: threading.RLock                 # REQUIRED - Thread safety
```

---

## Function Signatures (Contracts)

### `register_endpoint(endpoint: str, limit: RateLimit) -> None`
**Pre:** endpoint is non-empty string
**Post:** Endpoint registered with rate limit
**Raises:** ValueError if endpoint already registered
**Retry:** No
**Side Effects:** Stores limit in _limits

### `can_proceed(endpoint: str) -> bool`
**Pre:** endpoint registered
**Post:** Returns True if within limits, False otherwise
**Raises:** KeyError if endpoint not registered
**Retry:** No
**Side Effects:** Updates timestamps for current time

### `wait_if_needed(endpoint: str) -> None`
**Pre:** endpoint registered
**Post:** Blocks until rate limit allows request
**Raises:** KeyError if endpoint not registered
**Retry:** No
**Side Effects:** Sleeps if needed, updates timestamps

### `get_reset_time(endpoint: str) -> float`
**Pre:** endpoint registered
**Post:** Returns Unix timestamp when oldest request expires
**Raises:** KeyError if endpoint not registered
**Retry:** No
**Side Effects:** None

---

## Acceptance Criteria
- [ ] SEC-006: Rate limiting implemented for APIs
- [ ] Thread-safe with RLock
- [ ] Sliding window algorithm (not token bucket)
- [ ] Per-endpoint rate limits
- [ ] can_proceed() non-blocking check
- [ ] wait_if_needed() blocking wait
- [ ] get_reset_time() returns valid timestamp
- [ ] Old timestamps pruned from deque

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules organized by priority)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SEC-006 | BASE_RULES.md | Rate limiting | ✅ OK |
| ASYNC-004 | BASE_RULES.md | No blocking in async | ⚠️ GAP - wait_if_needed blocks |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK |
| CFG-003 | BASE_RULES.md | Validation | ✅ OK |

---

## Dependencies
- **External:** threading, collections, time, pydantic
- **Internal:** None

---

## Required Tests
- **tests/core/test_rate_limit_governor.py:**
  - Test register_endpoint() stores limit
  - Test can_proceed() returns True when under limit
  - Test can_proceed() returns False when over limit
  - Test wait_if_needed() blocks until allowed
  - Test get_reset_time() returns correct timestamp
  - Test thread-safe concurrent access
  - Test old timestamps pruned from deque
  - Test ValueError for duplicate endpoint
  - Test KeyError for unknown endpoint

---

## Notes
CRITICAL for broker API compliance. Most brokers enforce rate limits (e.g., 120 requests/minute). Exceeding limits results in temporary bans or account suspension.
