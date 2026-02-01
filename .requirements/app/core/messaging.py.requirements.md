# messaging.py

## Purpose
Message bus implementation with Redis pub/sub, ZeroMQ fallback, and in-memory fallback for trading system communication.

---

## Type Definitions / Data Classes

⚠️ **CRITICAL:** This file uses standard types only (no Pydantic models or dataclasses).

### MessageBus Configuration
```python
class MessageBus:
    redis_host: str                    # REQUIRED - Redis server host
    redis_port: int                    # REQUIRED - Redis server port
    use_zmq: bool                      # REQUIRED - Enable ZeroMQ fallback
    zmq_port: int                      # REQUIRED - ZeroMQ port
    fallback_in_memory: bool           # REQUIRED - Enable in-memory fallback
```

---

## Function Signatures (Contracts)

### `__init__(redis_host: str, redis_port: int, use_zmq: bool, zmq_port: int, fallback_in_memory: bool)`
**Pre:** Valid host and port values
**Post:** MessageBus initialized with specified transports
**Raises:** ConnectionError if all transports fail
**Retry:** No
**Side Effects:** Initializes Redis, ZeroMQ, in-memory transports

### `publish(channel: str, message: Any) -> None`
**Pre:** channel is non-empty string
**Post:** message published to all subscribers
**Raises:** ConnectionError if all transports fail
**Retry:** ✅ Yes (falls back through transports)
**Side Effects:** Message queued for delivery

### `subscribe(channel: str, callback: Callable[[Any], None]) -> None`
**Pre:** channel is non-empty string, callback is callable
**Post:** callback invoked for messages on channel
**Raises:** ConnectionError if all transports fail
**Retry:** ✅ Yes (falls back through transports)
**Side Effects:** Adds subscription to transport

### `unsubscribe(channel: str, callback: Callable[[Any], None]) -> None`
**Pre:** channel and callback previously subscribed
**Post:** callback removed from subscriptions
**Raises:** KeyError if subscription not found
**Retry:** No
**Side Effects:** Removes subscription

### `close() -> None`
**Pre:** None
**Post:** All connections closed
**Raises:** None
**Retry:** No
**Side Effects:** Closes Redis, ZeroMQ connections

---

## Acceptance Criteria
- [ ] Redis pub/sub is primary transport
- [ ] ZeroMQ fallback when Redis unavailable
- [ ] In-memory fallback when both external transports fail
- [ ] Graceful degradation through transport hierarchy
- [ ] Thread-safe publish/subscribe operations
- [ ] Connection error raised only if all transports fail
- [ ] Proper cleanup in close()
- [ ] Callbacks invoked on message receipt

---

## Critical Rules (MUST NOT BREAK)

**Reglas universales:** Ver `../../BASE_RULES.md` (96+ rules organized by priority)

### Reglas ESPECÍFICAS de este archivo:

| Rule | Source | Requirement | Current Status |
|------|--------|-------------|----------------|
| ASYNC-001 | BASE_RULES.md | Use async def | ⚠️ PARTIAL - May need async publish/subscribe |
| ASYNC-005 | BASE_RULES.md | Timeouts for external calls | ⚠️ GAP - No timeout configuration |
| CC-006 | BASE_RULES.md | Explicit error handling | ✅ OK - ConnectionError raised |
| LOG-004 | BASE_RULES.md | Error logging with stack traces | ⚠️ GAP - Should log transport failures |

---

## Dependencies
- **External:** redis, zmq (optional)
- **Internal:** None

---

## Required Tests
- **tests/core/test_messaging.py:**
  - Test Redis publish/subscribe
  - Test ZeroMQ fallback when Redis unavailable
  - Test in-memory fallback when both external fail
  - Test connection error when all transports fail
  - Test unsubscribe removes subscription
  - Test close() cleans up connections
  - Test thread-safe concurrent operations

---

## Notes
Multi-transport fallback ensures resilience. Consider async/await for better performance with high message throughput.
