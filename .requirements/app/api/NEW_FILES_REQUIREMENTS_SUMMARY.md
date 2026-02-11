# API New Files Requirements Summary

**Date:** 2026-02-04
**Task:** Create requirements documents for new API files

---

## Requirements Created: 3/3 (100%)

| File | Status | Key Classes | Key Functions | GAP Violations |
|------|--------|--------------|---------------|----------------|
| middleware.py | ✅ YES | AuthMiddleware, CorrelationIdMiddleware, SecurityHeadersMiddleware, RequestLoggingMiddleware | dispatch(), _validate_bearer_token(), _validate_api_key(), _requires_authentication() | 2 (SEC-001 P0, SEC-009 P1) |
| security.py | ✅ YES | RateLimiter, SecurityConfig, RateLimitMiddleware, SecurityHeadersMiddleware | is_allowed(), rate_limit(), require_auth(), audit_log(), get_cors_config() | 3 (SEC-002 P0, SEC-001 P0, CC-002 P1) |
| utils.py | ✅ YES | RateLimiter, CorrelationIdMiddleware | timeout_context(), with_timeout(), with_rate_limit(), log_endpoint_call(), log_error_with_trace() | 1 (CC-002 P1) |

---

## Key Classes Identified

### middleware.py
1. **AuthMiddleware** - Authentication for sensitive operations (deployment, strategies write, optimization write)
2. **CorrelationIdMiddleware** - Request tracing with X-Correlation-ID
3. **SecurityHeadersMiddleware** - Security headers enforcement (X-Frame-Options, CSP, HSTS, etc.)
4. **RequestLoggingMiddleware** - Structured request logging with context

### security.py
1. **RateLimiter** - Sliding window rate limiting (in-memory, single-instance)
2. **SecurityConfig** - Security configuration (auth enabled flag, roles)
3. **RateLimitMiddleware** - Global rate limiting middleware
4. **SecurityHeadersMiddleware** - DUPLICATE from middleware.py

### utils.py
1. **RateLimiter** - Token bucket rate limiting (different algorithm from security.py)
2. **CorrelationIdMiddleware** - DUPLICATE from middleware.py

---

## Key Functions Identified

### middleware.py
- `AuthMiddleware.dispatch()` - Main authentication flow
- `AuthMiddleware._validate_bearer_token()` - JWT/API key validation
- `AuthMiddleware._requires_authentication()` - Path/method-based auth requirement
- `CorrelationIdMiddleware.dispatch()` - Correlation ID injection
- `SecurityHeadersMiddleware.dispatch()` - Security headers injection
- `RequestLoggingMiddleware.dispatch()` - Request logging

### security.py
- `RateLimiter.is_allowed()` - Check rate limit with sliding window
- `RateLimiter.cleanup_old_entries()` - Memory leak prevention
- `rate_limit()` - Decorator for endpoint rate limiting
- `require_auth()` - Authentication/authorization decorator
- `audit_log()` - Comprehensive audit logging decorator
- `get_cors_config()` - CORS configuration

### utils.py
- `RateLimiter.is_allowed()` - Check rate limit with token bucket
- `timeout_context()` - Async timeout context manager
- `with_timeout()` - Timeout decorator for async functions
- `with_rate_limit()` - Rate limiting decorator
- `log_endpoint_call()` - Structured logging decorator
- `log_error_with_trace()` - Error logging with stack trace

---

## GAP Violations Found

### Priority P0 (Critical)

#### middleware.py
| Rule | Issue | Impact |
|------|-------|--------|
| SEC-001 | Hardcoded default API key "dev-api-key-12345" | Security risk if deployed to production |

#### security.py
| Rule | Issue | Impact |
|------|-------|--------|
| SEC-002 | SecurityConfig has hardcoded values (AUTH_ENABLED=False) | Not configurable for production |
| SEC-001 | get_cors_config has hardcoded localhost origins | Not configurable for production |

### Priority P1 (High)

#### middleware.py
| Rule | Issue | Impact |
|------|-------|--------|
| SEC-009 | JWT validation is commented placeholder | Production needs real JWT implementation |

#### security.py
| Rule | Issue | Impact |
|------|-------|--------|
| CC-002 | SecurityHeadersMiddleware duplicated from middleware.py | Code duplication |

#### utils.py
| Rule | Issue | Impact |
|------|-------|--------|
| CC-002 | CorrelationIdMiddleware duplicated from middleware.py | Code duplication |

---

## Acceptance Criteria Summary

### middleware.py (9 criteria)
- Authentication with Bearer tokens (dev mode accepts "dev-*")
- Authentication with API keys
- Sets user_id and auth_method in request.state
- Raises 401 with proper headers when auth fails
- Correlation ID generation and preservation
- Security headers enforcement (5 headers)
- Request logging with correlation_id
- All middleware handle exceptions properly

### security.py (14 criteria)
- Sliding window rate limiting algorithm
- Rate limit remaining count accuracy
- Reset time calculation
- Memory leak prevention via cleanup
- 429 errors with proper headers
- Path exclusion from rate limiting
- 401 errors for missing credentials
- 403 errors for insufficient roles
- request.state.user setting on success
- Sensitive param redaction in audit logs
- Duration calculation in audit logs
- Error logging with stack traces
- Security headers enforcement
- CORS configuration structure

### utils.py (12 criteria)
- Token bucket refill based on elapsed time
- Returns False when insufficient tokens
- Deducts tokens_per_request when allowed
- Bucket removal on reset
- Context variable setting for correlation ID
- TimeoutError raising on expiry
- Timeout error logging with correlation_id
- 429 raising when rate limit exceeded
- Key extraction from Request
- Duration logging in success/error cases
- Correlation ID in log context
- Stack trace logging with exc_info=True

---

## Dependencies Analysis

### middleware.py
- **External:** fastapi, starlette, uuid, logging
- **Internal:** app.core.config (get_settings)
- **Note:** Minimal dependencies, good separation of concerns

### security.py
- **External:** fastapi, starlette, asyncio, time, datetime, collections, functools, traceback
- **Internal:** app.api (audit_logger, get_correlation_id)
- **Note:** Moderate dependencies, relies on internal audit_logger

### utils.py
- **External:** fastapi, starlette, asyncio, time, uuid, contextlib, functools, typing
- **Internal:** app.core.logging_config (get_correlation_id, set_correlation_id)
- **Note:** Minimal dependencies, good separation of concerns

---

## Test Requirements

### Test Files Needed
1. **tests/api/test_middleware.py** - 11 test cases
2. **tests/api/test_security.py** - 16 test cases
3. **tests/api/test_utils.py** - 17 test cases

**Total Test Cases:** 44

### Critical Test Paths
- Authentication success/failure paths
- Rate limiting enforcement
- Timeout handling
- Audit logging with sensitive data redaction
- Correlation ID propagation
- Security headers presence

---

## Recommendations

### Immediate Actions (P0)
1. Move hardcoded API key to environment variables (middleware.py)
2. Move SecurityConfig to environment-based configuration (security.py)
3. Move CORS origins to environment configuration (security.py)

### High Priority (P1)
1. Implement real JWT validation (middleware.py, security.py)
2. Consolidate duplicated SecurityHeadersMiddleware (middleware.py + security.py)
3. Consolidate duplicated CorrelationIdMiddleware (middleware.py + utils.py)

### Design Considerations
1. Rate limiter inconsistency: security.py uses sliding window, utils.py uses token bucket - consider consolidation
2. Three files with overlapping concerns - consider architectural refactoring
3. Audit logging in security.py could be integrated with utils.py logging decorators

---

## Files Created

1. `/Users/kepa.cantero/Projects/algoTrading/.requirements/app/api/middleware.py.requirements.md`
2. `/Users/kepa.cantero/Projects/algoTrading/.requirements/app/api/security.py.requirements.md`
3. `/Users/kepa.cantero/Projects/algoTrading/.requirements/app/api/utils.py.requirements.md`

---

## Conclusion

All three requirements documents have been successfully created following the template structure. Key findings:

- **GAP Violations:** 6 total (3 P0, 3 P1)
- **Code Duplication:** SecurityHeadersMiddleware and CorrelationIdMiddleware duplicated across files
- **Security Issues:** Hardcoded values need to move to environment variables
- **Test Coverage:** 44 test cases identified across 3 test files

The codebase would benefit from:
1. Consolidating duplicated middleware classes
2. Moving configuration to environment variables
3. Implementing production-ready JWT authentication
4. Standardizing on one rate limiting algorithm
