"""
API Circuit Breaker - Resilience pattern for API calls.

Implements the circuit breaker pattern to prevent cascading failures
when calling external APIs. Tracks error rates and automatically
opens/closes circuits based on configurable thresholds.

Uses centralized configuration for all thresholds.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Optional

from app.shared.config.centralized_config import get_config
from app.shared.utils.timezone_utils import utc_now

logger = logging.getLogger(__name__)


class CircuitBreakerType(str, Enum):
    """Types of circuit breakers for different API endpoints."""

    API_ERRORS = "api_errors"
    DATA_SERVICE = "data_service"
    ORDER_EXECUTION = "order_execution"
    BROKER_CONNECTION = "broker_connection"


class CircuitState(str, Enum):
    """State of a circuit breaker."""

    CLOSED = "closed"  # Operating normally
    OPEN = "open"  # Circuit is open, blocking calls
    HALF_OPEN = "half_open"  # Testing if service has recovered


@dataclass
class CircuitBreaker:
    """Individual circuit breaker instance."""

    name: str
    failure_threshold: int = 5
    recovery_timeout: int = 60  # seconds
    half_open_attempts: int = 3

    # State tracking
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None

    def is_open(self) -> bool:
        """Check if circuit is open."""
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self.last_failure_time and utc_now() >= self.last_failure_time + timedelta(
                seconds=self.recovery_timeout
            ):
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit {self.name} transitioned to HALF_OPEN")
                return False
            return True
        return False

    def record_success(self) -> None:
        """Record a successful call."""
        self.success_count += 1
        self.last_success_time = utc_now()

        if self.state == CircuitState.HALF_OPEN and self.success_count >= self.half_open_attempts:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            logger.info(f"Circuit {self.name} recovered, transitioned to CLOSED")

    def record_failure(self) -> None:
        """Record a failed call."""
        self.failure_count += 1
        self.last_failure_time = utc_now()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit {self.name} opened after {self.failure_count} failures")

    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_success_time = None
        logger.info(f"Circuit {self.name} reset")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "last_failure_time": (
                self.last_failure_time.isoformat() if self.last_failure_time else None
            ),
            "last_success_time": (
                self.last_success_time.isoformat() if self.last_success_time else None
            ),
        }


class CircuitBreakerManager:
    """
    Manages multiple circuit breakers for API resilience.

    This is the ORIGINAL circuit breaker pattern for API error handling,
    separate from the market halt detection circuit breaker.
    """

    def __init__(self):
        """Initialize circuit breaker manager with centralized config."""
        # Get thresholds from centralized config - use directly, no hasattr
        tt = get_config().trading_thresholds
        self._tt = tt

        # Use centralized config directly
        self.failure_threshold = tt.circuit_breaker_failure_threshold
        self.recovery_timeout = tt.circuit_breaker_recovery_timeout

        # Initialize default circuit breakers
        self.circuit_breakers: Dict[str, CircuitBreaker] = {
            CircuitBreakerType.API_ERRORS: CircuitBreaker(
                name=CircuitBreakerType.API_ERRORS,
                failure_threshold=self.failure_threshold,
                recovery_timeout=self.recovery_timeout,
            ),
            CircuitBreakerType.DATA_SERVICE: CircuitBreaker(
                name=CircuitBreakerType.DATA_SERVICE,
                failure_threshold=self.failure_threshold,
                recovery_timeout=self.recovery_timeout,
            ),
            CircuitBreakerType.ORDER_EXECUTION: CircuitBreaker(
                name=CircuitBreakerType.ORDER_EXECUTION,
                failure_threshold=self.failure_threshold,
                recovery_timeout=self.recovery_timeout,
            ),
            CircuitBreakerType.BROKER_CONNECTION: CircuitBreaker(
                name=CircuitBreakerType.BROKER_CONNECTION,
                failure_threshold=self.failure_threshold,
                recovery_timeout=self.recovery_timeout,
            ),
        }

        # Statistics
        self.total_operations = 0
        self.successful_operations = 0
        self.failed_operations = 0

        logger.info("CircuitBreakerManager initialized")

    def add_circuit_breaker(
        self,
        name: str,
        failure_threshold: int,
        recovery_timeout: int,
        half_open_attempts: int = 3,
    ) -> None:
        """Add a new circuit breaker."""
        self.circuit_breakers[name] = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            half_open_attempts=half_open_attempts,
        )

    def is_breaker_open(self, breaker_name: str) -> bool:
        """Check if a circuit breaker is open."""
        breaker = self.circuit_breakers.get(breaker_name)
        return breaker.is_open() if breaker else False

    def record_success(self, breaker_name: str) -> None:
        """Record a successful operation."""
        breaker = self.circuit_breakers.get(breaker_name)
        if breaker:
            breaker.record_success()
        self.total_operations += 1
        self.successful_operations += 1

    def record_error(self, breaker_name: str, error_message: str = "") -> None:
        """Record a failed operation."""
        breaker = self.circuit_breakers.get(breaker_name)
        if breaker:
            breaker.record_failure()
        self.total_operations += 1
        self.failed_operations += 1
        if error_message:
            logger.debug(f"Circuit breaker error ({breaker_name}): {error_message}")

    def get_all_breaker_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers."""
        return {name: breaker.to_dict() for name, breaker in self.circuit_breakers.items()}

    def reset_breaker(self, breaker_name: str) -> bool:
        """Reset a specific circuit breaker."""
        breaker = self.circuit_breakers.get(breaker_name)
        if breaker:
            breaker.reset()
            return True
        return False

    def reset_all_breakers(self) -> None:
        """Reset all circuit breakers."""
        for breaker in self.circuit_breakers.values():
            breaker.reset()
        logger.info("All circuit breakers reset")

    def clear_history(self) -> None:
        """Clear all circuit breakers."""
        self.circuit_breakers.clear()
        logger.info("Circuit breaker history cleared")

    def get_manager_statistics(self) -> Dict[str, Any]:
        """Get manager statistics."""
        return {
            "total_operations": self.total_operations,
            "successful_operations": self.successful_operations,
            "failed_operations": self.failed_operations,
            "success_rate": (
                self.successful_operations / self.total_operations
                if self.total_operations > 0
                else 0
            ),
            "active_breakers": len(self.circuit_breakers),
            "open_breakers": sum(1 for b in self.circuit_breakers.values() if b.is_open()),
        }
