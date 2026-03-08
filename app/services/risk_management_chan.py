"""
Risk Management - Ernest Chan Methodologies

This module implements Ernest Chan's risk management methodologies from
"Algorithmic Trading: A Practitioner's Guide".

Key Concepts:
1. Stop-loss placement strategies
2. Maximum drawdown limits
3. Position sizing with risk limits
4. Kelly Criterion application
5. Risk parity and portfolio risk management

Reference:
    "Algorithmic Trading" by Ernest P. Chan (2013)
    Chapter 6: Risk Management
    Chapter 7: Position Sizing
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import pandas as pd

from app.shared.config.centralized_config import get_config

logger = logging.getLogger(__name__)


@dataclass
class StopLossResult:
    """Result from stop-loss calculation."""

    stop_loss_price: float
    stop_loss_distance: float
    stop_loss_percentage: float
    method_used: str
    risk_amount: float
    reason: str


@dataclass
class PositionSizeResult:
    """Result from position sizing calculation."""

    shares: int
    dollar_amount: float
    risk_amount: float
    risk_percentage: float
    kelly_fraction: Optional[float] = None
    method_used: str = ""


@dataclass
class RiskMetrics:
    """Risk metrics for a portfolio or strategy."""

    daily_var_95: float  # Value at Risk at 95% confidence
    daily_cvar_95: float  # Conditional VaR at 95% confidence
    max_drawdown: float
    max_drawdown_duration: int
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    risk_of_ruin: float


class ChanStopLossCalculator:
    """
    Stop-loss placement strategies per Ernest Chan.

    Chan's methods:
    1. ATR-based stops (adaptive to volatility)
    2. Multiple of ATR (typically 2-3x)
    3. Fixed percentage stops (simple but less effective)
    4. Time-based stops (exit if no movement after N periods)
    """

    def __init__(
        self,
        atr_multiplier: float = None,
        fixed_stop_pct: float = None,
    ):
        """
        Initialize stop-loss calculator.

        Args:
            atr_multiplier: Multiplier for ATR-based stops (uses config if None)
            fixed_stop_pct: Fixed percentage for simple stops (uses config if None)
        """
        # Get defaults from config
        config = get_config()
        self.atr_multiplier = (
            float(getattr(config.trading, 'chan_atr_multiplier', 2.0))
            if atr_multiplier is None
            else float(atr_multiplier)
        )
        self.fixed_stop_pct = (
            float(getattr(config.trading, 'chan_fixed_stop_pct', 0.05))
            if fixed_stop_pct is None
            else float(fixed_stop_pct)
        )

    def calculate_atr_stop_loss(
        self,
        entry_price: float,
        atr: float,
        direction: str = "long",
        multiplier: Optional[float] = None,
    ) -> StopLossResult:
        """
        Calculate ATR-based stop loss.

        Ernest Chan's formula:
        stop_loss = entry_price ± (ATR * multiplier)

        For long: stop_loss = entry_price - (ATR * multiplier)
        For short: stop_loss = entry_price + (ATR * multiplier)

        Args:
            entry_price: Entry price of the trade
            atr: Average True Range value
            direction: 'long' or 'short'
            multiplier: Optional custom multiplier (defaults to instance value)

        Returns:
            StopLossResult with stop price and risk metrics

        Examples:
            >>> calc = ChanStopLossCalculator()
            >>> result = calc.calculate_atr_stop_loss(100.0, 2.5, "long")
            >>> print(f"Stop loss: ${result.stop_loss_price:.2f}")
        """
        try:
            mult = multiplier or self.atr_multiplier
            stop_distance = atr * mult

            if direction.lower() == "long":
                stop_loss_price = entry_price - stop_distance
            elif direction.lower() == "short":
                stop_loss_price = entry_price + stop_distance
            else:
                raise ValueError(f"Invalid direction: {direction}")

            stop_pct = stop_distance / entry_price if entry_price > 0 else 0

            return StopLossResult(
                stop_loss_price=float(stop_loss_price),
                stop_loss_distance=float(stop_distance),
                stop_loss_percentage=float(stop_pct),
                method_used="ATR-based",
                risk_amount=float(stop_distance),
                reason=f"ATR ({atr:.2f}) * multiplier ({mult:.1f}) = ${stop_distance:.2f}",
            )

        except (ValueError, TypeError) as e:
            logger.error(f"Error calculating ATR stop loss: {e}")
            return StopLossResult(
                stop_loss_price=entry_price * (1 - self.fixed_stop_pct),
                stop_loss_distance=entry_price * self.fixed_stop_pct,
                stop_loss_percentage=float(self.fixed_stop_pct),
                method_used="Fixed (fallback)",
                risk_amount=entry_price * self.fixed_stop_pct,
                reason="Calculation error, using fixed stop",
            )

    def calculate_fixed_percentage_stop(
        self,
        entry_price: float,
        direction: str = "long",
        stop_pct: Optional[float] = None,
    ) -> StopLossResult:
        """
        Calculate fixed percentage stop loss.

        Ernest Chan notes this is simpler but less adaptive than ATR-based stops.

        Args:
            entry_price: Entry price
            direction: 'long' or 'short'
            stop_pct: Optional custom stop percentage

        Returns:
            StopLossResult with stop price
        """
        try:
            pct = stop_pct or self.fixed_stop_pct

            if direction.lower() == "long":
                stop_loss_price = entry_price * (1 - pct)
            elif direction.lower() == "short":
                stop_loss_price = entry_price * (1 + pct)
            else:
                raise ValueError(f"Invalid direction: {direction}")

            stop_distance = abs(entry_price - stop_loss_price)

            return StopLossResult(
                stop_loss_price=float(stop_loss_price),
                stop_loss_distance=float(stop_distance),
                stop_loss_percentage=float(pct),
                method_used="Fixed percentage",
                risk_amount=float(stop_distance),
                reason=f"Fixed {pct:.1%} stop loss",
            )

        except (ValueError, TypeError) as e:
            logger.error(f"Error calculating fixed stop loss: {e}")
            # Get fallback stop percentage from config
            config = get_config()
            fallback_stop = float(getattr(config.trading, 'stop_loss_pct', 0.05))
            return StopLossResult(
                stop_loss_price=entry_price * (1 - fallback_stop),
                stop_loss_distance=entry_price * fallback_stop,
                stop_loss_percentage=fallback_stop,
                method_used="Fixed (fallback)",
                risk_amount=entry_price * fallback_stop,
                reason="Calculation error",
            )

    def calculate_trailing_stop(
        self,
        current_price: float,
        highest_price_since_entry: float,
        atr: float,
        direction: str = "long",
        multiplier: Optional[float] = None,
    ) -> StopLossResult:
        """
        Calculate trailing stop loss.

        Ernest Chan's trailing stop formula:
        stop = highest_price - (ATR * multiplier)

        The stop trails upward as price moves in favor.

        Args:
            current_price: Current market price
            highest_price_since_entry: Highest favorable price since entry
            atr: Current ATR value
            direction: 'long' or 'short'
            multiplier: Optional custom multiplier

        Returns:
            StopLossResult with trailing stop price
        """
        try:
            mult = multiplier or self.atr_multiplier

            if direction.lower() == "long":
                stop_loss_price = highest_price_since_entry - (atr * mult)
            elif direction.lower() == "short":
                lowest_price_since_entry = (
                    highest_price_since_entry  # For shorts, this is the lowest
                )
                stop_loss_price = lowest_price_since_entry + (atr * mult)
            else:
                raise ValueError(f"Invalid direction: {direction}")

            stop_distance = abs(highest_price_since_entry - stop_loss_price)
            stop_pct = (
                stop_distance / highest_price_since_entry if highest_price_since_entry > 0 else 0
            )

            return StopLossResult(
                stop_loss_price=float(stop_loss_price),
                stop_loss_distance=float(stop_distance),
                stop_loss_percentage=float(stop_pct),
                method_used="Trailing ATR",
                risk_amount=float(stop_distance),
                reason=f"Trailing stop from high ${highest_price_since_entry:.2f}",
            )

        except (ValueError, TypeError) as e:
            logger.error(f"Error calculating trailing stop: {e}")
            # Get fallback stop percentage from config
            config = get_config()
            fallback_stop = float(getattr(config.trading, 'stop_loss_pct', 0.05))
            return StopLossResult(
                stop_loss_price=current_price * (1 - fallback_stop),
                stop_loss_distance=current_price * fallback_stop,
                stop_loss_percentage=fallback_stop,
                method_used="Fixed (fallback)",
                risk_amount=current_price * fallback_stop,
                reason="Calculation error",
            )


class ChanPositionSizer:
    """
    Position sizing methods per Ernest Chan.

    Chan's methods:
    1. Risk-based sizing (fixed % of capital at risk)
    2. Kelly Criterion sizing (optimal growth)
    3. Volatility-adjusted sizing (size inversely proportional to volatility)
    4. Maximum drawdown constraints
    """

    def __init__(
        self,
        risk_per_trade: float = None,
        max_position_pct: float = None,
    ):
        """
        Initialize position sizer.

        Args:
            risk_per_trade: Maximum % of capital to risk per trade (uses config if None)
            max_position_pct: Maximum position size as % of capital (uses config if None)
        """
        # Get defaults from config
        config = get_config()
        self.risk_per_trade = (
            float(getattr(config.trading, 'max_risk_per_trade', 0.02))
            if risk_per_trade is None
            else float(risk_per_trade)
        )
        self.max_position_pct = (
            float(getattr(config.trading, 'max_position_size', 0.25))
            if max_position_pct is None
            else float(max_position_pct)
        )

    def calculate_risk_based_position(
        self,
        capital: float,
        entry_price: float,
        stop_loss_price: float,
        risk_per_trade: Optional[float] = None,
    ) -> PositionSizeResult:
        """
        Calculate position size based on risk.

        Ernest Chan's formula:
        risk_amount = capital * risk_per_trade
        shares = risk_amount / (entry_price - stop_loss_price)

        Args:
            capital: Total capital available
            entry_price: Entry price
            stop_loss_price: Stop loss price
            risk_per_trade: Optional custom risk percentage

        Returns:
            PositionSizeResult with shares and dollar amount

        Examples:
            >>> sizer = ChanPositionSizer()
            >>> result = sizer.calculate_risk_based_position(100000, 100, 95)
            >>> print(f"Buy {result.shares} shares (${result.dollar_amount:.2f})")
        """
        try:
            risk_pct = risk_per_trade or self.risk_per_trade

            # Calculate risk amount
            risk_amount = capital * risk_pct

            # Calculate risk per share
            risk_per_share = abs(entry_price - stop_loss_price)

            if risk_per_share == 0:
                logger.warning("Stop loss equals entry price, using minimum position")
                # Get minimum position size from config
                config = get_config()
                min_pos_pct = float(getattr(config.trading, 'min_position_size', 0.01))
                risk_per_share = entry_price * min_pos_pct

            # Calculate shares
            shares = int(risk_amount / risk_per_share)

            # Calculate dollar amount
            dollar_amount = shares * entry_price

            # Check against maximum position size
            max_dollar = capital * self.max_position_pct
            if dollar_amount > max_dollar:
                shares = int(max_dollar / entry_price)
                dollar_amount = shares * entry_price
                logger.info(f"Position size capped at max {self.max_position_pct:.1%} of capital")

            return PositionSizeResult(
                shares=shares,
                dollar_amount=float(dollar_amount),
                risk_amount=float(risk_amount),
                risk_percentage=float(risk_pct),
                method_used="Risk-based",
            )

        except (ValueError, ZeroDivisionError) as e:
            logger.error(f"Error calculating risk-based position: {e}")
            return PositionSizeResult(
                shares=0,
                dollar_amount=0.0,
                risk_amount=0.0,
                risk_percentage=0.0,
                method_used="Error",
            )

    def calculate_kelly_position(
        self,
        capital: float,
        entry_price: float,
        stop_loss_price: float,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        kelly_fraction: float = 0.5,  # Half-Kelly for safety
    ) -> PositionSizeResult:
        """
        Calculate position size using Kelly Criterion.

        Ernest Chan's Kelly formula:
        f* = (win_rate * avg_win - loss_rate * avg_loss) / avg_win

        For safety, Chan recommends using half-Kelly (f* / 2)

        Args:
            capital: Total capital available
            entry_price: Entry price
            stop_loss_price: Stop loss price
            win_rate: Historical win rate (0-1)
            avg_win: Average winning trade amount
            avg_loss: Average losing trade amount (positive)
            kelly_fraction: Fraction of full Kelly to use (default: 0.5 = half-Kelly)

        Returns:
            PositionSizeResult with Kelly-optimized position

        Examples:
            >>> sizer = ChanPositionSizer()
            >>> result = sizer.calculate_kelly_position(
            >>>     100000, 100, 95,
            >>>     win_rate=0.55, avg_win=5.0, avg_loss=3.0
            >>> )
        """
        try:
            # Calculate Kelly fraction
            loss_rate = 1 - win_rate

            if avg_win == 0:
                logger.warning("Average win is zero, cannot calculate Kelly")
                return PositionSizeResult(
                    shares=0,
                    dollar_amount=0.0,
                    risk_amount=0.0,
                    risk_percentage=0.0,
                    kelly_fraction=0.0,
                    method_used="Kelly (failed)",
                )

            # Full Kelly formula
            full_kelly = (win_rate * avg_win - loss_rate * avg_loss) / avg_win

            # Apply safety fraction (typically half-Kelly)
            kelly_f = full_kelly * kelly_fraction

            # Calculate position size
            dollar_amount = capital * max(0, kelly_f)
            shares = int(dollar_amount / entry_price)

            # Calculate risk amount
            risk_per_share = abs(entry_price - stop_loss_price)
            risk_amount = shares * risk_per_share

            return PositionSizeResult(
                shares=shares,
                dollar_amount=float(dollar_amount),
                risk_amount=float(risk_amount),
                risk_percentage=float(risk_amount / capital if capital > 0 else 0),
                kelly_fraction=float(kelly_f),
                method_used=f"Kelly ({kelly_fraction:.0%} of full)",
            )

        except (ValueError, ZeroDivisionError) as e:
            logger.error(f"Error calculating Kelly position: {e}")
            return PositionSizeResult(
                shares=0,
                dollar_amount=0.0,
                risk_amount=0.0,
                risk_percentage=0.0,
                kelly_fraction=0.0,
                method_used="Kelly (error)",
            )

    def calculate_volatility_adjusted_position(
        self,
        capital: float,
        entry_price: float,
        stop_loss_price: float,
        volatility: float,
        target_risk: float = None,
    ) -> PositionSizeResult:
        """
        Calculate position size adjusted for volatility.

        Ernest Chan's approach:
        - Higher volatility = smaller position
        - Lower volatility = larger position
        - Target constant risk across trades

        Args:
            capital: Total capital
            entry_price: Entry price
            stop_loss_price: Stop loss price
            volatility: Current volatility (std dev of returns)
            target_risk: Target risk amount as % of capital (uses config if None)

        Returns:
            PositionSizeResult with volatility-adjusted size
        """
        # Get default target risk from config
        if target_risk is None:
            config = get_config()
            target_risk = float(getattr(config.trading, 'max_risk_per_trade', 0.02))
        try:
            # Base position on risk
            base_result = self.calculate_risk_based_position(
                capital=capital,
                entry_price=entry_price,
                stop_loss_price=stop_loss_price,
                risk_per_trade=target_risk,
            )

            # Adjust for volatility
            # Get high volatility threshold from config
            config = get_config()
            # volatility_threshold_extreme is stored as a percentage (50.0 = 50%), convert to decimal
            high_volatility_threshold = (
                float(getattr(config.trading, 'volatility_threshold_extreme', 50.0)) / 100.0
            )

            # If volatility is high (above threshold), reduce position
            vol_adjustment = (
                min(1.0, high_volatility_threshold / volatility) if volatility > 0 else 1.0
            )

            adjusted_shares = int(base_result.shares * vol_adjustment)
            adjusted_dollar_amount = adjusted_shares * entry_price

            return PositionSizeResult(
                shares=adjusted_shares,
                dollar_amount=float(adjusted_dollar_amount),
                risk_amount=float(adjusted_shares * abs(entry_price - stop_loss_price)),
                risk_percentage=float(target_risk * vol_adjustment),
                method_used=f"Volatility-adjusted ({vol_adjustment:.2f}x base)",
            )

        except (ValueError, ZeroDivisionError) as e:
            logger.error(f"Error calculating volatility-adjusted position: {e}")
            return PositionSizeResult(
                shares=0,
                dollar_amount=0.0,
                risk_amount=0.0,
                risk_percentage=0.0,
                method_used="Volatility-adjusted (error)",
            )


class ChanDrawdownController:
    """
    Maximum drawdown controller per Ernest Chan.

    Chan's methodology:
    1. Set maximum acceptable drawdown
    2. Reduce position sizes as drawdown increases
    3. Stop trading if maximum drawdown exceeded
    4. Scale back in gradually after drawdown

    Uses centralized configuration for thresholds.
    """

    def __init__(
        self,
        max_drawdown: float = None,
        peak_equity: float = 100000.0,
    ):
        """
        Initialize drawdown controller.

        Args:
            max_drawdown: Maximum acceptable drawdown (0-1, uses config if None)
            peak_equity: Starting peak equity
        """
        # Get max drawdown from config if not provided
        if max_drawdown is None:
            config = get_config()
            max_drawdown = config.trading.max_drawdown_limit

        self.max_drawdown = max_drawdown
        self.peak_equity = peak_equity
        self.current_equity = peak_equity
        self.is_trading_halted = False

        # Drawdown levels for position reduction (from config)
        config = get_config()
        self.drawdown_reduction_levels = {
            config.trading.max_drawdown_limit * 0.4: 0.75,  # At 40% of max DD, reduce to 75% size
            config.trading.max_drawdown_limit * 0.6: 0.50,  # At 60% of max DD, reduce to 50% size
            config.trading.max_drawdown_limit * 0.8: 0.25,  # At 80% of max DD, reduce to 25% size
        }

    def update_equity(self, new_equity: float) -> None:
        """
        Update equity and track peak.

        Args:
            new_equity: Current equity value
        """
        self.current_equity = new_equity
        if new_equity > self.peak_equity:
            self.peak_equity = new_equity

    def get_current_drawdown(self) -> float:
        """Calculate current drawdown."""
        if self.peak_equity <= 0:
            return 0.0
        return (self.peak_equity - self.current_equity) / self.peak_equity

    def should_halt_trading(self) -> bool:
        """
        Check if trading should be halted due to excessive drawdown.

        Returns:
            True if maximum drawdown exceeded
        """
        current_dd = self.get_current_drawdown()
        self.is_trading_halted = current_dd >= self.max_drawdown

        if self.is_trading_halted:
            logger.warning(
                f"Trading halted: Maximum drawdown exceeded "
                f"({current_dd:.1%} >= {self.max_drawdown:.1%})"
            )

        return self.is_trading_halted

    def get_position_size_multiplier(self) -> float:
        """
        Calculate position size multiplier based on current drawdown.

        Returns:
            Multiplier to apply to base position sizes (0-1)
        """
        if self.is_trading_halted:
            return 0.0

        current_dd = self.get_current_drawdown()

        # Find the appropriate reduction level
        for dd_threshold, multiplier in sorted(self.drawdown_reduction_levels.items()):
            if current_dd >= dd_threshold:
                return multiplier

        return 1.0  # No reduction

    def calculate_risk_of_ruin(
        self,
        win_rate: float,
        avg_win: float,
        avg_loss: float,
        capital_units: int = 100,
    ) -> float:
        """
        Calculate risk of ruin per Ernest Chan.

        Risk of ruin formula (approximation):
        RoR = ((1 - edge) / (1 + edge))^capital_units

        where edge = (win_rate * avg_win - loss_rate * avg_loss) / avg_win

        Args:
            win_rate: Win rate (0-1)
            avg_win: Average winning trade
            avg_loss: Average losing trade (positive)
            capital_units: Number of "risk units" in account

        Returns:
            Risk of ruin (0-1)
        """
        try:
            loss_rate = 1 - win_rate
            edge = (win_rate * avg_win - loss_rate * avg_loss) / avg_win if avg_win > 0 else 0

            if edge <= 0:
                return 1.0  # Certain ruin with negative or zero edge

            # Risk of ruin calculation
            numerator = (1 - edge) / (1 + edge)
            risk_of_ruin = numerator**capital_units

            return float(risk_of_ruin)

        except (ValueError, ZeroDivisionError):
            return 1.0


class ChanRiskMetrics:
    """
    Risk metrics calculator per Ernest Chan.

    Calculates comprehensive risk metrics for strategy evaluation.
    """

    def __init__(self, confidence_level: float = 0.95):
        """
        Initialize risk metrics calculator.

        Args:
            confidence_level: Confidence level for VaR calculation
        """
        self.confidence_level = confidence_level

    def calculate_all_metrics(
        self,
        returns: pd.Series,
        equity_curve: Optional[pd.Series] = None,
        risk_free_rate: float = None,
    ) -> RiskMetrics:
        """
        Calculate all risk metrics.

        Args:
            returns: Return series
            equity_curve: Optional equity curve for drawdown calculation
            risk_free_rate: Annual risk-free rate (uses config if None)

        Returns:
            RiskMetrics with all calculated metrics
        """
        # Get default risk-free rate from config
        if risk_free_rate is None:
            config = get_config()
            risk_free_rate = float(getattr(config.trading, 'portfolio_risk_free_rate', 0.02))
        try:
            returns_clean = returns.dropna()

            # VaR and CVaR
            daily_var_95 = self._calculate_var(returns_clean, 0.95)
            daily_cvar_95 = self._calculate_cvar(returns_clean, 0.95)

            # Drawdown
            if equity_curve is not None:
                max_dd, max_dd_duration = self._calculate_max_drawdown(equity_curve)
            else:
                max_dd = self._calculate_max_drawdown_from_returns(returns_clean)
                max_dd_duration = 0

            # Risk-adjusted returns
            sharpe = self._calculate_sharpe(returns_clean, risk_free_rate)
            sortino = self._calculate_sortino(returns_clean, risk_free_rate)

            # Calmar ratio
            if max_dd != 0:
                annual_return = returns_clean.mean() * 252
                calmar = annual_return / abs(max_dd)
            else:
                calmar = 0.0

            # Risk of ruin (simplified - uses win rate from returns)
            win_rate = (returns_clean > 0).mean()
            avg_win = returns_clean[returns_clean > 0].mean() if win_rate > 0 else 0
            avg_loss = abs(returns_clean[returns_clean < 0].mean()) if win_rate < 1 else 0

            controller = ChanDrawdownController()
            risk_of_ruin = controller.calculate_risk_of_ruin(
                win_rate=float(win_rate),
                avg_win=float(avg_win),
                avg_loss=float(avg_loss),
                capital_units=100,
            )

            return RiskMetrics(
                daily_var_95=float(daily_var_95),
                daily_cvar_95=float(daily_cvar_95),
                max_drawdown=float(max_dd),
                max_drawdown_duration=int(max_dd_duration),
                sharpe_ratio=float(sharpe),
                sortino_ratio=float(sortino),
                calmar_ratio=float(calmar),
                risk_of_ruin=float(risk_of_ruin),
            )

        except (ValueError, TypeError) as e:
            logger.error(f"Error calculating risk metrics: {e}")
            return RiskMetrics(
                daily_var_95=0.0,
                daily_cvar_95=0.0,
                max_drawdown=0.0,
                max_drawdown_duration=0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                calmar_ratio=0.0,
                risk_of_ruin=1.0,
            )

    def _calculate_var(self, returns: pd.Series, confidence: float) -> float:
        """Calculate Value at Risk."""
        try:
            return float(np.percentile(returns, (1 - confidence) * 100))
        except (ValueError, IndexError):
            return 0.0

    def _calculate_cvar(self, returns: pd.Series, confidence: float) -> float:
        """Calculate Conditional VaR (Expected Shortfall)."""
        try:
            var = self._calculate_var(returns, confidence)
            return float(returns[returns <= var].mean())
        except (ValueError, IndexError):
            return 0.0

    def _calculate_max_drawdown(self, equity_curve: pd.Series) -> Tuple[float, int]:
        """Calculate maximum drawdown and duration."""
        try:
            rolling_max = equity_curve.expanding().max()
            drawdown = (equity_curve - rolling_max) / rolling_max

            max_dd = drawdown.min()

            # Find duration of max drawdown
            max_dd_idx = drawdown.idxmin()
            peak_idx = (equity_curve[:max_dd_idx]).idxmax()
            duration = (max_dd_idx - peak_idx).days if hasattr(max_dd_idx, 'days') else 0

            return float(max_dd), int(duration)

        except (ValueError, KeyError):
            return 0.0, 0

    def _calculate_max_drawdown_from_returns(self, returns: pd.Series) -> float:
        """Calculate max drawdown from returns series."""
        try:
            cumulative = (1 + returns).cumprod()
            rolling_max = cumulative.expanding().max()
            drawdown = (cumulative - rolling_max) / rolling_max
            return float(drawdown.min())
        except (ValueError, KeyError):
            return 0.0

    def _calculate_sharpe(self, returns: pd.Series, risk_free_rate: float) -> float:
        """Calculate Sharpe ratio."""
        try:
            excess_returns = returns - risk_free_rate / 252
            return float(excess_returns.mean() / excess_returns.std() * np.sqrt(252))
        except (ValueError, ZeroDivisionError):
            return 0.0

    def _calculate_sortino(self, returns: pd.Series, risk_free_rate: float) -> float:
        """Calculate Sortino ratio."""
        try:
            excess_returns = returns - risk_free_rate / 252
            downside_returns = excess_returns[excess_returns < 0]
            downside_std = downside_returns.std()

            if downside_std == 0:
                return 0.0

            return float(excess_returns.mean() / downside_std * np.sqrt(252))
        except (ValueError, ZeroDivisionError):
            return 0.0


def calculate_optimal_stop_loss(
    entry_price: float,
    atr: float,
    direction: str = "long",
    method: str = "atr",
) -> StopLossResult:
    """
    Convenience function to calculate optimal stop loss.

    Args:
        entry_price: Entry price
        atr: ATR value
        direction: 'long' or 'short'
        method: 'atr', 'fixed', or 'trailing'

    Returns:
        StopLossResult with optimal stop loss
    """
    calculator = ChanStopLossCalculator()

    if method == "atr":
        return calculator.calculate_atr_stop_loss(entry_price, atr, direction)
    elif method == "fixed":
        return calculator.calculate_fixed_percentage_stop(entry_price, direction)
    else:
        return calculator.calculate_atr_stop_loss(entry_price, atr, direction)


def calculate_optimal_position_size(
    capital: float,
    entry_price: float,
    stop_loss_price: float,
    method: str = "risk_based",
    **kwargs,
) -> PositionSizeResult:
    """
    Convenience function to calculate optimal position size.

    Args:
        capital: Total capital
        entry_price: Entry price
        stop_loss_price: Stop loss price
        method: 'risk_based', 'kelly', or 'volatility_adjusted'
        **kwargs: Additional parameters for specific methods

    Returns:
        PositionSizeResult with optimal size
    """
    sizer = ChanPositionSizer()

    if method == "risk_based":
        return sizer.calculate_risk_based_position(capital, entry_price, stop_loss_price)
    elif method == "kelly":
        return sizer.calculate_kelly_position(
            capital,
            entry_price,
            stop_loss_price,
            kwargs.get("win_rate", 0.5),
            kwargs.get("avg_win", 1.0),
            kwargs.get("avg_loss", 1.0),
            kwargs.get("kelly_fraction", 0.5),
        )
    elif method == "volatility_adjusted":
        # Get default volatility from config if not provided
        config = get_config()
        default_vol = float(getattr(config.trading, 'pairs_trading_default_volatility', 0.02))
        return sizer.calculate_volatility_adjusted_position(
            capital,
            entry_price,
            stop_loss_price,
            kwargs.get("volatility", default_vol),
        )
    else:
        return sizer.calculate_risk_based_position(capital, entry_price, stop_loss_price)
