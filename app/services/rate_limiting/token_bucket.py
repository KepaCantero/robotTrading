"""
Rate Limiter - Token bucket algorithm for rate limiting.

Protects against hitting broker API rate limits:
- IBKR: 50-100 req/s
- Alpaca: 200 req/min
- Interactive Brokers has different limits for different endpoints

Uses token bucket algorithm for smooth rate limiting.

Phase 3.4: Broker API Rate Limiting for 24/7 Operation
- Token bucket rate limiting per broker
- Priority queue (close position > query price)
- Exponential backoff on 429 errors
- Rate limit monitoring and alerts
- Configurable limits per broker

Uses centralized configuration for all rate limits and backoff parameters.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum, IntEnum
from typing import Callable, Dict, List, Optional

from requests.exceptions import HTTPError

from app.core.centralized_config import get_config
from app.core.timezone_utils import utc_now

logger = logging.getLogger(__name__)


class BrokerType(Enum):
    """Broker types with different rate limits."""

    IBKR = "ibkr"
    ALPACA = "alpaca"
    POLYGON = "polygon"
    BINANCE = "binance"


class RequestPriority(IntEnum):
    """
    Request priority levels.

    Higher priority requests get preferential treatment when rate limits are approached.
    Critical operations like closing positions should have higher priority.

    Values:
        CRITICAL: 100 - Close positions, emergency operations
        HIGH: 75 - Place orders, modify orders
        MEDIUM: 50 - Query positions, account data
        LOW: 25 - Query historical data, market data
        BACKGROUND: 0 - Analytics, reporting
    """

    CRITICAL = 100  # Close positions, emergency operations
    HIGH = 75  # Place orders, modify orders
    MEDIUM = 50  # Query positions, account data
    LOW = 25  # Query historical data, market data
    BACKGROUND = 0  # Analytics, reporting


@dataclass
class RateLimit:
    """Rate limit configuration."""

    requests_per_second: float
    burst_capacity: int = 10

    def to_per_minute(self) -> int:
        """Convert to requests per minute."""
        return int(self.requests_per_second * 60)

    def to_per_hour(self) -> int:
        """Convert to requests per hour."""
        return int(self.requests_per_second * 3600)


def _get_broker_rate_limits() -> Dict[BrokerType, RateLimit]:
    """
    Get broker-specific rate limits from centralized config.

    Returns:
        Dict mapping BrokerType to RateLimit configuration
    """
    # Get rate limits from centralized config
    tt = get_config().trading_thresholds

    return {
        BrokerType.IBKR: RateLimit(
            requests_per_second=float(tt.rate_limit_ibkr_requests_per_second),
            burst_capacity=tt.rate_limit_ibkr_burst_capacity,
        ),
        BrokerType.ALPACA: RateLimit(
            requests_per_second=float(tt.rate_limit_alpaca_requests_per_second),
            burst_capacity=tt.rate_limit_alpaca_burst_capacity,
        ),
        BrokerType.POLYGON: RateLimit(
            requests_per_second=float(tt.rate_limit_polygon_requests_per_second),
            burst_capacity=tt.rate_limit_polygon_burst_capacity,
        ),
        BrokerType.BINANCE: RateLimit(
            requests_per_second=float(tt.rate_limit_binance_requests_per_second),
            burst_capacity=tt.rate_limit_binance_burst_capacity,
        ),
    }


# Broker-specific rate limits (loaded from centralized config)
BROKER_RATE_LIMITS = _get_broker_rate_limits()


@dataclass
class TokenBucketState:
    """State of a token bucket."""

    tokens: float
    last_update: float

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "tokens": self.tokens,
            "last_update": self.last_update,
            "last_update_iso": utc_now().fromtimestamp(self.last_update).isoformat(),
        }


@dataclass
class RateLimitStatistics:
    """Statistics for rate limiter."""

    requests_total: int = 0
    requests_allowed: int = 0
    requests_throttled: int = 0
    wait_time_total: float = 0.0
    backoff_count: int = 0

    @property
    def throttle_rate(self) -> float:
        """Calculate throttle rate as percentage."""
        if self.requests_total == 0:
            return 0.0
        return (self.requests_throttled / self.requests_total) * 100

    @property
    def average_wait_time(self) -> float:
        """Calculate average wait time in seconds."""
        if self.requests_allowed == 0:
            return 0.0
        return self.wait_time_total / self.requests_allowed

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "requests_total": self.requests_total,
            "requests_allowed": self.requests_allowed,
            "requests_throttled": self.requests_throttled,
            "throttle_rate_percent": round(self.throttle_rate, 2),
            "wait_time_total_seconds": round(self.wait_time_total, 3),
            "average_wait_time_seconds": round(self.average_wait_time, 3),
            "backoff_count": self.backoff_count,
        }


class TokenBucketRateLimiter:
    """
    Token bucket algorithm for rate limiting.

    Features:
    - Token bucket rate limiting per broker
    - Priority queue (close position > query price)
    - Exponential backoff on 429 errors
    - Rate limit monitoring and alerts
    - Configurable limits per broker

    The token bucket algorithm works as follows:
    1. Bucket has a maximum capacity (burst capacity)
    2. Tokens are added at a constant rate (requests per second)
    3. Each request consumes one or more tokens
    4. If bucket is empty, requests must wait for tokens to refill
    5. Bucket can burst up to capacity if not recently used

    Example:
        >>> from app.services.rate_limiting import BrokerType, TokenBucketRateLimiter
        >>> limiter = TokenBucketRateLimiter(BrokerType.IBKR)
        >>> await limiter.acquire()  # Acquire tokens, wait if necessary
        >>> await limiter.acquire_with_backoff()  # With exponential backoff
        >>> stats = limiter.get_statistics()
    """

    def __init__(
        self,
        broker_type: BrokerType,
        rate_limit: Optional[RateLimit] = None,
        on_limit_exceeded: Optional[Callable[[], None]] = None,
        alert_threshold: Optional[float] = None,
    ):
        """
        Initialize token bucket rate limiter.

        Args:
            broker_type: Type of broker
            rate_limit: Custom rate limit (uses default if None)
            on_limit_exceeded: Callback when limit exceeded
            alert_threshold: Alert when token usage exceeds this ratio (uses centralized config if None)
        """
        self.broker_type = broker_type
        self.rate_limit = rate_limit or BROKER_RATE_LIMITS.get(broker_type)
        if self.rate_limit is None:
            raise ValueError(f"No rate limit configured for broker: {broker_type}")

        self.on_limit_exceeded = on_limit_exceeded

        # Use centralized config for alert_threshold if not provided
        if alert_threshold is None:
            tt = get_config().trading_thresholds
            alert_threshold = tt.rate_limit_alert_threshold
        self.alert_threshold = alert_threshold

        # Token bucket state
        self._state = TokenBucketState(
            tokens=float(self.rate_limit.burst_capacity), last_update=time.time()
        )

        # Priority queue for pending requests
        self._priority_queue: List[tuple[int, asyncio.Future]] = []

        # Statistics
        self._stats = RateLimitStatistics()

        # Lock for thread safety
        self._lock = asyncio.Lock()

        logger.info(
            f"TokenBucketRateLimiter initialized for {broker_type.value}: "
            f"{self.rate_limit.requests_per_second} req/s, "
            f"burst {self.rate_limit.burst_capacity}"
        )

    async def acquire(
        self,
        tokens: int = 1,
        priority: int = RequestPriority.MEDIUM,
        timeout: Optional[float] = None,
    ) -> bool:
        """
        Acquire tokens, wait if necessary.

        Args:
            tokens: Number of tokens to acquire
            priority: Priority level (higher = more important)
            timeout: Max time to wait (None = infinite)

        Returns:
            True if tokens acquired, False if timeout

        Example:
            >>> limiter = TokenBucketRateLimiter(BrokerType.IBKR)
            >>> # High priority request (closing position)
            >>> await limiter.acquire(priority=RequestPriority.CRITICAL)
            >>> # Low priority request (querying historical data)
            >>> await limiter.acquire(priority=RequestPriority.LOW)
        """
        if tokens > self.rate_limit.burst_capacity:
            raise ValueError(
                f"Cannot acquire {tokens} tokens, "
                f"burst capacity is {self.rate_limit.burst_capacity}"
            )

        async with self._lock:
            self._stats.requests_total += 1

        start_time = time.time()

        while True:
            # Try to acquire
            acquired = await self._try_acquire(tokens, priority)

            if acquired:
                async with self._lock:
                    self._stats.requests_allowed += 1
                    self._stats.wait_time_total += time.time() - start_time
                return True

            # Check timeout
            if timeout and (time.time() - start_time) >= timeout:
                async with self._lock:
                    self._stats.requests_throttled += 1
                logger.warning(f"Rate limit timeout after {timeout}s")
                return False

            # Calculate wait time
            wait_time = self._calculate_wait_time(tokens)

            if timeout:
                remaining_time = timeout - (time.time() - start_time)
                wait_time = min(wait_time, remaining_time)

            # Wait for refill
            await asyncio.sleep(wait_time)

    async def _try_acquire(self, tokens: int, priority: int) -> bool:
        """Try to acquire tokens without waiting."""
        async with self._lock:
            now = time.time()

            # Refill tokens based on time elapsed
            elapsed = now - self._state.last_update
            refill = elapsed * self.rate_limit.requests_per_second

            self._state.tokens = min(
                self._state.tokens + refill, float(self.rate_limit.burst_capacity)
            )
            self._state.last_update = now

            # Check for low token alert
            utilization = 1.0 - (self._state.tokens / self.rate_limit.burst_capacity)
            if utilization >= self.alert_threshold:
                logger.warning(
                    f"Rate limit alert for {self.broker_type.value}: "
                    f"{utilization:.1%} utilized ({self._state.tokens:.1f} tokens remaining)"
                )

            # Check if we have enough tokens
            if self._state.tokens >= tokens:
                self._state.tokens -= tokens
                return True

            # Not enough tokens - check priority queue
            # Higher priority requests can preempt lower priority ones
            if self._priority_queue:
                # Sort by priority (highest first)
                self._priority_queue.sort(key=lambda x: x[0], reverse=True)

                # Check if this request has higher priority than queued ones
                if self._priority_queue and priority > self._priority_queue[0][0]:
                    # Preempt lower priority request
                    self._priority_queue.pop(0)
                    self._state.tokens -= tokens
                    return True

            # Queue the request
            future = asyncio.Future()
            self._priority_queue.append((priority, future))

            return False

    def _calculate_wait_time(self, tokens: int) -> float:
        """Calculate wait time for token refill."""
        now = time.time()

        # Refill tokens based on time elapsed
        elapsed = now - self._state.last_update
        refill = elapsed * self.rate_limit.requests_per_second

        current_tokens = min(self._state.tokens + refill, float(self.rate_limit.burst_capacity))

        # Calculate time needed for refill
        tokens_needed = tokens - current_tokens
        wait_time = tokens_needed / self.rate_limit.requests_per_second

        # Add small buffer to ensure tokens are available
        return max(wait_time, 0.01)

    async def acquire_with_backoff(
        self,
        tokens: int = 1,
        max_retries: Optional[int] = None,
        initial_backoff: Optional[float] = None,
        priority: int = RequestPriority.MEDIUM,
    ) -> bool:
        """
        Acquire tokens with exponential backoff on 429 errors.

        This method should be used when making API calls that might return
        429 (Too Many Requests) errors. It implements exponential backoff
        with jitter to help recover from rate limit errors.

        Args:
            tokens: Number of tokens to acquire
            max_retries: Maximum retry attempts (uses centralized config if None)
            initial_backoff: Initial backoff time in seconds (uses centralized config if None)
            priority: Priority level for the request

        Returns:
            True if tokens acquired, False if all retries failed

        Example:
            >>> limiter = TokenBucketRateLimiter(BrokerType.IBKR)
            >>> success = await limiter.acquire_with_backoff(
            ...     max_retries=5,
            ...     initial_backoff=2.0
            ... )
        """
        # Use centralized config for defaults if not provided
        if max_retries is None or initial_backoff is None:
            tt = get_config().trading_thresholds
            if max_retries is None:
                max_retries = tt.rate_limit_max_retries
            if initial_backoff is None:
                initial_backoff = tt.rate_limit_initial_backoff

        for attempt in range(max_retries):
            try:
                # Try to acquire - use centralized config for timeout
                tt = get_config().trading_thresholds
                timeout = tt.rate_limit_default_timeout
                if await self.acquire(tokens, priority=priority, timeout=timeout):
                    return True

            except (asyncio.TimeoutError, ConnectionError, OSError) as e:
                if attempt < max_retries - 1:
                    # Exponential backoff with jitter - use centralized config for jitter pct
                    tt = get_config().trading_thresholds
                    backoff = initial_backoff * (2**attempt)
                    jitter_pct = tt.rate_limit_backoff_jitter_pct
                    jitter = backoff * jitter_pct
                    wait_time = backoff + (jitter * (2 * (hash(id(self)) % 100) / 100 - 1))

                    logger.warning(
                        f"Rate limit exceeded, backing off {wait_time:.2f}s "
                        f"(attempt {attempt + 1}/{max_retries}): {e}"
                    )

                    # Update statistics
                    async with self._lock:
                        self._stats.backoff_count += 1

                    # Call callback if registered
                    if self.on_limit_exceeded:
                        try:
                            self.on_limit_exceeded()
                        except (
                            ConnectionError,
                            TimeoutError,
                            HTTPError,
                            ValueError,
                        ) as callback_error:
                            logger.error(f"Error in limit exceeded callback: {callback_error}")

                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Rate limit: all {max_retries} retries failed")
                    return False

        return False

    def get_available_tokens(self) -> int:
        """
        Get currently available tokens.

        This method triggers a token refill calculation before returning
        the available token count.

        Returns:
            Number of tokens currently available

        Example:
            >>> limiter = TokenBucketRateLimiter(BrokerType.IBKR)
            >>> tokens = limiter.get_available_tokens()
            >>> print(f"Available tokens: {tokens}")
        """
        # Trigger refill calculation (synchronous)
        now = time.time()

        # Refill tokens based on time elapsed
        elapsed = now - self._state.last_update
        refill = elapsed * self.rate_limit.requests_per_second

        self._state.tokens = min(self._state.tokens + refill, float(self.rate_limit.burst_capacity))
        self._state.last_update = now

        return int(self._state.tokens)

    def get_utilization(self) -> float:
        """
        Get current bucket utilization as a ratio.

        Returns:
            Utilization ratio (0.0 to 1.0), where 1.0 means bucket is empty

        Example:
            >>> limiter = TokenBucketRateLimiter(BrokerType.IBKR)
            >>> utilization = limiter.get_utilization()
            >>> print(f"Bucket utilization: {utilization:.1%}")
        """
        available = self.get_available_tokens()
        return 1.0 - (available / self.rate_limit.burst_capacity)

    def get_statistics(self) -> Dict[str, any]:
        """
        Get rate limiter statistics.

        Returns:
            Dictionary containing current state and statistics

        Example:
            >>> limiter = TokenBucketRateLimiter(BrokerType.IBKR)
            >>> stats = limiter.get_statistics()
            >>> print(stats)
        """
        return {
            "broker_type": self.broker_type.value,
            "rate_limit": {
                "requests_per_second": self.rate_limit.requests_per_second,
                "burst_capacity": self.rate_limit.burst_capacity,
                "requests_per_minute": self.rate_limit.to_per_minute(),
                "requests_per_hour": self.rate_limit.to_per_hour(),
            },
            "state": self._state.to_dict(),
            "statistics": self._stats.to_dict(),
            "utilization": round(self.get_utilization() * 100, 2),
            "available_tokens": self.get_available_tokens(),
        }

    def reset(self) -> None:
        """
        Reset rate limiter state.

        This resets the token bucket to full capacity and clears all statistics.
        Use this when switching to a new API key or after extended downtime.

        Example:
            >>> limiter = TokenBucketRateLimiter(BrokerType.IBKR)
            >>> limiter.reset()
        """
        # Use synchronous approach for reset
        self._state = TokenBucketState(
            tokens=float(self.rate_limit.burst_capacity), last_update=time.time()
        )
        self._priority_queue.clear()
        self._stats = RateLimitStatistics()

        logger.info(f"Rate limiter reset for {self.broker_type.value}")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # No cleanup needed

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"TokenBucketRateLimiter(broker={self.broker_type.value}, "
            f"rate={self.rate_limit.requests_per_second} req/s, "
            f"tokens={self.get_available_tokens()}/{self.rate_limit.burst_capacity})"
        )


class RateLimitManager:
    """
    Manage multiple rate limiters for different brokers.

    This is a singleton manager that provides a centralized point for
    accessing and managing rate limiters for all supported brokers.

    Example:
        >>> from app.services.rate_limiting import RateLimitManager, BrokerType
        >>> manager = RateLimitManager()
        >>> limiter = manager.get_limiter(BrokerType.IBKR)
        >>> await limiter.acquire()
        >>> all_stats = manager.get_all_statistics()
    """

    def __init__(self):
        """Initialize rate limit manager."""
        self._limiters: Dict[BrokerType, TokenBucketRateLimiter] = {}

        logger.info("RateLimitManager initialized")

    def get_limiter(
        self,
        broker_type: BrokerType,
        create_if_missing: bool = True,
        rate_limit: Optional[RateLimit] = None,
        on_limit_exceeded: Optional[Callable[[], None]] = None,
    ) -> Optional[TokenBucketRateLimiter]:
        """
        Get rate limiter for a specific broker.

        Args:
            broker_type: Type of broker
            create_if_missing: Create limiter if it doesn't exist
            rate_limit: Custom rate limit (only used if creating new limiter)
            on_limit_exceeded: Callback when limit exceeded (only used if creating new limiter)

        Returns:
            TokenBucketRateLimiter instance or None if not found and not created

        Example:
            >>> manager = RateLimitManager()
            >>> limiter = manager.get_limiter(BrokerType.IBKR)
        """
        if broker_type not in self._limiters and create_if_missing:
            self._limiters[broker_type] = TokenBucketRateLimiter(
                broker_type, rate_limit=rate_limit, on_limit_exceeded=on_limit_exceeded
            )

        return self._limiters.get(broker_type)

    def remove_limiter(self, broker_type: BrokerType) -> bool:
        """
        Remove a rate limiter.

        Args:
            broker_type: Type of broker

        Returns:
            True if limiter was removed, False if it didn't exist

        Example:
            >>> manager = RateLimitManager()
            >>> manager.remove_limiter(BrokerType.ALPACA)
        """
        if broker_type in self._limiters:
            del self._limiters[broker_type]
            logger.info(f"Removed rate limiter for {broker_type.value}")
            return True
        return False

    def reset_limiter(self, broker_type: BrokerType) -> bool:
        """
        Reset a specific rate limiter.

        Args:
            broker_type: Type of broker

        Returns:
            True if limiter was reset, False if it doesn't exist

        Example:
            >>> manager = RateLimitManager()
            >>> manager.reset_limiter(BrokerType.IBKR)
        """
        limiter = self._limiters.get(broker_type)
        if limiter:
            limiter.reset()
            return True
        return False

    def reset_all(self) -> None:
        """
        Reset all rate limiters.

        Example:
            >>> manager = RateLimitManager()
            >>> manager.reset_all()
        """
        for limiter in self._limiters.values():
            limiter.reset()
        logger.info("All rate limiters reset")

    def get_all_statistics(self) -> Dict[str, Dict]:
        """
        Get statistics for all limiters.

        Returns:
            Dictionary mapping broker type names to their statistics

        Example:
            >>> manager = RateLimitManager()
            >>> stats = manager.get_all_statistics()
            >>> for broker, broker_stats in stats.items():
            ...     print(f"{broker}: {broker_stats['statistics']}")
        """
        return {
            broker_type.value: limiter.get_statistics()
            for broker_type, limiter in self._limiters.items()
        }

    def get_summary(self) -> Dict[str, any]:
        """
        Get a summary of all rate limiters.

        Returns:
            Dictionary with summary information for all limiters

        Example:
            >>> manager = RateLimitManager()
            >>> summary = manager.get_summary()
        """
        stats = self.get_all_statistics()

        return {
            "total_limiters": len(self._limiters),
            "brokers": list(self._limiters.keys()),
            "statistics": stats,
        }

    def __repr__(self) -> str:
        """String representation."""
        return f"RateLimitManager(limiters={len(self._limiters)})"
