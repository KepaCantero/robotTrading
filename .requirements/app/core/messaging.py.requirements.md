# messaging.py Requirements

**File:** `app/core/messaging.py`  
**Purpose:** Messaging system for inter-module communication  
**Audit Status:** NEEDS_AUDIT

---

## References
- **BASE_RULES:** See ../../BASE_RULES.md for universal rules
- **Related Files:**
  - `app/core/secure_serialization.py` (sign_and_dump, verify_and_load)
  - All modules that use pub/sub messaging

---

## Purpose & Scope

This module provides a unified message bus for inter-module communication using Redis pub/sub for most cases, ZeroMQ for high-frequency data, and falling back to in-memory message passing if dependencies are unavailable.

**Critical for Production:** Enables real-time communication between trading components without tight coupling.

---

## Classes & Functions

### Classes

| Class | Purpose | Methods |
|-------|---------|---------|
| `MessageBus` | Unified message bus | `publish()`, `subscribe()`, `close()` |

### Functions

| Function | Purpose | Return Type |
|----------|---------|-------------|
| `get_message_bus()` | Get or create global message bus | `MessageBus` |

---

## File-Specific Requirements

### MSG-001: Redis Fallback
**Priority:** P1 (High - Availability)

**Requirement:** System must fall back to in-memory messaging if Redis unavailable.

**Acceptance Criteria:**
```python
# Redis connection fails
bus = MessageBus(redis_host="invalid")
# Should fall back to in-memory
assert bus.redis_client is None
# Publish/subscribe should still work
assert bus.publish("test", {"data": "test"}) == True
```

**Check:** Fallback logic works

---

### MSG-002: ZeroMQ High-Frequency
**Priority:** P2 (Medium - Performance)

**Requirement:** High-frequency channels (market-ticks, signals) should use ZeroMQ when enabled.

**Acceptance Criteria:**
```python
bus = MessageBus(use_zmq=True)
# High-frequency channels should use ZMQ
bus.publish("market-ticks", {"price": 100.0})
# Should publish to ZMQ socket
```

**Check:** ZeroMQ used for high-freq channels

---

### MSG-003: Secure Serialization
**Priority:** P0 (Critical - Security)

**Requirement:** All messages must use JSON+HMAC signing, not pickle.

**Acceptance Criteria:**
```python
# Must use sign_and_dump, not pickle
# This is enforced in the code
```

**Check:** sign_and_dump/verify_and_load used

---

### MSG-004: Thread-Safe Subscription
**Priority:** P1 (High - Concurrent access)

**Requirement:** Subscriptions must run in separate threads to avoid blocking.

**Acceptance Criteria:**
```python
bus = MessageBus()
def callback(msg):
    pass
thread = bus.subscribe("test", callback)
assert thread is not None  # Thread returned
assert thread.is_alive()  # Thread running
```

**Check:** Threading used correctly

---

### MSG-005: In-Memory Callbacks
**Priority:** P2 (Medium - Fallback behavior)

**Requirement:** In-memory fallback must call registered callbacks synchronously.

**Acceptance Criteria:**
```python
bus = MessageBus()  # Redis unavailable
messages = []
def callback(msg):
    messages.append(msg)
bus.subscribe("test", callback)
bus.publish("test", {"data": "test"})
assert len(messages) == 1  # Callback invoked
```

**Check:** In-memory callbacks work

---

### MSG-006: Connection Cleanup
**Priority:** P1 (High - Resource management)

**Requirement:** All connections must be properly closed on cleanup.

**Acceptance Criteria:**
```python
bus = MessageBus()
bus.close()
# All connections should be closed
# No resource leaks
```

**Check:** close() method cleans up

---

### MSG-007: Error Handling
**Priority:** P1 (High - Robustness)

**Requirement:** Publish failures should be logged but not crash.

**Acceptance Criteria:**
```python
bus = MessageBus()
# Publish with invalid data should log error, not crash
result = bus.publish("test", "invalid")
# Should return False, log error
```

**Check:** Error handling in publish()

---

### MSG-008: Global Instance Management
**Priority:** P2 (Medium - Singleton pattern)

**Requirement:** Global message bus should be singleton (same instance returned).

**Acceptance Criteria:**
```python
bus1 = get_message_bus()
bus2 = get_message_bus()
assert bus1 is bus2  # Same instance
```

**Check:** Singleton pattern works

---

## BASE_RULES Compliance

### Critical Rules (P0)
- **SEC-005:** Audit logging ✅ (all operations logged)
- **CC-006:** Explicit error handling ✅

### High Priority (P1)
- **TYP-001:** Type hints present ✅
- **CC-001:** Descriptive names ✅
- **LOG-002:** Context in logs ✅

### Medium Priority (P2)
- **QL-001:** Complexity reasonable ✅
- **CC-007:** Small methods ✅

---

## Known Issues & Technical Debt

### Issues
1. **No message persistence** - Messages lost if no subscribers
2. **No message ordering** - No guarantee of message order
3. **No backpressure** - No flow control for slow consumers

### Technical Debt
1. **Add message queue** - For message persistence
2. **Add message ordering** - Sequence numbers or timestamps
3. **Add backpressure** - Flow control for high-throughput scenarios

---

## Testing Requirements

### Unit Tests
- [ ] Test Redis fallback
- [ ] Test ZeroMQ high-frequency
- [ ] Test secure serialization
- [ ] Test thread-safe subscriptions
- [ ] Test in-memory callbacks
- [ ] Test connection cleanup
- [ ] Test error handling
- [ ] Test global instance

### Integration Tests
- [ ] Test with real Redis
- [ ] Test with real ZeroMQ
- [ ] Test high-throughput scenarios
- [ ] Test message delivery guarantees

---

## Security Considerations

1. **No pickle** ✅ (uses JSON+HMAC)
2. **Message signing** ✅ (HMAC signatures)
3. **No injection** ✅ (structured data)

---

## Performance Considerations

1. **Redis pub/sub** - High throughput ✅
2. **ZeroMQ** - Very high throughput ✅
3. **In-memory** - Fast but no persistence ✅

---

## Dependencies

**External:**
- `redis` (optional, for pub/sub)
- `zmq` (optional, for high-frequency)
- `logging` (stdlib)
- `threading` (stdlib)
- `typing` (stdlib)

**Internal:**
- `app.core.secure_serialization` (sign_and_dump, verify_and_load)

---

## Migration Notes

**From direct calls:**
1. Identify inter-module communication
2. Replace with pub/sub messaging
3. Add message handlers
4. Test message delivery

**To messaging system:**
1. Import get_message_bus()
2. Use publish() for sending
3. Use subscribe() for receiving
4. Handle async message processing

---

## Changelog

### Version 1.0.0 (Initial)
- Redis pub/sub messaging
- ZeroMQ high-frequency support
- In-memory fallback
- Secure serialization
- Thread-safe subscriptions

---

**Last Updated:** 2026-02-06  
**Next Review:** After production deployment
