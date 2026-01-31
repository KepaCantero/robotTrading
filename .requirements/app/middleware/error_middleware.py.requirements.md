# error_middleware.py

## Purpose
FastAPI middleware stack providing unified error handling, request logging, security headers, rate limiting, and health check routing for production-ready API with comprehensive observability.

---

## Type Definitions / Data Classes

### ErrorHandlingMiddleware (Class)
```python
class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    app: Any                          # REQUIRED - FastAPI application instance
    enable_request_logging: bool       # REQUIRED - Default: True, enables request logging
    logger: logging.Logger            # REQUIRED - Module logger instance
```

**Configuration Rules:**
- enable_request_logging controls whether requests are logged
- Must be initialized with FastAPI app instance

### RequestContextMiddleware (Class)
```python
class RequestContextMiddleware(BaseHTTPMiddleware):
    app: Any                          # REQUIRED - FastAPI application instance
```

**Configuration Rules:**
- Adds request.request_id (UUID) to all requests
- Adds request.start_time (timestamp) to all requests

### SecurityHeadersMiddleware (Class)
```python
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    app: Any                          # REQUIRED - FastAPI application instance
    enable_cors: bool                 # REQUIRED - Default: True, enables CORS headers
```

**Security Headers Applied:**
```python
X-Content-Type-Options: nosnif
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Referrer-Policy: strict-origin-when-cross-origin
Access-Control-Allow-Origin: *              # If enable_cors=True
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
```

### RateLimitingMiddleware (Class)
```python
class RateLimitingMiddleware(BaseHTTPMiddleware):
    app: Any                          # REQUIRED - FastAPI application instance
    requests_per_minute: int          # REQUIRED - Default: 60
    request_counts: Dict[str, List[float]]  # Runtime state - IP -> timestamps
    logger: logging.Logger            # REQUIRED - Module logger instance
```

**Rate Limiting Rules:**
- Tracks requests by client IP address
- Cleans entries older than 60 seconds
- Returns 429 status with Retry-After header when limit exceeded
- JSON error response with code "RATE_LIMIT_EXCEEDED"

### HealthCheckMiddleware (Class)
```python
class HealthCheckMiddleware(BaseHTTPMiddleware):
    app: Any                          # REQUIRED - FastAPI application instance
```

**Health Check Paths:**
- `/health` - Bypass middleware
- `/healthz` - Bypass middleware (Kubernetes standard)
- `/ready` - Bypass middleware (readiness probe)
- `/live` - Bypass middleware (liveness probe)

---

## Function Signatures (Contracts)

### `ErrorHandlingMiddleware.dispatch(request: Request, call_next: Callable) -> Response`
**Pre:** Request has valid structure
**Post:** Response includes X-Request-ID and X-Process-Time headers
**Raises:** No (exceptions caught and handled)
**Retry:** No
**Side Effects:** Logs request start/completion/error, generates UUID, measures processing time

### `ErrorHandlingMiddleware._log_request_start(request: Request) -> None`
**Pre:** request.request_id must be set
**Post:** Logs request metadata at INFO level
**Raises:** No
**Retry:** No
**Side Effects:** Writes to centralized_logger

**Logged Metadata:**
```python
{
    "request_id": str,
    "method": str,
    "path": str,
    "query_params": Dict[str, str],
    "client_ip": str,
    "user_agent": str,
    "content_type": str,
    "content_length": str
}
```

### `ErrorHandlingMiddleware._log_request_completion(request: Request, response: Response, process_time: float) -> None`
**Pre:** request.request_id must be set, response must have status_code
**Post:** Logs completion at appropriate level (INFO/WARNING/ERROR)
**Raises:** No
**Retry:** No
**Side Effects:** Writes to centralized_logger

**Log Level Logic:**
- ERROR if status_code >= 500
- WARNING if status_code >= 400 OR process_time > 5.0 seconds
- INFO otherwise

### `ErrorHandlingMiddleware._log_request_error(request: Request, exc: Exception, process_time: float) -> None`
**Pre:** request.request_id must be set, exc must be Exception instance
**Post:** Logs error at ERROR level with exception details
**Raises:** No
**Retry:** No
**Side Effects:** Writes to centralized_logger with exception message

**Logged Metadata:**
```python
{
    "request_id": str,
    "method": str,
    "path": str,
    "process_time": float,
    "exception_type": str,
    "exception_message": str
}
```

### `ErrorHandlingMiddleware._handle_exception(request: Request, exc: Exception) -> JSONResponse`
**Pre:** request.request_id must be set
**Post:** Returns JSONResponse from error_handler
**Raises:** No (wraps exception in response)
**Retry:** No
**Side Effects:** Adds request context to exception.details if present

### `RequestContextMiddleware.dispatch(request: Request, call_next: Callable) -> Response`
**Pre:** None
**Post:** Response includes X-Request-ID header
**Raises:** No
**Retry:** No
**Side Effects:** Sets request.request_id and request.start_time attributes

### `SecurityHeadersMiddleware.dispatch(request: Request, call_next: Callable) -> Response`
**Pre:** None
**Post:** Response includes all security headers
**Raises:** No
**Retry:** No
**Side Effects:** Adds security headers to response

### `RateLimitingMiddleware.dispatch(request: Request, call_next: Callable) -> Response`
**Pre:** request.client must have host attribute
**Post:** Returns response or 429 if rate limit exceeded
**Raises:** No
**Retry:** No
**Side Effects:** Cleans old entries, records request, logs rate limit warnings

### `RateLimitingMiddleware._cleanup_old_entries(current_time: float) -> None`
**Pre:** current_time must be valid timestamp
**Post:** Removes request timestamps older than 60 seconds
**Raises:** No
**Retry:** No
**Side Effects:** Mutates request_counts dict

### `RateLimitingMiddleware._is_rate_limited(client_ip: str, current_time: float) -> bool`
**Pre:** client_ip must be valid IP string
**Post:** Returns True if client exceeded rate limit
**Raises:** No
**Retry:** No
**Side Effects:** None

### `RateLimitingMiddleware._record_request(client_ip: str, current_time: float) -> None`
**Pre:** client_ip must be valid IP string
**Post:** Appends timestamp to client's request list
**Raises:** No
**Retry:** No
**Side Effects:** Mutates request_counts dict

### `HealthCheckMiddleware.dispatch(request: Request, call_next: Callable) -> Response`
**Pre:** None
**Post:** Returns response normally or bypasses for health paths
**Raises:** No
**Retry:** No
**Side Effects:** None (pass-through for health endpoints)

---

## Acceptance Criteria
- [ ] AC-MID-001: ErrorHandlingMiddleware generates unique UUID for each request
- [ ] AC-MID-002: ErrorHandlingMiddleware adds X-Request-ID and X-Process-Time headers
- [ ] AC-MID-003: ErrorHandlingMiddleware logs request start at INFO level
- [ ] AC-MID-004: ErrorHandlingMiddleware logs completion with appropriate level (INFO/WARNING/ERROR)
- [ ] AC-MID-005: ErrorHandlingMiddleware logs errors at ERROR level with exception details
- [ ] AC-MID-006: ErrorHandlingMiddleware catches ValueError, TypeError, KeyError, AttributeError
- [ ] AC-MID-007: RequestContextMiddleware sets request.request_id if not present
- [ ] AC-MID-008: RequestContextMiddleware sets request.start_time
- [ ] AC-MID-009: SecurityHeadersMiddleware adds all 6 security headers
- [ ] AC-MID-010: SecurityHeadersMiddleware adds CORS headers when enabled
- [ ] AC-MID-011: RateLimitingMiddleware returns 429 when limit exceeded
- [ ] AC-MID-012: RateLimitingMiddleware cleans entries older than 60 seconds
- [ ] AC-MID-013: RateLimitingMiddleware includes Retry-After header in 429 response
- [ ] AC-MID-014: HealthCheckMiddleware bypasses processing for /health, /healthz, /ready, /live
- [ ] AC-MID-015: All middleware uses centralized_logger for structured logging

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../../BASE_RULES.md` (96+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| ASYNC-001 | BASE_RULES | Use async def for middleware dispatch | ✅ OK |
| ASYNC-002 | BASE_RULES | Await async call_next | ✅ OK |
| ASYNC-005 | BASE_RULES | Timeouts for external calls | ⚠️ GAP - No timeout on call_next |
| LOG-001 | BASE_RULES | Structured logging with centralized_logger | ✅ OK |
| LOG-002 | BASE_RULES | Context in logs (request_id, etc) | ✅ OK |
| LOG-003 | BASE_RULES | Appropriate log levels | ✅ OK |
| LOG-004 | BASE_RULES | Error logging with stack traces | ⚠️ PARTIAL - Logs exc but no stack trace |
| SEC-005 | BASE_RULES | Audit logging - all requests logged | ✅ OK |
| SEC-006 | BASE_RULES | Rate limiting implemented | ✅ OK |
| SEC-007 | BASE_RULES | Input validation - errors caught | ✅ OK |
| CC-006 | BASE_RULES | Explicit error handling | ✅ OK |
| ARCH-005 | BASE_RULES | Early returns for health checks | ✅ OK |

### Security-Specific Rules

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| SEC-003 | BASE_RULES | Security headers present | ✅ OK |
| SEC-009 | BASE_RULES | CORS handling | ✅ OK |
| SEC-001 | BASE_RULES | No hardcoded secrets | ✅ OK (no secrets here) |

**NOTE:** This analysis considers all 96 rules from BASE_RULES.md

---

## Dependencies
- **External:**
  - `fastapi.Request` (Request object)
  - `fastapi.Response` (Response object)
  - `fastapi.responses.JSONResponse` (JSON response builder)
  - `starlette.middleware.base.BaseHTTPMiddleware` (Base middleware class)
  - `logging` (stdlib)
  - `time` (stdlib)
  - `uuid` (stdlib)
  - `typing` (stdlib)
- **Internal:**
  - `app.exceptions.error_handler.error_handler` (Global error handler)
  - `app.services.centralized_logging.LogLevel` (Log level enum)
  - `app.services.centralized_logging.LogService` (Service enum)
  - `app.services.centralized_logging.centralized_logger` (Logger instance)

---

## Required Tests
- **tests/middleware/test_error_middleware.py:**
  - Test ErrorHandlingMiddleware generates unique request_id
  - Test ErrorHandlingMiddleware adds X-Request-ID header to response
  - Test ErrorHandlingMiddleware adds X-Process-Time header to response
  - Test ErrorHandlingMiddleware logs request start with metadata
  - Test ErrorHandlingMiddleware logs request completion at INFO (200 OK)
  - Test ErrorHandlingMiddleware logs at WARNING for 4xx status
  - Test ErrorHandlingMiddleware logs at ERROR for 5xx status
  - Test ErrorHandlingMiddleware logs at WARNING for slow requests (> 5s)
  - Test ErrorHandlingMiddleware catches ValueError and returns error response
  - Test ErrorHandlingMiddleware catches TypeError and returns error response
  - Test ErrorHandlingMiddleware logs exceptions with details
  - Test ErrorHandlingMiddleware adds request context to exception.details
  - Test RequestContextMiddleware sets request.request_id if missing
  - Test RequestContextMiddleware sets request.start_time
  - Test SecurityHeadersMiddleware adds X-Content-Type-Options
  - Test SecurityHeadersMiddleware adds X-Frame-Options
  - Test SecurityHeadersMiddleware adds X-XSS-Protection
  - Test SecurityHeadersMiddleware adds Strict-Transport-Security
  - Test SecurityHeadersMiddleware adds Referrer-Policy
  - Test SecurityHeadersMiddleware adds CORS headers when enable_cors=True
  - Test SecurityHeadersMiddleware skips CORS when enable_cors=False
  - Test RateLimitingMiddleware allows requests under limit
  - Test RateLimitingMiddleware returns 429 when limit exceeded
  - Test RateLimitingMiddleware includes Retry-After header in 429 response
  - Test RateLimitingMiddleware cleans old entries (> 60s)
  - Test RateLimitingMiddleware logs warning when limit exceeded
  - Test RateLimitingMiddleware tracks by client IP
  - Test HealthCheckMiddleware bypasses /health endpoint
  - Test HealthCheckMiddleware bypasses /healthz endpoint
  - Test HealthCheckMiddleware bypasses /ready endpoint
  - Test HealthCheckMiddleware bypasses /live endpoint
  - Test HealthCheckMiddleware processes non-health endpoints normally
  - Test middleware chain order (error -> context -> security -> rate limit -> health)

---

## Notes
Implements comprehensive middleware stack for production FastAPI application. TASK-4: Sistema de manejo de errores unificado. All middleware uses async/await properly. Centralized logging via LogService ensures consistent log format across all middleware. Rate limiting is in-memory (suitable for single-instance deployment; use Redis for distributed). Security headers follow OWASP recommendations. Health check paths follow Kubernetes and cloud provider standards.
