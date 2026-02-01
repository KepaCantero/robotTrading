# health.py

## Purpose
Health check endpoint for production monitoring - returns HTTP 200 if all systems healthy, HTTP 503 if any critical service down.

---

## Type Definitions / Data Classes

### HealthCheckResponse (Pydantic BaseModel)
```python
class HealthCheckResponse(BaseModel):
    status: str                    # REQUIRED - "healthy", "degraded", or "unhealthy"
    timestamp: str                 # REQUIRED - ISO format timestamp
    checks: Dict[str, Any]         # REQUIRED - Individual check results
    uptime_seconds: float          # REQUIRED - System uptime in seconds
```

### HealthChecker Class
```python
class HealthChecker:
    start_time: datetime           # REQUIRED - Application start time
    _db_path: Optional[str]        # OPTIONAL - Database file path
    _broker: Optional[Any]         # OPTIONAL - Broker instance for connectivity
```

---

## Function Signatures (Contracts)

### `__init__(self) -> None`
**Pre:** None
**Post:** HealthChecker initialized with start_time set
**Raises:** None
**Retry:** No
**Side Effects:** None

### `set_dependencies(self, db_path: Optional[str] = None, broker: Optional[Any] = None) -> None`
**Pre:** None
**Post:** Dependencies set for health checks
**Raises:** None
**Retry:** No
**Side Effects:** Updates instance variables

### `async check_database(self) -> Dict[str, Any]`
**Pre:** None
**Post:** Returns dict with status ("healthy", "degraded", "unhealthy")
**Raises:** No (catches exceptions and returns in status)
**Retry:** No
**Side Effects:** Opens SQLite connection for validation

**Checks:**
- Database file exists
- File size > 0
- Can connect and query tables
- Returns table count

### `async check_broker(self) -> Dict[str, Any]`
**Pre:** None
**Post:** Returns dict with broker connectivity status
**Raises:** No (catches exceptions)
**Retry:** No
**Side Effects:** Calls broker.get_account_info() with 5s timeout

**Checks:**
- Broker configured
- Can get account info
- Returns broker type name

### `check_memory(self) -> Dict[str, Any]`
**Pre:** None
**Post:** Returns dict with memory usage and status
**Raises:** No (catches exceptions)
**Retry:** No
**Side Effects:** Uses psutil to read process memory

**Status Thresholds:**
- healthy: < 2GB
- degraded: 2-4GB
- unhealthy: > 4GB

**Returns:**
- memory_mb: RSS in MB
- memory_percent: % of total memory
- available_mb: System available memory

### `async check_positions(self) -> Dict[str, Any]`
**Pre:** None
**Post:** Returns dict with position count and status
**Raises:** No (catches exceptions)
**Retry:** No
**Side Effects:** Calls broker.get_positions() with 5s timeout

**Returns:**
- count: Number of open positions
- message: Position summary

### `async run_all_checks(self) -> Dict[str, Any]`
**Pre:** Dependencies set (optional)
**Post:** Returns combined health status
**Raises:** No
**Retry:** No
**Side Effects:** Calls all check methods

**Overall Status Logic:**
- unhealthy: if any check returns "unhealthy"
- degraded: if any check returns "degraded" (but none "unhealthy")
- healthy: all checks return "healthy"

**Returns:**
- status: Overall status
- checks: Dict of individual check results
- uptime_seconds: System uptime

### `get_health_checker() -> HealthChecker`
**Pre:** None
**Post:** Returns singleton HealthChecker instance
**Raises:** None
**Retry:** No
**Side Effects:** Creates instance on first call

### `@router.get("/health") async health_check() -> HealthCheckResponse`
**Pre:** None
**Post:** Returns health check response
**Raises:** No (handled internally)
**Retry:** No
**Side Effects:** None

**HTTP Status Codes:**
- 200: healthy or degraded
- 503: unhealthy (should be implemented)

---

## Acceptance Criteria
- [ ] Health check endpoint responds within 5 seconds
- [ ] All health checks handle missing dependencies gracefully
- [ ] Database check validates file exists and is readable
- [ ] Broker check uses timeout to prevent hanging
- [ ] Memory check uses psutil with fallback if missing
- [ ] Overall status calculated correctly from individual checks
- [ ] Uptime tracked from application start
- [ ] Returns HTTP 503 for unhealthy status (TO BE IMPLEMENTED)

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../CRITICAL_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Timeout Protection | CRITICAL_RULES.md | All external calls must have timeout | ✅ OK (5s timeout) |
| Error Handling | BASE_RULES.md | Specific exceptions caught | ✅ OK |
| Type Hints | BASE_RULES.md | All functions typed | ✅ OK |
| Logging | BASE_RULES.md | All checks logged | ✅ FIXED - 2026-02-01 - All health checks now log with context |
| Validation | BASE_RULES.md | Input validation | ✅ OK |
| HTTP Status Codes | CRITICAL_RULES.md | 503 for unhealthy | ⚠️ PARTIAL - Status calculated but not returned |
| Singleton Pattern | BASE_RULES.md | Global instance management | ✅ OK |
| Graceful Degradation | CRITICAL_RULES.md | Handle missing deps | ✅ OK |

---

## Dependencies
- **External:** asyncio, logging, os, datetime, typing, fastapi, pydantic, sqlalchemy, sqlite3, psutil (optional)
- **Internal:** None

---

## Required Tests
- **test_health.py:**
  - Test database check with valid database
  - Test database check with missing file
  - Test database check with empty file
  - Test broker check with timeout
  - Test broker check with valid broker
  - Test memory check with psutil
  - Test memory check without psutil
  - Test positions check
  - Test overall status calculation
  - Test uptime calculation
  - Test singleton pattern
  - Test HTTP response codes

---

## Notes
- CRITICAL: This is production infrastructure for monitoring
- All health checks must be fast (< 5s total)
- Missing dependencies should return "degraded" not crash
- HTTP status code 503 should be returned for unhealthy status (currently not implemented)
- psutil is optional (degraded response if missing)
