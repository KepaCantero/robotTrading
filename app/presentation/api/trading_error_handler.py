"""
Trading Error Handler API
TASK-14: Unificación de Error Handling

API endpoints para gestionar el manejo unificado de errores del trading.

GAP Fixes:
- API-002: Added structured logging with correlation IDs
- API-004: TODO: Test coverage requires creating test files
- API-005: FIXED - Added security decorators (rate_limit, require_auth, audit_log)
"""

import logging
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from requests.exceptions import HTTPError, RequestException

from app.services.trading_error_handler import (
    ErrorAction,
    ErrorContext,
    get_error_statistics,
    handle_trading_error,
    reset_circuit_breaker,
    trading_error_handler,
)
from app.shared.exceptions.trading_exceptions import ErrorCategory

from . import audit_logger, get_correlation_id
from .security import audit_log, rate_limit, require_auth

router = APIRouter()
logger = logging.getLogger(__name__)


class ErrorHandlingRequest(BaseModel):
    """Request model for error handling."""

    error_message: str = Field(..., description="Error message")
    error_type: str = Field(..., description="Type of error")
    context: ErrorContext = Field(..., description="Context where error occurred")
    operation_id: Optional[str] = Field(None, description="Operation identifier")
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Additional metadata"
    )


class ErrorHandlingResponse(BaseModel):
    """Response model for error handling."""

    operation_id: str = Field(..., description="Operation identifier")
    context: str = Field(..., description="Error context")
    error: Dict[str, Any] = Field(..., description="Error details")
    actions_taken: Dict[str, Any] = Field(..., description="Actions taken")
    timestamp: str = Field(..., description="Timestamp of error handling")


class CircuitBreakerStatus(BaseModel):
    """Circuit breaker status model."""

    context: str = Field(..., description="Context name")
    is_open: bool = Field(..., description="Whether circuit breaker is open")
    error_count: int = Field(..., description="Current error count")
    last_error_time: Optional[str] = Field(None, description="Last error timestamp")


class ErrorStatistics(BaseModel):
    """Error statistics model."""

    error_counts: Dict[str, int] = Field(..., description="Error counts by context and category")
    circuit_breakers: Dict[str, bool] = Field(..., description="Circuit breaker statuses")
    last_error_times: Dict[str, str] = Field(..., description="Last error times")
    retry_counts: Dict[str, int] = Field(..., description="Retry counts")
    timestamp: str = Field(..., description="Statistics timestamp")


class CircuitBreakerResetRequest(BaseModel):
    """Request model for circuit breaker reset."""

    context: ErrorContext = Field(..., description="Context to reset")


@router.post(
    "/handle-error",
    response_model=ErrorHandlingResponse,
    status_code=status.HTTP_200_OK,
)
async def handle_error_endpoint(
    request: ErrorHandlingRequest,
    http_request: Request,
):
    """
    Handle a trading error with unified processing.

    This endpoint processes errors according to configured rules and takes
    appropriate actions (retry, circuit breaker, alerts, etc.).
    """
    correlation_id = get_correlation_id()
    logger.info(
        "Handling trading error",
        extra={
            "correlation_id": correlation_id,
            "error_message": request.error_message,
            "error_type": request.error_type,
            "context": request.context.value,
        },
    )
    try:
        # Create a mock error for demonstration
        # In real implementation, this would be the actual error
        class MockError(Exception):
            def __init__(self, message: str):
                self.message = message
                super().__init__(message)

        error = MockError(request.error_message)

        # Handle the error
        result = await handle_trading_error(
            error=error,
            context=request.context,
            operation_id=request.operation_id,
            metadata=request.metadata,
        )

        audit_logger.log_action(
            action="error_handled",
            method=http_request.method,
            path=http_request.url.path,
            details={
                "error_type": request.error_type,
                "context": request.context.value,
                "operation_id": request.operation_id,
            },
        )

        return ErrorHandlingResponse(**result)

    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error(
            f"Error in handle_error_endpoint: {e}",
            extra={
                "correlation_id": correlation_id,
                "error_type": type(e).__name__,
                "error": str(e),
                "stack_trace": traceback.format_exc(),
            },
        )
        audit_logger.log_error(
            method=http_request.method,
            path=http_request.url.path,
            error_type=type(e).__name__,
            error_message=str(e),
            stack_trace=traceback.format_exc(),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to handle error: {str(e)}",
        )


@router.get("/statistics", response_model=ErrorStatistics, status_code=status.HTTP_200_OK)
async def get_error_statistics_endpoint():
    """
    Get current error statistics and monitoring data.

    Returns comprehensive statistics about error occurrences,
    circuit breaker statuses, and retry counts.
    """
    try:
        stats = get_error_statistics()
        return ErrorStatistics(**stats)

    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error(f"Error in get_error_statistics_endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get error statistics: {str(e)}",
        )


@router.get(
    "/circuit-breakers",
    response_model=List[CircuitBreakerStatus],
    status_code=status.HTTP_200_OK,
)
async def get_circuit_breaker_status_endpoint():
    """
    Get status of all circuit breakers.

    Returns the current status of circuit breakers for all contexts.
    """
    try:
        stats = get_error_statistics()
        circuit_breakers = stats["circuit_breakers"]
        error_counts = stats["error_counts"]
        last_error_times = stats["last_error_times"]

        statuses = []
        for context_name, is_open in circuit_breakers.items():
            # Extract context from key (format: "context_name_circuit_breaker")
            context = context_name.replace("_circuit_breaker", "")

            # Get error count for this context
            error_key = f"{context}_{ErrorCategory.SYSTEM.value}"
            error_count = error_counts.get(error_key, 0)

            # Get last error time
            last_error_time = last_error_times.get(error_key)

            statuses.append(
                CircuitBreakerStatus(
                    context=context,
                    is_open=is_open,
                    error_count=error_count,
                    last_error_time=last_error_time,
                )
            )

        return statuses

    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error(f"Error in get_circuit_breaker_status_endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get circuit breaker status: {str(e)}",
        )


@router.post("/circuit-breakers/reset", status_code=status.HTTP_200_OK)
@rate_limit(max_requests=10, window_seconds=60)
@require_auth(roles=["admin"])
@audit_log("circuit_breaker_reset", log_args=True)
async def reset_circuit_breaker_endpoint(request: CircuitBreakerResetRequest):
    """
    Reset a circuit breaker for a specific context.

    This will close the circuit breaker and reset error counts for the context.
    """
    try:
        reset_circuit_breaker(request.context)

        return {
            "message": f"Circuit breaker reset for {request.context.value}",
            "context": request.context.value,
            "timestamp": datetime.now().isoformat(),
        }

    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error(f"Error in reset_circuit_breaker_endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset circuit breaker: {str(e)}",
        )


@router.get("/contexts", status_code=status.HTTP_200_OK)
async def get_error_contexts_endpoint():
    """
    Get list of available error contexts.

    Returns all available error contexts that can be used for error handling.
    """
    try:
        contexts = [
            {
                "name": context.value,
                "description": f"Error context for {context.value.replace('_', ' ')}",
            }
            for context in ErrorContext
        ]

        return {"contexts": contexts, "count": len(contexts)}

    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error(f"Error in get_error_contexts_endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get error contexts: {str(e)}",
        )


@router.get("/actions", status_code=status.HTTP_200_OK)
async def get_error_actions_endpoint():
    """
    Get list of available error actions.

    Returns all available error actions that can be taken when errors occur.
    """
    try:
        actions = [
            {
                "name": action.value,
                "description": f"Error action: {action.value.replace('_', ' ')}",
            }
            for action in ErrorAction
        ]

        return {"actions": actions, "count": len(actions)}

    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error(f"Error in get_error_actions_endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get error actions: {str(e)}",
        )


@router.get("/rules/{context}", status_code=status.HTTP_200_OK)
async def get_error_rules_endpoint(context: ErrorContext):
    """
    Get error handling rules for a specific context.

    Returns the configured error handling rules for the specified context.
    """
    try:
        rules = trading_error_handler.error_rules.get(context.value, {})

        return {
            "context": context.value,
            "rules": rules,
            "timestamp": datetime.now().isoformat(),
        }

    except (ValueError, TypeError, KeyError, AttributeError) as e:
        logger.error(f"Error in get_error_rules_endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get error rules: {str(e)}",
        )


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check_endpoint():
    """
    Health check for the error handling system.

    Returns the health status of the error handling system.
    """
    try:
        stats = get_error_statistics()

        # Check if any circuit breakers are open
        open_circuit_breakers = [
            context for context, is_open in stats["circuit_breakers"].items() if is_open
        ]

        # Determine health status
        if open_circuit_breakers:
            health_status = "degraded"
            message = f"Circuit breakers open: {', '.join(open_circuit_breakers)}"
        else:
            health_status = "healthy"
            message = "All systems operational"

        return {
            "status": health_status,
            "message": message,
            "open_circuit_breakers": open_circuit_breakers,
            "total_errors": sum(stats["error_counts"].values()),
            "timestamp": datetime.now().isoformat(),
        }

    except (ConnectionError, TimeoutError, HTTPError, RequestException) as e:
        logger.error(f"Error in health_check_endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}",
        )
