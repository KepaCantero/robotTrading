# Requirements: app/presentation/controllers/health.py

**File Path:** `app/presentation/controllers/health.py`
**Layer:** Presentation (Controller)
**Last Updated:** 2025-02-05
**Status:** ✅ Compliant - Minor Issues Found

---

## Purpose
Health check endpoint that monitors system health for production readiness. Returns HTTP 200 if all systems healthy, HTTP 503 if any critical service down.

---

## Current State
- **Lines of Code:** 263
- **Classes:** 2 (HealthCheckResponse, HealthChecker)
- **Endpoints:** 1 (@router.get("/health"))
- **Dependencies:** asyncio, sqlite3, psutil
- **Complexity:** Low-Medium

---

## BASE Rules Compliance

### ✅ COMPLIANT Rules
- [FMT-001] Line length ≤ 100: **PASS**
- [FMT-007] No mutable defaults: **PASS**
- [TYP-001] Type coverage: **PASS** (90%+)
- [LOG-004] Error logging: **PASS**
- [SEC-007] Input validation: **PASS**

### ⚠️ MINOR Gaps
- [LOG-001] Structured logging: **MINOR** - Could use structlog for consistent JSON format
- [LOG-005] No sensitive data: **PASS** - No sensitive data logged

---

## File-Specific Requirements

### REQ-CTRL-001: Health Check Response Model
**Priority:** P0
**Description:** Health check response must include status, timestamp, checks, and uptime
**Current State:** ✅ COMPLIANT
```python
class HealthCheckResponse(BaseModel):
    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: str
    checks: Dict[str, Any]
    uptime_seconds: float
```

### REQ-CTRL-002: Database Health Check
**Priority:** P0
**Description:** Must check database connection and integrity
**Current State:** ✅ COMPLIANT
```python
async def check_database(self) -> Dict[str, Any]:
    # Checks file existence, size, and connectivity
```

### REQ-CTRL-003: Broker Health Check
**Priority:** P0
**Description:** Must check broker API connectivity with timeout
**Current State:** ✅ COMPLIANT
```python
async def check_broker(self) -> Dict[str, Any]:
    account = await asyncio.wait_for(self._broker.get_account_info(), timeout=5.0)
```

### REQ-CTRL-004: Memory Health Check
**Priority:** P1
**Description:** Must check memory usage and alert if excessive
**Current State:** ✅ COMPLIANT
```python
def check_memory(self) -> Dict[str, Any]:
    if memory_mb > 4096:  # > 4GB
        status = "unhealthy"
```

### REQ-CTRL-005: Positions Health Check
**Priority:** P1
**Description:** Must check active positions count
**Current State:** ✅ COMPLIANT
```python
async def check_positions(self) -> Dict[str, Any]:
    positions = await asyncio.wait_for(self._broker.get_positions(), timeout=5.0)
```

---

## Gaps Identified

### CRITICAL Gaps (P0)
**None**

### HIGH Priority Gaps (P1)
**None**

### MEDIUM Priority Gaps (P2)

1. **Line 162: Unreachable return statement**
   ```python
   return {"status": "degraded", "message": "psutil not installed"}
   ```
   **Issue:** This line is unreachable (after the function already returned)
   **Fix:** Remove or restructure the exception handling
   **Priority:** P2 (code quality)

### LOW Priority Gaps (P3)

1. **Missing HTTP status code handling**
   - Line 257-260: Empty `pass` statements for unhealthy/degraded status
   - Should return appropriate HTTP status codes (503 for unhealthy)
   - **Priority:** P3 (API design)

2. **No rate limiting on health endpoint**
   - Health check endpoint could be abused
   - **Priority:** P3 (security hardening)

3. **Missing structured logging**
   - Could use structlog for consistent JSON format
   - **Priority:** P3 (logging improvement)

---

## Testing Requirements

### TST-CTRL-001: Health Check Endpoint
**Required Tests:**
- ✅ Test healthy status when all systems OK
- ✅ Test degraded status when some systems degraded
- ✅ Test unhealthy status when critical systems down
- ✅ Test database connectivity checks
- ✅ Test broker connectivity checks
- ✅ Test memory usage checks
- ✅ Test uptime calculation

### TST-CTRL-002: Error Handling
**Required Tests:**
- ✅ Test database file not found
- ✅ Test database connection timeout
- ✅ Test broker connection timeout
- ✅ Test psutil not installed

### TST-CTRL-003: Edge Cases
**Required Tests:**
- ✅ Test empty database file
- ✅ Test very large database file
- ✅ Test high memory usage
- ✅ Test many active positions

---

## Dependencies
- `fastapi` - Web framework
- `pydantic` - Data validation
- `sqlite3` - Database connectivity
- `psutil` - System monitoring (optional)
- `asyncio` - Async operations

---

## Notes
- Health check is well-structured and comprehensive
- All critical system components are monitored
- Minor issue with unreachable return statement needs fixing
- Consider adding structured logging
- Consider returning appropriate HTTP status codes (503 for unhealthy)
