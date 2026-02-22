"""
Example: How to use correlation ID logging utilities in API endpoints.

This file demonstrates the proper usage of the logging utilities for request tracking.
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.presentation.api.logging_utils import (
    get_correlation_id_from_request,
    log_debug,
    log_error,
    log_info,
    log_warning,
    log_with_context,
)

router = APIRouter(prefix="/example", tags=["logging-examples"])


class ExampleRequest(BaseModel):
    """Example request model."""

    data: str


class ExampleResponse(BaseModel):
    """Example response model."""

    message: str
    correlation_id: str


@router.post("/endpoint", response_model=ExampleResponse)
async def example_endpoint(request: Request, body: ExampleRequest) -> ExampleResponse:
    """
    Example endpoint demonstrating correlation ID logging.

    This endpoint shows how to use the logging utilities throughout
    the request lifecycle for proper request tracking.
    """
    # Log endpoint entry with correlation ID
    log_info(
        request,
        "Example endpoint called",
        endpoint="/example/endpoint",
        method=request.method,
        data_length=len(body.data),
    )

    correlation_id = get_correlation_id_from_request(request)

    try:
        # Log processing steps
        log_debug(request, "Processing request data", input_data=body.data)

        # Simulate some processing
        result = f"Processed: {body.data}"

        # Log successful completion
        log_info(
            request,
            "Request processed successfully",
            result_length=len(result),
        )

        return ExampleResponse(
            message=result,
            correlation_id=correlation_id,
        )

    except ValueError as e:
        # Log error with exception details
        log_error(
            request,
            "Failed to process request",
            exception=e,
            input_data=body.data,
        )
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        # Log unexpected errors
        log_error(
            request,
            "Unexpected error occurred",
            exception=e,
            error_type=type(e).__name__,
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/warnings")
async def example_with_warnings(request: Request) -> dict:
    """Example endpoint showing warning level logging."""
    log_info(request, "Warnings endpoint called")

    # Simulate a condition that should trigger a warning
    some_condition = True

    if some_condition:
        log_warning(
            request,
            "Warning condition detected",
            warning_code="WARN_001",
            condition_value="threshold_exceeded",
        )

    return {"status": "ok", "warnings_logged": 1}


@router.post("/custom-levels")
async def example_with_custom_levels(request: Request, body: ExampleRequest) -> dict:
    """Example endpoint showing custom log levels."""
    # Use log_with_context for custom level specification
    log_with_context(
        request,
        "Custom level logging example",
        level="info",
        custom_field="custom_value",
        request_data=body.data,
    )

    return {"status": "logged"}


@router.get("/multiple-steps")
async def example_multiple_steps(request: Request) -> dict:
    """Example endpoint showing logging at multiple processing steps."""
    # Step 1: Initialization
    log_info(request, "Step 1: Initializing", step="initialization")

    # Step 2: Validation
    log_debug(request, "Step 2: Validating input", step="validation")
    # ... validation logic ...

    # Step 3: Processing
    log_info(request, "Step 3: Processing data", step="processing")
    # ... processing logic ...

    # Step 4: Completion
    log_info(request, "Step 4: Completed", step="completion")

    return {
        "status": "completed",
        "steps": ["initialization", "validation", "processing", "completion"],
    }


@router.post("/error-scenarios")
async def example_error_scenarios(request: Request, body: ExampleRequest) -> dict:
    """Example endpoint showing error logging with different scenarios."""
    log_info(request, "Error scenarios endpoint called", input_data=body.data)

    try:
        # Simulate different error scenarios
        if body.data == "error":
            raise ValueError("Simulated value error")

        if body.data == "critical":
            raise RuntimeError("Simulated critical error")

        log_with_context(
            request,
            "Request processed without errors",
            level="info",
            result="success",
        )

        return {"status": "success"}

    except ValueError as e:
        # Log business logic errors
        log_error(
            request,
            "Business logic error occurred",
            exception=e,
            error_category="validation",
            severity="low",
        )
        raise HTTPException(status_code=400, detail=str(e))

    except RuntimeError as e:
        # Log critical errors
        log_error(
            request,
            "Critical error occurred",
            exception=e,
            error_category="system",
            severity="critical",
            requires_immediate_attention=True,
        )
        raise HTTPException(status_code=500, detail="Critical system error")

    except Exception as e:
        # Log unexpected errors
        log_error(
            request,
            "Unexpected error type occurred",
            exception=e,
            error_category="unknown",
            severity="high",
        )
        raise HTTPException(status_code=500, detail="Unexpected error")


# ============================================================================
# Integration with existing correlation ID middleware
# ============================================================================

"""
The logging utilities work seamlessly with the existing correlation ID middleware
in app/api/__init__.py. The correlation ID is automatically:

1. Generated or extracted from the X-Correlation-ID header by AuditMiddleware
2. Stored in request.state.correlation_id
3. Available through get_correlation_id_from_request()
4. Included in all logs via the logging utilities

Usage in production endpoints:

```python
from fastapi import APIRouter, Request
from app.presentation.api.logging_utils import log_info, log_error

@router.post("/trade")
async def execute_trade(request: Request, trade_data: TradeRequest):
    log_info(request, "Trade execution started", symbol=trade_data.symbol)

    try:
        result = await trade_service.execute(trade_data)
        log_info(request, "Trade executed successfully", trade_id=result.id)
        return result
    except Exception as e:
        log_error(request, "Trade execution failed", exception=e)
        raise
```

This ensures all logs include the correlation ID for complete request tracing.
"""
