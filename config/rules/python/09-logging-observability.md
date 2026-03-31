# Logging and Observability

Structured logging, metrics, tracing, and monitoring for Python applications.

## Structured Logging with `structlog`

### ✅ CORRECT

```python
import structlog
from typing import Any

# Configure structlog
structlog.configure(
    processors=[
        # Add context information
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        # Exception handling
        structlog.processors.format_exc_info,
        # JSON output for production
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

# Get logger
log = structlog.get_logger()


def process_order(order_id: int, user_id: int) -> None:
    """Process order with structured logging."""
    log.info(
        "Processing order",
        order_id=order_id,
        user_id=user_id,
        action="process_order",
    )

    try:
        result = _execute_order(order_id)
        log.info(
            "Order processed successfully",
            order_id=order_id,
            result=result,
            status="success",
        )
    except ValidationError as e:
        log.error(
            "Order validation failed",
            order_id=order_id,
            error=str(e),
            error_type="ValidationError",
            status="failed",
        )
        raise
    except Exception as e:
        log.exception(
            "Unexpected error processing order",
            order_id=order_id,
            status="error",
        )
        raise


# Output (JSON):
# {"event": "Processing order", "order_id": 123, "user_id": 456, "action": "process_order", "timestamp": "2024-01-15T10:30:00Z", "level": "info", "logger": "__main__"}
```

### ❌ INCORRECT

```python
# Using print() - no structure, no levels
print(f"Processing order {order_id}")

# Using standard logging without context
import logging
logging.info(f"Processing order {order_id}")  # Hard to parse and query

# String formatting - can't parse fields
logging.info("Processing order %s for user %s", order_id, user_id)
```

## Log Levels

### ✅ CORRECT

```python
# Use appropriate log levels
log.debug(
    "Detailed diagnostic information",
    cache_key=key,
    cache_value=value,
    execution_time_ms=elapsed,
)  # Detailed info for debugging

log.info(
    "Application started",
    app_name=settings.app_name,
    version=settings.version,
    environment=settings.environment,
)  # Normal application flow

log.warning(
    "Cache miss rate high",
    cache_miss_rate=0.85,
    threshold=0.5,
)  # Something concerning but not an error

log.error(
    "Failed to connect to database",
    host=db_host,
    port=db_port,
    error=str(e),
)  # Error that prevents operation

log.critical(
    "System out of memory",
    available_memory_mb=100,
    required_memory_mb=1024,
)  # Critical system failure
```

### ❌ INCORRECT

```python
# Using wrong levels
log.error("User logged in", user_id=123)  # Should be info
log.info("Database connection failed", error=str(e))  # Should be error
log.debug("Starting application")  # Should be info
```

## Contextual Logging

### ✅ CORRECT

```python
from structlog import contextvars

# Bind context that applies to all logs in the request
def handle_request(request_id: str, user_id: int) -> None:
    # Bind context once
    contextvars.bind_contextvars(request_id=request_id, user_id=user_id)

    log.info("Handling request")  # Automatically includes request_id and user_id

    try:
        process_payment()
    except Exception:
        log.error("Payment failed")  # Still includes context
        raise

    finally:
        # Clear context when done
        contextvars.unbind_contextvars("request_id", "user_id")


# Nested context
def process_payment():
    contextvars.bind_contextvars(payment_method="credit_card")

    log.info("Processing payment")  # Includes request_id, user_id, payment_method

    validate_card()
    charge_card()

    contextvars.unbind_contextvars("payment_method")


# Using context manager
from contextlib import contextmanager

@contextmanager
def log_context(**kwargs):
    """Context manager for logging context."""
    contextvars.bind_contextvars(**kwargs)
    try:
        yield
    finally:
        for key in kwargs:
            contextvars.unbind_contextvars(key)


# Usage
with log_context(operation="batch_import", batch_id=123):
    for item in items:
        process_item(item)  # All logs include operation and batch_id
```

## Error Logging

### ✅ CORRECT

```python
# Log exceptions with full traceback
def risky_operation(data: dict) -> None:
    try:
        result = process_data(data)
    except ValueError as e:
        # Structured error logging
        log.error(
            "Invalid data provided",
            error_message=str(e),
            error_type=type(e).__name__,
            input_data=data,
            status="validation_failed",
        )
        raise
    except DatabaseError as e:
        # Log with stack trace
        log.exception(
            "Database error occurred",
            error_message=str(e),
            query=e.query,
            status="database_error",
        )
        raise


# Custom exception info
class OrderError(Exception):
    def __init__(self, order_id: int, message: str):
        self.order_id = order_id
        super().__init__(message)


def process_order(order: Order) -> None:
    try:
        execute_order(order)
    except OrderError as e:
        log.error(
            "Order processing failed",
            order_id=e.order_id,
            error_message=str(e),
            order_value=order.total,
        )
        raise
```

## Performance Logging

### ✅ CORRECT

```python
import time
from functools import wraps
from typing import Callable

def log_execution_time(log: structlog.BoundLogger) -> Callable:
    """Decorator to log function execution time."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            function = func.__name__

            try:
                result = await func(*args, **kwargs)
                elapsed_ms = (time.perf_counter() - start) * 1000

                log.info(
                    "Function executed",
                    function=function,
                    elapsed_ms=round(elapsed_ms, 2),
                    status="success",
                )
                return result

            except Exception as e:
                elapsed_ms = (time.perf_counter() - start) * 1000

                log.error(
                    "Function failed",
                    function=function,
                    elapsed_ms=round(elapsed_ms, 2),
                    error=str(e),
                    status="error",
                )
                raise

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            function = func.__name__

            try:
                result = func(*args, **kwargs)
                elapsed_ms = (time.perf_counter() - start) * 1000

                log.info(
                    "Function executed",
                    function=function,
                    elapsed_ms=round(elapsed_ms, 2),
                    status="success",
                )
                return result

            except Exception as e:
                elapsed_ms = (time.perf_counter() - start) * 1000

                log.error(
                    "Function failed",
                    function=function,
                    elapsed_ms=round(elapsed_ms, 2),
                    error=str(e),
                    status="error",
                )
                raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


# Usage
@log_execution_time(log)
async def fetch_user_data(user_id: int) -> dict:
    # Simulate slow operation
    await asyncio.sleep(0.5)
    return {"id": user_id, "name": "Alice"}
```

## Metrics

### ✅ CORRECT - Using Prometheus

```python
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time

# Define metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"],
)

active_connections = Gauge(
    "active_connections",
    "Number of active connections",
)

orders_processed_total = Counter(
    "orders_processed_total",
    "Total orders processed",
    ["status"],
)

order_processing_duration = Histogram(
    "order_processing_duration_seconds",
    "Order processing duration",
    ["order_type"],
)


# Instrument your code
def process_request(method: str, endpoint: str) -> None:
    start = time.time()

    try:
        # Handle request
        response = handle_request(method, endpoint)
        status = response.status_code

    except Exception as e:
        status = 500
        raise

    finally:
        # Record metrics
        duration = time.time() - start
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=status,
        ).inc()
        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint,
        ).observe(duration)


async def process_order(order: Order) -> None:
    start = time.time()

    try:
        await execute_order(order)
        status = "success"

    except ValidationError:
        status = "validation_failed"
        raise

    except Exception:
        status = "error"
        raise

    finally:
        duration = time.time() - start
        orders_processed_total.labels(status=status).inc()
        order_processing_duration.labels(
            order_type=order.type,
        ).observe(duration)


# Start metrics server
def start_metrics_server(port: int = 9090) -> None:
    """Start Prometheus metrics server."""
    start_http_server(port)
    log.info("Metrics server started", port=port)


# /metrics endpoint will expose metrics
# http_requests_total{method="GET",endpoint="/api/users",status="200"} 1234
# http_request_duration_seconds_bucket{method="GET",endpoint="/api/users",le="0.1"} 1000
```

## Distributed Tracing

### ✅ CORRECT - Using OpenTelemetry

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME

# Setup tracing
resource = Resource(attributes={SERVICE_NAME: "my-app"})

provider = TracerProvider(resource=resource)
jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831,
)
provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
trace.set_tracer_provider(provider)

tracer = trace.get_tracer(__name__)


# Instrument code
def process_order(order_id: int) -> None:
    with tracer.start_as_current_span("process_order") as span:
        span.set_attribute("order.id", order_id)
        span.set_attribute("order.type", "standard")

        try:
            validate_order(order_id)
            charge_payment(order_id)
            ship_order(order_id)

            span.set_attribute("order.status", "completed")

        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise


def validate_order(order_id: int) -> None:
    with tracer.start_as_current_span("validate_order"):
        # Validation logic
        time.sleep(0.01)


# Async tracing
async def async_process_order(order_id: int) -> None:
    with tracer.start_as_current_span("async_process_order") as span:
        span.set_attribute("order.id", order_id)

        await async_validate(order_id)
        await async_charge(order_id)
```

## Health Checks

### ✅ CORRECT

```python
from dataclasses import dataclass
from typing import Callable
from enum import Enum

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: str | None = None
    response_time_ms: float | None = None


class HealthChecker:
    """Health checker for application components."""

    def __init__(self) -> None:
        self._checks: dict[str, Callable] = {}

    def register(self, name: str, check: Callable) -> None:
        """Register a health check."""
        self._checks[name] = check

    async def check_all(self) -> dict[str, HealthCheckResult]:
        """Run all health checks."""
        results = {}

        for name, check in self._checks.items():
            start = time.perf_counter()
            try:
                await check()
                elapsed_ms = (time.perf_counter() - start) * 1000
                results[name] = HealthCheckResult(
                    name=name,
                    status=HealthStatus.HEALTHY,
                    response_time_ms=elapsed_ms,
                )
            except DegradedError as e:
                elapsed_ms = (time.perf_counter() - start) * 1000
                results[name] = HealthCheckResult(
                    name=name,
                    status=HealthStatus.DEGRADED,
                    message=str(e),
                    response_time_ms=elapsed_ms,
                )
            except Exception as e:
                elapsed_ms = (time.perf_counter() - start) * 1000
                results[name] = HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=str(e),
                    response_time_ms=elapsed_ms,
                )

        return results


# Usage
health_checker = HealthChecker()

async def check_database():
    """Check database connectivity."""
    if not await database.ping():
        raise Exception("Database not responding")

async def check_cache():
    """Check cache connectivity."""
    if not await cache.ping():
        raise DegradedError("Cache not responding")

async def check_external_api():
    """Check external API."""
    response = await http_client.get("https://api.example.com/health")
    if response.status_code != 200:
        raise Exception(f"API unhealthy: {response.status_code}")

health_checker.register("database", check_database)
health_checker.register("cache", check_cache)
health_checker.register("external_api", check_external_api)


# FastAPI endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    results = await health_checker.check_all()
    overall_status = _determine_overall_status(results)
    return {
        "status": overall_status,
        "checks": {
            name: {
                "status": result.status,
                "message": result.message,
                "response_time_ms": result.response_time_ms,
            }
            for name, result in results.items()
        },
        "timestamp": datetime.utcnow().isoformat(),
    }
```

## Logging Checklist

- [ ] Use structured logging (JSON format)
- [ ] Include context in all logs
- [ ] Use appropriate log levels
- [ ] Log at entry points and exit points
- [ ] Log errors with stack traces
- [ ] Include correlation IDs for request tracking
- [ ] Add timing information for operations
- [ ] Don't log sensitive data (passwords, tokens, PII)
- [ ] Use log aggregation (ELK, CloudWatch, etc.)
- [ ] Set up log retention policies
- [ ] Monitor log volume and errors
- [ ] Use metrics for quantitative monitoring
- [ ] Use tracing for request flow visualization
- [ ] Set up alerts on error rates and patterns
- [ ] Implement health check endpoints
