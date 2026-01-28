# Async Patterns

Python async/await patterns with `asyncio`, generators, and context managers.

## Basic Async/Await

### ✅ CORRECT

```python
import asyncio
from typing import Awaitable

async def fetch_data(url: str) -> dict[str, Any]:
    """Fetch data asynchronously."""
    await asyncio.sleep(1)  # Simulate I/O
    return {"url": url, "data": "sample"}


async def process_multiple_urls(urls: list[str]) -> list[dict[str, Any]]:
    """Process multiple URLs concurrently."""
    tasks = [fetch_data(url) for url in urls]
    results = await asyncio.gather(*tasks)
    return results


async def main() -> None:
    urls = ["https://api1.com", "https://api2.com", "https://api3.com"]
    results = await process_multiple_urls(urls)
    for result in results:
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
```

### ❌ INCORRECT

```python
# Mixing sync and async incorrectly
def fetch_data(url: str) -> dict[str, Any]:
    # This is sync but calls async code!
    return asyncio.run(fetch_data(url))  # Don't do this in async context

# Using blocking calls in async
async def process():
    time.sleep(1)  # Blocks the event loop!
    # Use: await asyncio.sleep(1)
```

## Async Context Managers

### ✅ CORRECT

```python
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
        # Connection logic
        await asyncio.sleep(0.1)
        return MockConnection()

    async def execute(self, query: str) -> list[dict]:
        """Execute query."""
        await asyncio.sleep(0.1)
        return [{"result": "data"}]


# Usage
async def query_database() -> None:
    async with AsyncDatabaseConnection("postgresql://...") as db:
        results = await db.execute("SELECT * FROM users")
        print(results)


# Using asynccontextmanager decorator
@asynccontextmanager
async def async_lock(lock: asyncio.Lock):
    """Async lock context manager."""
    await lock.acquire()
    try:
        yield
    finally:
        lock.release()


async def critical_section():
    lock = asyncio.Lock()
    async with async_lock(lock):
        # Critical section
        await do_something()
```

### ❌ INCORRECT

```python
# Forgetting to close connection
async def query_database():
    db = AsyncDatabaseConnection("...")
    await db._connect()
    results = await db.execute("SELECT * FROM users")
    # Connection never closed!


# Using sync context manager with async
async def process():
    with AsyncDatabaseConnection(...) as db:  # Wrong! Use async with
        await db.execute("SELECT *")
```

## Async Iterators and Generators

### ✅ CORRECT

```python
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


# Async generator function
async def fetch_pages(url: str, max_pages: int = 5) -> AsyncGenerator[dict, None]:
    """Fetch multiple pages asynchronously."""
    for page in range(1, max_pages + 1):
        await asyncio.sleep(0.1)
        yield {"page": page, "url": url, "data": f"content-{page}"}


async def consume_pages() -> None:
    """Consume pages from async generator."""
    async for page in fetch_pages("https://api.example.com"):
        print(page)


# Async comprehension
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

### ❌ INCORRECT

```python
# Using sync iteration with async
async def process():
    streamer = AsyncDataStreamer("...")
    for chunk in streamer:  # Wrong! Use async for
        print(chunk)


# Mixing sync and async generators
def mixed_generator():
    yield 1
    await asyncio.sleep(1)  # Syntax error!
```

## Concurrent Execution Patterns

### ✅ CORRECT

```python
import asyncio
from typing import Any

async def fetch_with_timeout(
    coro: Awaitable[Any],
    timeout: float,
) -> Any:
    """Execute coroutine with timeout."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        raise TimeoutError(f"Operation timed out after {timeout}s")


async def wait_first(
    *coros: Awaitable[Any],
) -> tuple[Any, set[asyncio.Task]]:
    """Wait for first coroutine to complete."""
    done, pending = await asyncio.wait(
        coros,
        return_when=asyncio.FIRST_COMPLETED,
    )
    return done.pop(), pending


async def wait_all(*coros: Awaitable[Any]) -> list[Any]:
    """Wait for all coroutines to complete."""
    return await asyncio.gather(*coros)


async def fetch_with_retry(
    func: Callable[..., Awaitable[Any]],
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


# Bounded concurrency
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

## Async Classes

### ✅ CORRECT

```python
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

## Sync to Async Bridge

### ✅ CORRECT

```python
import concurrent.futures
from functools import partial

async def run_in_executor(
    func: Callable,
    *args: Any,
) -> Any:
    """Run blocking function in thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, func, *args)


async def run_cpu_bound(func: Callable, *args: Any) -> Any:
    """Run CPU-bound function in process pool."""
    loop = asyncio.get_event_loop()
    with concurrent.futures.ProcessPoolExecutor() as pool:
        return await loop.run_in_executor(pool, partial(func, *args))


# Usage
def blocking_io_operation(filename: str) -> str:
    """Blocking I/O operation."""
    with open(filename) as f:
        return f.read()


async def read_file_async(filename: str) -> str:
    """Read file asynchronously (wraps blocking I/O)."""
    return await run_in_executor(blocking_io_operation, filename)


def cpu_bound_calculation(n: int) -> int:
    """CPU-bound calculation."""
    return sum(i ** 2 for i in range(n))


async def calculate_async(n: int) -> int:
    """Calculate asynchronously."""
    return await run_cpu_bound(cpu_bound_calculation, n)
```

### ❌ INCORRECT

```python
# Running blocking code in async function
async def bad_example():
    # This blocks the event loop!
    time.sleep(1)
    # Use: await asyncio.sleep(1)

    # This also blocks!
    result = expensive_calculation()
    # Use: await run_in_executor(expensive_calculation)
```

## Error Handling in Async

### ✅ CORRECT

```python
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


async def with_timeout_retry(
    coro: Callable[[], Awaitable[Any]],
    timeout: float = 5.0,
    max_retries: int = 3,
) -> Any:
    """Execute with timeout and retry."""
    last_error = None

    for attempt in range(max_retries):
        try:
            async with asyncio.timeout(timeout):
                return await coro()
        except (asyncio.TimeoutError, TimeoutError) as e:
            last_error = e
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
            continue

    raise last_error  # type: ignore
```

## Testing Async Code

### ✅ CORRECT

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


@pytest.mark.asyncio
async def test_concurrent_execution():
    """Test concurrent execution."""
    results = await asyncio.gather(
        fetch_data("url1"),
        fetch_data("url2"),
        fetch_data("url3"),
    )
    assert len(results) == 3


# Using pytest-asyncio fixtures
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

## Async Checklist

- [ ] Use `async def` for async functions, not `def`
- [ ] `await` all async calls (don't forget await!)
- [ ] Use `async with` for async context managers
- [ ] Use `async for` for async iterators
- [ ] Don't use blocking calls in async functions
- [ ] Use `asyncio.sleep()` instead of `time.sleep()`
- [ ] Run blocking I/O in executor with `run_in_executor`
- [ ] Set timeouts for external async calls
- [ ] Handle `asyncio.TimeoutError`
- [ ] Cancel tasks properly on cleanup
- [ ] Use `asyncio.gather()` for concurrent execution
- [ ] Use `asyncio.Queue` for producer/consumer patterns
- [ ] Test async code with `@pytest.mark.asyncio`
- [ ] Use async fixtures for async test setup
