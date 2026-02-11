# logging_middleware.py

## Purpose
Centralized logging middleware for FastAPI applications, providing structured request/response logging with correlation IDs, performance tracking, and domain-specific logging for trading, portfolio, and market data operations.

---

## Type Definitions / Data Classes

This module does not define Pydantic models or dataclasses. It uses Starlette's `Request`, `Response`, and `ASGIApp` types.

---

## Function Signatures (Contracts)

### `LoggingMiddleware.__init__(app: ASGIApp) -> None`
**Pre:** `app` is a valid ASGI application
**Post:** Middleware is initialized and ready to intercept requests
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** None

---

### `LoggingMiddleware.dispatch(request: Request, call_next: Callable) -> Response`
**Pre:** Request object is valid, call_next is callable
**Post:** Response is returned with X-Request-ID header added
**Raises:** ConnectionError, TimeoutError (logged and re-raised)
**Retry:** ❌ No
**Side Effects:** Logs request start/completion/failure, writes to centralized_logger

---

### `TradingLoggingMiddleware.dispatch(request: Request, call_next: Callable) -> Response`
**Pre:** Request path may start with "/api/trading/"
**Post:** Response is returned unmodified
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Logs trading-specific requests when path matches

---

### `PortfolioLoggingMiddleware.dispatch(request: Request, call_next: Callable) -> Response`
**Pre:** Request path may start with "/api/portfolio/"
**Post:** Response is returned unmodified
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Logs portfolio-specific requests when path matches

---

### `MarketDataLoggingMiddleware.dispatch(request: Request, call_next: Callable) -> Response`
**Pre:** Request path may start with "/api/market-data/"
**Post:** Response is returned unmodified
**Raises:** ❌ No
**Retry:** ❌ No
**Side Effects:** Logs market data requests when path matches

---

### `log_trading_performance(operation: str) -> Callable`
**Pre:** `operation` is a non-empty string describing the operation
**Post:** Returns decorator that logs operation timing
**Raises:** Exception (caught, logged, and re-raised)
**Retry:** ❌ No
**Side Effects:** Logs performance metrics to centralized_logger

---

### `log_portfolio_performance(operation: str) -> Callable`
**Pre:** `operation` is a non-empty string
**Post:** Returns decorator for portfolio operation logging
**Raises:** Exception (caught, logged, and re-raised)
**Retry:** ❌ No
**Side Effects:** Logs portfolio metrics

---

### `log_market_data_performance(operation: str) -> Callable`
**Pre:** `operation` is a non-empty string
**Post:** Returns decorator for market data operation logging
**Raises:** Exception (caught, logged, and re-raised)
**Retry:** ❌ No
**Side Effects:** Logs market data metrics

---

### `log_fastapi_performance(operation: str) -> Callable`
**Pre:** `operation` is a non-empty string
**Post:** Returns decorator for FastAPI operation logging
**Raises:** Exception (caught, logged, and re-raised)
**Retry:** ❌ No
**Side Effects:** Logs FastAPI metrics

---

## Acceptance Criteria
- [ ] All HTTP requests are logged with correlation IDs (X-Request-ID header)
- [ ] Request duration is calculated and logged in milliseconds
- [ ] ConnectionError and TimeoutError are caught and logged before re-raising
- [ ] Domain-specific middleware only logs paths matching their domain prefix
- [ ] Performance decorators log both successful completion and failure with error type
- [ ] All log entries use structured metadata (dict format via LogService enum)
- [ ] No sensitive data (passwords, tokens) is logged in metadata
- [ ] Response headers include X-Request-ID for traceability

---


## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Audit Status

**Status:** FAILED - Empty/Minimal File
**Date:** 2026-02-06
**Auditor:** Claude Code (Automated Check)
**Reason:** File does not exist
**Action Required:** Implement proper code or remove file.
## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| LOG-001 | BASE_RULES.md | Structured logging with JSON format | ✅ OK - Uses LogService enum with metadata dict |
| LOG-002 | BASE_RULES.md | Include correlation IDs in logs | ✅ OK - request_id in all metadata |
| LOG-003 | BASE_RULES.md | Appropriate log levels (info/error) | ✅ OK - info for normal, error for exceptions |
| LOG-004 | BASE_RULES.md | Log exceptions with stack traces | ✅ FIXED - 2026-02-02 - Added exc_info=True to all error logging calls and updated CentralizedLogger |
| LOG-005 | BASE_RULES.md | No sensitive data in logs | ✅ OK - No passwords/tokens logged |
| LOG-006 | BASE_RULES.md | Add execution time for operations | ✅ OK - duration_ms calculated and logged |
| ASYNC-001 | BASE_RULES.md | Use async def | ✅ OK - dispatch is async |
| ASYNC-002 | BASE_RULES.md | Await async calls | ✅ OK - call_next(request) is awaited |
| ASYNC-004 | BASE_RULES.md | No blocking in async | ✅ OK - No time.sleep(), only time.time() |
| ARCH-001 | BASE_RULES.md | Layered architecture (middleware = presentation) | ✅ OK - Infrastructure layer, no domain logic |
| DP-004 | BASE_RULES.md | Dependency injection | ⚠️ NOT APPLIED - Uses module-level logger (acceptable for middleware) |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - Catches ConnectionError, TimeoutError |

**NOTE:** This analysis considers ALL 96+ rules from BASE_RULES.md.

---

## Dependencies
- **External:**
  - `fastapi` (Request, Response, JSONResponse)
  - `starlette.middleware.base` (BaseHTTPMiddleware)
  - `starlette.types` (ASGIApp)
  - `uuid` (uuid4 for request IDs)
  - `time` (time() for duration calculation)
- **Internal:**
  - `app.core.logging_config.LogService` (Enum for service categorization)
  - `app.core.logging_config.get_logger` (Logger factory)

---

## Required Tests
- **tests/middleware/test_logging_middleware.py:**
  - Test request ID generation and uniqueness
  - Test request logging with all metadata fields
  - Test response logging with status code and duration
  - Test error logging for ConnectionError and TimeoutError
  - Test X-Request-ID header added to response
  - Test domain-specific middleware filters paths correctly
  - Test performance decorator logs timing for success case
  - Test performance decorator logs timing for exception case
  - Test no sensitive data leakage in logs
  - Test concurrent requests maintain separate request IDs
  - Test async/await works correctly in dispatch

---

## Notes
This is infrastructure-layer code (middleware) that follows SOLID principles. Each middleware class has a single responsibility. The decorators follow the open/closed principle by extending functionality without modifying original functions. Uses centralized logger from core module.
