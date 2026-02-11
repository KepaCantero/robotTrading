"""
T12.1: ErrorHandling - Exception handling, fallback strategies, graceful degradation

Provides:
- Custom exception classes for different service failures
- FallbackStrategy pattern for graceful degradation
- ErrorHandler for try-catch wrappers and error logging
- Retry logic with exponential backoff
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar

from app.core.config.base import get_config

logger = logging.getLogger(__name__)

T = TypeVar('T')


# =============================================================================
# Custom Exception Classes
# =============================================================================


class ServiceException(Exception):
    """Base exception for all service errors."""

    def __init__(self, service_name: str, message: str, error_code: str = "UNKNOWN"):
        self.service_name = service_name
        self.message = message
        self.error_code = error_code
        self.timestamp = datetime.now().isoformat()
        super().__init__(f"[{service_name}] {message} (Code: {error_code})")


class BacktestException(ServiceException):
    """Exception for backtest orchestration failures."""

    def __init__(self, message: str, error_code: str = "BACKTEST_ERROR"):
        super().__init__("BacktestOrchestrator", message, error_code)


class ValidationException(ServiceException):
    """Exception for validation engine failures."""

    def __init__(self, message: str, error_code: str = "VALIDATION_ERROR"):
        super().__init__("ValidationEngine", message, error_code)


class ConfigurationException(ServiceException):
    """Exception for configuration persistence failures."""

    def __init__(self, message: str, error_code: str = "CONFIG_ERROR"):
        super().__init__("ConfigurationRepository", message, error_code)


class ParameterizationException(ServiceException):
    """Exception for parametrization failures."""

    def __init__(self, message: str, error_code: str = "PARAM_ERROR"):
        super().__init__("ModuleParametrizer", message, error_code)


class RecommendationException(ServiceException):
    """Exception for recommendation engine failures."""

    def __init__(self, message: str, error_code: str = "RECOMMENDATION_ERROR"):
        super().__init__("StrategyRecommender", message, error_code)


class PortfolioException(ServiceException):
    """Exception for portfolio construction failures."""

    def __init__(self, message: str, error_code: str = "PORTFOLIO_ERROR"):
        super().__init__("PortfolioConstructor", message, error_code)


# =============================================================================
# Fallback Strategy Pattern
# =============================================================================


class FallbackStrategy(ABC):
    """Abstract base class for fallback strategies."""

    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Any:
        """Execute fallback strategy."""

    @abstractmethod
    def can_handle(self, exception: ServiceException) -> bool:
        """Check if this strategy can handle the exception."""


class ConservativeBacktestFallback(FallbackStrategy):
    """Fallback strategy for backtest failures: use simplified model."""

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Return conservative backtest result.

        Uses configurable fallback parameters for conservative estimates when
        the actual backtest engine is unavailable.
        """
        logger.warning("🟡 Using conservative backtest fallback strategy")

        try:
            config = get_config()
            # Get fallback parameters from config with defaults
            annual_return = float(getattr(
                config.trading, 'fallback_conservative_annual_return', 0.05
            ))
            sharpe_ratio = float(getattr(
                config.trading, 'fallback_conservative_sharpe_ratio', 0.5
            ))
            max_drawdown = float(getattr(
                config.trading, 'fallback_expected_max_drawdown', -0.15
            ))
            feasibility_ratio = float(getattr(
                config.trading, 'fallback_feasibility_ratio', 0.8
            ))
        except (AttributeError, ValueError) as e:
            logger.error(f"Error loading fallback config: {e}, using defaults")
            annual_return = 0.05
            sharpe_ratio = 0.5
            max_drawdown = -0.15
            feasibility_ratio = 0.8

        # Use historical average returns as fallback
        context.get("capital", 50000)
        return {
            "strategy_name": context.get("strategy_name", "fallback"),
            "total_return": annual_return,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "feasibility_ratio": feasibility_ratio,
            "viability_status": "CONDITIONAL",
            "is_fallback": True,
            "fallback_reason": "Using conservative backtest model",
        }

    def can_handle(self, exception: ServiceException) -> bool:
        """Handle backtest exceptions."""
        return isinstance(exception, BacktestException)


class EqualWeightPortfolioFallback(FallbackStrategy):
    """Fallback strategy for portfolio optimization: equal weighting."""

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Return equal-weighted portfolio allocation."""
        logger.warning("🟡 Using equal-weight portfolio fallback strategy")

        assets = context.get("assets", [])
        if not assets:
            assets = ["SPY", "AGG", "GLD"]  # Default fallback assets

        equal_weight = 1.0 / len(assets)
        allocation = {asset: equal_weight for asset in assets}

        return {
            "allocation": allocation,
            "strategy": "equal_weight",
            "is_fallback": True,
            "fallback_reason": "Using equal-weight allocation",
        }

    def can_handle(self, exception: ServiceException) -> bool:
        """Handle portfolio exceptions."""
        return isinstance(exception, PortfolioException)


class ConservativeRecommendationFallback(FallbackStrategy):
    """Fallback strategy for recommendation failures: return conservative recommendation."""

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Return conservative recommendation."""
        logger.warning("🟡 Using conservative recommendation fallback strategy")

        return {
            "recommendation": "HOLD",
            "confidence_level": "LOW",
            "score": 50,  # Neutral score
            "reasons": ["Recommendation engine unavailable", "Using fallback recommendation"],
            "is_fallback": True,
            "fallback_reason": "Recommendation engine failed",
        }

    def can_handle(self, exception: ServiceException) -> bool:
        """Handle recommendation exceptions."""
        return isinstance(exception, RecommendationException)


# =============================================================================
# Error Handler with Retry & Fallback
# =============================================================================


class ErrorHandler:
    """
    T12.1: ErrorHandler for managing errors and fallbacks across all services.

    Provides:
    - Try-catch wrappers for async functions
    - Retry logic with exponential backoff
    - Fallback strategy selection and execution
    - Error logging and metrics
    """

    def __init__(self):
        """Initialize ErrorHandler."""
        self.logger = logging.getLogger(__name__)
        self.fallback_strategies: List[FallbackStrategy] = [
            ConservativeBacktestFallback(),
            EqualWeightPortfolioFallback(),
            ConservativeRecommendationFallback(),
        ]
        self.error_count = 0
        self.error_log: List[Dict[str, Any]] = []
        self.logger.info("✅ ErrorHandler initialized with 3 fallback strategies")

    def register_fallback(self, strategy: FallbackStrategy) -> None:
        """Register a new fallback strategy."""
        self.fallback_strategies.append(strategy)
        self.logger.info(f"📝 Registered fallback strategy: {strategy.__class__.__name__}")

    async def with_fallback(
        self, async_fn: Callable, *args, fallback_context: Optional[Dict[str, Any]] = None, **kwargs
    ) -> Any:
        """
        Execute async function with fallback strategy on exception.

        Args:
            async_fn: Async function to execute
            fallback_context: Context dict for fallback strategy
            args: Positional arguments for async_fn
            kwargs: Keyword arguments for async_fn

        Returns:
            Result from async_fn or fallback strategy
        """
        try:
            return await async_fn(*args, **kwargs)
        except ServiceException as e:
            self.logger.error(f"❌ Service error: {e}")
            self.error_count += 1

            # Log error
            error_entry = {
                "timestamp": datetime.now().isoformat(),
                "service": e.service_name,
                "error_code": e.error_code,
                "message": e.message,
            }
            self.error_log.append(error_entry)

            # Try to find matching fallback strategy
            for strategy in self.fallback_strategies:
                if strategy.can_handle(e):
                    self.logger.info(f"🔄 Using fallback strategy: {strategy.__class__.__name__}")
                    context = fallback_context or {}
                    try:
                        return await strategy.execute(context)
                    except (asyncio.TimeoutError, ConnectionError, OSError) as fallback_error:
                        self.logger.error(f"❌ Fallback strategy failed: {fallback_error}")
                        raise

            # No matching fallback found
            self.logger.error(f"❌ No fallback strategy found for {type(e).__name__}")
            raise

    async def with_retry(
        self, async_fn: Callable, *args, max_retries: int = 3, initial_delay: float = 0.5, **kwargs
    ) -> Any:
        """
        Execute async function with exponential backoff retry.

        Args:
            async_fn: Async function to execute
            max_retries: Maximum number of retries
            initial_delay: Initial delay in seconds between retries
            args: Positional arguments for async_fn
            kwargs: Keyword arguments for async_fn

        Returns:
            Result from async_fn if successful

        Raises:
            Exception: If all retries fail
        """
        delay = initial_delay
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                return await async_fn(*args, **kwargs)
            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                last_exception = e
                if attempt < max_retries:
                    self.logger.warning(
                        f"⚠️  Attempt {attempt + 1}/{max_retries + 1} failed, "
                        f"retrying in {delay}s: {e}"
                    )
                    await asyncio.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    self.logger.error(
                        f"❌ All {max_retries + 1} attempts failed for {async_fn.__name__}"
                    )

        raise last_exception

    async def with_timeout(
        self, async_fn: Callable, timeout_seconds: float = 30.0, *args, **kwargs
    ) -> Any:
        """
        Execute async function with timeout protection.

        Args:
            async_fn: Async function to execute
            timeout_seconds: Maximum execution time in seconds
            args: Positional arguments for async_fn
            kwargs: Keyword arguments for async_fn

        Returns:
            Result from async_fn if completed within timeout

        Raises:
            asyncio.TimeoutError: If function exceeds timeout
        """
        try:
            return await asyncio.wait_for(async_fn(*args, **kwargs), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            self.logger.error(
                f"❌ Function {async_fn.__name__} exceeded timeout of {timeout_seconds}s"
            )
            raise

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        return {
            "total_errors": self.error_count,
            "error_log": self.error_log,
            "recent_errors": self.error_log[-5:] if self.error_log else [],
        }

    def clear_error_log(self) -> None:
        """Clear error log."""
        self.error_log.clear()
        self.error_count = 0
        self.logger.info("🗑️  Error log cleared")


# =============================================================================
# Decorator for Service Methods
# =============================================================================


def service_error_handler(fallback_context: Optional[Dict[str, Any]] = None):
    """
    Decorator for wrapping service methods with error handling.

    Usage:
        @service_error_handler(fallback_context={"capital": 50000})
        async def my_service_method(self):
            return await self._actual_implementation()
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            ErrorHandler()

            async def execute():
                return await func(*args, **kwargs)

            try:
                return await execute()
            except ServiceException as e:
                logger.error(f"❌ Service error in {func.__name__}: {e}")
                # Re-raise to allow caller to handle
                raise
            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                logger.error(f"❌ Unexpected error in {func.__name__}: {e}")
                raise ServiceException(
                    service_name=func.__module__, message=str(e), error_code="UNKNOWN_ERROR"
                )

        return wrapper

    return decorator
