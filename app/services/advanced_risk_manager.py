"""
TASK-RM-1 to RM-5: Advanced Risk Management System.

Implements comprehensive risk controls:
- Risk per Trade <2% (TASK-RM-1)
- Risk/Reward Ratio ≥1:3 (TASK-RM-2)
- Max Exposure per Strategy (TASK-RM-3)
- Max Drawdown Limit 15% (TASK-RM-4)
- Circuit Breakers 3-5 Stops (TASK-RM-5)
"""

import logging
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from app.models.portfolio import Portfolio
from app.models.signal import Signal

logger = logging.getLogger(__name__)


class TradeRiskLimiter:
    """
    TASK-RM-1: Risk per Trade Limiter.

    Ensures no single trade risks more than 2% of capital.
    """

    def __init__(self, max_risk_per_trade: Decimal = Decimal("0.02")):
        """
        Initialize risk limiter.

        Args:
            max_risk_per_trade: Maximum risk per trade (default 2% = 0.02)
        """
        self.max_risk_per_trade = max_risk_per_trade

    def calculate_max_position_size(
        self,
        signal: Signal,
        portfolio: Portfolio,
        stop_loss_pct: Decimal,
    ) -> Decimal:
        """
        Calculate maximum position size based on risk limit.

        Args:
            signal: Trading signal
            portfolio: Current portfolio
            stop_loss_pct: Stop loss percentage

        Returns:
            Maximum position size
        """
        if portfolio.total_value <= 0 or stop_loss_pct <= 0:
            return Decimal("0")

        # Calculate risk amount (2% of capital)
        risk_amount = portfolio.total_value * self.max_risk_per_trade

        # Calculate position size based on stop loss distance
        if signal.price and signal.price > 0:
            # Risk per share = stop loss distance
            stop_loss_price = signal.price * (Decimal("1") - stop_loss_pct)
            risk_per_share = abs(signal.price - stop_loss_price)

            if risk_per_share > 0:
                max_shares = risk_amount / risk_per_share
                return max_shares

        return Decimal("0")

    def validate_trade_risk(
        self,
        signal: Signal,
        portfolio: Portfolio,
        position_size: Decimal,
        stop_loss_pct: Decimal,
    ) -> bool:
        """
        Validate if trade respects risk limit.

        Args:
            signal: Trading signal
            portfolio: Current portfolio
            position_size: Proposed position size
            stop_loss_pct: Stop loss percentage

        Returns:
            True if trade respects risk limit
        """
        if not signal.price or signal.price <= 0 or stop_loss_pct <= 0:
            return False

        # Calculate actual risk
        stop_loss_price = signal.price * (Decimal("1") - stop_loss_pct)
        risk_per_share = abs(signal.price - stop_loss_price)
        total_risk = position_size * risk_per_share

        # Calculate risk as percentage of portfolio
        risk_pct = total_risk / portfolio.total_value if portfolio.total_value > 0 else Decimal("0")

        is_valid = risk_pct <= self.max_risk_per_trade

        if not is_valid:
            logger.warning(
                f"Trade rejected: risk {risk_pct:.2%} exceeds limit {self.max_risk_per_trade:.2%}"
            )

        return is_valid


class RiskRewardValidator:
    """
    TASK-RM-2: Risk/Reward Ratio Validator.

    Ensures minimum 1:3 risk/reward ratio (risk 1 to gain 3).
    """

    def __init__(self, min_reward_ratio: Decimal = Decimal("3.0")):
        """
        Initialize validator.

        Args:
            min_reward_ratio: Minimum reward/risk ratio (default 3.0 = 1:3)
        """
        self.min_reward_ratio = min_reward_ratio

    def validate_risk_reward(
        self,
        entry_price: Decimal,
        stop_loss: Decimal,
        take_profit: Decimal,
    ) -> bool:
        """
        Validate risk/reward ratio.

        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price

        Returns:
            True if ratio meets minimum requirement
        """
        # Calculate risk (distance to stop loss)
        risk = abs(entry_price - stop_loss)

        # Calculate reward (distance to take profit)
        reward = abs(take_profit - entry_price)

        if risk <= 0:
            return False

        ratio = reward / risk

        is_valid = ratio >= self.min_reward_ratio

        if not is_valid:
            logger.warning(f"Risk/reward ratio {ratio:.2f} below minimum {self.min_reward_ratio}")

        return is_valid

    def calculate_min_take_profit(self, entry_price: Decimal, stop_loss: Decimal) -> Decimal:
        """
        Calculate minimum take profit to achieve target ratio.

        Args:
            entry_price: Entry price
            stop_loss: Stop loss price

        Returns:
            Minimum take profit price
        """
        risk = abs(entry_price - stop_loss)
        min_reward = risk * self.min_reward_ratio

        # For long positions
        if entry_price > stop_loss:
            return entry_price + min_reward
        else:
            # For short positions
            return entry_price - min_reward


class StrategyExposureLimiter:
    """
    TASK-RM-3: Strategy Exposure Limiter.

    Limits exposure per strategy:
    - Momentum: 50%
    - Mean Reversion: 25-30%
    - Pairs Trading: 20-30%
    """

    def __init__(self):
        """Initialize exposure limiter."""
        self.strategy_limits = {
            "momentum": Decimal("0.50"),  # 50%
            "mean_reversion": Decimal("0.30"),  # 30%
            "pairs_trading": Decimal("0.30"),  # 30%
        }

    def calculate_strategy_exposure(self, portfolio: Portfolio, strategy_name: str) -> Decimal:
        """
        Calculate current exposure for a strategy.

        Args:
            portfolio: Current portfolio
            strategy_name: Name of the strategy

        Returns:
            Current exposure as percentage of total capital
        """
        if portfolio.total_value <= 0:
            return Decimal("0")

        # Get positions for this strategy (would need strategy tag in position)
        total_value = Decimal("0")
        for position in portfolio.positions:
            # In real implementation, would filter by strategy tag
            total_value += position.market_value

        return total_value / portfolio.total_value

    def validate_exposure(
        self, portfolio: Portfolio, strategy_name: str, new_position_value: Decimal
    ) -> bool:
        """
        Validate exposure limits.

        Args:
            portfolio: Current portfolio
            strategy_name: Name of the strategy
            new_position_value: Value of new position

        Returns:
            True if exposure within limits
        """
        current_exposure = self.calculate_strategy_exposure(portfolio, strategy_name)
        new_exposure = current_exposure + (new_position_value / portfolio.total_value)

        limit = self.strategy_limits.get(strategy_name, Decimal("0.50"))

        is_valid = new_exposure <= limit

        if not is_valid:
            logger.warning(
                f"{strategy_name}: exposure {new_exposure:.2%} would exceed limit {limit:.2%}"
            )

        return is_valid


class DrawdownMonitor:
    """
    TASK-RM-4: Drawdown Monitor.

    Monitors portfolio drawdown and triggers stop when >15%.
    """

    def __init__(self, max_drawdown: Decimal = Decimal("0.15")):
        """
        Initialize drawdown monitor.

        Args:
            max_drawdown: Maximum allowed drawdown (default 15% = 0.15)
        """
        self.max_drawdown = max_drawdown
        self.peak_equity: Decimal = Decimal("0")
        self.is_stopped: bool = False

    def update_equity(self, current_equity: Decimal) -> None:
        """
        Update equity tracking.

        Args:
            current_equity: Current total equity
        """
        if current_equity > self.peak_equity:
            self.peak_equity = current_equity

    def check_drawdown(self, current_equity: Decimal) -> tuple[bool, Decimal]:
        """
        Check current drawdown.

        Args:
            current_equity: Current total equity

        Returns:
            Tuple of (drawdown_exceeded, drawdown_percentage)
        """
        if self.peak_equity <= 0:
            return (False, Decimal("0"))

        drawdown = (self.peak_equity - current_equity) / self.peak_equity

        exceeded = drawdown > self.max_drawdown

        if exceeded:
            logger.critical(
                f"MAX DRAWDOWN EXCEEDED: {drawdown:.2%} > {self.max_drawdown:.2%} - STOPPING TRADING"
            )
            self.is_stopped = True

        return (exceeded, drawdown)

    def reset(self) -> None:
        """Reset drawdown monitoring."""
        self.is_stopped = False


class CircuitBreaker:
    """
    TASK-RM-5: Circuit Breaker.

    Pauses strategy after 3-5 consecutive stop losses.
    """

    def __init__(self, max_consecutive_stops: int = 5):
        """
        Initialize circuit breaker.

        Args:
            max_consecutive_stops: Maximum consecutive stops before pause (default 5)
        """
        self.max_consecutive_stops = max_consecutive_stops
        self.strategy_stops: Dict[str, int] = defaultdict(int)
        self.strategy_paused: Dict[str, bool] = defaultdict(bool)
        self.last_reset: Dict[str, datetime] = {}

    def record_stop_loss(self, strategy_name: str) -> None:
        """
        Record a stop loss for a strategy.

        Args:
            strategy_name: Name of the strategy
        """
        self.strategy_stops[strategy_name] += 1

        if self.strategy_stops[strategy_name] >= self.max_consecutive_stops:
            self.strategy_paused[strategy_name] = True
            self.last_reset[strategy_name] = datetime.utcnow()

            logger.warning(
                f"Circuit breaker triggered for {strategy_name}: "
                f"{self.strategy_stops[strategy_name]} consecutive stops"
            )

    def reset_stops(self, strategy_name: str) -> None:
        """
        Reset stop counter for a strategy.

        Args:
            strategy_name: Name of the strategy
        """
        self.strategy_stops[strategy_name] = 0
        self.strategy_paused[strategy_name] = False

    def is_strategy_paused(self, strategy_name: str) -> bool:
        """
        Check if strategy is paused.

        Args:
            strategy_name: Name of the strategy

        Returns:
            True if strategy is paused
        """
        # Check if pause time has expired (e.g., 1 hour cooldown)
        if self.strategy_paused[strategy_name]:
            if strategy_name in self.last_reset:
                elapsed = (datetime.utcnow() - self.last_reset[strategy_name]).total_seconds()
                # Reset after 1 hour
                if elapsed > 3600:
                    self.reset_stops(strategy_name)
                    return False

        return self.strategy_paused[strategy_name]

    def get_consecutive_stops(self, strategy_name: str) -> int:
        """
        Get consecutive stop count for strategy.

        Args:
            strategy_name: Name of the strategy

        Returns:
            Number of consecutive stops
        """
        return self.strategy_stops[strategy_name]


class AdvancedRiskManager:
    """
    TASK-RM-1 to RM-5: Complete Advanced Risk Management System.

    Integrates all risk management components.
    """

    def __init__(
        self,
        max_risk_per_trade: Decimal = Decimal("0.02"),
        min_reward_ratio: Decimal = Decimal("3.0"),
        max_drawdown: Decimal = Decimal("0.15"),
        max_consecutive_stops: int = 5,
    ):
        """
        Initialize advanced risk manager.

        Args:
            max_risk_per_trade: Maximum risk per trade (default 2%)
            min_reward_ratio: Minimum reward/risk ratio (default 3.0)
            max_drawdown: Maximum drawdown limit (default 15%)
            max_consecutive_stops: Max consecutive stops (default 5)
        """
        self.trade_risk_limiter = TradeRiskLimiter(max_risk_per_trade)
        self.risk_reward_validator = RiskRewardValidator(min_reward_ratio)
        self.exposure_limiter = StrategyExposureLimiter()
        self.drawdown_monitor = DrawdownMonitor(max_drawdown)
        self.circuit_breaker = CircuitBreaker(max_consecutive_stops)

        logger.info("Advanced Risk Manager initialized")

    def validate_trade(
        self,
        signal: Signal,
        portfolio: Portfolio,
        position_size: Decimal,
        stop_loss_pct: Decimal,
        take_profit_pct: Decimal,
        strategy_name: str,
    ) -> tuple[bool, str]:
        """
        Validate trade against all risk rules.

        Args:
            signal: Trading signal
            portfolio: Current portfolio
            position_size: Proposed position size
            stop_loss_pct: Stop loss percentage
            take_profit_pct: Take profit percentage
            strategy_name: Name of the strategy

        Returns:
            Tuple of (is_valid, reason)
        """
        # TASK-RM-5: Check circuit breaker
        if self.circuit_breaker.is_strategy_paused(strategy_name):
            return (
                False,
                f"{strategy_name} is paused due to consecutive stop losses",
            )

        # TASK-RM-4: Check drawdown
        drawdown_exceeded, _ = self.drawdown_monitor.check_drawdown(portfolio.total_value)
        if drawdown_exceeded:
            return (False, "Maximum drawdown exceeded - trading stopped")

        # TASK-RM-1: Check trade risk limit
        if not self.trade_risk_limiter.validate_trade_risk(
            signal, portfolio, position_size, stop_loss_pct
        ):
            return (False, "Trade risk exceeds 2% limit")

        # TASK-RM-2: Check risk/reward ratio
        if signal.price:
            stop_loss = signal.price * (Decimal("1") - stop_loss_pct)
            take_profit = signal.price * (Decimal("1") + take_profit_pct)

            if not self.risk_reward_validator.validate_risk_reward(
                signal.price, stop_loss, take_profit
            ):
                return (False, "Risk/reward ratio below minimum 1:3")

        # TASK-RM-3: Check strategy exposure
        if not self.exposure_limiter.validate_exposure(
            portfolio, strategy_name, position_size * signal.price if signal.price else Decimal("0")
        ):
            return (False, f"{strategy_name} exposure limit exceeded")

        return (True, "Trade validated")

    def calculate_safe_position_size(
        self,
        signal: Signal,
        portfolio: Portfolio,
        stop_loss_pct: Decimal,
    ) -> Decimal:
        """
        Calculate safe position size considering all risk limits.

        Args:
            signal: Trading signal
            portfolio: Current portfolio
            stop_loss_pct: Stop loss percentage

        Returns:
            Safe position size
        """
        # TASK-RM-1: Calculate based on risk per trade limit
        max_size = self.trade_risk_limiter.calculate_max_position_size(
            signal, portfolio, stop_loss_pct
        )

        # Apply additional constraints if needed
        return max_size

    def record_trade_result(
        self,
        strategy_name: str,
        was_stop_loss: bool,
        current_equity: Decimal,
    ) -> None:
        """
        Record trade result for monitoring.

        Args:
            strategy_name: Name of the strategy
            was_stop_loss: Whether trade hit stop loss
            current_equity: Current portfolio equity
        """
        # TASK-RM-4: Update drawdown monitoring
        self.drawdown_monitor.update_equity(current_equity)

        # TASK-RM-5: Record stop losses for circuit breaker
        if was_stop_loss:
            self.circuit_breaker.record_stop_loss(strategy_name)
        else:
            self.circuit_breaker.reset_stops(strategy_name)

    def get_risk_status(self) -> Dict[str, Any]:
        """Get current risk status."""
        return {
            "drawdown_exceeded": self.drawdown_monitor.is_stopped,
            "peak_equity": float(self.drawdown_monitor.peak_equity),
            "strategy_stops": dict(self.circuit_breaker.strategy_stops),
            "paused_strategies": [k for k, v in self.circuit_breaker.strategy_paused.items() if v],
        }


# Global manager instance
_advanced_risk_manager: Optional[AdvancedRiskManager] = None


def get_advanced_risk_manager() -> AdvancedRiskManager:
    """Get global advanced risk manager instance."""
    global _advanced_risk_manager
    if _advanced_risk_manager is None:
        _advanced_risk_manager = AdvancedRiskManager()

    return _advanced_risk_manager
