# Quick Start Guide: Correlation ID Logging

## Overview

The correlation ID logging utilities provide an easy way to add structured logging with automatic request tracking to your API endpoints. All logs automatically include the correlation ID for complete request tracing.

## Installation

No installation required - the utilities are already in `app/api/logging_utils.py` and integrate with the existing correlation ID middleware.

## Basic Usage

### 1. Import the utilities

```python
from app.api.logging_utils import log_info, log_error, log_warning
```

### 2. Add Request parameter to your endpoint

```python
from fastapi import APIRouter, Request

@router.post("/my-endpoint")
async def my_endpoint(request: Request, data: MyRequestModel):
    # Your code here
    pass
```

### 3. Log with correlation ID

```python
@router.post("/my-endpoint")
async def my_endpoint(request: Request, data: MyRequestModel):
    # Log endpoint entry
    log_info(request, "Processing request", user_id=data.user_id)

    try:
        result = await process_data(data)
        log_info(request, "Request completed successfully", result_id=result.id)
        return result
    except Exception as e:
        log_error(request, "Request failed", exception=e)
        raise
```

## Available Functions

### `log_info(request, message, **kwargs)`
Log informational messages with correlation ID.

```python
log_info(
    request,
    "User logged in",
    user_id="12345",
    login_method="oauth",
)
```

### `log_warning(request, message, **kwargs)`
Log warning messages with correlation ID.

```python
log_warning(
    request,
    "Rate limit approaching",
    current_usage=95,
    limit=100,
)
```

### `log_error(request, message, exception=None, **kwargs)`
Log error messages with optional exception details.

```python
try:
    await risky_operation()
except ValueError as e:
    log_error(
        request,
        "Validation failed",
        exception=e,
        error_category="validation",
    )
```

### `log_debug(request, message, **kwargs)`
Log debug messages with correlation ID.

```python
log_debug(
    request,
    "Processing details",
    item_count=len(items),
    processing_time_ms=42,
)
```

### `log_with_context(request, message, level, **kwargs)`
Generic logging function with custom log level.

```python
log_with_context(
    request,
    "Custom log message",
    level="info",  # debug, info, warning, error, critical
    custom_field="custom_value",
    another_field=123,
)
```

### `get_correlation_id_from_request(request)`
Extract the correlation ID from the request.

```python
correlation_id = get_correlation_id_from_request(request)
# Returns correlation ID or "unknown" if not set
```

## Complete Example

```python
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from app.api.logging_utils import log_info, log_error, log_warning, log_debug

router = APIRouter(prefix="/orders", tags=["orders"])

class CreateOrderRequest(BaseModel):
    symbol: str
    quantity: int
    price: float

@router.post("/create")
async def create_order(request: Request, order_data: CreateOrderRequest):
    # Log endpoint entry
    log_info(
        request,
        "Order creation requested",
        symbol=order_data.symbol,
        quantity=order_data.quantity,
    )

    # Debug logging for detailed tracking
    log_debug(
        request,
        "Validating order data",
        price=order_data.price,
        order_type="market",
    )

    try:
        # Validate order
        if order_data.quantity <= 0:
            log_warning(
                request,
                "Invalid quantity detected",
                quantity=order_data.quantity,
                severity="low",
            )
            raise HTTPException(status_code=400, detail="Quantity must be positive")

        # Process order
        order = await order_service.create(order_data)

        # Log success
        log_info(
            request,
            "Order created successfully",
            order_id=order.id,
            status=order.status,
        )

        return order

    except Exception as e:
        # Log error with exception details
        log_error(
            request,
            "Order creation failed",
            exception=e,
            symbol=order_data.symbol,
            quantity=order_data.quantity,
        )
        raise HTTPException(status_code=500, detail="Failed to create order")
```

## How It Works

1. **Middleware**: The `AuditMiddleware` in `app/api/__init__.py` automatically generates or extracts a correlation ID from the `X-Correlation-ID` header

2. **Storage**: The correlation ID is stored in `request.state.correlation_id`

3. **Logging**: When you call any logging utility, it automatically:
   - Extracts the correlation ID from the request
   - Adds it to the log entry's extra context
   - Includes any additional context you provide via kwargs

4. **Tracing**: All logs with the same correlation ID can be traced together in your log aggregation system

## Best Practices

### ✅ DO:
- Log endpoint entry with key parameters
- Log successful completion with result IDs
- Log errors with exception details
- Use appropriate log levels (debug, info, warning, error)
- Include relevant context via kwargs
- Use descriptive messages

### ❌ DON'T:
- Log sensitive data (passwords, tokens, etc.)
- Use logging for control flow
- Log at debug level in production for critical events
- Include large objects in logs (use summaries instead)
- Forget to log errors before re-raising exceptions

## Log Levels

| Level | Usage | Example |
|-------|-------|---------|
| **DEBUG** | Detailed diagnostic information | "Processing item 5 of 100" |
| **INFO** | Normal operational information | "User logged in successfully" |
| **WARNING** | Something unexpected but not critical | "Rate limit at 90%" |
| **ERROR** | Error that doesn't stop execution | "Failed to send email notification" |
| **CRITICAL** | Serious error that may stop execution | "Database connection lost" |

## Correlation ID in Logs

All log entries automatically include:
```
{
    "message": "Your log message",
    "correlation_id": "abc-123-def-456",
    "level": "info",
    "timestamp": "2026-02-03T20:00:00Z",
    # Plus any additional kwargs you provide
}
```

This enables you to:
- Trace a single request across multiple services
- Debug issues by finding all logs for a specific request
- Analyze request patterns and performance
- Monitor error rates per request

## Testing

The logging utilities are fully tested. Run tests with:

```bash
python -m pytest tests/api/test_logging_utils.py -v
```

All 12 tests should pass.

## Need Help?

- **Examples**: See `app/api/logging_utils_examples.py` for comprehensive examples
- **Tests**: See `tests/api/test_logging_utils.py` for usage patterns
- **Summary**: See `.requirements/app/API-007_FIX_SUMMARY.md` for implementation details

## Integration with Existing Code

The utilities work with existing infrastructure:

- ✅ Works with `AuditMiddleware` in `app/api/__init__.py`
- ✅ Compatible with existing `get_correlation_id()` function
- ✅ Integrates with `AuditLogger` for audit trails
- ✅ No changes needed to middleware or configuration

Just import and use!
