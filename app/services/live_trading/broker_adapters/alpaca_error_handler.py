"""
Error handling and recovery for Alpaca broker integration.

Implements:
- Detailed error classification (transient vs permanent)
- Circuit breaker pattern for API calls
- Retry logic with exponential backoff
- Position sync recovery
- Error recovery callbacks
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, ClassVar, Optional

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Classification of error types."""

    # Transient errors - can be retried
    NETWORK_ERROR = "network_error"  # Connection timeout, DNS failure
    RATE_LIMIT = "rate_limit"  # 429 Too Many Requests
    TEMPORARY_SERVICE_ERROR = "temporary_service"  # 503 Service Unavailable
    TIMEOUT = "timeout"  # Request timeout

    # Authentication/Authorization errors - may be recoverable
    AUTH_FAILED = "auth_failed"  # Invalid credentials
    EXPIRED_SESSION = "expired_session"  # Token expired
    INSUFFICIENT_PERMISSIONS = "insufficient_permissions"  # Scope issue

    # Business logic errors - not retryable
    INSUFFICIENT_FUNDS = "insufficient_funds"  # Not enough cash/buying power
    INVALID_SYMBOL = "invalid_symbol"  # Stock symbol doesn't exist
    INVALID_ORDER = "invalid_order"  # Order parameters invalid
    POSITION_CLOSED = "position_closed"  # Position already closed
    ORDER_NOT_FOUND = "order_not_found"  # Order ID doesn't exist

    # Unknown error
    UNKNOWN = "unknown"


class ErrorRecoveryStrategy(Enum):
    """Recovery strategy for different error types."""

    RETRY = "retry"  # Retry with exponential backoff
    SKIP = "skip"  # Skip this operation, continue
    FAIL = "fail"  # Fail immediately, don't retry
    ALERT = "alert"  # Alert user, ask for intervention
    SYNC = "sync"  # Perform sync operation to recover


class AlpacaErrorClassifier:
    """Classify Alpaca errors and determine recovery strategy."""

    # Map error patterns to error types
    ERROR_PATTERNS: ClassVar[dict[str, ErrorType]] = {
        # Network errors
        r"(?i)(connection|timeout|dns|network|unreachable)": ErrorType.NETWORK_ERROR,
        # Rate limiting
        r"(?i)(429|rate limit|too many requests)": ErrorType.RATE_LIMIT,
        # Service errors
        r"(?i)(503|service unavailable|temporarily unavailable)": ErrorType.TEMPORARY_SERVICE_ERROR,
        # Authentication
        r"(?i)(401|unauthorized|invalid.*key|invalid.*secret)": ErrorType.AUTH_FAILED,
        r"(?i)(token.*expir|session.*expir)": ErrorType.EXPIRED_SESSION,
        # Business logic
        r"(?i)(insufficient.*fund|not enough|buying power)": ErrorType.INSUFFICIENT_FUNDS,
        r"(?i)(invalid.*symbol|unknown.*symbol)": ErrorType.INVALID_SYMBOL,
        r"(?i)(invalid.*order|bad.*param)": ErrorType.INVALID_ORDER,
        r"(?i)(position.*closed|already closed)": ErrorType.POSITION_CLOSED,
        r"(?i)(order.*not.*found|order.*not.*exist)": ErrorType.ORDER_NOT_FOUND,
    }

    # Recovery strategy for each error type
    RECOVERY_STRATEGIES: ClassVar[dict[ErrorType, ErrorRecoveryStrategy]] = {
        ErrorType.NETWORK_ERROR: ErrorRecoveryStrategy.RETRY,
        ErrorType.RATE_LIMIT: ErrorRecoveryStrategy.RETRY,
        ErrorType.TEMPORARY_SERVICE_ERROR: ErrorRecoveryStrategy.RETRY,
        ErrorType.TIMEOUT: ErrorRecoveryStrategy.RETRY,
        ErrorType.EXPIRED_SESSION: ErrorRecoveryStrategy.SYNC,
        ErrorType.AUTH_FAILED: ErrorRecoveryStrategy.ALERT,
        ErrorType.INSUFFICIENT_FUNDS: ErrorRecoveryStrategy.FAIL,
        ErrorType.INVALID_SYMBOL: ErrorRecoveryStrategy.FAIL,
        ErrorType.INVALID_ORDER: ErrorRecoveryStrategy.FAIL,
        ErrorType.POSITION_CLOSED: ErrorRecoveryStrategy.SKIP,
        ErrorType.ORDER_NOT_FOUND: ErrorRecoveryStrategy.SKIP,
        ErrorType.UNKNOWN: ErrorRecoveryStrategy.ALERT,
    }

    @staticmethod
    def classify(error: Exception) -> ErrorType:
        """Classify error into error type.

        Args:
            error: Exception to classify

        Returns:
            ErrorType: Classified error type
        """
        import re

        error_str = str(error).lower()

        for pattern, error_type in AlpacaErrorClassifier.ERROR_PATTERNS.items():
            if re.search(pattern, error_str):
                return error_type

        return ErrorType.UNKNOWN

    @staticmethod
    def get_strategy(error_type: ErrorType) -> ErrorRecoveryStrategy:
        """Get recovery strategy for error type.

        Args:
            error_type: Type of error

        Returns:
            ErrorRecoveryStrategy: Recovery strategy
        """
        return AlpacaErrorClassifier.RECOVERY_STRATEGIES.get(
            error_type, ErrorRecoveryStrategy.ALERT
        )

    @staticmethod
    def is_retryable(error: Exception) -> bool:
        """Check if error is retryable.

        Args:
            error: Exception to check

        Returns:
            bool: True if error can be retried
        """
        error_type = AlpacaErrorClassifier.classify(error)
        strategy = AlpacaErrorClassifier.get_strategy(error_type)
        return strategy == ErrorRecoveryStrategy.RETRY


class CircuitBreaker:
    """Circuit breaker pattern for API calls.

    Prevents cascading failures by stopping requests when error rate exceeds threshold.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many errors, requests fail fast
    - HALF_OPEN: Limited requests to test if service recovered
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout_seconds: int = 60,
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Failures before opening circuit
            success_threshold: Successes while half-open to close circuit
            timeout_seconds: Seconds to wait before trying half-open
        """
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timedelta(seconds=timeout_seconds)

        self.state = self.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None

    def record_success(self) -> None:
        """Record successful API call."""
        self.failure_count = 0

        if self.state == self.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                self._close()

    def record_failure(self) -> None:
        """Record failed API call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self._open()

    def is_available(self) -> bool:
        """Check if circuit breaker allows requests.

        Returns:
            bool: True if requests are allowed
        """
        if self.state == self.CLOSED:
            return True

        if self.state == self.OPEN:
            # Try to transition to half-open after timeout
            if self.last_failure_time and datetime.now() > (self.last_failure_time + self.timeout):
                self._half_open()
                return True
            return False

        # HALF_OPEN - allow requests
        return True

    def _open(self) -> None:
        """Open circuit - stop accepting requests."""
        self.state = self.OPEN
        logger.error(f"❌ Circuit breaker OPEN: {self.failure_count} failures detected")

    def _close(self) -> None:
        """Close circuit - resume normal operation."""
        self.state = self.CLOSED
        self.failure_count = 0
        self.success_count = 0
        logger.info("✅ Circuit breaker CLOSED: Service recovered")

    def _half_open(self) -> None:
        """Half-open circuit - test if service recovered."""
        self.state = self.HALF_OPEN
        self.success_count = 0
        logger.info("🔄 Circuit breaker HALF_OPEN: Testing service recovery")

    def __repr__(self) -> str:
        """String representation."""
        return f"CircuitBreaker(state={self.state}, failures={self.failure_count})"


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        backoff_factor: float = 2.0,
    ):
        """Initialize retry config.

        Args:
            max_attempts: Maximum number of attempts
            base_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            backoff_factor: Exponential backoff factor
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for attempt number.

        Args:
            attempt: Attempt number (0-indexed)

        Returns:
            float: Delay in seconds
        """
        delay = self.base_delay * (self.backoff_factor**attempt)
        return min(delay, self.max_delay)


class PositionSyncRecovery:
    """Recovery strategy for position sync failures."""

    def __init__(self, max_retries: int = 3, timeout_seconds: int = 5):
        """Initialize position sync recovery.

        Args:
            max_retries: Maximum sync attempts
            timeout_seconds: Timeout for each sync
        """
        self.max_retries = max_retries
        self.timeout = timeout_seconds
        self.last_successful_sync: Optional[datetime] = None
        self.sync_failure_count = 0

    def record_sync_success(self) -> None:
        """Record successful sync."""
        self.last_successful_sync = datetime.now()
        self.sync_failure_count = 0
        logger.info("✅ Position sync successful")

    def record_sync_failure(self) -> None:
        """Record failed sync."""
        self.sync_failure_count += 1
        logger.warning(f"⚠️  Position sync failed ({self.sync_failure_count}/{self.max_retries})")

    def should_retry(self) -> bool:
        """Check if should retry sync.

        Returns:
            bool: True if should retry
        """
        return self.sync_failure_count < self.max_retries

    def is_stale(self, max_age_seconds: int = 300) -> bool:
        """Check if position data is stale.

        Args:
            max_age_seconds: Maximum acceptable age in seconds

        Returns:
            bool: True if data is stale
        """
        if not self.last_successful_sync:
            return True

        age = (datetime.now() - self.last_successful_sync).total_seconds()
        return age > max_age_seconds

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"PositionSyncRecovery(failures={self.sync_failure_count}/"
            f"{self.max_retries}, "
            f"last_sync={self.last_successful_sync})"
        )


class ErrorRecoveryManager:
    """Central manager for error recovery operations."""

    def __init__(self):
        """Initialize error recovery manager."""
        self.circuit_breaker = CircuitBreaker()
        self.retry_config = RetryConfig()
        self.position_sync_recovery = PositionSyncRecovery()
        self.classifier = AlpacaErrorClassifier()

        # Callbacks
        self.on_circuit_open: Optional[Callable[[], None]] = None
        self.on_sync_needed: Optional[Callable[[], None]] = None
        self.on_manual_intervention: Optional[Callable[[str], None]] = None

    def should_allow_request(self) -> bool:
        """Check if request should be allowed.

        Returns:
            bool: True if request can proceed
        """
        return self.circuit_breaker.is_available()

    def handle_request_failure(self, error: Exception) -> ErrorRecoveryStrategy:
        """Handle request failure and determine recovery strategy.

        Args:
            error: Exception from request

        Returns:
            ErrorRecoveryStrategy: Recommended recovery action
        """
        self.circuit_breaker.record_failure()

        if not self.circuit_breaker.is_available():
            if self.on_circuit_open is not None:
                self.on_circuit_open()
            return ErrorRecoveryStrategy.FAIL

        error_type = self.classifier.classify(error)
        strategy = self.classifier.get_strategy(error_type)

        logger.warning(
            f"⚠️  API error [{error_type.value}]: {error!s} → Strategy: {strategy.value}"
        )

        if strategy == ErrorRecoveryStrategy.ALERT and self.on_manual_intervention is not None:
            self.on_manual_intervention(str(error))

        if strategy == ErrorRecoveryStrategy.SYNC and self.on_sync_needed is not None:
            self.on_sync_needed()

        return strategy

    def handle_request_success(self) -> None:
        """Handle successful request."""
        self.circuit_breaker.record_success()

    def get_retry_delay(self, attempt: int) -> float:
        """Get delay for retry attempt.

        Args:
            attempt: Attempt number (0-indexed)

        Returns:
            float: Delay in seconds
        """
        return self.retry_config.get_delay(attempt)

    def __repr__(self) -> str:
        """String representation."""
        return (
            "ErrorRecoveryManager("
            f"circuit={self.circuit_breaker}, "
            f"position_sync={self.position_sync_recovery})"
        )
