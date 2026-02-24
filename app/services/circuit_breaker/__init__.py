"""
Circuit Breaker Package

Provides risk management circuit breakers for algorithmic trading:

- DailyCircuitBreaker: Daily loss-based circuit breaker (FASE 5 Task 2)
- Tracks daily P&L and halts trading at -5% threshold (Chan #15, Hull #65)

Example:
    >>> from app.services.circuit_breaker import DailyCircuitBreaker, create_daily_breaker
    >>> breaker = create_daily_breaker(threshold_pct=-0.05)
    >>> breaker.reset_for_trading_day(starting_equity=100000)
    >>> if not breaker.can_trade():
    ...     print("Trading halted by circuit breaker")
"""

from app.services.circuit_breaker.daily_circuit_breaker import (
    DailyBreakerEvent,
    DailyBreakerState,
    DailyBreakerStatus,
    DailyCircuitBreaker,
    create_daily_breaker,
)

__all__ = [
    "DailyCircuitBreaker",
    "DailyBreakerState",
    "DailyBreakerStatus",
    "DailyBreakerEvent",
    "create_daily_breaker",
]
