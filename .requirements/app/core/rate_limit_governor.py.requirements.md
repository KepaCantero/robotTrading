# rate_limit_governor.py Requirements

**File:** `app/core/rate_limit_governor.py`  
**Purpose:** Rate Limit Governor - Token Bucket Algorithm + WebSocket First Strategy  
**Author:** SRE Feedback Integration  
**Date:** 2025-01-25  
**Audit Status:** NEEDS_AUDIT

---

## References
- **BASE_RULES:** See ../../BASE_RULES.md for universal rules
- **Related Files:**
  - `app/core/interfaces/broker_base.py` (BrokerType interface)
  - Trading system rate limiting strategies

---

## Purpose & Scope

This module implements a critical rate limiting system to prevent IP bans from crypto brokers (Binance, Kraken, etc.). It combines:

1. **Token Bucket Algorithm** - Guarantees never exceeding X requests/second
2. **WebSocket First Strategy** - Uses WebSocket for real-time data (no REST rate limits)
3. **Adaptive Rate Limiting** - Adjusts dynamically based on broker responses

**Critical for Production:** Prevents 24-hour IP bans from rate limit violations.

---

## Classes & Functions

### Classes

| Class | Purpose | Methods |
|-------|---------|---------|
| `RateLimitConfig` | Configuration for rate limiting | `max_requests_per_second`, `burst_capacity`, `refill_rate`, `broker_limits` |
| `TokenBucketState` | Token bucket state tracking | `tokens`, `last_refill`, `capacity`, statistics |
| `TokenBucketAlgorithm` | Token bucket implementation | `acquire()`, `_refill()`, `_calculate_wait_time()`, `get_stats()` |
| `WebSocketFirstStrategy` | WebSocket-first data fetching | `get_ticker()`, `subscribe_ticker()`, `start_websocket()`, `stop_websocket()` |
| `AdaptiveRateLimiter` | Adaptive rate adjustment | `record_response()`, `_adjust_for_429()`, `_consider_increase()` |
| `RateLimitGovernor` | Main governor component | `acquire_token()`, `get_ticker()`, `subscribe_ticker()`, `record_response()`, `get_stats()` |

### Functions

| Function | Purpose | Return Type |
|----------|---------|-------------|
| `rate_limit(governor)` | Decorator for async rate limiting | `Callable` |

---

## File-Specific Requirements

### RLG-001: Critical Rate Limit Safety
**Priority:** P0 (Critical - Prevents IP bans)

**Requirement:** Token Bucket Algorithm must guarantee rate limits are never exceeded.

**Acceptance Criteria:**
```python
# Token bucket never allows exceeding configured rate
governor = RateLimitGovernor('binance', RateLimitConfig(max_requests_per_second=20))
# 20 requests in 1 second should succeed
# 21st request should wait or timeout
```

**Check:** Manual review of token bucket logic

---

### RLG-002: WebSocket Fallback Graceful Degradation
**Priority:** P0 (Critical - System reliability)

**Requirement:** If WebSocket fails, system must fall back to REST with rate limiting without crashing.

**Acceptance Criteria:**
```python
# WebSocket connection failure falls back to REST
try:
    await governor.start_websocket(url)
except (ConnectionError, TimeoutError):
    # System continues with REST + rate limiting
    assert governor.is_websocket_connected() == False
```

**Check:** Exception handling in WebSocket methods

---

### RLG-003: Adaptive Rate Limiting on 429 Responses
**Priority:** P1 (High - Prevents bans)

**Requirement:** Upon receiving HTTP 429, automatically reduce rate limit by 50%.

**Acceptance Criteria:**
```python
old_rate = governor.adaptive_limiter.current_rate
await governor.record_response(429)
new_rate = governor.adaptive_limiter.current_rate
assert new_rate < old_rate  # Rate reduced
```

**Check:** Test adaptive limiter behavior

---

### RLG-004: Broker-Specific Rate Limits
**Priority:** P1 (High - Correct limits per broker)

**Requirement:** Apply correct rate limits for each broker (Binance: 20/s, Kraken: 10/s, etc.).

**Acceptance Criteria:**
```python
governor_binance = RateLimitGovernor('binance')
assert governor_binance.config.max_requests_per_second == 20

governor_kraken = RateLimitGovernor('kraken')
assert governor_kraken.config.max_requests_per_second == 10
```

**Check:** Verify broker_limits dictionary

---

### RLG-005: Async Safety with Token Bucket
**Priority:** P0 (Critical - Race conditions)

**Requirement:** Token bucket must use async locks to prevent race conditions in concurrent requests.

**Acceptance Criteria:**
```python
# Multiple concurrent requests should not exceed rate limit
tasks = [governor.acquire_token() for _ in range(100)]
await asyncio.gather(*tasks)
# Total requests should respect rate limit
```

**Check:** Verify `asyncio.Lock()` usage

---

### RLG-006: WebSocket Data Freshness
**Priority:** P1 (High - Data quality)

**Requirement:** WebSocket data must be fresh (< 1 second old) or fall back to REST.

**Acceptance Criteria:**
```python
# Stale WebSocket data should trigger REST fallback
# Data older than 1 second is considered stale
```

**Check:** Time validation in `get_ticker()`

---

### RLG-007: Rate Limit Statistics Tracking
**Priority:** P2 (Medium - Monitoring)

**Requirement:** Track rate limit statistics (blocked requests, utilization, etc.).

**Acceptance Criteria:**
```python
stats = governor.get_stats()
assert 'token_bucket' in stats
assert 'utilization_pct' in stats['token_bucket']
```

**Check:** Verify statistics collection

---

### RLG-008: Decorator Usability
**Priority:** P2 (Medium - Developer experience)

**Requirement:** `@rate_limit` decorator must be easy to apply to async functions.

**Acceptance Criteria:**
```python
@rate_limit(governor)
async def fetch_price(symbol: str) -> Decimal:
    # Automatically rate limited
    pass
```

**Check:** Manual test of decorator

---

## BASE_RULES Compliance

### Critical Rules (P0)
- **LOG-004:** All exceptions logged with stack traces ✅ (uses logger.error with exc_info)
- **ASYNC-001:** Async functions properly marked ✅
- **ASYNC-003:** Async context managers used ✅
- **CC-006:** Explicit error handling ✅ (RateLimitError raised)

### High Priority (P1)
- **LOG-002:** Context in logs ✅ (broker_name, rate info)
- **LOG-003:** Appropriate log levels ✅
- **PERF-006:** Async I/O used ✅

### Medium Priority (P2)
- **TYP-001:** Type hints present ✅
- **CC-001:** Descriptive names ✅
- **QL-001:** Complexity reasonable ✅

---

## Known Issues & Technical Debt

### Issues
1. **No circuit breaker** for repeated rate limit violations
2. **Hardcoded broker limits** should be in configuration file
3. **Missing distributed locking** for multi-instance deployments

### Technical Debt
1. Consider implementing **exponential backoff** after 429 responses
2. Add **metrics export** (Prometheus) for rate limit monitoring
3. Implement **request prioritization** for critical operations

---

## Testing Requirements

### Unit Tests
- [ ] Test token bucket acquire/release
- [ ] Test WebSocket fallback to REST
- [ ] Test adaptive rate limiting on 429
- [ ] Test broker-specific rate limits
- [ ] Test concurrent request safety

### Integration Tests
- [ ] Test with real Binance WebSocket
- [ ] Test rate limit governor under load
- [ ] Test WebSocket reconnection logic

---

## Security Considerations

1. **No secrets in code** ✅ (uses environment variables)
2. **WebSocket URL validation** - should validate URLs before connecting
3. **Rate limit bypass prevention** - ensure decorator cannot be bypassed

---

## Performance Considerations

1. **Token bucket operations** should be O(1) ✅
2. **WebSocket overhead** minimal compared to REST polling
3. **Lock contention** minimal under high concurrency

---

## Dependencies

**External:**
- `asyncio` (stdlib)
- `logging` (stdlib)
- `dataclasses` (stdlib)
- `decimal` (stdlib)
- `enum` (stdlib)
- `aiohttp` (optional, for WebSocket)
- `typing` (stdlib)

**Internal:**
- None (standalone module)

---

## Migration Notes

**From old rate limiting:**
1. Replace direct API calls with `@rate_limit` decorator
2. Configure broker-specific rate limits
3. Enable WebSocket for real-time data

**To new rate limiting:**
1. Setup WebSocket connections
2. Configure adaptive rate limiting
3. Monitor rate limit statistics

---

## Changelog

### Version 1.0.0 (2025-01-25)
- Initial implementation
- Token Bucket Algorithm
- WebSocket First Strategy
- Adaptive Rate Limiting
- Multi-broker support

---

**Last Updated:** 2026-02-06  
**Next Review:** After production deployment
