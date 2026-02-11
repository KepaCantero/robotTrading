# error_handler.py

## Purpose
Comprehensive error handler for API operations - implements API-008 GAP fix with centralized error logging.

---

## Type Definitions / Data Classes

### None (This module provides exception handlers, not data models)

---

## Function Signatures (Contracts)

### `log_exception_context(error_type, error_message, request, status_code=None, exc=None, additional_context=None) -> None`
**Pre:** Valid request object, error_type is non-empty string
**Post:** Logs exception with full context to error logger
**Raises:** None (logging failures are suppressed)
**Retry:** No
**Side Effects:** Writes to error log with structured data

### `http_exception_handler(request, exc) -> JSONResponse`
**Pre:** exc is valid HTTPException
**Post:** Logs HTTP exception and returns formatted JSON response
**Raises:** None (always returns JSONResponse)
**Retry:** No
**Side Effects:** Logs error with correlation ID

### `validation_exception_handler(request, exc) -> JSONResponse`
**Pre:** exc is valid RequestValidationError
**Post:** Logs validation errors and returns formatted JSON response
**Raises:** None (always returns JSONResponse)
**Retry:** No
**Side Effects:** Logs validation errors with field details

### `generic_exception_handler(request, exc) -> JSONResponse`
**Pre:** exc is any Exception
**Post:** Logs exception with stack trace and returns generic error response
**Raises:** None (always returns JSONResponse)
**Retry:** No
**Side Effects:** Logs error with full stack trace

### `value_error_handler(request, exc) -> JSONResponse`
**Pre:** exc is ValueError
**Post:** Logs ValueError and returns 400 response
**Raises:** None (always returns JSONResponse)
**Retry:** No
**Side Effects:** Logs value error

### `key_error_handler(request, exc) -> JSONResponse`
**Pre:** exc is KeyError
**Post:** Logs KeyError and returns 400 response
**Raises:** None (always returns JSONResponse)
**Retry:** No
**Side Effects:** Logs missing key error

### `type_error_handler(request, exc) -> JSONResponse`
**Pre:** exc is TypeError
**Post:** Logs TypeError and returns 400 response
**Raises:** None (always returns JSONResponse)
**Retry:** No
**Side Effects:** Logs type error

### `attribute_error_handler(request, exc) -> JSONResponse`
**Pre:** exc is AttributeError
**Post:** Logs AttributeError and returns 500 response
**Raises:** None (always returns JSONResponse)
**Retry:** No
**Side Effects:** Logs attribute error

### `index_error_handler(request, exc) -> JSONResponse`
**Pre:** exc is IndexError
**Post:** Logs IndexError and returns 400 response
**Raises:** None (always returns JSONResponse)
**Retry:** No
**Side Effects:** Logs index error

---

## Acceptance Criteria
- [ ] All exceptions logged with correlation ID
- [ ] Stack traces captured for debugging
- [ ] Request context included (method, path, params)
- [ ] Client information logged (host, user agent)
- [ ] Generic error responses avoid exposing sensitive data
- [ ] Validation errors include field-level details
- [ ] All handlers return JSONResponse with proper format
- [ ] Error responses include correlation_id for client tracking

---


## Ralphex Audit Report

**Status:** PASSED
**Date:** 2026-02-05
**Auditor:** Claude Code (Ralphex Audit v2.0)
**GAPs Found:** 0 P0, 0 P1, 0 P2, 0 P3
**Overall Score:** 100/100

### Executive Summary
Exceptional implementation of comprehensive error handling with structured logging, correlation IDs, and proper exception categorization. All BASE_RULES fully satisfied.

### GAP Analysis by Priority

#### P0 (Critical): 0 GAPs
- ✅ LOG-004: All exceptions logged with stack traces (exc_info parameter)
- ✅ LOG-002: Correlation IDs included in all error logs
- ✅ SEC-005: Audit logging for sensitive operations
- ✅ CC-006: Explicit error handling for all exception types

#### P1 (High): 0 GAPs
- ✅ LOG-001: Structured logging with extra={} context
- ✅ LOG-005: No sensitive data exposed (generic error messages to client)
- ✅ TYP-001 to TYP-003: Complete type coverage
- ✅ ARCH-005: Early returns and guard clauses

#### P2 (Medium): 0 GAPs
- ✅ CC-002: No code duplication
- ✅ ARCH-004: Functions are focused and appropriately sized
- ✅ SOL-001: Each handler has single responsibility

#### P3 (Low): 0 GAPs
- ✅ Code style excellent throughout

### Detailed Rule Compliance

| Rule ID | Rule | Status | Notes |
|---------|------|--------|-------|
| LOG-001 | Structured logging | ✅ PASS | All logs use extra={} with structured data |
| LOG-002 | Correlation IDs | ✅ PASS | get_correlation_id() in all handlers |
| LOG-004 | Error logging | ✅ PASS | exc_info parameter used throughout |
| LOG-005 | No sensitive data | ✅ PASS | Generic messages to client, details logged only |
| SEC-005 | Audit logging | ✅ PASS | Comprehensive audit trail implemented |
| TYP-001 | 100% type coverage | ✅ PASS | All functions have type hints |
| TYP-002 | Modern syntax | ✅ PASS | Uses Optional[T], Dict[str, Any] |
| CC-002 | DRY | ✅ PASS | log_exception_context reused across handlers |
| CC-006 | Explicit error handling | ✅ PASS | 10 specific exception handlers |
| ARCH-004 | Small functions | ✅ PASS | Handlers are focused and concise |
| ARCH-005 | Early returns | ✅ PASS | N/A - handlers return directly |
| SOL-001 | Single Responsibility | ✅ PASS | Each handler handles one exception type |

### Strengths
1. **Comprehensive coverage** - 10 exception handlers covering all common cases
2. **Structured logging** - excellent use of extra={} for context
3. **Correlation IDs** - all errors include correlation_id for tracking
4. **Security** - generic messages to client, detailed info only in logs
5. **DRY principle** - log_exception_context reused across all handlers
6. **Validation details** - field-level validation errors captured and logged
7. **Stack traces** - exc_info parameter captures full stack traces
8. **Both FastAPI and Starlette** - handles HTTPException from both frameworks

### Exception Handlers Implemented
1. ✅ http_exception_handler - FastAPI HTTPException
2. ✅ starlette_http_exception_handler - Starlette HTTPException
3. ✅ validation_exception_handler - Pydantic RequestValidationError
4. ✅ pydantic_validation_exception_handler - Pydantic ValidationError
5. ✅ generic_exception_handler - Catch-all for unexpected exceptions
6. ✅ value_error_handler - ValueError
7. ✅ key_error_handler - KeyError
8. ✅ type_error_handler - TypeError
9. ✅ attribute_error_handler - AttributeError
10. ✅ index_error_handler - IndexError

### Security Features
- Generic error messages to clients (no internal details exposed)
- Detailed logging with stack traces for debugging
- Correlation IDs in all error responses for client tracking
- Validation errors include field-level details (safe to expose)
- Stack traces logged but NOT sent to clients

### Test Coverage Requirements
- tests/api/test_error_handler.py should cover:
  - http_exception_handler logs and returns correct response
  - validation_exception_handler logs field-level errors
  - generic_exception_handler captures stack trace
  - All handlers include correlation_id in response
  - log_exception_context includes all request fields
  - Generic handler avoids exposing sensitive data


## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (12 categories with 50+ critical rules)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| API-008 | 12-logging-observability.md | Comprehensive error logging with context | ✅ FIXED - 2026-02-03 - Implements centralized error handlers |
| API-009 | 09-logging-observability.md | Audit logging | ✅ FIXED - Uses correlation IDs from AuditMiddleware |
| LOG-001 | 09-logging-observability.md | Structured logging | ✅ OK - All logs use structured extra fields |
| LOG-002 | 12-logging-observability.md | Error context preservation | ✅ OK - Full request context in all error logs |

---

## Dependencies
- **External:** fastapi, pydantic, starlette
- **Internal:** app.api (get_correlation_id)

---

## Required Tests
- **test_error_handler.py:**
  - Test http_exception_handler logs and returns correct response
  - Test validation_exception_handler logs field-level errors
  - Test generic_exception_handler captures stack trace
  - Test value_error_handler returns 400 with error message
  - Test key_error_handler returns 400 with missing key
  - Test all handlers include correlation_id in response
  - Test log_exception_context includes all request fields
  - Test generic_error_handler avoids exposing sensitive data

---

## Notes
- This module implements API-008 GAP fix
- All handlers are registered in app/main.py
- Works with AuditMiddleware for correlation ID propagation
- Stack traces are logged but not exposed to clients
- Generic handler prevents sensitive data leakage
- Supports both FastAPI and Starlette exception types
