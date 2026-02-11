# utils.py

## Purpose
API utility functions for common patterns including correlation IDs, rate limiting, timeout handling, and structured logging decorators for API endpoints.

---

## Type Definitions / Data Classes

### RateLimiter Class (Token Bucket Algorithm)
```python
class RateLimiter:
    _buckets: Dict[str, Dict[str, Any]]     # Rate limit buckets by key
    # Each bucket: {
    #     "tokens": float,
    #     "last_update": float,
    #     "max_tokens": int,
    #     "refill_rate": float  # tokens per second
    # }
```

**Validation Rules:**
- Uses token bucket algorithm (different from security.py sliding window)
- Tokens refill based on elapsed time
- Default: 10 tokens, 1.0 refill_rate
- Tokens capped at max_tokens

### CorrelationIdMiddleware Class
```python
class CorrelationIdMiddleware(BaseHTTPMiddleware):
    # No configuration parameters
    # Extracts X-Correlation-ID header or generates UUID4
    # Sets context variable for logging via set_correlation_id()
```

**Validation Rules:**
- Accepts existing correlation ID from X-Correlation-ID header
- Generates new UUID4 if header not present
- Stores in context variable via set_correlation_id()

---

## Function Signatures (Contracts)

### `RateLimiter.__init__() -> None`
**Pre:** None
**Post:** Rate limiter initialized with empty buckets dict
**Raises:** None
**Retry:** No
**Side Effects:** Creates empty Dict for buckets

### `RateLimiter._get_bucket(key: str) -> Dict[str, Any]`
**Pre:** key is non-empty string
**Post:** Returns bucket dict, creating default bucket if not exists
**Raises:** None
**Retry:** No
**Side Effects:** Modifies _buckets dict

### `RateLimiter._refill(bucket: Dict[str, Any]) -> None`
**Pre:** bucket is valid bucket dict
**Post:** Refills tokens based on elapsed time, capped at max_tokens
**Raises:** None
**Retry:** No
**Side Effects:** Modifies bucket["tokens"] and bucket["last_update"]

### `RateLimiter.is_allowed(key: str, max_tokens: int, refill_rate: float, tokens_per_request: int) -> bool`
**Pre:** key is non-empty string, max_tokens > 0, refill_rate > 0, tokens_per_request > 0
**Post:** Returns True if request allowed (enough tokens), False otherwise
**Raises:** None
**Retry:** No
**Side Effects:** Refills bucket, deducts tokens if allowed

### `RateLimiter.reset(key: Optional[str]) -> None`
**Pre:** None
**Post:** Removes specified bucket or all buckets if key is None
**Raises:** None
**Retry:** No
**Side Effects:** Modifies _buckets dict

### `get_rate_limiter() -> RateLimiter`
**Pre:** None
**Post:** Returns global RateLimiter instance (singleton pattern)
**Raises:** None
**Retry:** No
**Side Effects:** Creates RateLimiter on first call

### `CorrelationIdMiddleware.dispatch(request: Request, call_next: Callable) -> Response`
**Pre:** request is valid FastAPI Request
**Post:** Returns response with X-Correlation-ID header set
**Raises:** None
**Retry:** No
**Side Effects:** Calls set_correlation_id(), adds X-Correlation-ID to response headers

### `timeout_context(seconds: float) -> AsyncGenerator[None, None]`
**Pre:** seconds > 0
**Post:** Yields control within timeout context
**Raises:** asyncio.TimeoutError if operation exceeds timeout
**Retry:** No
**Side Effects:** Uses asyncio.timeout(seconds) context manager

### `with_timeout(seconds: float) -> Callable[[Callable[..., T]], Callable[..., T]]`
**Pre:** seconds > 0
**Post:** Returns decorator that wraps async function with timeout
**Raises:** asyncio.TimeoutError if function exceeds timeout
**Retry:** No
**Side Effects:** Logs error with correlation_id on timeout

### `with_rate_limit(key_func: Optional[Callable], max_tokens: int, refill_rate: float, tokens_per_request: int) -> Callable`
**Pre:** max_tokens > 0, refill_rate > 0, tokens_per_request > 0
**Post:** Returns decorator that applies rate limiting to endpoint
**Raises:** HTTPException 429 if rate limit exceeded
**Retry:** No
**Side Effects:** Calls rate_limiter.is_allowed(), logs warning if exceeded

### `log_endpoint_call(operation: str, service: str) -> Callable[[Callable[..., T]], Callable[..., T]]`
**Pre:** operation is non-empty string, service is non-empty string
**Post:** Returns decorator that logs operation start/completion/failure
**Raises:** None (re-raises original exception)
**Retry:** No
**Side Effects:** Logs with correlation_id, operation, service, function, duration_ms, status

### `log_error_with_trace(error: Exception, context: Dict[str, Any], service: str) -> None`
**Pre:** error is Exception instance, context is dict, service is string
**Post:** Logs error with full context and stack trace
**Raises:** None
**Retry:** No
**Side Effects:** Logs error with exc_info=True

---

## Acceptance Criteria
- [ ] AC-UTL-001: RateLimiter token bucket refills correctly based on elapsed time
- [ ] AC-UTL-002: RateLimiter.is_allowed returns False when insufficient tokens
- [ ] AC-UTL-003: RateLimiter.is_allowed deducts tokens_per_request when allowed
- [ ] AC-UTL-004: RateLimiter.reset removes specified or all buckets
- [ ] AC-UTL-005: CorrelationIdMiddleware sets context variable for logging
- [ ] AC-UTL-006: timeout_context raises asyncio.TimeoutError on expiry
- [ ] AC-UTL-007: with_timeout decorator logs timeout error with correlation_id
- [ ] AC-UTL-008: with_rate_limit decorator raises 429 when limit exceeded
- [ ] AC-UTL-009: with_rate_limit decorator extracts key from Request using key_func
- [ ] AC-UTL-010: log_endpoint_call logs duration_ms in success and error cases
- [ ] AC-UTL-011: log_endpoint_call includes correlation_id in log context
- [ ] AC-UTL-012: log_error_with_trace logs with exc_info=True

---


## Ralphex Audit Report

**Status:** PASSED
**Date:** 2026-02-05
**Auditor:** Claude Code (Ralphex Audit v2.0)
**GAPs Found:** 0 P0, 0 P1, 1 P2, 0 P3
**Overall Score:** 95/100

### Executive Summary
File provides excellent utility functions with proper async timeout handling, rate limiting decorators, and structured logging. Minor P2 issue with duplicated CorrelationIdMiddleware.

### GAP Analysis by Priority

#### P0 (Critical): 0 GAPs
- ✅ ASYNC-001 to ASYNC-006: All async patterns correctly implemented
- ✅ ASYNC-005: Timeout handling with asyncio.timeout()
- ✅ LOG-004: Error logging with exc_info=True
- ✅ LOG-006: Timing info logged (duration_ms)

#### P1 (High): 0 GAPs
- ✅ LOG-001 to LOG-003: Structured logging with correlation IDs
- ✅ SEC-006: Rate limiting decorator implemented
- ✅ TYP-001 to TYP-003: Complete type coverage
- ✅ CC-006: Explicit error handling in all decorators

#### P2 (Medium): 1 GAP
- ❌ CC-002: CorrelationIdMiddleware duplicated from middleware.py (lines 108-129)
  - **Impact:** Low - code duplication, maintenance burden
  - **Recommendation:** Import from middleware.py or use only one implementation

#### P3 (Low): 0 GAPs
- ✅ Code style consistent

### Detailed Rule Compliance

| Rule ID | Rule | Status | Notes |
|---------|------|--------|-------|
| ASYNC-001 | Use async def | ✅ PASS | timeout_context uses async def |
| ASYNC-002 | Await async calls | ✅ PASS | All async calls properly awaited |
| ASYNC-003 | Async context managers | ✅ PASS | timeout_context uses async with asyncio.timeout |
| ASYNC-004 | No blocking in async | ✅ PASS | No time.sleep(), uses asyncio.timeout |
| ASYNC-005 | Set timeouts | ✅ PASS | timeout_context and with_timeout provide this |
| ASYNC-006 | Handle asyncio.TimeoutError | ✅ PASS | Both timeout helpers catch and re-raise |
| LOG-001 | Structured logging | ✅ PASS | All decorators use extra={} |
| LOG-002 | Correlation IDs | ✅ PASS | Uses get_correlation_id() throughout |
| LOG-003 | Appropriate log levels | ✅ PASS | info for operations, error for failures |
| LOG-004 | Error logging | ✅ PASS | log_error_with_trace uses exc_info=True |
| LOG-006 | Timing info | ✅ PASS | log_endpoint_call logs duration_ms |
| SEC-006 | Rate limiting | ✅ PASS | with_rate_limit decorator implemented |
| TYP-001 | 100% type coverage | ✅ PASS | All functions have type hints |
| TYP-002 | Modern syntax | ✅ PASS | Uses Optional[T], Dict[K,V], AsyncGenerator |
| TYP-003 | No Any without justification | ✅ PASS | Any used in generic decorator signatures |
| CC-002 | DRY | ❌ P2 | CorrelationIdMiddleware duplicated |
| SOL-001 | Single Responsibility | ✅ PASS | Each function has one responsibility |
| ARCH-004 | Small functions | ✅ PASS | Most functions are small and focused |
| CC-003 | KISS | ✅ PASS | Code is simple and straightforward |

### Strengths
1. **Excellent timeout handling** - proper use of asyncio.timeout (Python 3.11+)
2. **Token bucket rate limiting** - different algorithm from security.py, provides options
3. **Comprehensive decorators** - with_timeout, with_rate_limit, log_endpoint_call
4. **Structured logging** - all decorators include correlation_id and timing
5. **Proper error handling** - exceptions logged with exc_info=True
6. **Type safety** - excellent use of TypeVar and generics

### Recommendations
1. **CC-002 (P2):** Consolidate CorrelationIdMiddleware
   - Option A: Import from middleware.py
   - Option B: Keep only one implementation and document the choice
   - Consider that this version uses set_correlation_id() context variable

2. **Documentation:** Add note about token bucket vs sliding window algorithms:
   ```python
   # Note: utils.py uses token bucket algorithm
   # security.py uses sliding window algorithm
   # Choose based on your rate limiting requirements
   ```

### Test Coverage Requirements
- tests/api/test_utils.py should cover:
  - Rate limiter token bucket refill algorithm
  - timeout_context raises asyncio.TimeoutError
  - with_timeout decorator logs timeout errors
  - with_rate_limit decorator raises 429
  - log_endpoint_call logs duration_ms
  - log_error_with_trace includes exc_info


## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| ASYNC-001 | 07-async-patterns.md | Use async def for async functions | ✅ OK - timeout_context and with_timeout use async |
| ASYNC-002 | 07-async-patterns.md | Await async calls properly | ✅ OK - All async calls awaited |
| ASYNC-003 | 07-async-patterns.md | Async context managers | ✅ OK - timeout_context uses async with |
| ASYNC-004 | 07-async-patterns.md | No blocking in async | ✅ OK - No time.sleep(), uses asyncio.timeout |
| ASYNC-005 | 07-async-patterns.md | Set timeouts for external calls | ✅ OK - timeout_context and with_timeout provide this |
| ASYNC-006 | 07-async-patterns.md | Handle asyncio.TimeoutError | ✅ OK - Both timeout helpers catch and re-raise |
| LOG-001 | 09-logging-observability.md | Structured logging with context | ✅ OK - All decorators use extra={} |
| LOG-002 | 09-logging-observability.md | Include correlation IDs | ✅ OK - Uses get_correlation_id() throughout |
| LOG-003 | 09-logging-observability.md | Appropriate log levels | ✅ OK - info for operations, error for failures |
| LOG-004 | 09-logging-observability.md | Log exceptions with stack traces | ✅ OK - log_error_with_trace uses exc_info=True |
| LOG-006 | 09-logging-observability.md | Timing info (duration_ms) | ✅ OK - log_endpoint_call logs duration_ms |
| SEC-006 | 28-security-and-secrets.md | Rate limiting | ✅ OK - with_rate_limit decorator |
| TYP-001 | 02-type-hints.md | 100% type coverage | ✅ OK - All functions have type hints |
| TYP-002 | 02-type-hints.md | Modern syntax (X \| None) | ✅ OK - Uses Optional[T], Dict[K,V] |
| TYP-003 | 02-type-hints.md | No Any without justification | ⚠️ PARTIAL - Any used in generic decorator signatures (acceptable) |
| CC-002 | 05-architecture.md | DRY - No code duplication | ❌ GAP - CorrelationIdMiddleware duplicated from middleware.py |
| SOL-001 | 03-solid-principles.md | Single Responsibility | ✅ OK - Each function has one responsibility |
| ARCH-004 | 05-architecture.md | Small functions < 20 lines | ✅ OK - Most functions are small and focused |

**GAP Issues Identified:**
1. **CC-002 (P1):** CorrelationIdMiddleware is duplicated from middleware.py (DRY violation)
2. **RateLimiter inconsistency:** This file uses token bucket, security.py uses sliding window - consider consolidation

---

## Dependencies
- **External:** fastapi (HTTPException, Request, Response, status), starlette (BaseHTTPMiddleware), asyncio, time, uuid, contextlib (asynccontextmanager), functools (wraps), typing (Any, Callable, Dict, Optional, TypeVar)
- **Internal:** app.core.logging_config (get_correlation_id, set_correlation_id)

---

## Required Tests
- **tests/api/test_utils.py:**
  - test_rate_limiter_token_bucket_refill()
  - test_rate_limiter_is_allowed_deducts_tokens()
  - test_rate_limiter_is_allowed_returns_false_when_empty()
  - test_rate_limiter_reset_removes_bucket()
  - test_rate_limiter_reset_clears_all_when_none()
  - test_correlation_id_middleware_sets_context_variable()
  - test_correlation_id_middleware_generates_uuid()
  - test_timeout_context_raises_on_expiry()
  - test_with_timeout_decorator_raises_timeout_error()
  - test_with_timeout_decorator_logs_error()
  - test_with_rate_limit_decorator_raises_429()
  - test_with_rate_limit_decorator_uses_key_func()
  - test_log_endpoint_call_logs_duration()
  - test_log_endpoint_call_includes_correlation_id()
  - test_log_endpoint_call_logs_error()
  - test_log_error_with_trace_includes_exc_info()

---

## Notes
- This module ensures API-007 (structured logging with correlation IDs)
- This module ensures API-010 (timeout handling for async operations)
- RateLimiter uses token bucket algorithm (different from security.py's sliding window)
- CorrelationIdMiddleware is duplicated from middleware.py - consider consolidating
- All decorators are designed for use with FastAPI endpoint functions
- timeout_context uses Python 3.11+ asyncio.timeout (asyncio.timeout after Python 3.11)
- log_endpoint_call provides standardized logging pattern across API endpoints
