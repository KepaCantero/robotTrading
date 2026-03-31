"""
Retry management for external integrations.

Implements exponential backoff with jitter and automatic retry logic
for transient failures from external services (QuestDB, Dagster, MLFlow, Zipline).
"""

from __future__ import annotations

import asyncio
import logging
import random
from decimal import Decimal
from typing import Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay_ms: int = 100,
        max_delay_ms: int = 10000,
        exponential_base: Optional[Decimal] = None,
        jitter_factor: Optional[Decimal] = None,
    ):
        """
        Initialize retry configuration.

        Args:
            max_retries: Maximum number of retry attempts
            initial_delay_ms: Initial delay in milliseconds
            max_delay_ms: Maximum delay cap in milliseconds
            exponential_base: Base for exponential backoff
            jitter_factor: Jitter as fraction of delay (0.0-1.0)
        """
        if exponential_base is None:
            exponential_base = Decimal("2.0")
        if jitter_factor is None:
            jitter_factor = Decimal("0.1")
        self.max_retries = max_retries
        self.initial_delay_ms = initial_delay_ms
        self.max_delay_ms = max_delay_ms
        self.exponential_base = exponential_base
        self.jitter_factor = jitter_factor


class RetryManager:
    """Manages retries with exponential backoff for external service calls."""

    def __init__(self, config: Optional[RetryConfig] = None):
        """
        Initialize retry manager.

        Args:
            config: Retry configuration (uses defaults if None)
        """
        self.config = config or RetryConfig()
        self.logger = logging.getLogger(self.__class__.__name__)

    async def execute_with_retry(
        self,
        func: Callable,
        *args,
        operation_name: str = "operation",
        retryable_exceptions: tuple = (ConnectionError, TimeoutError),
        **kwargs,
    ) -> object:
        """
        Execute a function with automatic retry on failure.

        Args:
            func: Async function to execute
            *args: Positional arguments for function
            operation_name: Name of operation for logging
            retryable_exceptions: Tuple of exceptions to retry on
            **kwargs: Keyword arguments for function

        Returns:
            Result from function

        Raises:
            Exception: If all retries exhausted
        """
        last_exception = None

        for attempt in range(self.config.max_retries + 1):
            try:
                result = await func(*args, **kwargs)
                if attempt > 0:
                    self.logger.info(f"✅ {operation_name} succeeded on attempt {attempt + 1}")
                return result

            except retryable_exceptions as e:
                last_exception = e

                if attempt >= self.config.max_retries:
                    self.logger.error(
                        f"❌ {operation_name} failed after {self.config.max_retries + 1} attempts: {e!s}"
                    )
                    raise

                # Calculate delay with exponential backoff and jitter
                delay_ms = await self._calculate_delay(attempt)
                self.logger.warning(
                    f"⚠️ {operation_name} failed (attempt {attempt + 1}), "
                    f"retrying in {delay_ms}ms: {e!s}"
                )

                await asyncio.sleep(delay_ms / 1000.0)

            except (asyncio.TimeoutError, OSError) as e:
                # Non-retryable exception
                self.logger.error(f"❌ {operation_name} failed with non-retryable exception: {e!s}")
                raise

        # Should not reach here, but just in case
        if last_exception:
            raise last_exception

    async def _calculate_delay(self, attempt: int) -> int:
        """
        Calculate delay with exponential backoff and jitter.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in milliseconds
        """
        # Exponential backoff: initial_delay * (base ^ attempt)
        exponential_delay = int(
            self.config.initial_delay_ms * float(self.config.exponential_base**attempt)
        )

        # Cap at max delay
        exponential_delay = min(exponential_delay, self.config.max_delay_ms)

        # Add jitter: random value between 0 and (delay * jitter_factor)
        jitter_range = int(exponential_delay * float(self.config.jitter_factor))
        jitter = random.randint(0, jitter_range) if jitter_range > 0 else 0

        return exponential_delay + jitter


# Default instance
_retry_manager: Optional[RetryManager] = None


def get_retry_manager() -> RetryManager:
    """Get or create the retry manager singleton."""
    global _retry_manager
    if _retry_manager is None:
        _retry_manager = RetryManager()
        logger.info("✅ RetryManager singleton initialized")
    return _retry_manager
