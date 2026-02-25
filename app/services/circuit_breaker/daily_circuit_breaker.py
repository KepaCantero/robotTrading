"""
Daily Circuit Breaker for Trading Strategy Risk Management (FASE 5 Task 2)

This module implements daily loss-based circuit breaking per Chan (2013) and Hull (2018):
- Tracks daily P&L in real-time
- Halts trading when -5% daily threshold is reached
- Resets at the start of the next trading day

This is a CRITICAL risk control component for backtesting and live trading.

Reference:
    Chan, E. (2013). "Algorithmic Trading." Chapter 15
    Hull, J. (2018). "Risk Management and Financial Institutions." Chapter 65
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from app.shared.config.centralized_config import get_config
from app.shared.utils.timezone_utils import utc_now

logger = logging.getLogger(__name__)


class DailyBreakerStatus(str, Enum):
    """Status of the daily circuit breaker."""

    ARMED = "armed"  # Monitoring, trading allowed
    TRIGGERED = "triggered"  # Threshold exceeded, trading halted
    RESET_PENDING = "reset_pending"  # Waiting for next trading day


@dataclass
class DailyBreakerEvent:
    """
    Record of a daily circuit breaker event.

    Attributes:
        timestamp: When the event occurred
        trading_date: The trading date for the event
        daily_pnl_pct: Daily P&L percentage at trigger time
        threshold_pct: The threshold that was triggered
        equity_before: Equity before the trigger trade
        equity_after: Equity after the trigger trade
        trigger_symbol: Symbol that caused the trigger (if any)
        reason: Description of what triggered the event
    """

    timestamp: datetime
    trading_date: date
    daily_pnl_pct: Decimal
    threshold_pct: Decimal
    equity_before: Decimal
    equity_after: Decimal
    trigger_symbol: Optional[str] = None
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "trading_date": self.trading_date.isoformat(),
            "daily_pnl_pct": float(self.daily_pnl_pct),
            "threshold_pct": float(self.threshold_pct),
            "equity_before": float(self.equity_before),
            "equity_after": float(self.equity_after),
            "trigger_symbol": self.trigger_symbol,
            "reason": self.reason,
        }


@dataclass
class DailyBreakerState:
    """
    Current state of the daily circuit breaker.

    Attributes:
        trading_date: Current trading date being tracked
        status: Current breaker status
        starting_equity: Equity at start of trading day
        current_equity: Current equity value
        daily_pnl: Daily P&L in dollars
        daily_pnl_pct: Daily P&L as percentage
        threshold_pct: Loss threshold that triggers halt
        last_event: Most recent breaker event (if any)
        last_update: When state was last updated
    """

    trading_date: date
    status: DailyBreakerStatus
    starting_equity: Decimal
    current_equity: Decimal
    daily_pnl: Decimal
    daily_pnl_pct: Decimal
    threshold_pct: Decimal
    last_event: Optional[DailyBreakerEvent] = None
    last_update: datetime = field(default_factory=utc_now)

    @property
    def is_trading_halted(self) -> bool:
        """Check if trading is currently halted."""
        return self.status == DailyBreakerStatus.TRIGGERED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "trading_date": self.trading_date.isoformat(),
            "status": self.status.value,
            "starting_equity": float(self.starting_equity),
            "current_equity": float(self.current_equity),
            "daily_pnl": float(self.daily_pnl),
            "daily_pnl_pct": float(self.daily_pnl_pct),
            "threshold_pct": float(self.threshold_pct),
            "is_trading_halted": self.is_trading_halted,
            "last_event": self.last_event.to_dict() if self.last_event else None,
            "last_update": self.last_update.isoformat(),
        }


class DailyCircuitBreaker:
    """
    Daily loss-based circuit breaker for risk management.

    Per Chan (2013), Chapter 15, and Hull (2018), Chapter 65:
    - Tracks daily P&L in real-time during backtesting or live trading
    - Halts all trading when daily loss exceeds threshold (uses centralized config)
    - Resets at the start of the next trading day

    This protects against:
    - Catastrophic strategy failures
    - Market regime shifts
    - Technical issues causing excessive losses

    Example:
        >>> breaker = DailyCircuitBreaker()
        >>> breaker.reset_for_trading_day(starting_equity=Decimal("100000"))
        >>>
        >>> # After a trade
        >>> breaker.update_pnl(current_equity=Decimal("96000"))
        >>> if breaker.is_trading_halted():
        ...     print("Trading halted due to daily loss limit")
    """

    def __init__(
        self,
        threshold_pct: Optional[Decimal] = None,
        auto_reset_on_new_day: bool = True,
    ):
        """
        Initialize the daily circuit breaker.

        Args:
            threshold_pct: Daily loss threshold as negative decimal
                (default: uses centralized config -5%)
            auto_reset_on_new_day: Automatically reset when new trading day detected
        """
        # Use centralized config for default threshold
        if threshold_pct is None:
            threshold_pct = Decimal(str(get_config().trading_thresholds.circuit_breaker_daily_loss))

        self.threshold_pct = threshold_pct
        self.auto_reset_on_new_day = auto_reset_on_new_day
        self._state: Optional[DailyBreakerState] = None
        self._event_history: List[DailyBreakerEvent] = []

        # Store config reference for other values
        self._tt = get_config().trading_thresholds

    def reset_for_trading_day(
        self,
        starting_equity: Decimal,
        trading_date: Optional[date] = None,
    ) -> DailyBreakerState:
        """
        Reset the circuit breaker for a new trading day.

        This should be called at the start of each trading day to:
        - Set the starting equity baseline
        - Reset the breaker status to ARMED
        - Clear any previous halt

        Args:
            starting_equity: Portfolio equity at start of trading day
            trading_date: Trading date (defaults to today)

        Returns:
            The new breaker state

        Raises:
            ValueError: If starting_equity is less than minimum
        """
        # Use config value for minimum equity (1 dollar minimum)
        min_equity = Decimal("1.0")
        if starting_equity < min_equity:
            raise ValueError(f"Starting equity {starting_equity} must be >= {min_equity}")

        current_date = trading_date or utc_now().date()

        self._state = DailyBreakerState(
            trading_date=current_date,
            status=DailyBreakerStatus.ARMED,
            starting_equity=starting_equity,
            current_equity=starting_equity,
            daily_pnl=Decimal("0"),
            daily_pnl_pct=Decimal("0"),
            threshold_pct=self.threshold_pct,
        )

        logger.info(
            f"Daily circuit breaker reset for {current_date}: "
            f"starting_equity=${starting_equity:.2f}, threshold={self.threshold_pct:.2%}"
        )

        return self._state

    def update_pnl(
        self,
        current_equity: Decimal,
        trigger_symbol: Optional[str] = None,
    ) -> DailyBreakerState:
        """
        Update daily P&L and check if breaker should trigger.

        This should be called after each trade or at regular intervals
        to track daily performance and potentially halt trading.

        Args:
            current_equity: Current portfolio equity
            trigger_symbol: Symbol that caused the P&L change (if applicable)

        Returns:
            Updated breaker state

        Raises:
            RuntimeError: If breaker has not been reset for trading day
        """
        if self._state is None:
            raise RuntimeError(
                "Circuit breaker not initialized. Call reset_for_trading_day() first."
            )

        # Check for new trading day
        current_date = utc_now().date()
        if self.auto_reset_on_new_day and current_date != self._state.trading_date:
            logger.info(f"New trading day detected: {current_date}")
            return self.reset_for_trading_day(starting_equity=current_equity)

        # If already triggered, no further action
        if self._state.is_trading_halted:
            logger.warning("Trading already halted, P&L update ignored")
            return self._state

        # Calculate daily P&L
        daily_pnl = current_equity - self._state.starting_equity
        daily_pnl_pct = daily_pnl / self._state.starting_equity

        # Update state
        self._state.current_equity = current_equity
        self._state.daily_pnl = daily_pnl
        self._state.daily_pnl_pct = daily_pnl_pct
        self._state.last_update = utc_now()

        # Check if threshold exceeded
        if daily_pnl_pct <= self.threshold_pct:
            self._trigger_breaker(trigger_symbol=trigger_symbol)

        return self._state

    def _trigger_breaker(self, trigger_symbol: Optional[str] = None) -> None:
        """
        Trigger the circuit breaker and halt trading.

        Creates a breaker event and updates status to TRIGGERED.

        Args:
            trigger_symbol: Symbol that caused the trigger
        """
        if self._state is None:
            return

        event = DailyBreakerEvent(
            timestamp=utc_now(),
            trading_date=self._state.trading_date,
            daily_pnl_pct=self._state.daily_pnl_pct,
            threshold_pct=self._state.threshold_pct,
            equity_before=self._state.starting_equity,
            equity_after=self._state.current_equity,
            trigger_symbol=trigger_symbol,
            reason=(
                f"Daily P&L ({self._state.daily_pnl_pct:.2%}) exceeded threshold "
                f"({self._state.threshold_pct:.2%})"
            ),
        )

        self._state.status = DailyBreakerStatus.TRIGGERED
        self._state.last_event = event
        self._event_history.append(event)

        logger.critical(
            f"DAILY CIRCUIT BREAKER TRIGGERED: {event.reason}\n"
            f"  Trading Date: {self._state.trading_date}\n"
            f"  Starting Equity: ${self._state.starting_equity:,.2f}\n"
            f"  Current Equity: ${self._state.current_equity:,.2f}\n"
            f"  Daily P&L: {self._state.daily_pnl_pct:.2%}\n"
            f"  Threshold: {self._state.threshold_pct:.2%}"
        )

    def is_trading_halted(self) -> bool:
        """
        Check if trading is currently halted.

        Returns:
            True if breaker is triggered and trading is halted
        """
        if self._state is None:
            return False
        return self._state.is_trading_halted

    def get_state(self) -> Optional[DailyBreakerState]:
        """
        Get current breaker state.

        Returns:
            Current state or None if not initialized
        """
        return self._state

    def get_event_history(self) -> List[DailyBreakerEvent]:
        """
        Get history of all breaker events.

        Returns:
            List of events in chronological order
        """
        return self._event_history.copy()

    def can_trade(self) -> bool:
        """
        Check if trading is allowed.

        Convenience method for checking if new trades can be executed.

        Returns:
            True if trading is allowed (breaker is armed and not triggered)
        """
        if self._state is None:
            return False
        return self._state.status == DailyBreakerStatus.ARMED


# Convenience function for creating breaker with default settings
def create_daily_breaker(threshold_pct: float = -0.05) -> DailyCircuitBreaker:
    """
    Create a daily circuit breaker with specified threshold.

    Args:
        threshold_pct: Loss threshold as percentage (e.g., -0.05 for -5%)

    Returns:
        Configured DailyCircuitBreaker instance
    """
    return DailyCircuitBreaker(threshold_pct=Decimal(str(threshold_pct)))
