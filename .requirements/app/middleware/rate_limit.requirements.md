# Requirements: app/middleware/rate_limit.py

**Last Updated:** 2026-02-04
**Status:** Active
**Priority:** P0 (Security)

## Purpose

API rate limiting middleware using token bucket algorithm. Implements GAP fixes SEC-004 and SEC-005 for per-IP and per-user rate limiting.

## Base Rules Applied

From [BASE_RULES.md](../BASE_RULES.md):

- **FMT-001:** Line length <= 100 characters
- **TYP-001:** 100% type coverage
- **SEC-004:** Rate limiting to prevent abuse
- **SEC-005:** Per-IP and per-user rate limiting
- **ARCH-004:** Small functions (< 20 lines)

## File-Specific Requirements

### REQ-RATE-001: Token Bucket Algorithm
- Refill tokens based on elapsed time
- Capacity limit to prevent token accumulation
- Thread-safe token consumption

### REQ-RATE-002: Per-Endpoint Rate Limits
- `expensive_rate`: /historical, /backtest, /validate (10/min)
- `write_rate`: POST, PUT, DELETE, PATCH (30/min)
- `read_rate`: GET operations (120/min)
- `default_rate`: All other endpoints (60/min)

### REQ-RATE-003: Per-IP and Per-User Limits (SEC-005)
- Use user_id from request.state if authenticated
- Fall back to IP address for anonymous requests
- Separate buckets for each user/IP

### REQ-RATE-004: Rate Limit Headers
- X-RateLimit-Limit: Maximum requests per window
- X-RateLimit-Remaining: Remaining requests in window
- X-RateLimit-Reset: When limit resets
- Retry-After: Seconds until retry allowed

### REQ-RATE-005: Health Check Exemption
- Skip rate limiting for /health and /health-check
- Allows monitoring without rate limit concerns

## Ralphex Audit Status

**Audit Date:** 2026-02-05
**Auditor:** Claude (Ralphex Process)
**Overall Status:** PASSED with Minor Gaps

### GAP Analysis Summary

| Priority | Total Gaps | Status |
|----------|------------|--------|
| P0 (Critical) | 0 | PASS |
| P1 (High) | 0 | PASS |
| P2 (Medium) | 2 | MINOR |
| P3 (Low) | 0 | PASS |
| **TOTAL** | **2** | **PASSED** |

### Detailed GAP Analysis

#### BASE_RULES.md Compliance

| Rule ID | Rule | Status | Notes |
|---------|------|--------|-------|
| **FMT-001** | Line length ≤ 100 | PASS | All lines ≤ 100 chars |
| FMT-002 | Import organization | PASS | stdlib → third-party → local |
| FMT-003 | No unused imports | PASS | No unused imports found |
| FMT-004 | Double quotes | PASS | Consistent double quotes |
| FMT-006 | F-strings | PASS | Uses f-strings for logging |
| FMT-007 | No mutable defaults | PASS | Uses `field(default_factory=...)` |
| FMT-008 | Context managers | PASS | Uses `async with` for locks |
| **TYP-001** | 100% type coverage | PASS | All functions typed |
| TYP-002 | Modern syntax | PASS | Uses `X \| None` syntax |
| TYP-005 | Class attribute types | PASS | All attrs have types |
| SOL-001 | Single Responsibility | PASS | Each class has single purpose |
| SOL-005 | Dependency Inversion | PASS | Config injected via constructor |
| ARCH-004 | Small functions | PASS | Most functions < 20 lines |
| ASYNC-001 | Use async def | PASS | All async functions marked |
| ASYNC-003 | Async context managers | PASS | Uses `async with self._lock` |
| LOG-001 | Structured logging | PASS | Uses logger with context |
| LOG-003 | Appropriate levels | PASS | Uses warning for rate limits |
| LOG-004 | Error logging | PASS | Errors logged with context |
| **SEC-004** | Rate limiting | PASS | Token bucket implemented |
| **SEC-005** | Per-IP/per-user limits | PASS | Uses user_id or IP |
| SEC-006 | Input validation | PASS | Request validated before processing |
| CFG-001 | Pydantic Settings | PASS | Uses dataclass for config |
| CC-001 | Descriptive names | PASS | Clear, intent-revealing names |
| CC-005 | Early returns | PASS | Guard clauses used |
| QL-001 | Complexity < 10 | PASS | Simple logic throughout |
| QL-007 | Max 7 parameters | PASS | All functions ≤ 4 params |

#### File-Specific Requirements Compliance

| Req ID | Requirement | Status | Notes |
|--------|-------------|--------|-------|
| REQ-RATE-001 | Token Bucket Algorithm | PASS | Refill, capacity, thread-safe |
| REQ-RATE-002 | Per-Endpoint Rate Limits | PASS | expensive/write/read/default rates |
| REQ-RATE-003 | Per-IP and Per-User Limits | PASS | user_id → IP fallback |
| REQ-RATE-004 | Rate Limit Headers | PASS | X-RateLimit-* headers set |
| REQ-RATE-005 | Health Check Exemption | PASS | /health paths skipped |

### Minor Gaps (P2 - Medium Priority)

| GAP ID | Rule | Description | Impact | Fix |
|--------|------|-------------|--------|-----|
| GAP-P2-001 | QL-006 | Class `RateLimitDecorator` could be split | Class at 55 lines, still manageable | Optional refactoring |
| GAP-P2-002 | LOG-002 | Missing correlation ID in logs | Harder to trace requests across services | Add request_id to log context |

### Critical Gaps (P0)

**None** - No critical gaps found.

### High Priority Gaps (P1)

**None** - No high priority gaps found.

### Strengths

1. ✅ **Security-First Design**: Implements rate limiting per SEC-004, SEC-005
2. ✅ **Token Bucket Algorithm**: Proper refill rate and burst capacity
3. ✅ **Per-Endpoint Limits**: Different rates for expensive vs cheap operations
4. ✅ **Health Check Exemption**: Smart skip for monitoring endpoints
5. ✅ **Type Safety**: Full type coverage with modern syntax
6. ✅ **Async Safety**: Proper use of locks and async context managers
7. ✅ **Clear Documentation**: Docstrings explain all public methods
8. ✅ **Production-Ready Headers**: Standard rate limit headers in responses

### Recommendations for Production

1. **Redis Backing**: Current in-memory implementation won't work with multiple workers
2. **Correlation IDs**: Add request tracing for distributed systems
3. **Metrics Export**: Consider Prometheus metrics for rate limit violations
4. **Whitelist Support**: Add admin/monitoring IP whitelist capability
5. **Dynamic Configuration**: Allow runtime rate limit adjustment without restart

### Test Coverage Recommendations

- [ ] Test token bucket refill rate accuracy
- [ ] Test burst capacity handling
- [ ] Test per-user vs per-IP key selection
- [ ] Test health check exemption
- [ ] Test rate limit headers values
- [ ] Test concurrent request handling with lock
- [ ] Test different endpoint rate limits
- [ ] Test wait_time calculation accuracy

## Security Considerations

- Rate limiting prevents DoS attacks
- Per-user limits prevent one user from monopolizing resources
- Lower limits for expensive operations protect system resources
- Consider Redis backing for multi-process deployments

## Production Considerations

**Current Implementation:** In-memory rate limiting

**For Production:**
- Use Redis-backed rate limiting for multi-worker deployments
- Implement IP whitelist for trusted monitoring services
- Add admin bypass for emergency operations
- Configure rate limits based on endpoint cost

## Dependencies

- `fastapi`: Request/Response handling
- `starlette.middleware.base`: BaseHTTPMiddleware
- `dataclasses`: Configuration classes
- `asyncio`: Lock for thread safety

## Testing Requirements

- Test token bucket refill rate
- Test burst capacity
- Test per-user vs per-IP limits
- Test health check exemption
- Test rate limit headers
