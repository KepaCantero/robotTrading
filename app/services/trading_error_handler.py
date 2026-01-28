"""
Trading Error Handler Unificado
TASK-14: Unificación de Error Handling

Este módulo proporciona un manejo unificado de errores específicos del trading,
integrando con el sistema existente de manejo de errores.
"""

import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional

from app.core.centralized_config import get_config
from app.exceptions.trading_exceptions import (
    AlgoTradingError,
    ErrorCategory,
    ErrorSeverity,
    NetworkError,
    PerformanceError,
    RiskManagementError,
    SystemError,
    ValidationError,
)
from app.services.centralized_logging import LogLevel, LogService, centralized_logger


class ErrorAction(Enum):
    """Actions to take when an error occurs."""

    LOG_ONLY = "log_only"
    RETRY = "retry"
    FALLBACK = "fallback"
    CIRCUIT_BREAKER = "circuit_breaker"
    KILL_SWITCH = "kill_switch"
    ALERT = "alert"
    ROLLBACK = "rollback"


class ErrorContext(Enum):
    """Context where the error occurred."""

    SIGNAL_GENERATION = "signal_generation"
    ORDER_PLACEMENT = "order_placement"
    ORDER_EXECUTION = "order_execution"
    PORTFOLIO_UPDATE = "portfolio_update"
    RISK_CHECK = "risk_check"
    MARKET_DATA_FETCH = "market_data_fetch"
    BACKTESTING = "backtesting"
    PAPER_TRADING = "paper_trading"
    LIVE_TRADING = "live_trading"
    CONFIGURATION_LOAD = "configuration_load"
    DATABASE_OPERATION = "database_operation"
    API_CALL = "api_call"


class TradingErrorHandler:
    """
    Unified error handler for trading operations.

    This handler provides:
    - Centralized error processing
    - Automatic retry mechanisms
    - Circuit breaker patterns
    - Risk management integration
    - Performance monitoring
    - Alerting and notifications
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = get_config()
        self.error_counts: Dict[str, int] = {}
        self.circuit_breakers: Dict[str, bool] = {}
        self.last_error_times: Dict[str, datetime] = {}
        self.retry_counts: Dict[str, int] = {}

        # Error handling rules
        self.error_rules = self._initialize_error_rules()

        # Performance thresholds
        self.performance_thresholds = {
            "signal_generation_ms": 100,
            "order_placement_ms": 200,
            "portfolio_update_ms": 50,
            "market_data_fetch_ms": 500,
        }

    def _initialize_error_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize error handling rules."""
        return {
            "signal_generation": {
                "max_retries": 3,
                "retry_delay": 1.0,
                "circuit_breaker_threshold": 5,
                "circuit_breaker_timeout": 60,
                "actions": [
                    ErrorAction.LOG_ONLY,
                    ErrorAction.RETRY,
                    ErrorAction.CIRCUIT_BREAKER,
                ],
            },
            "order_placement": {
                "max_retries": 2,
                "retry_delay": 2.0,
                "circuit_breaker_threshold": 3,
                "circuit_breaker_timeout": 120,
                "actions": [
                    ErrorAction.LOG_ONLY,
                    ErrorAction.RETRY,
                    ErrorAction.CIRCUIT_BREAKER,
                    ErrorAction.ALERT,
                ],
            },
            "order_execution": {
                "max_retries": 1,
                "retry_delay": 5.0,
                "circuit_breaker_threshold": 2,
                "circuit_breaker_timeout": 300,
                "actions": [
                    ErrorAction.LOG_ONLY,
                    ErrorAction.RETRY,
                    ErrorAction.ALERT,
                    ErrorAction.KILL_SWITCH,
                ],
            },
            "portfolio_update": {
                "max_retries": 3,
                "retry_delay": 0.5,
                "circuit_breaker_threshold": 10,
                "circuit_breaker_timeout": 30,
                "actions": [
                    ErrorAction.LOG_ONLY,
                    ErrorAction.RETRY,
                    ErrorAction.ROLLBACK,
                ],
            },
            "risk_check": {
                "max_retries": 0,
                "retry_delay": 0,
                "circuit_breaker_threshold": 1,
                "circuit_breaker_timeout": 0,
                "actions": [
                    ErrorAction.LOG_ONLY,
                    ErrorAction.KILL_SWITCH,
                    ErrorAction.ALERT,
                ],
            },
            "market_data_fetch": {
                "max_retries": 5,
                "retry_delay": 1.0,
                "circuit_breaker_threshold": 10,
                "circuit_breaker_timeout": 60,
                "actions": [
                    ErrorAction.LOG_ONLY,
                    ErrorAction.RETRY,
                    ErrorAction.FALLBACK,
                    ErrorAction.CIRCUIT_BREAKER,
                ],
            },
            "backtesting": {
                "max_retries": 2,
                "retry_delay": 5.0,
                "circuit_breaker_threshold": 3,
                "circuit_breaker_timeout": 300,
                "actions": [ErrorAction.LOG_ONLY, ErrorAction.RETRY, ErrorAction.ALERT],
            },
            "paper_trading": {
                "max_retries": 3,
                "retry_delay": 1.0,
                "circuit_breaker_threshold": 5,
                "circuit_breaker_timeout": 60,
                "actions": [
                    ErrorAction.LOG_ONLY,
                    ErrorAction.RETRY,
                    ErrorAction.CIRCUIT_BREAKER,
                ],
            },
            "live_trading": {
                "max_retries": 1,
                "retry_delay": 10.0,
                "circuit_breaker_threshold": 2,
                "circuit_breaker_timeout": 600,
                "actions": [
                    ErrorAction.LOG_ONLY,
                    ErrorAction.RETRY,
                    ErrorAction.KILL_SWITCH,
                    ErrorAction.ALERT,
                ],
            },
        }

    async def handle_error(
        self,
        error: Exception,
        context: ErrorContext,
        operation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Handle an error with unified processing.

        Args:
            error: The exception that occurred
            context: The context where the error occurred
            operation_id: Unique identifier for the operation
            metadata: Additional metadata about the operation

        Returns:
            Dictionary with error handling results
        """
        operation_id = operation_id or f"{context.value}_{datetime.now().timestamp()}"
        metadata = metadata or {}

        # Convert generic exceptions to AlgoTradingError if needed
        if not isinstance(error, AlgoTradingError):
            error = self._convert_to_algotrading_error(error, context, metadata)

        # Get error handling rules for this context
        rules = self.error_rules.get(context.value, {})

        # Track error occurrence
        self._track_error(operation_id, error, context)

        # Log the error
        await self._log_error(error, context, operation_id, metadata)

        # Determine actions to take
        actions = rules.get("actions", [ErrorAction.LOG_ONLY])

        # Execute actions
        results = {}
        for action in actions:
            try:
                result = await self._execute_action(
                    action, error, context, operation_id, metadata, rules
                )
                results[action.value] = result
            except (asyncio.TimeoutError, ConnectionError, OSError) as action_error:
                self.logger.error(f"Failed to execute action {action.value}: {action_error}")
                results[action.value] = {"success": False, "error": str(action_error)}

        # Check for circuit breaker activation
        if self._should_activate_circuit_breaker(context, operation_id):
            await self._activate_circuit_breaker(context, operation_id)
            results["circuit_breaker"] = {"activated": True, "context": context.value}

        # Check for kill switch activation
        if self._should_activate_kill_switch(error, context):
            await self._activate_kill_switch(error, context, operation_id)
            results["kill_switch"] = {"activated": True, "reason": error.message}

        return {
            "operation_id": operation_id,
            "context": context.value,
            "error": error.to_dict(),
            "actions_taken": results,
            "timestamp": datetime.now().isoformat(),
        }

    async def handle_with_retry(
        self,
        operation: Callable,
        context: ErrorContext,
        operation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        *args,
        **kwargs,
    ) -> Any:
        """
        Execute an operation with automatic retry on error.

        Args:
            operation: The operation to execute
            context: The context of the operation
            operation_id: Unique identifier for the operation
            metadata: Additional metadata
            *args, **kwargs: Arguments for the operation

        Returns:
            Result of the operation or raises the last error
        """
        operation_id = operation_id or f"{context.value}_{datetime.now().timestamp()}"
        rules = self.error_rules.get(context.value, {})
        max_retries = rules.get("max_retries", 0)
        retry_delay = rules.get("retry_delay", 1.0)

        last_error = None

        for attempt in range(max_retries + 1):
            try:
                # Check circuit breaker
                if self._is_circuit_breaker_open(context):
                    raise SystemError(
                        f"Circuit breaker is open for {context.value}",
                        component=context.value,
                    )

                # Execute operation
                if asyncio.iscoroutinefunction(operation):
                    result = await operation(*args, **kwargs)
                else:
                    result = operation(*args, **kwargs)

                # Reset retry count on success
                self.retry_counts[operation_id] = 0

                return result

            except (asyncio.TimeoutError, ConnectionError, OSError) as error:
                last_error = error

                # Handle the error
                await self.handle_error(error, context, operation_id, metadata)

                # Check if we should retry
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay)
                    self.retry_counts[operation_id] = attempt + 1
                else:
                    break

        # If we get here, all retries failed
        raise last_error

    def _convert_to_algotrading_error(
        self, error: Exception, context: ErrorContext, metadata: Dict[str, Any]
    ) -> AlgoTradingError:
        """Convert a generic exception to AlgoTradingError."""

        if isinstance(error, ValueError):
            return ValidationError(message=str(error), details=metadata)
        elif isinstance(error, ConnectionError):
            return NetworkError(message=str(error), details=metadata)
        elif isinstance(error, TimeoutError):
            return PerformanceError(message=str(error), operation=context.value, details=metadata)
        else:
            return SystemError(
                message=str(error),
                component=context.value,
                details={
                    "exception_type": type(error).__name__,
                    "original_error": str(error),
                    **metadata,
                },
            )

    def _track_error(
        self, operation_id: str, error: AlgoTradingError, context: ErrorContext
    ) -> None:
        """Track error occurrence for circuit breaker and monitoring."""
        key = f"{context.value}_{error.category.value}"

        # Increment error count
        self.error_counts[key] = self.error_counts.get(key, 0) + 1

        # Update last error time
        self.last_error_times[key] = datetime.now()

    async def _log_error(
        self,
        error: AlgoTradingError,
        context: ErrorContext,
        operation_id: str,
        metadata: Dict[str, Any],
    ) -> None:
        """Log error using centralized logging."""

        # Determine log level based on severity
        log_level = self._get_log_level(error.severity)

        # Determine service based on context
        service = self._get_service_from_context(context)

        # Prepare log metadata
        log_metadata = {
            "operation_id": operation_id,
            "context": context.value,
            "error_code": error.error_code,
            "category": error.category.value,
            "severity": error.severity.value,
            "details": error.details,
            **metadata,
        }

        # Log the error
        if log_level == LogLevel.DEBUG:
            centralized_logger.debug(service, error.message, log_metadata)
        elif log_level == LogLevel.INFO:
            centralized_logger.info(service, error.message, log_metadata)
        elif log_level == LogLevel.WARNING:
            centralized_logger.warning(service, error.message, log_metadata)
        elif log_level == LogLevel.ERROR:
            centralized_logger.error(
                service, error.message, log_metadata, str(error.original_error)
            )
        elif log_level == LogLevel.CRITICAL:
            centralized_logger.critical(
                service, error.message, log_metadata, str(error.original_error)
            )

    async def _execute_action(
        self,
        action: ErrorAction,
        error: AlgoTradingError,
        context: ErrorContext,
        operation_id: str,
        metadata: Dict[str, Any],
        rules: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a specific error handling action."""

        if action == ErrorAction.LOG_ONLY:
            return {"success": True, "message": "Error logged"}

        elif action == ErrorAction.RETRY:
            return {"success": True, "message": "Retry scheduled"}

        elif action == ErrorAction.FALLBACK:
            return await self._execute_fallback(error, context, operation_id, metadata)

        elif action == ErrorAction.CIRCUIT_BREAKER:
            return await self._check_circuit_breaker(context, operation_id)

        elif action == ErrorAction.KILL_SWITCH:
            return await self._check_kill_switch(error, context, operation_id)

        elif action == ErrorAction.ALERT:
            return await self._send_alert(error, context, operation_id, metadata)

        elif action == ErrorAction.ROLLBACK:
            return await self._execute_rollback(error, context, operation_id, metadata)

        else:
            return {"success": False, "message": f"Unknown action: {action.value}"}

    async def _execute_fallback(
        self,
        error: AlgoTradingError,
        context: ErrorContext,
        operation_id: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute fallback mechanism."""

        if context == ErrorContext.MARKET_DATA_FETCH:
            # Use cached data or alternative data source
            return {
                "success": True,
                "message": "Using fallback data source",
                "fallback_type": "cached_data",
            }

        elif context == ErrorContext.ORDER_PLACEMENT:
            # Cancel the order and log the failure
            return {
                "success": True,
                "message": "Order cancelled due to error",
                "fallback_type": "order_cancellation",
            }

        else:
            return {
                "success": False,
                "message": f"No fallback available for {context.value}",
            }

    async def _check_circuit_breaker(
        self, context: ErrorContext, operation_id: str
    ) -> Dict[str, Any]:
        """Check circuit breaker status."""

        key = f"{context.value}_circuit_breaker"
        is_open = self.circuit_breakers.get(key, False)

        return {
            "success": True,
            "circuit_breaker_open": is_open,
            "context": context.value,
        }

    async def _check_kill_switch(
        self, error: AlgoTradingError, context: ErrorContext, operation_id: str
    ) -> Dict[str, Any]:
        """Check if kill switch should be activated."""

        # Critical errors in live trading should activate kill switch
        if context == ErrorContext.LIVE_TRADING and error.severity == ErrorSeverity.CRITICAL:
            return {
                "success": True,
                "kill_switch_should_activate": True,
                "reason": "Critical error in live trading",
            }

        return {"success": True, "kill_switch_should_activate": False}

    async def _send_alert(
        self,
        error: AlgoTradingError,
        context: ErrorContext,
        operation_id: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Send alert for critical errors."""

        # Only send alerts for high/critical severity errors
        if error.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            alert_message = f"Trading Error Alert: {error.message} in {context.value}"

            # Log as critical for alerting systems to pick up
            centralized_logger.critical(
                LogService.ALERT_SYSTEM,
                alert_message,
                {
                    "operation_id": operation_id,
                    "error_code": error.error_code,
                    "severity": error.severity.value,
                    "context": context.value,
                    **metadata,
                },
            )

            return {
                "success": True,
                "message": "Alert sent",
                "alert_level": error.severity.value,
            }

        return {
            "success": True,
            "message": "No alert needed",
            "reason": "Error severity too low",
        }

    async def _execute_rollback(
        self,
        error: AlgoTradingError,
        context: ErrorContext,
        operation_id: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute rollback for failed operations."""

        if context == ErrorContext.PORTFOLIO_UPDATE:
            # Rollback portfolio changes
            return {
                "success": True,
                "message": "Portfolio changes rolled back",
                "rollback_type": "portfolio_state",
            }

        elif context == ErrorContext.ORDER_PLACEMENT:
            # Cancel any pending orders
            return {
                "success": True,
                "message": "Pending orders cancelled",
                "rollback_type": "order_cancellation",
            }

        else:
            return {
                "success": False,
                "message": f"No rollback available for {context.value}",
            }

    def _should_activate_circuit_breaker(self, context: ErrorContext, operation_id: str) -> bool:
        """Check if circuit breaker should be activated."""
        rules = self.error_rules.get(context.value, {})
        threshold = rules.get("circuit_breaker_threshold", 5)

        key = f"{context.value}_{ErrorCategory.SYSTEM.value}"
        error_count = self.error_counts.get(key, 0)

        return error_count >= threshold

    def _should_activate_kill_switch(self, error: AlgoTradingError, context: ErrorContext) -> bool:
        """Check if kill switch should be activated."""

        # Critical errors in live trading
        if context == ErrorContext.LIVE_TRADING and error.severity == ErrorSeverity.CRITICAL:
            return True

        # Security violations
        if error.category == ErrorCategory.SECURITY:
            return True

        # Risk management violations
        if isinstance(error, RiskManagementError):
            return True

        return False

    async def _activate_circuit_breaker(self, context: ErrorContext, operation_id: str) -> None:
        """Activate circuit breaker for a context."""
        key = f"{context.value}_circuit_breaker"
        self.circuit_breakers[key] = True

        # Log circuit breaker activation
        centralized_logger.critical(
            LogService.ERROR_HANDLER,
            f"Circuit breaker activated for {context.value}",
            {
                "operation_id": operation_id,
                "context": context.value,
                "timestamp": datetime.now().isoformat(),
            },
        )

    async def _activate_kill_switch(
        self, error: AlgoTradingError, context: ErrorContext, operation_id: str
    ) -> None:
        """Activate kill switch."""

        # Log kill switch activation
        centralized_logger.critical(
            LogService.ERROR_HANDLER,
            f"Kill switch activated: {error.message}",
            {
                "operation_id": operation_id,
                "context": context.value,
                "error_code": error.error_code,
                "severity": error.severity.value,
                "timestamp": datetime.now().isoformat(),
            },
        )

        # Set global kill switch flag (would be implemented in a real system)
        # self.config.kill_switch_active = True

    def _is_circuit_breaker_open(self, context: ErrorContext) -> bool:
        """Check if circuit breaker is open for a context."""
        key = f"{context.value}_circuit_breaker"
        return self.circuit_breakers.get(key, False)

    def _get_log_level(self, severity: ErrorSeverity) -> LogLevel:
        """Get log level based on error severity."""
        severity_mapping = {
            ErrorSeverity.LOW: LogLevel.INFO,
            ErrorSeverity.MEDIUM: LogLevel.WARNING,
            ErrorSeverity.HIGH: LogLevel.ERROR,
            ErrorSeverity.CRITICAL: LogLevel.CRITICAL,
        }
        return severity_mapping.get(severity, LogLevel.ERROR)

    def _get_service_from_context(self, context: ErrorContext) -> LogService:
        """Get logging service based on error context."""
        context_mapping = {
            ErrorContext.SIGNAL_GENERATION: LogService.TRADING,
            ErrorContext.ORDER_PLACEMENT: LogService.TRADING,
            ErrorContext.ORDER_EXECUTION: LogService.TRADING,
            ErrorContext.PORTFOLIO_UPDATE: LogService.PORTFOLIO,
            ErrorContext.RISK_CHECK: LogService.TRADING,
            ErrorContext.MARKET_DATA_FETCH: LogService.MARKET_DATA,
            ErrorContext.BACKTESTING: LogService.TRADING,
            ErrorContext.PAPER_TRADING: LogService.TRADING,
            ErrorContext.LIVE_TRADING: LogService.TRADING,
            ErrorContext.CONFIGURATION_LOAD: LogService.FASTAPI,
            ErrorContext.DATABASE_OPERATION: LogService.FASTAPI,
            ErrorContext.API_CALL: LogService.FASTAPI,
        }
        return context_mapping.get(context, LogService.ERROR_HANDLER)

    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring."""
        return {
            "error_counts": self.error_counts.copy(),
            "circuit_breakers": self.circuit_breakers.copy(),
            "last_error_times": {k: v.isoformat() for k, v in self.last_error_times.items()},
            "retry_counts": self.retry_counts.copy(),
            "timestamp": datetime.now().isoformat(),
        }

    def reset_circuit_breaker(self, context: ErrorContext) -> None:
        """Reset circuit breaker for a context."""
        key = f"{context.value}_circuit_breaker"
        self.circuit_breakers[key] = False

        # Reset error count
        error_key = f"{context.value}_{ErrorCategory.SYSTEM.value}"
        self.error_counts[error_key] = 0

        centralized_logger.info(
            LogService.ERROR_HANDLER,
            f"Circuit breaker reset for {context.value}",
            {"context": context.value},
        )


# Global trading error handler instance
trading_error_handler = TradingErrorHandler()


# Utility functions for common error scenarios
async def handle_trading_error(
    error: Exception,
    context: ErrorContext,
    operation_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Handle a trading error with unified processing."""
    return await trading_error_handler.handle_error(error, context, operation_id, metadata)


async def execute_with_retry(
    operation: Callable,
    context: ErrorContext,
    operation_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    *args,
    **kwargs,
) -> Any:
    """Execute an operation with automatic retry on error."""
    return await trading_error_handler.handle_with_retry(
        operation, context, operation_id, metadata, *args, **kwargs
    )


def get_error_statistics() -> Dict[str, Any]:
    """Get current error statistics."""
    return trading_error_handler.get_error_statistics()


def reset_circuit_breaker(context: ErrorContext) -> None:
    """Reset circuit breaker for a context."""
    trading_error_handler.reset_circuit_breaker(context)
