# Async/Await Patterns

Python async/await patterns for concurrent and parallel operations.

## Table of Contents
1. Async Functions
2. Async Context Managers
3. Async Iterators
4. Concurrent Execution
5. Async Classes
6. Sync to Async Bridge
7. Error Handling
8. Testing Async Code

---

## Async Functions

### Basic Async Functions

```python
# ✅ CORRECT - Basic async functions
import asyncio
from typing import Awaitable, Any

async def fetch_user_data(user_id: int) -> dict[str, Any]:
    """
    Fetch user data asynchronously.

    Args:
        user_id: User identifier.

    Returns:
        User data dictionary.
    """
    # Simulated async I/O
    await asyncio.sleep(0.1)
    return {"id": user_id, "name": "User"}


async def fetch_multiple_users(user_ids: list[int]) -> list[dict[str, Any]]:
    """
    Fetch multiple users concurrently.

    Args:
        user_ids: List of user identifiers.

    Returns:
        List of user data dictionaries.
    """
    tasks = [fetch_user_data(user_id) for user_id in user_ids]
    return await asyncio.gather(*tasks)


async def main() -> None:
    """Main async function."""
    # Fetch single user
    user = await fetch_user_data(1)

    # Fetch multiple users concurrently
    users = await fetch_multiple_users([1, 2, 3, 4, 5])

    # Process results
    for user in users:
        print(user)


if __name__ == "__main__":
    asyncio.run(main())
```

### ❌ INCORRECT - Mixing sync and async

```python
# ❌ WRONG - Mixing sync and async incorrectly
def fetch_data(url: str) -> dict[str, Any]:
    # This is sync but calls async code!
    return asyncio.run(fetch_data(url))  # Don't do this in async context

# ❌ WRONG - Using blocking calls in async
async def process():
    time.sleep(1)  # Blocks the event loop!
    # Use: await asyncio.sleep(1)
```

---

## Async Context Managers

### Async Context Manager Implementation

```python
# ✅ CORRECT - Async context manager
from contextlib import asynccontextmanager

class AsyncDatabaseConnection:
    """Async database connection with context manager."""

    def __init__(self, connection_string: str) -> None:
        self.connection_string = connection_string
        self._connection = None

    async def __aenter__(self) -> "AsyncDatabaseConnection":
        """Connect when entering context."""
        self._connection = await self._connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Close connection when exiting context."""
        await self._connection.close()

    async def _connect(self) -> Any:
        """Create connection."""
        await asyncio.sleep(0.1)
        return MockConnection()

    async def execute(self, query: str) -> list[dict]:
        """Execute query."""
        await asyncio.sleep(0.1)
        return [{"result": "data"}]


# Usage
async def query_database() -> None:
    """Process async stream."""
    async with AsyncDatabaseConnection("postgresql://...") as db:
        results = await db.execute("SELECT * FROM users")
        print(results)
```

### Using asynccontextmanager Decorator

```python
@asynccontextmanager
async def async_lock(lock: asyncio.Lock):
    """Async lock context manager."""
    await lock.acquire()
    try:
        yield
    finally:
        lock.release()


async def critical_section():
    """Process with lock."""
    lock = asyncio.Lock()
    async with async_lock(lock):
        # Critical section
        await do_something()
```

### ❌ INCORRECT - Forgetting to close

```python
# ❌ WRONG - Forgetting to close connection
async def query_database():
    db = AsyncDatabaseConnection("...")
    await db._connect()
    results = await db.execute("SELECT * FROM users")
    # Connection never closed!


# ❌ WRONG - Using sync context manager with async
async def process():
    with AsyncDatabaseConnection(...) as db:  # Wrong! Use async with
        await db.execute("SELECT *")
```

---

## Async Iterators and Generators

### Async Iterator

```python
# ✅ CORRECT - Async iterator
from typing import AsyncIterator, AsyncGenerator

class AsyncDataStreamer:
    """Async data streamer."""

    def __init__(self, data_source: str) -> None:
        self.data_source = data_source

    def __aiter__(self) -> AsyncIterator[dict]:
        """Return async iterator."""
        return self._stream_data()

    async def _stream_data(self) -> AsyncGenerator[dict, None]:
        """Yield data chunks asynchronously."""
        for i in range(10):
            await asyncio.sleep(0.1)
            yield {"chunk": i, "data": f"sample-{i}"}


async def process_stream() -> None:
    """Process async stream."""
    streamer = AsyncDataStreamer("data://source")

    async for chunk in streamer:
        print(f"Processing: {chunk}")
```

### Async Generator Function

```python
# ✅ CORRECT - Async generator
async def fetch_pages(url: str, max_pages: int = 5) -> AsyncGenerator[dict, None]:
    """Fetch multiple pages asynchronously."""
    for page in range(1, max_pages + 1):
        await asyncio.sleep(0.1)
        yield {"page": page, "url": url, "data": f"content-{page}"}


async def consume_pages() -> None:
    """Consume pages from async generator."""
    async for page in fetch_pages("https://api.example.com"):
        print(page)
```

### Async Comprehension

```python
# ✅ CORRECT - Async comprehension
async def process_items() -> list[int]:
    """Process items with async comprehension."""
    results = [await process_item(i) async for i in async_range(10)]
    return results


async def async_range(n: int) -> AsyncIterator[int]:
    """Async range generator."""
    for i in range(n):
        await asyncio.sleep(0)
        yield i
```

### ❌ INCORRECT - Using sync iteration with async

```python
# ❌ WRONG - Using sync iteration with async
async def process():
    streamer = AsyncDataStreamer("...")
    for chunk in streamer:  # Wrong! Use async for
        print(chunk)
```

---

## Concurrent Execution Patterns

### Wait for First Completion

```python
# ✅ CORRECT - Wait for first coroutine to complete
async def wait_first(
    *coros: Awaitable[Any],
) -> tuple[Any, set[asyncio.Task]]:
    """Wait for first coroutine to complete."""
    done, pending = await asyncio.wait(
        coros,
        return_when=asyncio.FIRST_COMPLETED,
    )
    return done.pop(), pending


# Usage
task1 = asyncio.create_task(fetch_data("url1"))
task2 = asyncio.create_task(fetch_data("url2"))

result, pending = await wait_first(task1, task2)

# Cancel remaining tasks
for task in pending:
    task.cancel()
```

### Wait with Timeout

```python
# ✅ CORRECT - Execute coroutine with timeout
async def fetch_with_timeout(
    coro: Awaitable[Any],
    timeout: float,
) -> Any:
    """Execute coroutine with timeout."""
    try:
        async with asyncio.timeout(timeout):
            return await coro
    except asyncio.TimeoutError:
        raise TimeoutError(f"Operation timed out after {timeout}s")
```

### Retry with Exponential Backoff

```python
# ✅ CORRECT - Retry async function with exponential backoff
async def fetch_with_retry(
    func: Callable[[], Awaitable[Any]],
    max_retries: int = 3,
    delay: float = 1.0,
) -> Any:
    """Retry async function with exponential backoff."""
    last_exception = None

    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                await asyncio.sleep(delay * (2 ** attempt))

    raise last_exception  # type: ignore
```

### Bounded Concurrency

```python
# ✅ CORRECT - Process items with concurrency limit
async def process_with_concurrency_limit(
    items: list[T],
    func: Callable[[T], Awaitable[Any]],
    concurrency: int = 10,
) -> list[Any]:
    """Process items with concurrency limit."""
    semaphore = asyncio.Semaphore(concurrency)

    async def bounded_func(item: T) -> Any:
        async with semaphore:
            return await func(item)

    tasks = [bounded_func(item) for item in items]
    return await asyncio.gather(*tasks)
```

---

## Async Classes

### Async Cache

```python
# ✅ CORRECT - Async cache implementation
class AsyncCache:
    """Async cache implementation."""

    def __init__(self, ttl: float = 3600) -> None:
        self._cache: dict[str, tuple[Any, float]] = {}
        self._lock = asyncio.Lock()
        self._ttl = ttl

    async def get(self, key: str) -> Any | None:
        """Get value from cache."""
        async with self._lock:
            if key not in self._cache:
                return None

            value, timestamp = self._cache[key]
            if time.time() - timestamp > self._ttl:
                del self._cache[key]
                return None

            return value

    async def set(self, key: str, value: Any) -> None:
        """Set value in cache."""
        async with self._lock:
            self._cache[key] = (value, time.time())

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
```

### Async Queue Processor

```python
# ✅ CORRECT - Async queue processor
class AsyncQueueProcessor:
    """Process items from async queue."""

    def __init__(self, maxsize: int = 0) -> None:
        self._queue: asyncio.Queue[Any] = asyncio.Queue(maxsize)
        self._workers: list[asyncio.Task] = []
        self._running = False

    async def put(self, item: Any) -> None:
        """Add item to queue."""
        await self._queue.put(item)

    async def start(self, num_workers: int = 3) -> None:
        """Start worker tasks."""
        self._running = True
        for i in range(num_workers):
            task = asyncio.create_task(self._worker(f"worker-{i}"))
            self._workers.append(task)

    async def stop(self) -> None:
        """Stop all workers."""
        self._running = False
        for _ in self._workers:
            await self._queue.put(None)  # Sentinel
        await asyncio.gather(*self._workers)

    async def _worker(self, name: str) -> None:
        """Worker coroutine."""
        while self._running:
            item = await self._queue.get()
            if item is None:  # Sentinel
                break
            try:
                await self._process_item(item)
            finally:
                self._queue.task_done()

    async def _process_item(self, item: Any) -> None:
        """Process single item."""
        await asyncio.sleep(0.1)
        print(f"Processed: {item}")
```

---

## Sync to Async Bridge

### Running Blocking Code in Executor

```python
# ✅ CORRECT - Run blocking function in thread pool
async def run_in_executor(
    func: Callable,
    *args: Any,
) -> Any:
    """Run blocking function in thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args)


# Usage
def blocking_io_operation(filename: str) -> str:
    """Blocking I/O operation."""
    with open(filename) as f:
        return f.read()


async def read_file_async(filename: str) -> str:
    """Read file asynchronously (wraps blocking I/O)."""
    return await run_in_executor(blocking_io_operation, filename)
```

### Running CPU-Bound Code

```python
# ✅ CORRECT - Run CPU-bound function in process pool
async def run_cpu_bound(func: Callable, *args: Any) -> Any:
    """Run CPU-bound function in process pool."""
    loop = asyncio.get_event_loop()
    with concurrent.futures.ProcessPoolExecutor() as pool:
        return await loop.run_in_executor(pool, functools.partial(func, *args))


def cpu_bound_calculation(n: int) -> int:
    """CPU-bound calculation."""
    return sum(i ** 2 for i in range(n))


async def calculate_async(n: int) -> int:
    """Calculate asynchronously."""
    return await run_cpu_bound(cpu_bound_calculation, n)
```

### ❌ INCORRECT - Blocking in async

```python
# ❌ WRONG - Running blocking code in async function
async def bad_example():
    # This blocks the event loop!
    time.sleep(1)
    # Use: await asyncio.sleep(1)

    # This also blocks!
    result = expensive_calculation()
    # Use: await run_in_executor(expensive_calculation)
```

---

## Error Handling in Async

### Safe Gather

```python
# ✅ CORRECT - Gather continuing on exceptions
async def safe_gather(*coros: Awaitable[Any]) -> list[Any]:
    """Gather coroutines, continuing on exceptions."""
    results = []

    for coro in coros:
        try:
            result = await coro
            results.append(result)
        except Exception as e:
            logger.error(f"Task failed: {e}")
            results.append(None)

    return results
```

### Wait with Exceptions Collection

```python
# ✅ CORRECT - Wait collecting successes and failures
async def wait_with_exceptions(
    *coros: Awaitable[Any],
) -> tuple[list[Any], list[Exception]]:
    """Wait for all coroutines, collecting successes and failures."""
    results: list[Any] = []
    exceptions: list[Exception] = []

    tasks = [asyncio.create_task(c) for c in coros]

    for task in asyncio.as_completed(tasks):
        try:
            result = await task
            results.append(result)
        except Exception as e:
            exceptions.append(e)

    return results, exceptions
```

---

## Testing Async Code

### Basic Async Tests

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    """Test async function."""
    result = await fetch_data("https://api.example.com")
    assert result["url"] == "https://api.example.com"


@pytest.mark.asyncio
async def test_async_context_manager():
    """Test async context manager."""
    async with AsyncDatabaseConnection("test://") as db:
        results = await db.execute("SELECT 1")
        assert len(results) == 1


@pytest.mark.asyncio
async def test_async_iterator():
    """Test async iterator."""
    items = []
    async for item in AsyncDataStreamer("test://"):
        items.append(item)
    assert len(items) == 10
```

### Concurrent Execution Tests

```python
@pytest.mark.asyncio
async def test_concurrent_execution():
    """Test concurrent execution."""
    results = await asyncio.gather(
        fetch_data("url1"),
        fetch_data("url2"),
        fetch_data("url3"),
    )
    assert len(results) == 3
```

### Async Fixtures

```python
@pytest.fixture
async def async_client():
    """Async fixture."""
    client = AsyncClient()
    await client.connect()
    yield client
    await client.disconnect()


@pytest.mark.asyncio
async def test_with_fixture(async_client):
    """Test using async fixture."""
    result = await async_client.fetch("/")
    assert result.status == 200
```

---

## Async Checklist

- [ ] Use `async def` for async functions
- [ ] `await` all async calls
- [ ] Use `async with` for async context managers
- [ ] Use `async for` for async iterators
- [ ] Don't use blocking calls in async functions
- [ ] Use `asyncio.sleep()` instead of `time.sleep()`
- [ ] Run blocking I/O in executor
- [ ] Set timeouts for external async calls
- [ ] Handle `asyncio.TimeoutError`
- [ ] Cancel tasks properly on cleanup
- [ ] Use `asyncio.gather()` for concurrent execution
- [ ] Use `asyncio.Queue` for producer/consumer patterns
- [ ] Test async code with `@pytest.mark.asyncio`
- [ ] Use async fixtures for async test setup
