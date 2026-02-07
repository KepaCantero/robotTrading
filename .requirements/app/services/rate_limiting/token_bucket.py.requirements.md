# Requirements: services/rate_limiting/token_bucket.py

## Source File Analysis
- **File Path**: `app/services/rate_limiting/token_bucket.py`
- **Lines of Code**: 664
- **Language**: Python 3
- **Purpose**: Token bucket rate limiting algorithm for broker API protection

## Purpose
Implements token bucket algorithm to protect against hitting broker API rate limits:
- IBKR: 50-100 req/s
- Alpaca: 200 req/min
- Priority queue for critical operations
- Exponential backoff on 429 errors
- Rate limit monitoring and alerts

## Dependencies
- **Internal**:
  - `app.core.timezone_utils.utc_now` - UTC timestamp generation
- **External**:
  - `asyncio` - Async operations and locking
  - `logging` - Structured logging
  - `dataclasses` - Data structures
  - `requests.exceptions.HTTPError` - HTTP error handling

## Classes/Functions

### Data Classes
- **RateLimit** - Configuration (requests_per_second, burst_capacity)
- **TokenBucketState** - Current bucket state (tokens, last_update)
- **RateLimitStatistics** - Usage statistics (throttle_rate, wait_time)
- **BrokerType** (Enum) - IBKR, ALPACA, POLYGON, BINANCE
- **RequestPriority** (IntEnum) - CRITICAL(100) to BACKGROUND(0)

### TokenBucketRateLimiter
- **Purpose**: Implements token bucket algorithm per broker
- **Key Methods**:
  - `acquire()` - Acquire tokens with optional wait and timeout
  - `acquire_with_backoff()` - Exponential backoff on errors
  - `_try_acquire()` - Try to acquire without waiting
  - `_calculate_wait_time()` - Calculate time for token refill
  - `get_available_tokens()` - Get current token count
  - `get_statistics()` - Get usage statistics
  - `reset()` - Reset bucket to full capacity

### RateLimitManager
- **Purpose**: Singleton manager for multiple broker limiters
- **Key Methods**:
  - `get_limiter()` - Get or create limiter for broker
  - `reset_limiter()` - Reset specific limiter
  - `reset_all()` - Reset all limiters
  - `get_all_statistics()` - Statistics for all brokers

## Business Logic

### Token Bucket Algorithm
1. Bucket has maximum capacity (burst_capacity)
2. Tokens added at constant rate (requests_per_second)
3. Each request consumes one or more tokens
4. If bucket empty, requests wait for refill
5. Can burst up to capacity if recently unused

### Priority Queue
- Higher priority requests can preempt lower priority ones
- Priority levels: CRITICAL(100) > HIGH(75) > MEDIUM(50) > LOW(25) > BACKGROUND(0)
- Used when tokens are scarce

### Exponential Backoff
- Triggered on 429 (Too Many Requests) errors
- Formula: `backoff = initial_backoff * (2^attempt) + jitter`
- Jitter: 10% random variation to prevent thundering herd

## Data Models
- **BROKER_RATE_LIMITS**: Dict mapping BrokerType to RateLimit config
- Default limits configured per broker documentation

## API Contracts

### TokenBucketRateLimiter.acquire()
```python
async def acquire(
    tokens: int = 1,
    priority: int = RequestPriority.MEDIUM,
    timeout: Optional[float] = None
) -> bool
```

### TokenBucketRateLimiter.acquire_with_backoff()
```python
async def acquire_with_backoff(
    tokens: int = 1,
    max_retries: int = 3,
    initial_backoff: float = 1.0,
    priority: int = RequestPriority.MEDIUM
) -> bool
```

## Error Handling
- **Timeout**: Returns False if timeout exceeded
- **Invalid tokens**: Raises ValueError if tokens > burst_capacity
- **Async cancellation**: Handles asyncio.CancelledError appropriately
- **HTTPError**: Catches in backoff with retry logic

## Performance Considerations
- **Async Lock**: Uses asyncio.Lock for thread-safe token updates
- **Non-blocking**: Returns False on timeout instead of blocking forever
- **Efficient**: O(1) token calculation, O(n) priority queue where n = queued requests
- **Memory**: Minimal - only stores queue and statistics

## Testing Strategy
- **Unit Tests**:
  - Test token refill calculation
  - Test burst capacity behavior
  - Test priority queue ordering
  - Test timeout behavior
- **Integration Tests**:
  - Test with actual broker APIs
  - Test backoff with real 429 responses
- **Edge Cases**:
  - Zero requests_per_second
  - Burst capacity = 1
  - Concurrent acquire calls

## Compliance with BASE_RULES.md

### Format & Style
- FMT-001: Line length within 100 char limit
- FMT-002: Proper import organization (stdlib → third-party → local)
- FMT-006: F-strings used for logging
- FMT-007: No mutable defaults (dataclasses with default_factory)

### Type Hints
- TYP-001: 100% type coverage on all functions
- TYP-002: Modern syntax (Dict, List, Optional)
- TYP-003: No Any without justification - all types are specific
- TYP-005: Dataclass fields fully typed

### SOLID Principles
- SOL-001: Single Responsibility - Rate limiting only
- SOL-005: Dependency Inversion - Callable injected for callbacks

### Async Patterns
- ASYNC-001: All async functions properly marked
- ASYNC-002: All async calls properly awaited
- ASYNC-003: Async context manager support (__aenter__, __aexit__)
- ASYNC-004: No blocking time.sleep() - uses asyncio.sleep()
- ASYNC-005: Timeouts implemented on acquire()
- ASYNC-006: Handles asyncio.TimeoutError

### Clean Code
- CC-001: Descriptive names (acquire_with_backoff, calculate_wait_time)
- CC-006: Explicit error handling for ValueError, HTTPError, asyncio errors
- CC-007: Functions reasonable length (< 40 lines most methods)

### Security
- SEC-006: Rate limiting implemented (core feature)
- No hardcoded secrets

### Logging
- LOG-001: Structured logging with contextual info
- LOG-003: Appropriate levels (info, warning, error)
- LOG-004: Error logging with exception context

### Design Patterns
- DP-004: Dependency injection (on_limit_exceeded callback)
- Singleton pattern for RateLimitManager

## Audit Status
**Status**: PASSED

### Strengths
1. Excellent async implementation with proper locking
2. Comprehensive type hints throughout
3. Well-documented token bucket algorithm
4. Proper error handling with backoff strategy
5. Good separation of concerns (RateLimiter vs Manager)
6. Priority queue for critical operations
7. Async context manager support

### Minor Observations
1. Some constants could be class-level (magic numbers for backoff)
2. Priority queue implementation could use heapq for O(log n) instead of O(n)
3. utc_now() usage is correct for timezone-aware timestamps

### No Critical Gaps Found
- All P0 and P1 BASE_RULES satisfied
- Production-ready rate limiting implementation
- No security vulnerabilities
- No performance bottlenecks for expected load

---
*Audit completed: 2026-02-07*
*Auditor: GAP Audit Batch 0079*
*Status: PASSED*
