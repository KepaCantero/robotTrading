"""
Broker API Rate Limiting Module - Phase 3.4

This module provides rate limiting functionality for broker API calls to prevent
hitting broker API limits during 24/7 trading operations.

Features:
- Token bucket rate limiting per broker
- Priority queue (close position > query price)
- Exponential backoff on 429 errors
- Rate limit monitoring and alerts
- Configurable limits per broker

Supported Brokers:
- IBKR (Interactive Brokers): 50-100 req/s
- Alpaca: 200 req/min
- Polygon: 5 req/s
- Binance: 10 req/s

Usage:
    from app.services.rate_limiting import (
        BrokerType,
        TokenBucketRateLimiter,
        RateLimitManager,
        get_rate_limit_manager,
    )

    # Get the global rate limit manager
    manager = get_rate_limit_manager()

    # Get a limiter for a specific broker
    limiter = manager.get_limiter(BrokerType.IBKR)

    # Acquire tokens before making API calls
    await limiter.acquire()

    # Or use with backoff for resilience
    await limiter.acquire_with_backoff()
"""

from app.services.rate_limiting.token_bucket import (
    BrokerType,
    RateLimit,
    RateLimitManager,
    TokenBucketRateLimiter,
    TokenBucketState,
    BROKER_RATE_LIMITS,
)

__all__ = [
    # Core classes
    "BrokerType",
    "RateLimit",
    "RateLimitManager",
    "TokenBucketRateLimiter",
    "TokenBucketState",
    # Constants
    "BROKER_RATE_LIMITS",
]


# Global singleton instance
_rate_limit_manager: RateLimitManager = None


def get_rate_limit_manager() -> RateLimitManager:
    """
    Get the global rate limit manager singleton instance.

    This is the recommended way to access the rate limit manager throughout
    the application. The singleton pattern ensures a single point of control
    for all broker rate limiters.

    Returns:
        RateLimitManager: The global rate limit manager instance

    Example:
        >>> from app.services.rate_limiting import get_rate_limit_manager, BrokerType
        >>> manager = get_rate_limit_manager()
        >>> limiter = manager.get_limiter(BrokerType.IBKR)
        >>> await limiter.acquire()
    """
    global _rate_limit_manager
    if _rate_limit_manager is None:
        _rate_limit_manager = RateLimitManager()
    return _rate_limit_manager
