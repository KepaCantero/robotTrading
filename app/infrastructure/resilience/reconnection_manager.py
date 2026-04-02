"""
Reconnection Manager - Manages reconnection with exponential backoff.

Essential for 24/7 operation where network glitches are common.

Uses centralized configuration for all timeout and backoff parameters.
"""

from __future__ import annotations

import asyncio
import logging
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from app.shared.config.centralized_config import get_config
from app.shared.utils.timezone_utils import utc_now

if TYPE_CHECKING:
    from collections.abc import Awaitable
    from datetime import datetime

logger = logging.getLogger(__name__)


class ReconnectionConfig:
    """
    Configuration for reconnection behavior.

    Uses centralized configuration for all timeout and backoff parameters.
    Supports both keyword arguments and custom_config dict for overrides.
    """

    def __init__(
        self,
        custom_config: dict | None = None,
        *,
        max_attempts: int | None = None,
        base_delay_seconds: float | None = None,
        max_delay_seconds: float | None = None,
        exponential_base: float | None = None,
        jitter: bool | None = None,
        jitter_factor: float | None = None,
        alert_after_attempts: int | None = None,
        on_attempt: Callable[[int], None] | None = None,
        on_success: Callable[[int], None] | None = None,
        on_failure: Callable[[], None] | None = None,
        alert_callback: Callable[[int], None] | None = None,
    ):
        """
        Initialize ReconnectionConfig with centralized config values.

        Args:
            custom_config: Optional dict to override specific values (legacy)
            max_attempts: Override max reconnection attempts
            base_delay_seconds: Override base delay in seconds
            max_delay_seconds: Override max delay cap in seconds
            exponential_base: Override exponential backoff base
            jitter: Override jitter enabled flag
            jitter_factor: Override jitter factor
            alert_after_attempts: Override alert threshold
            on_attempt: Callback for each attempt
            on_success: Callback on successful connection
            on_failure: Callback when all attempts fail
            alert_callback: Callback when alert threshold reached
        """
        # Get centralized config for default values
        tt = get_config().trading_thresholds

        # Core reconnection parameters from centralized config (with kwarg overrides)
        self.max_attempts = (
            max_attempts if max_attempts is not None else tt.reconnection_max_attempts
        )
        self.base_delay_seconds = (
            base_delay_seconds
            if base_delay_seconds is not None
            else tt.reconnection_base_delay_seconds
        )
        self.max_delay_seconds = (
            max_delay_seconds
            if max_delay_seconds is not None
            else tt.reconnection_max_delay_seconds
        )
        self.exponential_base = (
            exponential_base if exponential_base is not None else tt.reconnection_exponential_base
        )
        self.jitter = jitter if jitter is not None else True
        self.jitter_factor = (
            jitter_factor if jitter_factor is not None else tt.reconnection_jitter_factor
        )

        # Alert thresholds from centralized config (with kwarg overrides)
        self.alert_after_attempts = (
            alert_after_attempts
            if alert_after_attempts is not None
            else tt.reconnection_alert_after_attempts
        )

        # Callbacks
        self.on_attempt = on_attempt
        self.on_success = on_success
        self.on_failure = on_failure
        self.alert_callback = alert_callback

        # Apply any custom overrides from dict (lowest priority)
        if custom_config:
            for key, value in custom_config.items():
                if hasattr(self, key):
                    setattr(self, key, value)


@dataclass
class ReconnectionStats:
    """Statistics for reconnection attempts."""

    total_attempts: int = 0
    successful_connections: int = 0
    failed_connections: int = 0
    last_connection_time: datetime | None = None
    last_failure_time: datetime | None = None
    current_backoff_seconds: float = 0.0

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_attempts == 0:
            return 0.0
        return self.successful_connections / self.total_attempts


class ReconnectionManager:
    """
    Manages reconnection with exponential backoff.

    Features:
    - Exponential backoff: 1s, 2s, 4s, 8s, ... max 60s
    - Jitter to prevent thundering herd
    - Configurable max retry attempts
    - Works for WebSocket and HTTP connections
    - Alerts after configured threshold
    """

    def __init__(
        self,
        service_name: str,
        config: ReconnectionConfig | None = None,
    ):
        """
        Initialize reconnection manager.

        Args:
            service_name: Name of the service being reconnected
            config: Reconnection configuration
        """
        self.service_name = service_name
        self.config = config or ReconnectionConfig()
        self.stats = ReconnectionStats()

        logger.info(f"ReconnectionManager initialized for {service_name}")

    def calculate_backoff(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay.

        Formula: min(base_delay * (exponential_base ^ attempt), max_delay)

        Args:
            attempt: Attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        # Calculate exponential backoff
        delay = self.config.base_delay_seconds * (self.config.exponential_base**attempt)

        # Cap at max delay
        delay = min(delay, self.config.max_delay_seconds)

        # Add jitter to prevent thundering herd
        if self.config.jitter:
            jitter_amount = delay * self.config.jitter_factor
            jitter = random.uniform(-jitter_amount, jitter_amount)
            delay = max(0, delay + jitter)

        self.stats.current_backoff_seconds = delay
        return delay

    async def connect_with_backoff(
        self,
        connect_func: Callable[[], Any],
    ) -> Any | None:
        """
        Try to connect with exponential backoff.

        Args:
            connect_func: Async function that attempts connection

        Returns:
            Connection object if successful, None otherwise
        """
        for attempt in range(self.config.max_attempts):
            self.stats.total_attempts += 1

            try:
                # Call attempt callback
                if self.config.on_attempt:
                    self.config.on_attempt(attempt)

                logger.info(
                    f"{self.service_name}: Connection attempt {attempt + 1}/"
                    f"{self.config.max_attempts}"
                )

                # Try to connect - use centralized config timeout
                tt = get_config().trading_thresholds
                timeout = tt.reconnection_default_timeout
                result = await asyncio.wait_for(connect_func(), timeout=timeout)

                # Success!
                self.stats.successful_connections += 1
                self.stats.last_connection_time = utc_now()
                self.stats.current_backoff_seconds = 0.0

                logger.info(f"{self.service_name}: Connected successfully on attempt {attempt + 1}")

                # Call success callback
                if self.config.on_success:
                    self.config.on_success(attempt)

                return result

            except asyncio.TimeoutError:
                logger.warning(f"{self.service_name}: Connection timeout on attempt {attempt + 1}")
            except OSError as e:
                logger.warning(
                    f"{self.service_name}: Connection failed on attempt {attempt + 1}: {e}"
                )
            except Exception as e:
                logger.warning(
                    f"{self.service_name}: Connection failed on attempt {attempt + 1}: {e}"
                )

            # Check if we should alert
            if attempt + 1 >= self.config.alert_after_attempts:
                if self.config.alert_callback:
                    self.config.alert_callback(attempt + 1)
                logger.error(f"{self.service_name}: Failed {attempt + 1} connection attempts")

            # Don't wait after last attempt
            if attempt < self.config.max_attempts - 1:
                # Calculate backoff and wait
                wait_time = self.calculate_backoff(attempt)
                logger.info(f"{self.service_name}: Waiting {wait_time:.2f}s before retry")
                await asyncio.sleep(wait_time)

        # All attempts failed
        self.stats.failed_connections += 1
        self.stats.last_failure_time = utc_now()

        # Call failure callback
        if self.config.on_failure:
            self.config.on_failure()

        logger.error(
            f"{self.service_name}: All {self.config.max_attempts} connection attempts failed"
        )

        return None

    async def maintain_connection(
        self,
        connect_func: Callable[[], Any],
        check_func: Callable[[], Awaitable[bool]] | None = None,
        reconnect_delay: float | None = None,
    ):
        """
        Continuously maintain connection, reconnecting if lost.

        Args:
            connect_func: Async function that attempts connection
            check_func: Optional function to check if connection is alive
            reconnect_delay: Delay before attempting reconnection (uses centralized config if None)
        """
        # Use centralized config for reconnect_delay if not provided
        if reconnect_delay is None:
            tt = get_config().trading_thresholds
            reconnect_delay = tt.reconnection_maintain_delay
        while True:
            try:
                # Try to connect
                connection = await self.connect_with_backoff(connect_func)

                if connection is None:
                    # Connection failed, wait before retry
                    await asyncio.sleep(reconnect_delay)
                    continue

                # Connection successful, monitor it
                if check_func:
                    # Monitor connection health - use centralized config interval
                    tt = get_config().trading_thresholds
                    health_check_interval = tt.reconnection_health_check_interval
                    while True:
                        await asyncio.sleep(health_check_interval)

                        if not await check_func():
                            logger.warning(f"{self.service_name}: Connection lost")
                            break
                else:
                    # No health check, just wait forever
                    await asyncio.sleep(float("inf"))

            except asyncio.CancelledError:
                logger.info(f"{self.service_name}: Connection maintenance cancelled")
                break
            except (asyncio.TimeoutError, OSError) as e:
                logger.error(f"{self.service_name}: Error in connection maintenance: {e}")
                await asyncio.sleep(reconnect_delay)

    def get_stats(self) -> dict[str, Any]:
        """Get connection statistics."""
        return {
            "service_name": self.service_name,
            "total_attempts": self.stats.total_attempts,
            "successful_connections": self.stats.successful_connections,
            "failed_connections": self.stats.failed_connections,
            "success_rate": self.stats.success_rate,
            "last_connection_time": (
                self.stats.last_connection_time.isoformat()
                if self.stats.last_connection_time
                else None
            ),
            "last_failure_time": (
                self.stats.last_failure_time.isoformat() if self.stats.last_failure_time else None
            ),
            "current_backoff_seconds": self.stats.current_backoff_seconds,
        }
