# Redis Fallback Quick Reference

## Overview
The codebase uses graceful fallback patterns for optional dependencies like `redis` and `zmq`. This ensures the application runs even when these packages are not installed.

## Files with Redis Fallback

### 1. Distributed Cache
**File:** `/Users/kepa.cantero/Projects/algoTrading/app/engines/data_engine/cache/distributed_cache.py`

**Pattern:**
```python
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None  # type: ignore
    logging.warning("redis package not installed. Using in-memory cache fallback only.")
```

**Fallback Behavior:**
- Redis available: Uses distributed Redis cache with PostgreSQL persistence
- Redis NOT available: Uses in-memory dictionary cache (`self.memory_cache`)
- All operations (get, set, delete, clear_expired) work transparently

**Usage:**
```python
from app.engines.data_engine.cache.distributed_cache import DistributedCache, REDIS_AVAILABLE

cache = DistributedCache(config={
    'default_ttl': 300,
    'use_redis': REDIS_AVAILABLE,  # Automatically enabled if available
    'use_postgres': True,
    'redis_url': 'redis://localhost:6379',
    'postgres_url': 'postgresql://user:pass@localhost/db'
})

await cache.set('key', {'data': 'value'}, ttl=60)
value = await cache.get('key')
```

### 2. Messaging System
**File:** `/Users/kepa.cantero/Projects/algoTrading/app/core/messaging.py`

**Pattern:**
```python
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None  # type: ignore
    logging.warning("redis package not installed. Messaging system will use in-memory fallback.")

try:
    import zmq
    ZMQ_AVAILABLE = True
except ImportError:
    ZMQ_AVAILABLE = False
    zmq = None  # type: ignore
    logging.warning("zmq package not installed. ZeroMQ messaging disabled.")
```

**Fallback Behavior:**
- Both available: Redis pub/sub + ZeroMQ for high-frequency channels
- Redis only: Redis pub/sub for all messaging
- Neither: In-memory publish/subscribe with direct callback invocation

**Usage:**
```python
from app.core.messaging import MessageBus, REDIS_AVAILABLE, ZMQ_AVAILABLE

bus = MessageBus(
    redis_host='localhost',
    redis_port=6379,
    use_zmq=ZMQ_AVAILABLE,  # Automatically enabled if available
    zmq_port=5555
)

# Publish
bus.publish('signals', {'symbol': 'AAPL', 'action': 'buy'})

# Subscribe
def callback(message):
    print(f"Received: {message}")

bus.subscribe('signals', callback)
```

## Implementation Pattern

When adding new optional dependencies, follow this pattern:

```python
# At top of file
import logging

try:
    import optional_package
    OPTIONAL_AVAILABLE = True
except ImportError:
    OPTIONAL_AVAILABLE = False
    optional_package = None  # type: ignore
    logging.warning("optional_package not installed. Feature disabled.")

# In class initialization
class MyClass:
    def __init__(self):
        self.optional_client = None
        if OPTIONAL_AVAILABLE:
            try:
                self.optional_client = optional_package.Client()
                logger.info("✓ Optional feature enabled")
            except (ConnectionError, TimeoutError) as e:
                logger.warning(f"⚠️ Optional feature failed: {e}")
                self.optional_client = None
        else:
            logger.warning("⚠️ Optional package not installed")

    def do_something(self):
        if self.optional_client:
            # Use optional feature
            return self.optional_client.do_it()
        else:
            # Fallback implementation
            return self._fallback_do_it()

    def _fallback_do_it(self):
        # In-memory or simplified fallback
        return None
```

## Testing

To test if fallbacks work correctly:

```python
# Test messaging
from app.core.messaging import MessageBus, REDIS_AVAILABLE, ZMQ_AVAILABLE

assert REDIS_AVAILABLE == False or REDIS_AVAILABLE == True
assert ZMQ_AVAILABLE == False or ZMQ_AVAILABLE == True

bus = MessageBus()
assert bus is not None
bus.publish('test', {'data': 'test'})  # Should not raise

# Test distributed cache
from app.engines.data_engine.cache.distributed_cache import DistributedCache

cache = DistributedCache({
    'default_ttl': 300,
    'use_redis': False,
    'use_postgres': False,
})

# In-memory operations work
import asyncio
asyncio.run(cache.set('key', 'value'))
result = asyncio.run(cache.get('key'))
assert result == 'value'
```

## Warnings to Expect

When running without redis/zmq, you'll see these warnings (this is normal):

```
WARNING:root:redis package not installed. Using in-memory cache fallback only.
WARNING:root:redis package not installed. Messaging system will use in-memory fallback.
WARNING:root:zmq package not installed. ZeroMQ messaging disabled.
WARNING:⚠️ Redis not installed. Using in-memory fallback.
WARNING:⚠️ ZeroMQ not installed. Using Redis fallback.
```

## Installing Optional Dependencies

If you want to enable the full features:

```bash
# Install Redis client
pip install redis>=5.0.0

# Install ZeroMQ
pip install pyzmq

# Or install all optional dependencies
pip install -r requirements-optional.txt  # If available
```

## Production Considerations

### Development
- Use fallbacks for easier local development
- No need to install all dependencies
- Faster startup times

### Staging
- Install all optional dependencies
- Test with actual Redis/ZeroMQ
- Verify fallback warnings disappear

### Production
- Install all optional dependencies
- Monitor for fallback activation in logs
- Alert if fallbacks are being used (indicates missing dependencies)

## Related Files

- `/Users/kepa.cantero/Projects/algoTrading/REDIS_FALLBACK_FIX_SUMMARY.md` - Implementation details
- `/Users/kepa.cantero/Projects/algoTrading/app/engines/data_engine/cache/distributed_cache.py` - Cache implementation
- `/Users/kepa.cantero/Projects/algoTrading/app/core/messaging.py` - Messaging implementation

## Common Issues

**Q: I see warnings about redis not installed**
- A: This is normal if you haven't installed redis. The app will use in-memory fallback.

**Q: How do I know if Redis is being used?**
- A: Check the logs:
  - "Redis cache inicializado" = Redis is active
  - "Using in-memory cache fallback only" = Fallback is active
  - Or check `REDIS_AVAILABLE` flag after import

**Q: Can I force use of in-memory even if Redis is installed?**
- A: Yes, set `use_redis=False` in the config when creating the cache:
  ```python
  cache = DistributedCache(config={
      'default_ttl': 300,
      'use_redis': False,  # Force in-memory even if Redis available
      'use_postgres': True,
  })
  ```

**Q: What about performance differences?**
- A: Redis is distributed and persists across restarts. In-memory is per-process and lost on restart. For development, in-memory is fine. For production, use Redis.
