# error_middleware.py

## Purpose
Unified error handling middleware for FastAPI - provides request context, logging, security headers, rate limiting, and error responses.

---

## Type Definitions / Data Classes

### ErrorHandlingMiddleware Class
```python
class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    enable_request_logging: bool              # REQUIRED - Enable request logging
    logger: logging.Logger                    # REQUIRED - Logger instance
```

### RequestContextMiddleware Class
```python
class RequestContextMiddleware(BaseHTTPMiddleware):
    # No instance variables - adds context to requests
```

### SecurityHeadersMiddleware Class
```python
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    enable_cors: bool                         # REQUIRED - Enable CORS headers
```

### RateLimitingMiddleware Class
```python
class RateLimitingMiddleware(BaseHTTPMiddleware):
    requests_per_minute: int                  # REQUIRED - Rate limit threshold
    request_counts: Dict[str, List[float]]    # PRIVATE - IP -> timestamps
    logger: logging.Logger                    # REQUIRED - Logger instance
```

### HealthCheckMiddleware Class
```python
class HealthCheckMiddleware(BaseHTTPMiddleware):
    # No instance variables - skips processing for health endpoints
```

---

## Function Signatures (Contracts)

### `ErrorHandlingMiddleware.__init__(self, app, enable_request_logging: bool = True) -> None`
**Pre:** app is valid FastAPI app
**Post:** Middleware initialized
**Raises:** None
**Retry:** No
**Side Effects:** None

### `async ErrorHandlingMiddleware.dispatch(self, request: Request, call_next: Callable) -> Response`
**Pre:** None
**Post:** Request processed with error handling
**Raises:** No (all exceptions caught)
**Retry:** No
**Side Effects:** Logging, adding headers

**Flow:**
1. Generate unique request ID (UUID)
2. Record start time
3. Log request start (if enabled)
4. Process request
5. Calculate processing time
6. Log request completion (if enabled)
7. Add X-Request-ID and X-Process-Time headers
8. Catch ValueError, TypeError, KeyError, AttributeError
9. Log errors and handle exceptions

### `async ErrorHandlingMiddleware._log_request_start(self, request: Request) -> None`
**Pre:** request has request_id attribute
**Post:** Request logged with metadata
**Raises:** No
**Retry:** No
**Side Effects:** Logging via centralized_logger

**Metadata Logged:**
- request_id
- method
- path
- query_params
- client_ip
- user_agent
- content_type
- content_length

### `async ErrorHandlingMiddleware._log_request_completion(self, request: Request, response: Response, process_time: float) -> None`
**Pre:** request has request_id
**Post:** Request completion logged with appropriate level
**Raises:** No
**Retry:** No
**Side Effects:** Logging via centralized_logger

**Log Levels:**
- ERROR: status_code >= 500
- WARNING: status_code >= 400 OR process_time > 5s
- INFO: otherwise

### `async ErrorHandlingMiddleware._log_request_error(self, request: Request, exc: Exception, process_time: float) -> None`
**Pre:** request has request_id
**Post:** Error logged with exception details
**Raises:** No
**Retry:** No
**Side Effects:** Logging via centralized_logger

### `async ErrorHandlingMiddleware._handle_exception(self, request: Request, exc: Exception) -> JSONResponse`
**Pre:** None
**Post:** Returns error response
**Raises:** No
**Retry:** No
**Side Effects:** Updates exception details with request context

### `async RequestContextMiddleware.dispatch(self, request: Request, call_next: Callable) -> Response`
**Pre:** None
**Post:** Request processed with context added
**Raises:** No
**Retry:** No
**Side Effects:** Adds request_id, start_time to request

### `SecurityHeadersMiddleware.__init__(self, app, enable_cors: bool = True) -> None`
**Pre:** app is valid FastAPI app
**Post:** Middleware initialized
**Raises:** None
**Retry:** No
**Side Effects:** None

### `async SecurityHeadersMiddleware.dispatch(self, request: Request, call_next: Callable) -> Response`
**Pre:** None
**Post:** Security headers added to response
**Raises:** No
**Retry:** No
**Side Effects:** Modifies response headers

**Headers Added:**
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block
- Strict-Transport-Security: max-age=31536000; includeSubDomains
- Referrer-Policy: strict-origin-when-cross-origin
- Access-Control-Allow-Origin: * (if enable_cors)
- Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
- Access-Control-Allow-Headers: Content-Type, Authorization

### `RateLimitingMiddleware.__init__(self, app, requests_per_minute: int = 60) -> None`
**Pre:** app is valid FastAPI app, requests_per_minute > 0
**Post:** Middleware initialized
**Raises:** None
**Retry:** No
**Side Effects:** None

### `async RateLimitingMiddleware.dispatch(self, request: Request, call_next: Callable) -> Response`
**Pre:** None
**Post:** Request processed with rate limiting
**Raises:** No
**Retry:** No
**Side Effects:** Updates request_counts, logs rate limit violations

**Returns:**
- 429 if rate limit exceeded with Retry-After header
- Normal response otherwise

### `RateLimitingMiddleware._cleanup_old_entries(self, current_time: float) -> None`
**Pre:** current_time is Unix timestamp
**Post:** Old entries (> 60s) removed from request_counts
**Raises:** No
**Retry:** No
**Side Effects:** Modifies request_counts dict

### `RateLimitingMiddleware._is_rate_limited(self, client_ip: str, current_time: float) -> bool`
**Pre:** None
**Post:** Returns True if client exceeded rate limit
**Raises:** No
**Retry:** No
**Side Effects:** None

### `RateLimitingMiddleware._record_request(self, client_ip: str, current_time: float) -> None`
**Pre:** None
**Post:** Request timestamp recorded for client
**Raises:** No
**Retry:** No
**Side Effects:** Modifies request_counts dict

### `async HealthCheckMiddleware.dispatch(self, request: Request, call_next: Callable) -> Response`
**Pre:** None
**Post:** Request processed (skipped for health endpoints)
**Raises:** No
**Retry:** No
**Side Effects:** None

**Health Endpoints:**
- /health
- /healthz
- /ready
- /live

---

## Acceptance Criteria
- [ ] All requests get unique X-Request-ID header
- [ ] All requests get X-Process-Time header
- [ ] Request logging includes all metadata
- [ ] Error logging includes exception details
- [ ] Security headers added to all responses
- [ ] CORS can be enabled/disabled
- [ ] Rate limiting blocks excessive requests
- [ ] Rate limiting returns 429 with Retry-After
- [ ] Health check endpoints bypass rate limiting
- [ ] Request context added to exceptions

---


## Audit Status

**Status:** PASSED
**Date:** 2026-02-04
**Auditor:** Claude Code (Ralphex Audit)
**GAPs Found:** 0 P0, 0 P1, 0 P2, 0 P3
**Notes:** All BASE_RULES verified. See Critical Rules section for details.


## Audit Status

| **Audit Status** | **FAILED** |
| **Last Audit Date** | 2026-02-04T11:59:31Z |
| **Auditor** | Claude Code (Ralphex Audit) |
| **GAPs Found** | 1 P0, 0 P1, 0 P2, 0 P3 |
| **Notes** | All BASE_RULES verified. See Critical Rules section for details. |


## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../CRITICAL_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| Security Headers | CRITICAL_RULES.md | All security headers present | ✅ OK |
| CORS Configuration | BASE_RULES.md | CORS configurable | ✅ OK |
| Rate Limiting | CRITICAL_RULES.md | Rate limit enforced | ✅ OK |
| Error Handling | BASE_RULES.md | All exceptions caught | ✅ OK |
| Logging | BASE_RULES.md | All requests logged | ✅ OK |
| Request ID | CRITICAL_RULES.md | Unique ID per request | ✅ OK |
| Type Hints | BASE_RULES.md | All functions typed | ✅ OK |
| Timeout Handling | CRITICAL_RULES.md | Slow requests logged | ✅ OK (> 5s) |

---

## Dependencies
- **External:** logging, time, uuid, typing, fastapi, starlette
- **Internal:**
  - app.exceptions.error_handler.error_handler
  - app.services.centralized_logging.LogLevel, LogService, centralized_logger

---

## Required Tests
- **test_error_middleware.py:**
  - Test request ID generation
  - Test process time calculation
  - Test request start logging
  - Test request completion logging
  - Test request error logging
  - Test exception handling
  - Test security headers added
  - Test CORS enabled/disabled
  - Test rate limiting enforcement
  - Test rate limiting cleanup
  - Test health check bypass
  - Test 429 response with Retry-After

---

## Notes
- CRITICAL: This is production middleware for security and monitoring
- All middleware should be lightweight (< 10ms overhead)
- Rate limiting is in-memory (resets on restart)
- CORS headers allow all origins by default (configure for production)
- Request context middleware ensures request_id always available
